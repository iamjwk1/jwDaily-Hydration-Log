/* jwDaily Hydration Log v1.1.0-beta.2 - independent Home Assistant Lovelace card.
 * Derived from Personal Hydration Manager (MIT), Copyright (c) 2026 Loryan Strant.
 * Copyright (c) 2026 jwDaily Hydration Log contributors (modifications).
 */
const JDHL_TAG='jwdaily-hydration-log-card';
const JDHL_EDITOR=`${JDHL_TAG}-editor`;
const JDHL_TYPES=[['water','Water','💧'],['coffee','Coffee','☕'],['tea','Tea','🍵'],['milk','Milk','🥛'],['soup','Soup','🍲'],['other','Other','◯']];
const JDHL_LABEL=Object.fromEntries(JDHL_TYPES.map(([k,n])=>[k,n]));
const JDHL_DEFAULTS={profile:'',title:'',show_title:true,show_cup:true,show_manual:true,
 show_history:true,show_export:true,unit:'mL',quick_add:[120,150,300,500]};
const jdhlEscape=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const jdhlNum=v=>Number.isFinite(Number(v))?Number(v):0;
const jdhlQuick=a=>{const n=(Array.isArray(a)?a:[]).map(Number).filter(v=>Number.isFinite(v)&&v>0&&v<=100000);return n.length?n:[120,150,300,500];};
const jdhlOz=29.5735;
const jdhlFmt=(n,u='mL')=>u==='fl_oz'?`${(n/jdhlOz).toFixed(1)} fl oz`:n>=1000?`${(n/1000).toFixed(2)} L`:`${Number(n.toFixed(1))} mL`;
const jdhlDate=d=>`${String(d.getDate()).padStart(2,'0')}-${String(d.getMonth()+1).padStart(2,'0')}-${d.getFullYear()}`;
const jdhlIsoDate=d=>`${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`;
const jdhlDateToIso=v=>/^\d{2}-\d{2}-\d{4}$/.test(v)?`${v.slice(6)}-${v.slice(3,5)}-${v.slice(0,2)}`:null;
const jdhlIsoToDate=v=>/^\d{4}-\d{2}-\d{2}$/.test(v)?`${v.slice(8)}-${v.slice(5,7)}-${v.slice(0,4)}`:null;

class JwDailyHydrationLogCard extends HTMLElement {
 constructor(){
  super();this.attachShadow({mode:'open'});
  this._hass=null;this._config=null;this._history=null;this._viewDate=null;
  this._selectedType=null;this._selectedVolume=null;this._undoId=null;this._modal=null;this._confirmDelete=false;
  this._manageOpen=false;this._customDraft=null;this._glassPrevY=179;
  this._busy=false;this._error='';this._status='';this._lastState='';this._lastRender='';
  this._fetching=false;this._fetchAgain=false;this._tickTimer=null;
  this.shadowRoot.addEventListener('click',e=>this._click(e));
  this.shadowRoot.addEventListener('input',e=>this._field(e));
  this.shadowRoot.addEventListener('change',e=>this._field(e));
  this.shadowRoot.addEventListener('keydown',e=>{
   if(e.key==='Escape'&&this._modal){this._modal=null;this._confirmDelete=false;this._render(true);}
   if(e.key==='Enter'&&e.target?.dataset?.action==='edit'){e.preventDefault();this._openEdit(e.target.dataset.id);}
  });
 }
 static getStubConfig(hass){
  const p=Object.keys(hass?.states||{}).find(x=>x.startsWith('sensor.jwdhl_')&&x.endsWith('_daily_target'));
  return {type:`custom:${JDHL_TAG}`,profile:p?p.slice('sensor.jwdhl_'.length,-'_daily_target'.length):'',
   title:'Vocht intake',show_title:true,show_cup:true,show_manual:true,show_history:true,show_export:true,unit:'mL',quick_add:[120,150,300,500]};
 }
 static async getConfigElement(){return document.createElement(JDHL_EDITOR);}
 setConfig(config){if(!config)throw Error('Missing card configuration');
  this._config={...JDHL_DEFAULTS,...config,quick_add:jdhlQuick(config.quick_add)};
  this._selectedType=null;this._selectedVolume=null;this._undoId=null;this._modal=null;this._viewDate=null;
  this._manageOpen=false;this._customDraft=null;this._glassPrevY=179;
  this._history=null;this._lastState='';this._lastRender='';this._render(true);this._fetchHistory();
 }
 set hass(h){this._hass=h;
  const p=this._config?.profile;
  if(p){const manual=h?.states?.[`sensor.jwdhl_${p}_manual_consumed`];const count=h?.states?.[`sensor.jwdhl_${p}_drink_count_today`];
   const key=JSON.stringify([manual?.attributes?.manual_consumed_ml,count?.state,this._todayISO()]);
   if(key!==this._lastState){this._lastState=key;this._fetchHistory();}}
  this._render();
  if(!this._tickTimer){this._tickTimer=setInterval(()=>{if(this._hass&&this._config){
   const key=this._todayISO();if(this._lastDateKey!==key){this._lastDateKey=key;this._fetchHistory();}
  }},30000);}
 }
 disconnectedCallback(){if(this._tickTimer){clearInterval(this._tickTimer);this._tickTimer=null;}}
 getCardSize(){return 5;}
 _nowLocal(){
  const tz=this._hass?.config?.time_zone;
  const date=new Date();
  if(!tz)return date;
  try{
   const parts=new Intl.DateTimeFormat('en-GB',{timeZone:tz,year:'numeric',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',second:'2-digit',hourCycle:'h23'}).formatToParts(date);
   const v=Object.fromEntries(parts.map(x=>[x.type,x.value]));
   return new Date(Number(v.year),Number(v.month)-1,Number(v.day),Number(v.hour),Number(v.minute),Number(v.second));
  }catch{return date;}
 }
 _todayISO(){return jdhlIsoDate(this._nowLocal());}
 _todayPretty(){return jdhlDate(this._nowLocal());}
 _nowTime(){const d=this._nowLocal();return `${String(d.getHours()).padStart(2,'0')}:${String(d.getMinutes()).padStart(2,'0')}:${String(d.getSeconds()).padStart(2,'0')}`;}
 _state(k){return this._hass?.states?.[`sensor.jwdhl_${this._config.profile}_${k}`];}
 _millilitres(k,attr){const e=this._state(k);if(!e)return 0;
  const exact=e.attributes?.[attr];if(exact!==null&&exact!==undefined&&Number.isFinite(Number(exact)))return Number(exact);
  const val=jdhlNum(e.state),unit=e.attributes?.unit_of_measurement;
  return unit==='L'?val*1000:unit==='fl oz'?val*jdhlOz:val;
 }
 _alert(e){this._error=String(e?.message||e||'Unknown error');this._status='';this._render(true);}
 async _fetchHistory(){
  if(!this._hass||!this._config?.profile)return;
  if(this._fetching){this._fetchAgain=true;return;}
  this._fetching=true;const profile=this._config.profile;const date=this._viewDate||this._todayISO();
  try{const res=await this._hass.callWS({type:'jw_daily_hydration_log/history',profile,date});
   if(this._config?.profile===profile&&(this._viewDate||this._todayISO())===date){this._history=res;this._render();}
  }catch(e){this._alert(e);}finally{this._fetching=false;if(this._fetchAgain){this._fetchAgain=false;this._fetchHistory();}}
 }
 async _field(e){const field=e.target?.dataset?.field;if(!field)return;
  if(this._manageOpen&&this._customDraft){
   if(field==='custom_svg_file'){
    const file=e.target.files?.[0];if(!file)return;
    if(file.size>16000||!(/\.svg$/i.test(file.name)||file.type==='image/svg+xml')){this._alert('Choose an SVG file up to 16 KB.');return;}
    try{const svg=await file.text();if(!svg.trim().startsWith('<svg')&&!svg.includes('<svg '))throw Error('Choose a valid SVG document.');
     this._customDraft.icon_svg=svg;this._customDraft.icon_mdi='';this._render(true);
    }catch(err){this._alert(err);}return;
   }
   if(Object.hasOwn(this._customDraft,field)){this._customDraft[field]=e.target.value;
    if(field==='icon_mdi'&&e.target.value)this._customDraft.icon_svg='';return;}
  }
  if(this._modal){this._modal[field]=e.target.value;return;}
  if(field==='history_date')this._typedHistoryDate=e.target.value;
 }
 _liquidDefs(){return this._history?.liquid_types?.length?this._history.liquid_types:
  JDHL_TYPES.map(([id,name,icon])=>({id,name,icon_mdi:({water:'mdi:water',coffee:'mdi:coffee',tea:'mdi:tea',milk:'mdi:glass-mug-variant',soup:'mdi:food-soup',other:'mdi:glass-cocktail'})[id],icon_svg:'',default_volume_ml:null,custom:false}));}
 _liquidInfo(id){return this._liquidDefs().find(t=>t.id===id);}
 _liquidIcon(t){if(!t)return '';
  if(t.icon_svg){const src='data:image/svg+xml;charset=utf-8,'+encodeURIComponent(t.icon_svg);
   return `<img class="liquid-icon svg-icon" alt="" src="${jdhlEscape(src)}"/>`;}
  const icon=/^mdi:[a-z0-9-]+$/.test(t.icon_mdi||'')?t.icon_mdi:'mdi:glass-mug-variant';
  return `<ha-icon class="liquid-icon" icon="${jdhlEscape(icon)}" aria-hidden="true"></ha-icon>`;
 }
 async _saveCustomLiquid(){const draft=this._customDraft;if(!draft||!this._modal||!this._hass?.user?.is_admin)return;
  const name=String(draft.custom_name||'').trim();const amount=String(draft.custom_default_volume_ml??'').trim();
  if(!name||name.length>48){this._alert('Enter a liquid name of 1-48 characters.');return;}
  if(amount&&(!Number.isFinite(Number(amount))||Number(amount)<=0||Number(amount)>100000)){
   this._alert('Default volume must be between 0 and 100,000 mL.');return;}
  this._busy=true;this._error='';this._status='Saving liquid type…';
  try{const saved=await this._hass.callWS({type:'jw_daily_hydration_log/add_liquid_type',profile:this._config.profile,
   name,icon_mdi:draft.icon_mdi||'',icon_svg:draft.icon_svg||'',
   ...(amount?{default_volume_ml:Number(amount)}:{})});
   await this._fetchHistory();this._manageOpen=false;this._customDraft=null;
   this._modal.liquid_type=saved.id;this._modal.volume_ml=amount||'';this._status='Liquid type added';
  }catch(err){this._alert(err);}finally{this._busy=false;this._render(true);}
 }
 async _deleteCustomLiquid(id){if(!this._hass?.user?.is_admin)return;
  this._busy=true;this._error='';try{await this._hass.callWS({type:'jw_daily_hydration_log/delete_liquid_type',
    profile:this._config.profile,liquid_type:id});
   await this._fetchHistory();if(this._modal?.liquid_type===id){this._modal.liquid_type='';this._modal.volume_ml='';}
  }catch(err){this._alert(err);}finally{this._busy=false;this._render(true);}
 }
 _selectedRecord(id){return (this._history?.entries||[]).find(r=>String(r.id)===id);}
 _openEdit(id){const r=this._selectedRecord(id);if(!r)return;
  const d=new Date(r.timestamp);const parts=this._timeParts(d);this._modal={mode:'edit',id:r.id,liquid_type:r.liquid_type==='unknown'?'':r.liquid_type,
   volume_ml:String(r.volume_ml),date:parts.date,time:parts.time};
  this._confirmDelete=false;this._render(true);
 }
 _timeParts(d){
  const tz=this._hass?.config?.time_zone||'Europe/Amsterdam';
  const pts=new Intl.DateTimeFormat('en-GB',{timeZone:tz,year:'numeric',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',second:'2-digit',hourCycle:'h23'}).formatToParts(d);
  const p=Object.fromEntries(pts.map(x=>[x.type,x.value]));
  return {date:`${p.day}-${p.month}-${p.year}`,time:`${p.hour}:${p.minute}:${p.second}`};
 }
 _openNew(){this._modal={mode:'new',id:'',liquid_type:'',volume_ml:'',date:this._todayPretty(),time:this._nowTime()};this._confirmDelete=false;this._render(true);}
 _payload(){const m=this._modal,volume=Number(m?.volume_ml),date=m?.date?.trim(),time=m?.time?.trim();
  if(!this._liquidInfo(m?.liquid_type))throw Error('Select a liquid type.');
  if(!Number.isFinite(volume)||volume<=0||volume>100000)throw Error('Enter a volume between 0 and 100,000 mL.');
  if(!/^\d{2}-\d{2}-\d{4}$/.test(date)||!/^([01]\d|2[0-3]):[0-5]\d(:[0-5]\d)?$/.test(time))throw Error('Use DD-MM-YYYY and a 24-hour time HH:MM or HH:MM:SS.');
  return {volume,liquid_type:m.liquid_type,date,time};
 }
 async _click(e){const el=e.target?.closest?.('[data-action]');if(!el||this._busy)return;
  const action=el.dataset.action;
  if(action==='type'){if(!this._modal||this._manageOpen)return;const info=this._liquidInfo(el.dataset.value);
   if(!info)return;this._modal.liquid_type=info.id;
   if(info.default_volume_ml!==null&&info.default_volume_ml!==undefined)this._modal.volume_ml=String(info.default_volume_ml);
   else if(this._modal.mode==='new')this._modal.volume_ml='';
   this._error='';this._render(true);return;}
  if(action==='amount'){if(!this._modal||this._manageOpen)return;
   this._modal.volume_ml=String(el.dataset.value);this._error='';this._render(true);return;}
  if(action==='manage-liquids'){if(!this._modal||!this._hass?.user?.is_admin)return;
   this._manageOpen=true;this._customDraft={custom_name:'',icon_mdi:'mdi:glass-mug-variant',icon_svg:'',custom_default_volume_ml:''};this._error='';this._render(true);return;}
  if(action==='manage-cancel'){this._manageOpen=false;this._customDraft=null;this._error='';this._render(true);return;}
  if(action==='manage-save'){await this._saveCustomLiquid();return;}
  if(action==='manage-remove'){await this._deleteCustomLiquid(el.dataset.value);return;}
  if(action==='new'){this._openNew();return;}
  if(action==='edit'){this._openEdit(el.dataset.id);return;}
  if(action==='cancel'){this._modal=null;this._manageOpen=false;this._customDraft=null;this._confirmDelete=false;this._error='';this._render(true);return;}
  if(action==='delete'){this._confirmDelete=true;this._render(true);return;}
  if(action==='delete-back'){this._confirmDelete=false;this._render(true);return;}
  if(action==='delete-confirm'){await this._delete();return;}
  if(action==='save'){await this._saveModal();return;}
  if(action==='undo'){await this._undo();return;}
  if(action==='prev'||action==='next'){
   const iso=this._viewDate||this._todayISO(),d=new Date(`${iso}T12:00:00`);
   d.setDate(d.getDate()+(action==='prev'?-1:1));this._viewDate=jdhlIsoDate(d);
   if(this._viewDate===this._todayISO())this._viewDate=null;
   this._history=null;this._render(true);this._fetchHistory();return;
  }
  if(action==='date-go'){
   const date=jdhlDateToIso(this._typedHistoryDate||'');
   if(!date||!Number.isFinite(Date.parse(`${date}T12:00:00`))||jdhlIsoDate(new Date(`${date}T12:00:00`))!==date){this._alert('Use a real date in DD-MM-YYYY format.');return;}
   if(date>this._todayISO()){this._alert('You cannot view a future date.');return;}
   this._viewDate=date===this._todayISO()?null:date;this._history=null;this._error='';this._render(true);this._fetchHistory();return;
  }
  if(action==='export'){await this._export();}
 }
 async _saveModal(){let p;try{p=this._payload();}catch(e){this._alert(e);return;}
  const m=this._modal;this._busy=true;this._error='';this._status='Saving drink…';this._render(true);
  try{if(m.mode==='new'){
   const saved=await this._hass.callWS({type:'jw_daily_hydration_log/add_drink',
    profile:this._config.profile,volume_ml:p.volume,liquid_type:p.liquid_type,
    date:p.date,time:p.time});
   this._undoId=saved.record_id||null;
   }else{
    await this._hass.callWS({type:'jw_daily_hydration_log/edit_drink',profile:this._config.profile,
     record_id:m.id,volume_ml:p.volume,liquid_type:p.liquid_type,date:p.date,time:p.time});
   }
   this._modal=null;this._manageOpen=false;this._customDraft=null;this._confirmDelete=false;this._selectedType=null;this._selectedVolume=null;
   this._viewDate=null;this._history=null;this._status='Drink saved';await this._fetchHistory();
  }catch(e){this._alert(e);}finally{this._busy=false;this._render(true);}
 }
 async _delete(){const m=this._modal;if(!m||m.mode!=='edit')return;
  this._busy=true;this._error='';this._status='Deleting drink…';this._render(true);
  try{await this._hass.callWS({type:'jw_daily_hydration_log/delete_drink',profile:this._config.profile,record_id:m.id});
   if(this._undoId===m.id)this._undoId=null;
   this._modal=null;this._confirmDelete=false;this._viewDate=null;this._history=null;
   this._status='Drink deleted';await this._fetchHistory();
  }catch(e){this._alert(e);}finally{this._busy=false;this._render(true);}
 }
 async _undo(){if(!this._undoId||!this._hass?.user?.is_admin)return;
  const id=this._undoId;this._busy=true;this._error='';this._status='Undoing drink…';this._render(true);
  try{await this._hass.callWS({type:'jw_daily_hydration_log/delete_drink',profile:this._config.profile,record_id:id});
   this._undoId=null;this._status='Last drink removed';this._viewDate=null;this._history=null;await this._fetchHistory();
  }catch(e){this._alert(e);}finally{this._busy=false;this._render(true);}
 }
 async _export(){this._busy=true;this._status='Preparing Excel export…';this._error='';this._render(true);
  try{const response=await this._hass.callWS({type:'jw_daily_hydration_log/export'});
   const data=Uint8Array.from(atob(response.base64),c=>c.charCodeAt(0));
   const blob=new Blob([data],{type:response.mime_type});const url=URL.createObjectURL(blob);
   const link=document.createElement('a');link.href=url;link.download=response.filename||'jwDaily Hydration Log - All Data.xlsx';
   this.shadowRoot.appendChild(link);link.click();link.remove();setTimeout(()=>URL.revokeObjectURL(url),15000);
   this._status='Excel export started';
  }catch(e){this._alert(e);}finally{this._busy=false;this._render(true);}
 }
 _glass(pct){const p=Math.min(100,Math.max(0,pct));
  // The target is deliberately 16 SVG units below the former y=23 line.
  // With the displayed 155px-wide glass and 160-unit viewBox this is about 15px.
  const targetY=39,bottomY=179,y=bottomY-(bottomY-targetY)*p/100;
  const fromY=Number.isFinite(this._glassPrevY)?this._glassPrevY:bottomY;
  this._glassPrevY=y;
  const w0=`M32 ${y} Q56 ${y-4} 80 ${y} T128 ${y}`;
  const w1=`M32 ${y} Q56 ${y+4} 80 ${y} T128 ${y}`;
  return `<svg class="glass" viewBox="0 0 160 200" role="img" aria-label="${p.toFixed(0)} percent of daily goal">
   <defs><clipPath id="jdhl-cup"><path d="M32 19 L128 19 L120 175 Q119 185 108 185 L52 185 Q41 185 40 175 Z"/></clipPath></defs>
   <path d="M32 19 L40 175 Q41 185 52 185 L108 185 Q119 185 120 175 L128 19" fill="none"
         stroke="var(--primary-text-color,#233245)" stroke-width="3" stroke-linecap="round"/>
   ${p>0?`<g clip-path="url(#jdhl-cup)"><rect x="32" y="${y}" width="96" height="185" fill="#59baf2" opacity=".9">
      <animate attributeName="y" from="${fromY}" to="${y}" dur="650ms" fill="freeze"/></rect>
      <path d="${w0}" stroke="#a2dcff" stroke-width="3" fill="none">
       <animate attributeName="d" values="${w0};${w1};${w0}" dur="2.7s" repeatCount="indefinite"/></path></g>`:''}
   <path class="target-line" d="M38 ${targetY} L122 ${targetY}" stroke="#df4545" stroke-width="2.6"
         stroke-dasharray="4 5" stroke-linecap="round"/>
   <text x="80" y="108" text-anchor="middle" font-size="29" font-weight="700" fill="var(--primary-text-color,#233245)"
         stroke="var(--card-background-color,#fff)" stroke-width="2.5" paint-order="stroke">${p.toFixed(0)}%</text>
  </svg>`;
 }
 _historyHTML(){if(this._config.show_history===false)return '';
  const iso=this._viewDate||this._todayISO(),rows=Array.isArray(this._history?.entries)?[...this._history.entries].reverse():[];
  const total=this._history?jdhlFmt(this._history.total_ml,this._config.unit):'—';
  const canEdit=!!this._hass?.user?.is_admin;
  const table=rows.length?`<div class="history-table"><table><thead><tr><th>Time</th><th>Liquid</th><th class="right">Volume</th></tr></thead><tbody>
   ${rows.map(r=>{const time=this._timeParts(new Date(r.timestamp)).time;
    return `<tr ${canEdit?`data-action="edit" data-id="${jdhlEscape(r.id)}" title="Edit drink moment" tabindex="0"`:''}>
    <td>${jdhlEscape(time)}</td><td>${jdhlEscape(this._liquidInfo(r.liquid_type)?.name||'Unknown (legacy)')}</td><td class="right">+${jdhlFmt(Number(r.volume_ml),this._config.unit)} ${canEdit?'✎':''}</td></tr>`;}).join('')}
   </tbody></table></div>`:`<p class="muted center">${this._history?'No drinks recorded on this date.':'Loading drink history…'}</p>`;
  return `<section class="history"><div class="history-head"><h3>Drink history</h3><span class="muted">${rows.length} entries</span></div>
   <div class="date-nav"><button data-action="prev" class="small secondary" aria-label="Previous day">‹</button>
   <input aria-label="History date" data-field="history_date" value="${jdhlEscape(jdhlIsoToDate(iso)||iso)}" placeholder="DD-MM-YYYY" inputmode="numeric"/>
   <button data-action="date-go" class="small secondary">Go</button><button data-action="next" class="small secondary" ${iso>=this._todayISO()?'disabled':''} aria-label="Next day">›</button></div>
   ${table}<div class="history-total"><strong>Total ${iso===this._todayISO()?'today':'on selected day'}</strong><strong>${total}</strong></div></section>`;
 }
 _manageHTML(){const d=this._customDraft||{};
  const existing=this._liquidDefs().filter(x=>x.custom);
  return `<div class="manage">
   <h3>Add custom liquid</h3>
   <p class="muted">Create a button that will appear with the standard liquid types.</p>
   ${this._error?`<p role="alert" class="error">${jdhlEscape(this._error)}</p>`:''}
   <div class="fields">
    <label>Liquid name<input data-field="custom_name" maxlength="48" value="${jdhlEscape(d.custom_name||'')}" placeholder="e.g. Orange juice"/></label>
    <label>Default volume (mL) · optional<input data-field="custom_default_volume_ml" type="number" min="0.01" max="100000" step="any" value="${jdhlEscape(d.custom_default_volume_ml||'')}" placeholder="Choose when selecting type"/></label>
    <label>Material Design Icon<input data-field="icon_mdi" value="${jdhlEscape(d.icon_mdi||'')}" placeholder="mdi:glass-mug-variant"/></label>
    <label>Or SVG icon (.svg, max 16 KB)<input data-field="custom_svg_file" type="file" accept=".svg,image/svg+xml"/></label>
   </div>${d.icon_svg?`<p class="status">SVG selected (${new TextEncoder().encode(d.icon_svg).length} bytes); the SVG replaces the MDI icon.</p>`:''}
   <div class="dialog-actions"><button class="secondary" data-action="manage-cancel">Back</button>
    <button data-action="manage-save" ${this._busy?'disabled':''}>Save liquid type</button></div>
   ${existing.length?`<h4>Added liquids</h4><div class="saved-liquids">${existing.map(t=>
    `<div class="saved-liquid">${this._liquidIcon(t)} <span>${jdhlEscape(t.name)}</span>
       <span class="muted">${t.default_volume_ml?jdhlFmt(t.default_volume_ml):'No default'}</span>
       <button class="secondary small" data-action="manage-remove" data-value="${jdhlEscape(t.id)}" title="Remove only when unused">Remove</button></div>`).join('')}</div>`:''}
  </div>`;
 }
 _modalHTML(){if(!this._modal)return '';
  const m=this._modal;
  const types=this._liquidDefs().map(t=>`<button class="liquid-choice ${m.liquid_type===t.id?'selected':''}"
    data-action="type" data-value="${jdhlEscape(t.id)}" aria-pressed="${m.liquid_type===t.id}">
    ${this._liquidIcon(t)}<span>${jdhlEscape(t.name)}</span></button>`).join('');
  const amounts=jdhlQuick(this._config.quick_add).map(v=>`<button class="amount ${Number(m.volume_ml)===v?'selected':''}"
     data-action="amount" data-value="${v}">${jdhlFmt(v)}</button>`).join('');
  return `<div class="overlay" role="presentation"><section class="dialog" role="dialog" aria-modal="true"
    aria-label="${m.mode==='edit'?'Edit drink moment':'Add drink moment'}">
   ${this._manageOpen?this._manageHTML():`
    <h3>${m.mode==='edit'?'Edit drink moment':'Add drink moment'}</h3>
    ${this._error?`<p class="error" role="alert">${jdhlEscape(this._error)}</p>`:''}
    <div class="modal-heading">Liquid type</div><div class="liquid-choices">${types}</div>
    ${this._hass?.user?.is_admin?`<button class="secondary small add-type" data-action="manage-liquids">+ Add custom liquid type</button>`:''}
    <div class="modal-heading">Volume (mL)</div><div class="volume-choices">${amounts}</div>
    <div class="fields">
     <label>Custom amount (mL)<input data-field="volume_ml" type="number" step="any" min="0.01" max="100000" value="${jdhlEscape(m.volume_ml)}" placeholder="Enter or select"/></label>
     <label>Date (DD-MM-YYYY)<input data-field="date" inputmode="numeric" placeholder="DD-MM-YYYY" value="${jdhlEscape(m.date)}"/></label>
     <label>Time (24-hour)<input data-field="time" inputmode="numeric" placeholder="HH:MM:SS" value="${jdhlEscape(m.time)}"/></label>
    </div>
    ${this._confirmDelete?`<div class="delete-warning">Permanently delete this drink? This cannot be undone.</div>
     <div class="dialog-actions"><button data-action="delete-back" class="secondary">Cancel</button>
      <button data-action="delete-confirm" class="danger" ${this._busy?'disabled':''}>Confirm delete</button></div>`:
     `<div class="dialog-actions">${m.mode==='edit'?`<button data-action="delete" class="danger" ${this._busy?'disabled':''}>Delete</button>`:''}
      <button data-action="cancel" class="secondary">Cancel</button>
      <button data-action="save" ${this._busy?'disabled':''}>Save</button></div>`}`}
   </section></div>`;
 }
 _render(force=false){if(!this._config||!this._hass)return;
  if(this._modal&&!force)return; // Do not replace popup input nodes during live typing.
  const target=this._millilitres('daily_target','target_ml');const consumed=this._millilitres('consumed_today','consumed_ml');
  const remaining=Math.max(0,target-consumed),pct=target?consumed/target*100:0;
  const title=this._config.title||'jwDaily Hydration Log';const count=jdhlNum(this._state('drink_count_today')?.state);
  const k=JSON.stringify([target,consumed,this._history,this._selectedType,this._selectedVolume,this._modal,this._confirmDelete,this._busy,this._error,this._status,this._viewDate,this._undoId,this._config]);
  if(!force&&this._lastRender===k)return;this._lastRender=k;
  this.shadowRoot.innerHTML=`<style>
   :host{display:block}ha-card{overflow:hidden}.root{padding:18px;display:flex;flex-direction:column;gap:15px;color:var(--primary-text-color)}
   header{display:flex;align-items:center;justify-content:space-between}header h2{margin:0;font-size:1.14rem;font-weight:650}header small{color:var(--secondary-text-color)}
   .hero{display:grid;grid-template-columns:minmax(115px,34%) 1fr;align-items:center;gap:12px;padding:2px 6px 8px;max-width:620px;width:100%;margin:auto;box-sizing:border-box}
   .glass{max-width:155px;width:100%;height:auto;display:block;margin:auto}.metrics{display:flex;flex-direction:column;gap:6px;min-width:0}
   .metrics .big{font-size:clamp(1.25rem,4vw,1.75rem);font-weight:700}.metrics .muted{font-size:.88rem}.metrics .row{font-size:.88rem;display:flex;align-items:center;gap:7px}
   .red{color:#da4141}.blue{color:#098cc8}.muted{color:var(--secondary-text-color)}.divider{border-top:1px solid var(--divider-color)}
   .section-label{font-size:.88rem;font-weight:600;margin-bottom:8px}.types,.amounts{display:flex;flex-wrap:wrap;gap:8px}
   button{font:inherit;border:none;border-radius:16px;background:var(--primary-color,#009dcc);color:white;padding:9px 13px;cursor:pointer}
   button.selected{outline:3px solid var(--primary-text-color);outline-offset:2px;background:var(--primary-color,#009dcc)}
   button.type,button.amount{background:var(--secondary-background-color,#e9eef3);color:var(--primary-text-color);border:1px solid var(--divider-color,#ccc);font-size:.86rem}
   button.type.selected,button.amount.selected{background:var(--primary-color,#009dcc);color:white}button.secondary{background:var(--secondary-background-color,#ebeff2);color:var(--primary-text-color)}
   button.danger{background:#b51f2d;color:white}button:disabled{opacity:.45;cursor:not-allowed}button.small{padding:5px 11px;border-radius:9px}
   .register{display:flex;justify-content:space-between;align-items:center;gap:10px;flex-wrap:wrap}.register .note{font-size:.82rem;color:var(--secondary-text-color)}
   .history{border-top:1px solid var(--divider-color);padding-top:13px}.history-head,.history-total{display:flex;justify-content:space-between;gap:10px;align-items:center}
   .history h3{margin:0;font-size:1rem}.history-head .muted{font-size:.82rem}.date-nav{display:flex;align-items:center;justify-content:flex-end;gap:5px;margin:9px 0}
   .date-nav input{width:112px;padding:6px 7px;border:1px solid var(--divider-color,#aaa);border-radius:8px;background:var(--card-background-color);color:var(--primary-text-color);font:inherit;font-size:.8rem;text-align:center}
   .history-table{max-height:280px;overflow:auto}table{width:100%;border-collapse:collapse}th{font-weight:500;color:var(--secondary-text-color);font-size:.8rem;text-align:left}
   td,th{padding:8px 5px;border-bottom:1px solid var(--divider-color);font-size:.88rem;font-variant-numeric:tabular-nums}td.right,th.right{text-align:right}
   tr[data-action]{cursor:pointer}tr[data-action]:hover{background:var(--secondary-background-color)}.history-total{margin-top:11px;font-size:.91rem}
   .center{text-align:center}.error{color:var(--error-color,#a11b25);font-size:.84rem}.status{color:var(--secondary-text-color);font-size:.82rem}
   .export{border-top:1px solid var(--divider-color);padding-top:12px;text-align:center}.export button{font-size:.85rem}
   .overlay{position:fixed;inset:0;z-index:10000;background:rgba(0,0,0,.4);display:flex;align-items:center;justify-content:center;padding:15px}
   .dialog{width:min(450px,100%);box-sizing:border-box;background:var(--card-background-color,#fff);color:var(--primary-text-color);border-radius:15px;padding:18px;box-shadow:0 18px 50px #0005}
   .dialog h3{margin:0 0 15px}.fields{display:grid;grid-template-columns:1fr 1fr;gap:12px}.fields label{display:flex;flex-direction:column;gap:4px;font-size:.81rem}
   .fields input,.fields select{min-width:0;width:100%;box-sizing:border-box;background:var(--card-background-color,#fff);color:var(--primary-text-color);border:1px solid var(--divider-color,#aaa);border-radius:8px;padding:10px 8px;font:inherit}
   .dialog-actions{display:flex;justify-content:flex-end;flex-wrap:wrap;gap:8px;margin-top:16px}.dialog-actions button:first-child.danger{margin-right:auto}
   .card-version{align-self:flex-end;margin-top:1px;font-size:.7rem;color:var(--secondary-text-color)}
   .register{justify-content:center}.register .add-drink{min-width:160px;font-weight:600;font-size:1rem}
   .liquid-choices{display:flex;flex-wrap:wrap;gap:9px}.liquid-choice{display:flex;align-items:center;gap:6px;
    background:var(--secondary-background-color,#e9eef3);color:var(--primary-text-color);
    border:1px solid var(--divider-color);min-height:48px;padding:7px 11px}
   .liquid-choice.selected,.volume-choices .selected{background:var(--primary-color,#009dcc);color:white;
    outline:2px solid var(--primary-text-color);outline-offset:1px}
   .liquid-icon{width:27px;height:27px;min-width:27px;--mdc-icon-size:27px;display:inline-block;object-fit:contain}
   .volume-choices{display:flex;flex-wrap:wrap;gap:8px}
   .volume-choices .amount{background:var(--secondary-background-color,#e9eef3);color:var(--primary-text-color);
     border:1px solid var(--divider-color)}
   .volume-choices .amount.selected{background:var(--primary-color,#009dcc);color:white}
   .modal-heading{font-size:.9rem;font-weight:600;margin:13px 0 8px}.add-type{margin-top:10px}
   .saved-liquids{display:flex;flex-direction:column;gap:7px;margin-top:9px}.saved-liquid{display:flex;gap:8px;align-items:center}
   .saved-liquid .muted{margin-left:auto}.manage h4{margin:18px 0 5px}
   .dialog{max-height:calc(100vh - 40px);overflow-y:auto}
   .delete-warning{margin-top:15px;padding:10px;border:1px solid #b51f2d;border-radius:8px;color:#b51f2d;font-size:.87rem}
   @media(max-width:380px){.root{padding:12px}.hero{grid-template-columns:110px 1fr;gap:5px}.metrics .row{font-size:.78rem}.fields{grid-template-columns:1fr}}
   </style><ha-card><div class="root">
   ${this._config.show_title!==false?`<header><h2>${jdhlEscape(title)}</h2></header>`:''}
   <div class="hero">${this._config.show_cup!==false?this._glass(pct):''}<div class="metrics">
    <div class="big">${jdhlFmt(consumed,this._config.unit)}</div><div class="muted">of ${jdhlFmt(target,this._config.unit)} today</div>
    <div class="row"><span class="red">⚑</span> Target: ${jdhlFmt(target,this._config.unit)}</div>
    <div class="row"><span class="blue">💧</span> Remaining: ${jdhlFmt(remaining,this._config.unit)}</div>
    <div class="row">◷ ${count} drink moments</div></div></div>
   ${this._config.show_manual!==false?`<div class="divider"></div><div class="register">
    <button class="add-drink" data-action="new" ${this._busy?'disabled':''}>+ Add drink</button>
    ${this._undoId&&this._hass?.user?.is_admin?`<button class="secondary" data-action="undo" ${this._busy?'disabled':''}>Undo last drink</button>`:''}
   </div>`:''}
   ${this._error?`<div class="error" role="alert">${jdhlEscape(this._error)}</div>`:''}${this._status?`<div class="status" aria-live="polite">${jdhlEscape(this._status)}</div>`:''}
   ${this._historyHTML()}
   ${this._config.show_export!==false&&this._hass?.user?.is_admin?`<div class="export"><button class="secondary" data-action="export" ${this._busy?'disabled':''}>Export all data to Excel (.xlsx)</button></div>`:''}
   ${this._modalHTML()}
   <footer class="card-version">v1.1.0-beta.2</footer></div></ha-card>`;
 }
}

const JDHL_EDITOR_LABELS={profile:'Person',title:'Card title',show_title:'Show title',show_cup:'Show glass',
 show_manual:'Show Add drink button',show_history:'Show drink history',show_export:'Show Excel export',
 unit:'Display units',quick_add:'Quick-select volumes (mL)'};
function jdhlEditorSchema(profiles){return [
 {name:'profile',selector:{select:{mode:'dropdown',options:profiles}}},{name:'title',selector:{text:{}}},
 {name:'',type:'grid',schema:['show_title','show_cup','show_manual','show_history','show_export'].map(name=>({name,selector:{boolean:{}}}))},
 {name:'unit',selector:{select:{options:[{value:'mL',label:'Metric (mL/L)'},{value:'fl_oz',label:'Imperial (fl oz)'}]}}},
 {name:'quick_add',selector:{select:{multiple:true,custom_value:true,options:[120,150,200,250,300,500,750,1000].map(n=>({value:String(n),label:String(n)}))}}}
 ];}
class JwDailyHydrationLogCardEditor extends HTMLElement{
 constructor(){super();this._config=null;this._hass=null;this._form=null;}
 setConfig(c){this._config={...JDHL_DEFAULTS,...c};this._render();}
 connectedCallback(){if(!customElements.get('ha-form')){const tile=customElements.get('hui-tile-card');if(tile?.getConfigElement)tile.getConfigElement();}}
 set hass(h){this._hass=h;this._render();}
 _profiles(){return Object.keys(this._hass?.states||{}).filter(x=>x.startsWith('sensor.jwdhl_')&&x.endsWith('_daily_target')).sort().map(id=>({value:id.slice('sensor.jwdhl_'.length,-'_daily_target'.length),label:(this._hass.states[id].attributes?.friendly_name||id).replace(/ Daily target$/,'')}));}
 _render(){if(!this._config||!this._hass)return;
  if(!this._form){const f=document.createElement('ha-form');f.computeLabel=s=>JDHL_EDITOR_LABELS[s.name]||'';
   f.addEventListener('value-changed',e=>{e.stopPropagation();const data={...e.detail.value};
    if(!data.profile&&this._config.profile)data.profile=this._config.profile;
    data.quick_add=jdhlQuick(data.quick_add);this._config=data;
    this.dispatchEvent(new CustomEvent('config-changed',{detail:{config:data},bubbles:true,composed:true}));});
   this.appendChild(f);this._form=f;}
  this._form.hass=this._hass;this._form.schema=jdhlEditorSchema(this._profiles());
  this._form.data={...this._config,quick_add:jdhlQuick(this._config.quick_add).map(String)};
 }
}
if(!customElements.get(JDHL_TAG))customElements.define(JDHL_TAG,JwDailyHydrationLogCard);
if(!customElements.get(JDHL_EDITOR))customElements.define(JDHL_EDITOR,JwDailyHydrationLogCardEditor);
window.customCards=window.customCards||[];
if(!window.customCards.some(c=>c.type===JDHL_TAG))window.customCards.push({type:JDHL_TAG,name:'jwDaily Hydration Log',description:'Editable individual liquid tracking with Excel export',preview:true});
console.info('jwDaily Hydration Log Card v1.1.0-beta.2');
