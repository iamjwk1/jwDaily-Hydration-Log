/* jwDaily Hydration Log v1.1.0-beta.11 - independent Home Assistant Lovelace card.
 * Derived from Personal Hydration Manager (MIT), Copyright (c) 2026 Loryan Strant.
 * Copyright (c) 2026 jwDaily Hydration Log contributors (modifications).
 */
const JDHL_TAG='jwdaily-hydration-log-card';
const JDHL_EDITOR=`${JDHL_TAG}-editor`;
const JDHL_TYPES=[['water','Water','💧'],['coffee','Coffee','☕'],['tea','Tea','🍵'],['milk','Milk','🐄'],['soup','Soup','🥣'],['wine','Wine','🍷'],['other','Other','🥛']];
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
const jdhlNormalizeTime=value=>{
 const raw=String(value??'').trim().replace(/[.\s]/g,':');
 let valueText=raw;
 if(/^\d{3,4}$/.test(raw)){const v=raw.padStart(4,'0');valueText=`${v.slice(0,2)}:${v.slice(2)}`;}
 else if(/^\d{5,6}$/.test(raw)){const v=raw.padStart(6,'0');valueText=`${v.slice(0,2)}:${v.slice(2,4)}:${v.slice(4)}`;}
 else if(/^\d{1,2}:\d{1,2}(:\d{1,2})?$/.test(raw))valueText=raw.split(':').map(v=>v.padStart(2,'0')).join(':');
 return /^([01]\d|2[0-3]):[0-5]\d(:[0-5]\d)?$/.test(valueText)?valueText:null;
};

class JwDailyHydrationLogCard extends HTMLElement {
 constructor(){
  super();this.attachShadow({mode:'open'});
  this._hass=null;this._config=null;this._history=null;this._viewDate=null;
  this._selectedType=null;this._selectedVolume=null;this._undoId=null;this._modal=null;this._confirmDelete=false;
  this._manageOpen=false;this._customDraft=null;this._editingLiquidId=null;
  this._volumeManageOpen=false;this._volumeDraft=null;this._glassPrevY=179;
  this._managePendingDelete=null;
  this._calendarOpen=false;this._calendarMonth=null;
  this._busy=false;this._error='';this._status='';this._lastState='';this._lastRender='';
  this._fetching=false;this._fetchAgain=false;this._tickTimer=null;
  this.shadowRoot.addEventListener('click',e=>this._click(e));
  this.shadowRoot.addEventListener('input',e=>this._field(e));
  this.shadowRoot.addEventListener('change',e=>this._field(e));
  this.shadowRoot.addEventListener('keydown',e=>{
   if(e.key==='Escape'&&this._calendarOpen){this._calendarOpen=false;this._render(true);return;}
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
  this._manageOpen=false;this._customDraft=null;this._editingLiquidId=null;
  this._volumeManageOpen=false;this._volumeDraft=null;this._glassPrevY=179;
  this._managePendingDelete=null;
  this._calendarOpen=false;this._calendarMonth=null;
  this._history=null;this._lastState='';this._lastRender='';this._render(true);this._fetchHistory();
 }
 set hass(h){this._hass=h;
  const p=this._config?.profile;
  if(p){const manual=h?.states?.[`sensor.jwdhl_${p}_manual_consumed`];const count=h?.states?.[`sensor.jwdhl_${p}_drink_count_today`];
   const consumed=h?.states?.[`sensor.jwdhl_${p}_consumed_today`];const target=h?.states?.[`sensor.jwdhl_${p}_daily_target`];
   const key=JSON.stringify([manual?.attributes?.manual_consumed_ml,count?.state,consumed?.attributes?.consumed_ml,target?.attributes?.target_ml,this._todayISO()]);
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
  if(this._volumeManageOpen && field==='volume_button'){
   const index=Number(e.target.dataset.index);
   if(Number.isInteger(index)&&index>=0&&index<this._volumeDraft.length)this._volumeDraft[index]=e.target.value;
   return;
  }
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
  if(this._modal){
   if(field==='time'&&e.type==='change'){
    const normal=jdhlNormalizeTime(e.target.value);
    if(normal){e.target.value=normal;this._modal.time=normal;}else this._modal.time=e.target.value;
   }else this._modal[field]=e.target.value;
   return;
  }
  if(field==='history_date')this._typedHistoryDate=e.target.value;
 }
 _liquidDefs(){return this._history?.liquid_types?.length?this._history.liquid_types:
  JDHL_TYPES.map(([id,name,icon])=>({id,name,icon_mdi:({water:'mdi:water',coffee:'mdi:coffee',tea:'mdi:tea',milk:'mdi:cow',soup:'mdi:bowl-mix',wine:'mdi:glass-wine',other:'mdi:glass-water'})[id],icon_svg:'',default_volume_ml:null,custom:false}));}
 _liquidInfo(id){return this._liquidDefs().find(t=>t.id===id);}
 _liquidIcon(t){if(!t)return '';
  if(t.icon_svg){const src='data:image/svg+xml;charset=utf-8,'+encodeURIComponent(t.icon_svg);
   return `<img class="liquid-icon svg-icon" alt="" src="${jdhlEscape(src)}"/>`;}
  const icon=/^mdi:[a-z0-9-]+$/.test(t.icon_mdi||'')?t.icon_mdi:'mdi:glass-mug-variant';
  return `<ha-icon class="liquid-icon" icon="${jdhlEscape(icon)}" aria-hidden="true"></ha-icon>`;
 }
 _newLiquidDraft(existing=null){return {custom_name:existing?.name||'',icon_mdi:existing?existing.icon_mdi:'mdi:glass-mug-variant',
  icon_svg:existing?.icon_svg||'',custom_default_volume_ml:existing?.default_volume_ml??''};}
 async _saveCustomLiquid(){const draft=this._customDraft;if(!draft||!this._modal||!this._hass?.user?.is_admin)return;
  const name=String(draft.custom_name||'').trim();const amount=String(draft.custom_default_volume_ml??'').trim();
  if(!name||name.length>48){this._alert('Enter a liquid name of 1-48 characters.');return;}
  if(amount&&(!Number.isFinite(Number(amount))||Number(amount)<=0||Number(amount)>100000)){
   this._alert('Default volume must be between 0 and 100,000 mL.');return;}
  const existingId=this._editingLiquidId;
  this._busy=true;this._error='';this._status=existingId?'Updating liquid type…':'Saving liquid type…';
  try{await this._ensureBackend();const saved=await this._hass.callWS({type:existingId?'jw_daily_hydration_log/update_liquid_type':'jw_daily_hydration_log/add_liquid_type',
   profile:this._config.profile,...(existingId?{liquid_type:existingId}:{}),name,
   icon_mdi:draft.icon_mdi||'',icon_svg:draft.icon_svg||'',
   ...(amount?{default_volume_ml:Number(amount)}:{})});
   await this._fetchHistory();this._customDraft=null;this._editingLiquidId=null;
   if(!existingId&&this._modal.mode==='new'){
    this._modal.liquid_type=saved.id;this._modal.volume_ml=amount||'';
   }
   this._status=existingId?'Liquid type updated':'Liquid type added';
  }catch(err){this._alert(err);}finally{this._busy=false;this._render(true);}
 }
 async _setBuiltinVisible(id,visible){if(!this._hass?.user?.is_admin)return;
  this._busy=true;this._error='';
  try{await this._ensureBackend();await this._hass.callWS({type:'jw_daily_hydration_log/set_builtin_liquid_visibility',
    profile:this._config.profile,liquid_type:id,visible});
   await this._fetchHistory();
   if(!visible&&this._modal?.liquid_type===id){this._modal.liquid_type='';this._modal.volume_ml='';}
   this._status=visible?'Built-in liquid restored':'Built-in liquid removed from Add choices';
  }catch(err){this._alert(err);}finally{this._busy=false;this._render(true);}
 }
 async _deleteCustomLiquid(id){if(!this._hass?.user?.is_admin)return;
  this._busy=true;this._error='';try{await this._ensureBackend();await this._hass.callWS({type:'jw_daily_hydration_log/delete_liquid_type',
    profile:this._config.profile,liquid_type:id});
   await this._fetchHistory();if(this._modal?.liquid_type===id){this._modal.liquid_type='';this._modal.volume_ml='';}
   this._status='Custom liquid deleted';
  }catch(err){this._alert(err);}finally{this._busy=false;this._render(true);}
 }
 async _moveLiquid(id,step){if(!this._hass?.user?.is_admin)return;
  const defs=this._liquidDefs();const visible=defs.filter(t=>!t.hidden).map(t=>t.id);
  const pos=visible.indexOf(id),dest=pos+step;
  if(pos<0||dest<0||dest>=visible.length)return;
  [visible[pos],visible[dest]]=[visible[dest],visible[pos]];
  // Hidden built-in choices still exist in the catalog but remain outside the picker.
  const list=[...visible,...defs.filter(t=>t.hidden).map(t=>t.id)];
  this._busy=true;this._error='';
  try{await this._ensureBackend();await this._hass.callWS({type:'jw_daily_hydration_log/set_liquid_order',profile:this._config.profile,order:list});
   await this._fetchHistory();this._status='Liquid order saved';
  }catch(err){this._alert(err);}finally{this._busy=false;this._render(true);}
 }
 _buttons(){const values=this._history?.volume_buttons;
  return Array.isArray(values)?values:jdhlQuick(this._config?.quick_add);}
 _openVolumeManager(){this._volumeDraft=this._buttons().map(String);this._volumeManageOpen=true;this._error='';this._render(true);}
 async _saveVolumeButtons(){if(!this._hass?.user?.is_admin||!this._volumeDraft)return;
  const entries=this._volumeDraft.map(v=>String(v).trim());const volumes=entries.map(Number);
  if(volumes.length>24||entries.some(v=>!v)||volumes.some(v=>!Number.isFinite(v)||v<=0||v>100000)||new Set(volumes.map(n=>n.toFixed(2))).size!==volumes.length){
   this._alert('Use 0-24 unique positive volumes (up to 100,000 mL). Remove empty rows before saving.');return;}
  this._busy=true;this._error='';
  try{await this._ensureBackend();await this._hass.callWS({type:'jw_daily_hydration_log/set_volume_buttons',profile:this._config.profile,volumes});
   await this._fetchHistory();this._volumeManageOpen=false;this._volumeDraft=null;this._status='Volume buttons saved';
  }catch(err){this._alert(err);}finally{this._busy=false;this._render(true);}
 }
 _selectedRecord(id){return (this._history?.entries||[]).find(r=>String(r.id)===id);}
 _openEdit(id){const r=this._selectedRecord(id);if(!r)return;
  const d=new Date(r.timestamp);const parts=this._timeParts(d);this._modal={mode:'edit',id:r.id,liquid_type:r.liquid_type==='unknown'?'':r.liquid_type,
   volume_ml:String(r.volume_ml),date:parts.date,time:parts.time};
  this._calendarOpen=false;this._calendarMonth=null;this._confirmDelete=false;this._render(true);
 }
 _timeParts(d){
  const tz=this._hass?.config?.time_zone||'Europe/Amsterdam';
  const pts=new Intl.DateTimeFormat('en-GB',{timeZone:tz,year:'numeric',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',second:'2-digit',hourCycle:'h23'}).formatToParts(d);
  const p=Object.fromEntries(pts.map(x=>[x.type,x.value]));
  return {date:`${p.day}-${p.month}-${p.year}`,time:`${p.hour}:${p.minute}:${p.second}`};
 }
 _openNew(){this._modal={mode:'new',id:'',liquid_type:'',volume_ml:'',date:jdhlIsoToDate(this._viewDate||this._todayISO()),time:this._nowTime()};this._calendarOpen=false;this._calendarMonth=null;this._confirmDelete=false;this._render(true);}
 _payload(){const m=this._modal,volume=Number(m?.volume_ml),date=m?.date?.trim(),time=jdhlNormalizeTime(m?.time);
  if(!this._liquidInfo(m?.liquid_type) || (m.mode==='new' && this._liquidInfo(m.liquid_type)?.hidden))throw Error('Select a visible liquid type.');
  if(!Number.isFinite(volume)||volume<=0||volume>100000)throw Error('Enter a volume between 0 and 100,000 mL.');
  if(!/^\d{2}-\d{2}-\d{4}$/.test(date))throw Error('Use DD-MM-YYYY for the date.');
  if(!time)throw Error('Enter a valid 24-hour time: 930 → 09:30, 1430 → 14:30. Hours must be 00–23 and minutes 00–59.');
  const iso=jdhlDateToIso(date);
  if(!iso||!Number.isFinite(Date.parse(`${iso}T12:00:00`))||jdhlIsoDate(new Date(`${iso}T12:00:00`))!==iso)throw Error('Use a valid calendar date.');
  if(iso>this._todayISO())throw Error('Future dates are not allowed; a later time today is allowed.');
  return {volume,liquid_type:m.liquid_type,date,time};
 }
 async _ensureBackend(){
  try{
   const info=await this._hass.callWS({type:'jw_daily_hydration_log/capabilities'});
   if(info?.version!=='1.1.0-beta.10')throw Error(`Frontend v1.1.0-beta.11 is connected to backend ${info?.version||'unknown'}. Restart Home Assistant Core and refresh the dashboard.`);
   return info;
  }catch(err){
   const message=String(err?.message||err||'Unknown error');
   if(/unknown[ _-]?command/i.test(message))throw Error('The new card is loaded, but Home Assistant Core still uses an older jwDaily Hydration Log backend. Restart Home Assistant Core (not only the browser), then refresh the dashboard.');
   throw err;
  }
 }
 _calendarHTML(){
  if(!this._calendarOpen||!this._modal)return '';
  const iso=jdhlDateToIso(this._modal.date)||this._todayISO();
  const ym=/^\d{4}-\d{2}$/.test(this._calendarMonth||'')?this._calendarMonth:iso.slice(0,7);
  const year=Number(ym.slice(0,4)),month=Number(ym.slice(5,7));
  const first=new Date(year,month-1,1),start=(first.getDay()+6)%7;
  const count=new Date(year,month,0).getDate();
  const title=new Intl.DateTimeFormat('en-GB',{year:'numeric',month:'long'}).format(first);
  const weekdays=['Mo','Tu','We','Th','Fr','Sa','Su'];
  const blank=Array.from({length:start},()=>'<span aria-hidden="true"></span>').join('');
  const days=Array.from({length:count},(_,n)=>{
   const day=String(n+1).padStart(2,'0');const value=`${ym}-${day}`;
   return `<button type="button" class="cal-day ${value===iso?'current':''}" data-action="calendar-day" data-value="${value}" ${value>this._todayISO()?'disabled':''} aria-label="${jdhlIsoToDate(value)}" aria-pressed="${value===iso}">${n+1}</button>`;
  }).join('');
  return `<div class="cal-popover" role="group" aria-label="Choose a date">
    <div class="cal-title"><button type="button" data-action="calendar-prev" class="secondary small" aria-label="Previous month">‹</button><strong>${jdhlEscape(title)}</strong><button type="button" data-action="calendar-next" class="secondary small" aria-label="Next month" ${ym>=this._todayISO().slice(0,7)?'disabled':''}>›</button></div>
    <div class="cal-grid">${weekdays.map(d=>`<span class="cal-weekday">${d}</span>`).join('')}${blank}${days}</div>
   </div>`;
 }
 _moveCalendar(delta){
  const ym=this._calendarMonth||(jdhlDateToIso(this._modal?.date)||this._todayISO()).slice(0,7);
  const d=new Date(Number(ym.slice(0,4)),Number(ym.slice(5,7))-1+delta,1);
  this._calendarMonth=jdhlIsoDate(d).slice(0,7);this._render(true);
 }
 async _click(e){const el=e.target?.closest?.('[data-action]');if(!el||this._busy)return;
  const action=el.dataset.action;
  if(action==='type'){if(!this._modal||this._manageOpen)return;const info=this._liquidInfo(el.dataset.value);
   if(!info||info.hidden)return;this._modal.liquid_type=info.id;
   if(info.default_volume_ml!==null&&info.default_volume_ml!==undefined)this._modal.volume_ml=String(info.default_volume_ml);
   else if(this._modal.mode==='new')this._modal.volume_ml='';
   this._error='';this._render(true);return;}
  if(action==='amount'){if(!this._modal||this._manageOpen)return;
   this._modal.volume_ml=String(el.dataset.value);this._error='';this._render(true);return;}
  if(action==='manage-liquids'){if(!this._modal||!this._hass?.user?.is_admin)return;
   this._manageOpen=true;this._customDraft=null;this._editingLiquidId=null;this._managePendingDelete=null;this._error='';this._render(true);return;}
  if(action==='manage-add'){this._customDraft=this._newLiquidDraft();this._editingLiquidId=null;this._error='';this._render(true);return;}
  if(action==='manage-edit'){const liquid=this._liquidInfo(el.dataset.value);if(!liquid)return;
   this._managePendingDelete=null;
   this._editingLiquidId=liquid.id;this._customDraft=this._newLiquidDraft(liquid);this._error='';this._render(true);return;}
  if(action==='manage-cancel'){
   if(this._customDraft){this._customDraft=null;this._editingLiquidId=null;}
   else this._manageOpen=false;
   this._managePendingDelete=null;this._error='';this._render(true);return;}
  if(action==='manage-save'){await this._saveCustomLiquid();return;}
  if(action==='manage-hide'||action==='manage-remove'){
   const t=this._liquidInfo(el.dataset.value);if(!t)return;
   this._managePendingDelete={id:t.id,name:t.name,custom:t.custom};this._error='';this._render(true);return;}
  if(action==='manage-delete-cancel'){this._managePendingDelete=null;this._render(true);return;}
  if(action==='manage-delete-confirm'){
   const item=this._managePendingDelete;if(!item)return;
   if(item.custom)await this._deleteCustomLiquid(item.id);
   else await this._setBuiltinVisible(item.id,false);
   if(!this._error)this._managePendingDelete=null;
   this._render(true);return;}
  if(action==='manage-restore'){await this._setBuiltinVisible(el.dataset.value,true);return;}
  if(action==='manage-up'){await this._moveLiquid(el.dataset.value,-1);return;}
  if(action==='manage-down'){await this._moveLiquid(el.dataset.value,1);return;}
  if(action==='manage-volumes'){this._openVolumeManager();return;}
  if(action==='volume-cancel'){this._volumeManageOpen=false;this._volumeDraft=null;this._error='';this._render(true);return;}
  if(action==='volume-add'){if(this._volumeDraft.length<24)this._volumeDraft.push('');this._render(true);return;}
  if(action==='volume-remove'){this._volumeDraft.splice(Number(el.dataset.index),1);this._render(true);return;}
  if(action==='volume-up'||action==='volume-down'){
   const i=Number(el.dataset.index),to=i+(action==='volume-up'?-1:1);
   if(i>=0&&to>=0&&to<this._volumeDraft.length){[this._volumeDraft[i],this._volumeDraft[to]]=[this._volumeDraft[to],this._volumeDraft[i]];this._render(true);}return;}
  if(action==='volume-save'){await this._saveVolumeButtons();return;}
  if(action==='calendar-toggle'){this._calendarOpen=!this._calendarOpen;this._calendarMonth=(jdhlDateToIso(this._modal?.date)||this._todayISO()).slice(0,7);this._render(true);return;}
  if(action==='calendar-prev'){this._moveCalendar(-1);return;}
  if(action==='calendar-next'){this._moveCalendar(1);return;}
  if(action==='calendar-day'){
   if(!this._modal)return;const iso=el.dataset.value;
   if(!/^\d{4}-\d{2}-\d{2}$/.test(iso)||iso>this._todayISO())return;
   this._modal.date=jdhlIsoToDate(iso);this._calendarOpen=false;this._render(true);return;}
  if(action==='new'){this._openNew();return;}
  if(action==='edit'){this._openEdit(el.dataset.id);return;}
  if(action==='cancel'){this._modal=null;this._manageOpen=false;this._customDraft=null;this._editingLiquidId=null;
   this._volumeManageOpen=false;this._volumeDraft=null;this._confirmDelete=false;this._error='';this._render(true);return;}
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
  try{await this._ensureBackend();if(m.mode==='new'){
   const saved=await this._hass.callWS({type:'jw_daily_hydration_log/add_drink',
    profile:this._config.profile,volume_ml:p.volume,liquid_type:p.liquid_type,
    date:p.date,time:p.time});
   this._undoId=saved.record_id||null;
   }else{
    await this._hass.callWS({type:'jw_daily_hydration_log/edit_drink',profile:this._config.profile,
     record_id:m.id,volume_ml:p.volume,liquid_type:p.liquid_type,date:p.date,time:p.time});
   }
   this._modal=null;this._calendarOpen=false;this._manageOpen=false;this._customDraft=null;this._confirmDelete=false;this._selectedType=null;this._selectedVolume=null;
   this._history=null;this._status='';await this._fetchHistory();
  }catch(e){this._alert(e);}finally{this._busy=false;this._render(true);}
 }
 async _delete(){const m=this._modal;if(!m||m.mode!=='edit')return;
  this._busy=true;this._error='';this._status='Deleting drink…';this._render(true);
  try{await this._ensureBackend();await this._hass.callWS({type:'jw_daily_hydration_log/delete_drink',profile:this._config.profile,record_id:m.id});
   if(this._undoId===m.id)this._undoId=null;
   this._modal=null;this._confirmDelete=false;this._history=null;
   this._status='';await this._fetchHistory();
  }catch(e){this._alert(e);}finally{this._busy=false;this._render(true);}
 }
 async _undo(){if(!this._undoId||!this._hass?.user?.is_admin)return;
  const id=this._undoId;this._busy=true;this._error='';this._status='Undoing drink…';this._render(true);
  try{await this._ensureBackend();await this._hass.callWS({type:'jw_daily_hydration_log/delete_drink',profile:this._config.profile,record_id:id});
   this._undoId=null;this._status='';this._history=null;await this._fetchHistory();
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
 _glass(pct,remaining,target){
  const actual=Math.max(0,Number(pct)||0),p=Math.min(100,actual),targetY=39,bottomY=179,topY=19;
  // Exactly 100% reaches target. Any over-target intake fills to the open rim;
  // volumes and percentages may keep increasing without growing beyond the glass.
  const y=actual>100?topY:bottomY-(bottomY-targetY)*p/100;
  const fromY=Number.isFinite(this._glassPrevY)?this._glassPrevY:bottomY;
  this._glassPrevY=y;
  const w0=`M32 ${y} Q56 ${y-4} 80 ${y} T128 ${y}`;
  const w1=`M32 ${y} Q56 ${y+4} 80 ${y} T128 ${y}`;
  const remainingY=Math.min(154,Math.max(63,targetY+(y-targetY)/2+7));
  return `<svg class="glass" viewBox="0 0 160 200" role="img" aria-label="${actual.toFixed(0)} percent of daily goal">
   <defs><clipPath id="jdhl-cup"><path d="M32 19 L128 19 L120 175 Q119 185 108 185 L52 185 Q41 185 40 175 Z"/></clipPath></defs>
   <path d="M32 19 L40 175 Q41 185 52 185 L108 185 Q119 185 120 175 L128 19" fill="none"
         stroke="var(--primary-text-color,#233245)" stroke-width="3" stroke-linecap="round"/>
   ${p>0?`<g clip-path="url(#jdhl-cup)"><rect x="32" y="${y}" width="96" height="185" fill="#59baf2" opacity=".9">
      <animate attributeName="y" from="${fromY}" to="${y}" dur="650ms" fill="freeze"/></rect>
      <path d="${w0}" stroke="#a2dcff" stroke-width="3" fill="none">
       <animate attributeName="d" values="${w0};${w1};${w0}" dur="2.7s" repeatCount="indefinite"/></path></g>`:''}
   <path d="M38 ${targetY} L122 ${targetY}" stroke="#fff" stroke-opacity=".95" stroke-width="5" stroke-dasharray="4 5" stroke-linecap="round"/>
   <path d="M38 ${targetY} L122 ${targetY}" stroke="#e04444" stroke-width="2.6" stroke-dasharray="4 5" stroke-linecap="round"/>
   <text x="80" y="30" text-anchor="middle" font-size="15" fill="#e03535" font-weight="650" stroke="#fff" stroke-width="3" paint-order="stroke">${jdhlFmt(target)}</text>
   ${p<96?`<text x="80" y="${remainingY}" text-anchor="middle" font-size="16" fill="var(--primary-text-color,#172b3b)" font-weight="500" stroke="var(--card-background-color,#fff)" stroke-width="2" paint-order="stroke">${jdhlFmt(remaining)}</text>`:''}
  </svg>`;
 }
 _dayBarsHTML(){
  const date=this._viewDate||this._todayISO(),isToday=date===this._todayISO();
  const ready=this._history?.date===date;
  const all=ready?(this._history?.day_summary?.liquid_breakdown||[]):[];
  const defs=this._liquidDefs();const label=id=>defs.find(t=>t.id===id)?.name||(id==='unknown'?'Unknown (legacy)':id);
  const data=all.filter(x=>Number(x.volume_ml)>0).sort((a,b)=>Number(b.volume_ml)-Number(a.volume_ml));
  const heading=isToday?'Today by liquid':`By liquid <span class="bars-date">${jdhlIsoToDate(date)}</span>`;
  if(!data.length)return `<div class="liquid-bars"><div class="bars-title">${heading}</div><p class="muted">${ready?'No classified drinks on this day.':'Loading day…'}</p></div>`;
  const high=Math.max(...data.map(x=>Number(x.volume_ml)));
  return `<div class="liquid-bars" aria-label="Volumes by liquid type on selected day"><div class="bars-title">${heading}</div>
   ${data.map(x=>`<div class="bar-line"><span title="${jdhlEscape(label(x.liquid_type))}">${jdhlEscape(label(x.liquid_type))}</span>
      <div class="bar-track"><div class="bar-fill" style="width:${(100*Number(x.volume_ml)/high).toFixed(2)}%"></div></div>
      <strong>${jdhlFmt(Number(x.volume_ml))}</strong></div>`).join('')}</div>`;
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
   ${table}</section>`;
 }
 _manageHTML(){const d=this._customDraft;
  const all=this._liquidDefs();const visible=all.filter(t=>!t.hidden);
  const hidden=all.filter(t=>t.hidden);
  const list=visible.map((t,index)=>`<div class="saved-liquid" data-testid="liquid-manage-row">
   ${this._liquidIcon(t)} <strong>${jdhlEscape(t.name)}</strong>
   <span class="muted">${t.default_volume_ml?jdhlFmt(t.default_volume_ml):'No default'}</span>
   <button class="secondary small" data-action="manage-up" data-value="${jdhlEscape(t.id)}" ${index===0?'disabled':''} aria-label="Move ${jdhlEscape(t.name)} up">↑</button>
   <button class="secondary small" data-action="manage-down" data-value="${jdhlEscape(t.id)}" ${index===visible.length-1?'disabled':''} aria-label="Move ${jdhlEscape(t.name)} down">↓</button>
   <button class="secondary small" data-action="manage-edit" data-value="${jdhlEscape(t.id)}">Edit</button>
   ${t.custom?`<button class="secondary small" data-action="manage-remove" data-value="${jdhlEscape(t.id)}" title="Delete custom type only when unused">Delete</button>`:`<button class="secondary small" data-action="manage-hide" data-value="${jdhlEscape(t.id)}" title="Remove built-in from Add choices; keep drink history">Delete</button>`}
   </div>`).join('');
  return `<div class="manage">
   <h3>Manage liquid types</h3><p class="muted manage-intro">Change names, icons, defaults and order. Delete built-in buttons to hide them; prior drinks remain available. Restore hidden types below.</p>
   ${this._error?`<p role="alert" class="error">${jdhlEscape(this._error)}</p>`:''}
   ${d?`<div class="manage-editor"><h4>${this._editingLiquidId?'Edit liquid':'Add liquid'}</h4>
    <div class="manage-form-grid">
     <label>Liquid name<input data-field="custom_name" maxlength="48" value="${jdhlEscape(d.custom_name||'')}" placeholder="e.g. Orange juice"/></label>
     <label>Default volume (mL)<input data-field="custom_default_volume_ml" type="number" min="0.01" max="100000" step="any" value="${jdhlEscape(d.custom_default_volume_ml??'')}" placeholder="No default"/></label>
     <label>Material Design Icon<input data-field="icon_mdi" value="${jdhlEscape(d.icon_mdi||'')}" placeholder="mdi:glass-mug-variant"/></label>
     <label class="svg-field">Or SVG icon (.svg, max 16 KB)<input data-field="custom_svg_file" type="file" accept=".svg,image/svg+xml"/></label>
    </div>${d.icon_svg?`<p class="status">SVG selected (${new TextEncoder().encode(d.icon_svg).length} bytes)</p>`:''}
    <div class="dialog-actions"><button class="secondary" data-action="manage-cancel">Back</button>
     <button data-action="manage-save" ${this._busy?'disabled':''}>Save liquid</button></div></div>`:
    `<div class="saved-liquids">${list||'<p class="muted">No visible types. Restore one below or add your own.</p>'}</div>
     ${hidden.length?`<h4>Hidden built-in liquid types</h4><div class="hidden-liquids">${hidden.map(t=>
        `<div class="hidden-liquid">${this._liquidIcon(t)} <strong>${jdhlEscape(t.name)}</strong>
         <button class="secondary small" data-action="manage-restore" data-value="${jdhlEscape(t.id)}">Restore</button></div>`).join('')}</div>`:''}
     ${this._managePendingDelete?`<div class="delete-warning" role="alert">${this._managePendingDelete.custom?
        `Permanently delete ${jdhlEscape(this._managePendingDelete.name)}? Only unused custom types can be deleted.`:
        `Remove ${jdhlEscape(this._managePendingDelete.name)} from Add choices? History and Excel remain intact; you can restore it later.`}
        <div class="dialog-actions"><button class="secondary" data-action="manage-delete-cancel">Cancel</button>
         <button class="danger" data-action="manage-delete-confirm">Confirm delete</button></div></div>`:''}
     <div class="dialog-actions"><button class="secondary" data-action="manage-cancel">Back to drink</button>
     <button data-action="manage-add">+ Add liquid</button></div>`}
  </div>`;
 }
 _volumeManageHTML(){const entries=this._volumeDraft||[];
  return `<div class="manage"><h3>Manage volume buttons</h3>
   <p class="muted">Add, edit, remove or reorder the volume buttons for this hydration profile. These settings persist after restart.</p>
   ${this._error?`<p role="alert" class="error">${jdhlEscape(this._error)}</p>`:''}
   <div class="volume-rows">${entries.map((value,index)=>`<div class="volume-edit-row">
    <label>Button ${index+1} (mL)<input type="number" data-field="volume_button" data-index="${index}" step="any" min="0.01" max="100000" value="${jdhlEscape(value)}"/></label>
    <button data-action="volume-up" data-index="${index}" class="secondary small" ${index===0?'disabled':''} aria-label="Move volume up">↑</button>
    <button data-action="volume-down" data-index="${index}" class="secondary small" ${index===entries.length-1?'disabled':''} aria-label="Move volume down">↓</button>
    <button data-action="volume-remove" data-index="${index}" class="secondary small">Remove</button>
   </div>`).join('')}</div>
   <div class="dialog-actions"><button class="secondary" data-action="volume-add" ${entries.length>=24?'disabled':''}>+ Add volume</button>
    <button class="secondary" data-action="volume-cancel">Cancel</button>
    <button data-action="volume-save" ${this._busy?'disabled':''}>Save buttons</button></div>
  </div>`;
 }
 _modalHTML(){if(!this._modal)return '';
  const m=this._modal;
  const types=this._liquidDefs().filter(t=>!t.hidden||(m.mode==='edit'&&t.id===m.liquid_type)).map(t=>`<button class="liquid-choice ${m.liquid_type===t.id?'selected':''}"
    data-action="type" data-value="${jdhlEscape(t.id)}" aria-pressed="${m.liquid_type===t.id}">
    ${this._liquidIcon(t)}<span>${jdhlEscape(t.name)}</span></button>`).join('');
  const amounts=this._buttons().map(v=>`<button class="amount ${Number(m.volume_ml)===v?'selected':''}"
     data-action="amount" data-value="${v}">${jdhlFmt(v)}</button>`).join('');
  return `<div class="overlay" role="presentation"><section class="dialog ${this._volumeManageOpen?'dialog-manage-volumes':this._manageOpen?'dialog-manage-liquids':'dialog-drink'}" role="dialog" aria-modal="true"
    aria-label="${m.mode==='edit'?'Edit drink moment':'Add drink moment'}">
   ${this._volumeManageOpen?this._volumeManageHTML():this._manageOpen?this._manageHTML():`
    <h3>${m.mode==='edit'?'Edit drink moment':'Add drink moment'}</h3>
    ${this._error?`<p class="error" role="alert">${jdhlEscape(this._error)}</p>`:''}
    <div class="modal-heading">Liquid type</div><div class="liquid-choices">${types}</div>
    ${this._hass?.user?.is_admin?`<button class="manage-control small add-type" data-action="manage-liquids">⚙ Manage liquid types</button>`:''}
    <div class="modal-heading">Volume (mL)</div><div class="volume-choices">${amounts}</div>
    ${this._hass?.user?.is_admin?`<button class="manage-control small manage-volumes" data-action="manage-volumes">⚙ Manage volume buttons</button>`:''}
    <div class="fields">
     <label>Custom amount (mL)<input data-field="volume_ml" type="number" step="any" min="0.01" max="100000" value="${jdhlEscape(m.volume_ml)}" placeholder="Enter or select"/></label>
     <label>Date (DD-MM-YYYY)<div class="date-select"><button type="button" class="date-trigger secondary" data-action="calendar-toggle" aria-label="Choose date" aria-expanded="${this._calendarOpen}">${jdhlEscape(m.date)} <span aria-hidden="true">▦</span></button>${this._calendarHTML()}</div></label>
     <label>Time (24-hour)<input data-field="time" type="text" inputmode="numeric" autocapitalize="off" autocomplete="off" spellcheck="false" placeholder="1430 → 14:30" title="Type 0930 for 09:30; colon is optional" value="${jdhlEscape(m.time)}"/></label>
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
  const selectedDate=this._viewDate||this._todayISO(),isToday=selectedDate===this._todayISO();
  const daySummary=this._history?.date===selectedDate?this._history?.day_summary:null;
  const pendingPast=!isToday&&!daySummary;
  const target=Number(daySummary?.target_ml??(isToday?this._millilitres('daily_target','target_ml'):0));
  const consumed=Number(daySummary?.consumed_ml??(isToday?this._millilitres('consumed_today','consumed_ml'):0));
  const remaining=Math.max(0,target-consumed),pct=target?consumed/target*100:0;
  const title=this._config.title||'jwDaily Hydration Log';
  const count=Number(daySummary?.drink_count??(isToday?jdhlNum(this._state('drink_count_today')?.state):0));
  const k=JSON.stringify([target,consumed,this._history,this._modal,this._calendarOpen,this._calendarMonth,this._manageOpen,this._customDraft,this._volumeManageOpen,this._volumeDraft,this._confirmDelete,this._busy,this._error,this._status,this._viewDate,this._undoId,this._config]);
  if(!force&&this._lastRender===k)return;this._lastRender=k;
  this.shadowRoot.innerHTML=`<style>
  :host{display:block;min-width:0;max-width:100%}
  ha-card{display:block;max-width:100%;box-sizing:border-box;overflow:hidden}
  .root{box-sizing:border-box;display:flex;flex-direction:column;gap:7px;min-width:0;padding:18px 20px 12px;color:var(--primary-text-color,#202a32)}
  header h2{font-size:1.15rem;font-weight:650;margin:0}
  .muted{color:var(--secondary-text-color,#63717d)}
  .error{color:var(--error-color,#b52027);font-size:.86rem}
  .center{text-align:center}
  .hero-shell{container-type:inline-size;max-width:100%;min-width:0}
  .hero{display:grid;grid-template-columns:274px minmax(0,1fr);gap:9px;min-width:0;align-items:start}
  .glass-side{width:274px;max-width:100%;min-width:0}
  .glass-stack{display:grid;grid-template-columns:108px 160px;grid-template-rows:200px 24px;column-gap:6px;width:274px;max-width:100%;align-items:start}
  .taken-slot{position:relative;grid-column:1;grid-row:1;height:200px;min-width:0}
  .taken{position:absolute;right:0;top:var(--fill-y);transform:translateY(-50%);color:#168dd1;font-size:24px;font-weight:700;line-height:1.13;white-space:nowrap;text-align:right}
  .glass-frame{grid-column:2;grid-row:1;width:160px;min-width:0}
  .glass{display:block;width:160px;height:200px;margin:0;max-width:100%}
  .drink-count{grid-column:2;grid-row:2;margin:0;width:160px;text-align:center;white-space:nowrap;font-size:.85rem;line-height:1.4}
  .hero-side{min-width:0;width:100%;max-width:100%;height:224px;display:flex;flex-direction:column;overflow:hidden;padding:1px 0 0;box-sizing:border-box}
  .liquid-bars{align-self:stretch;min-width:0;max-width:100%;width:100%;overflow:hidden}
  .bars-title{font-size:.88rem;font-weight:650;margin:0 0 11px;line-height:1.3}
  .bars-date{font-size:.74rem;font-weight:450}
  .bar-line{display:grid;grid-template-columns:minmax(74px,1.15fr) minmax(42px,1fr) max-content;gap:7px;align-items:center;min-width:0;width:100%;margin:9px 0;font-size:.82rem}
  .bar-line span{overflow:hidden;text-overflow:ellipsis;white-space:nowrap;min-width:0}
  .bar-line strong{font-size:.8rem;font-weight:600;white-space:nowrap;text-align:right;font-variant-numeric:tabular-nums}
  .bar-track{height:11px;min-width:0;border-radius:8px;background:var(--secondary-background-color,#e5e7eb);overflow:hidden}
  .bar-fill{height:100%;background:#34a5dc;border-radius:8px;min-width:2px}
  .hero-actions{margin-top:auto;display:flex;justify-content:flex-end;padding:4px 0 0;min-width:0}
  .hero-actions .add-drink{font-size:.86rem;font-weight:650;min-width:0;max-width:100%;padding:7px 12px;line-height:1.2;border-radius:13px;white-space:nowrap}
  .day-loading{font-size:.93rem;color:var(--secondary-text-color);padding:22px 8px;min-height:140px}
  .history{border-top:1px solid var(--divider-color,#ddd);padding-top:11px;margin-top:1px}
  .history-head{display:flex;justify-content:space-between;align-items:center;gap:10px}
  .history h3{font-size:1.05rem;font-weight:650;margin:0}
  .history-head .muted{font-size:.88rem}
  .date-nav{display:flex;align-items:center;justify-content:flex-start;gap:6px;margin:7px 0}
  .date-nav input{width:160px;max-width:48%;box-sizing:border-box;text-align:center;font:inherit;font-size:1.23rem;font-weight:700;line-height:1.2;padding:7px 8px;color:var(--primary-text-color);background:#fff;border:1px solid var(--divider-color,#bbb);border-radius:9px}
  .date-nav button{font-size:1rem;padding:6px 10px;min-height:34px}
  .history-table{max-height:360px;overflow-y:auto;overflow-x:hidden}
  .history-table table{border-collapse:collapse;table-layout:fixed;width:100%;min-width:0}
  .history-table th{padding:7px 6px;border-bottom:1px solid var(--divider-color,#ddd);font-size:.91rem;font-weight:500;color:var(--secondary-text-color,#667);text-align:left}
  .history-table tr{height:38px}
  .history-table td{height:38px;box-sizing:border-box;padding:4px 6px;line-height:1.15;font-size:1rem;vertical-align:middle;font-variant-numeric:tabular-nums;border-bottom:1px solid var(--divider-color,#ddd)}
  .history-table th:first-child,.history-table td:first-child{width:27%}
  .history-table th:last-child,.history-table td:last-child{width:29%}
  .history-table td.right,.history-table th.right{text-align:right;white-space:nowrap}
  .history-table tr[data-action]{cursor:pointer}
  .history-table tr[data-action]:hover{background:color-mix(in srgb,#b3e5fc 30%,white)}
  .export{border-top:1px solid var(--divider-color,#ddd);margin:0;padding:7px 0 0;text-align:left;align-self:stretch}
  .export button{font-size:.79rem;padding:6px 10px}
  .card-version{align-self:flex-end;margin:0;font-size:.72rem;color:var(--secondary-text-color,#666)}
  /* Centralized normal button palette: also applies to liquid/volume selections and modal actions. */
  button,button.secondary,button.small,button.liquid-choice,button.amount,button.danger{
    font:inherit;cursor:pointer;background:#B3E5FC;color:#18374b;
    border:1px solid #71b4d2;border-radius:11px;padding:6px 10px;
    box-sizing:border-box;transition:background-color .14s ease,border-color .14s ease,box-shadow .14s ease}
  button:hover:not(:disabled){background:#95d9f9;border-color:#3e96c2}
  button:active:not(:disabled){background:#80cfee}
  button:focus-visible{outline:2px solid #0578b3;outline-offset:2px}
  button.selected,button.liquid-choice.selected,button.amount.selected{
    background:#B3E5FC;color:#092e48;border-color:#046eac;
    box-shadow:inset 0 0 0 2px #046eac;font-weight:650}
  button:disabled{opacity:.39;filter:grayscale(.32);cursor:not-allowed;box-shadow:none}
  button.small{padding:5px 8px;border-radius:9px;font-size:.85rem}
  button.danger{color:#9a2525;border-color:#bd7a7a}
  button.manage-control,button.manage-control:not(:disabled){background:#EEEEEE;border-color:#c8ccd0;color:#242a30}
  button.manage-control:hover:not(:disabled){background:#dcdcdc;border-color:#9e9e9e}
  .overlay{position:fixed;inset:0;z-index:10000;background:rgba(0,0,0,.4);display:flex;align-items:center;justify-content:center;padding:14px;box-sizing:border-box}
  .dialog{width:min(660px,100%);box-sizing:border-box;max-height:calc(100vh - 28px);overflow-y:auto;background:var(--card-background-color,#fff);color:var(--primary-text-color,#222);border-radius:15px;padding:18px;box-shadow:0 15px 45px #0004}
  .dialog.dialog-manage-liquids{width:min(555px,100%)}
  .dialog.dialog-manage-volumes{width:min(450px,100%)}
  .dialog h3{margin:0 0 11px;font-size:1.19rem}
  .modal-heading{font-size:.95rem;font-weight:650;margin:11px 0 6px}
  .liquid-choices,.volume-choices{display:flex;flex-wrap:wrap;gap:6px;align-items:center}
  .liquid-choice,.volume-choices .amount{font-size:.93rem!important;line-height:1.2;min-height:34px;padding:5px 9px!important}
  .liquid-choice{display:inline-flex;align-items:center;gap:5px}
  .liquid-icon{width:23px;height:23px;min-width:23px;--mdc-icon-size:23px;display:inline-block;object-fit:contain}
  .volume-choices{margin-bottom:8px}
  .add-type,.manage-volumes{margin-top:7px;font-size:.86rem}
  .fields{display:grid;grid-template-columns:repeat(3,minmax(0,165px));gap:10px;justify-content:start;margin-top:8px}
  .fields label{min-width:0;display:flex;flex-direction:column;gap:5px;font-size:.91rem}
  .fields input,.fields select{min-width:0;width:100%;box-sizing:border-box;background:#fff;color:#222;border:1px solid #b8c4cc;border-radius:8px;padding:9px 8px;font:inherit;font-size:1.08rem}
  .date-select{position:relative}
  button.date-trigger,button.date-trigger:not(:disabled),button.date-trigger:hover:not(:disabled){
    display:flex;justify-content:space-between;align-items:center;gap:8px;width:100%;
    background:#FFFFFF;color:#222;border:1px solid #b8c4cc;border-radius:8px;
    text-align:left;font-size:1.08rem;padding:9px 8px;line-height:1.3}
  .cal-popover{position:relative;margin-top:7px;z-index:10100;background:#fff;border:1px solid #bbb;border-radius:10px;padding:10px;min-width:240px;box-shadow:0 8px 26px #0003}
  .cal-title{display:flex;justify-content:space-between;align-items:center;gap:6px;margin-bottom:8px;font-size:.9rem}
  .cal-grid{display:grid;grid-template-columns:repeat(7,1fr);gap:2px}
  .cal-weekday{text-align:center;color:#67717a;font-size:.75rem;padding:5px 0}
  .cal-day{font-size:.82rem!important;padding:5px 2px!important;border-radius:6px!important}
  .cal-day.current{box-shadow:inset 0 0 0 2px #046eac}
  .dialog-actions{display:flex;justify-content:flex-end;gap:7px;flex-wrap:wrap;margin-top:12px}
  .dialog-actions button:first-child.danger{margin-right:auto}
  .manage-intro{font-size:.82rem;line-height:1.35;color:var(--secondary-text-color,#667);margin:2px 0 9px}
  .saved-liquids{display:flex;flex-direction:column;gap:0;margin-top:5px}
  .saved-liquid{display:grid;grid-template-columns:27px minmax(78px,1fr) minmax(60px,auto) 30px 30px 43px 58px;gap:5px;align-items:center;padding:4px 0;border-bottom:1px solid var(--divider-color,#ddd);min-width:0}
  .saved-liquid .muted{font-size:.81rem;white-space:nowrap;text-align:right}
  .saved-liquid strong{font-size:.91rem;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
  .saved-liquid button{min-width:0;max-width:100%;padding:4px 4px;font-size:.78rem}
  .hidden-liquid{display:flex;align-items:center;gap:8px;padding:4px 0;border-bottom:1px solid var(--divider-color,#ddd)}
  .hidden-liquid button{margin-left:auto}
  .manage h4{font-size:.94rem;margin:12px 0 5px}
  .manage-editor{border-top:1px solid var(--divider-color,#ddd);padding-top:7px}
  .manage-form-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:9px}
  .manage-form-grid label{display:flex;flex-direction:column;gap:4px;min-width:0;font-size:.88rem}
  .manage-form-grid input{width:100%;min-width:0;box-sizing:border-box;padding:8px;background:#fff;border:1px solid #bbb;border-radius:8px;font:inherit}
  .manage-form-grid .svg-field{grid-column:1/-1}
  .manage-form-grid input[type=file]{font-size:.8rem;padding:6px}
  .volume-rows{display:flex;flex-direction:column;gap:2px}
  .volume-edit-row{display:grid;grid-template-columns:minmax(100px,1fr) 32px 32px 75px;gap:5px;align-items:end;border-bottom:1px solid var(--divider-color,#ddd);padding:3px 0 5px}
  .volume-edit-row label{font-size:.85rem;display:flex;flex-direction:column;gap:3px;min-width:0}
  .volume-edit-row input{width:100%;max-width:130px;min-width:0;box-sizing:border-box;border:1px solid #bbb;border-radius:8px;background:#fff;color:#222;font:inherit;font-size:1rem;padding:6px}
  .volume-edit-row button{padding:5px 4px!important;font-size:.78rem!important}
  .delete-warning{margin-top:12px;padding:9px;border:1px solid #b54242;border-radius:8px;color:#9b2121;font-size:.88rem}
  .status{font-size:.82rem;color:var(--secondary-text-color)}
  @container(max-width:510px){
    .hero{grid-template-columns:minmax(0,1fr);gap:5px}
    .glass-side{margin:0 auto}
    .hero-side{height:auto;min-height:0}
    .hero-actions{margin-top:6px}
  }
  @container(max-width:320px){.bar-line{grid-template-columns:minmax(60px,1fr) minmax(35px,1fr) max-content;gap:4px}}
  @media(max-width:570px){.dialog.dialog-manage-liquids{width:min(98vw,555px)}}
  @media(max-width:475px){
    .saved-liquid{grid-template-columns:25px minmax(90px,1fr) minmax(65px,auto);row-gap:4px}
    .saved-liquid button{grid-row:2}
    .volume-edit-row{grid-template-columns:minmax(95px,1fr) 32px 32px 70px}
    .fields{grid-template-columns:repeat(2,minmax(0,1fr))}
  }
  @media(max-width:380px){.root{padding:12px}.fields{grid-template-columns:1fr}.dialog{padding:12px}}

  </style><ha-card><div class="root">
   ${this._config.show_title!==false?`<header><h2>${jdhlEscape(title)}</h2></header>`:''}
   <div class="hero-shell">
    ${pendingPast?`<p class="day-loading">Loading ${jdhlEscape(jdhlIsoToDate(selectedDate))}…</p>`:`
    <div class="hero">
      <div class="glass-side"><div class="glass-stack">
        <div class="taken-slot"><span class="taken" style="--fill-y:${(100*(pct>100?19:179-(179-39)*Math.min(100,Math.max(0,pct))/100)/200).toFixed(2)}%">${jdhlFmt(consumed)}</span></div>
        <div class="glass-frame">${this._config.show_cup!==false?this._glass(pct,remaining,target):''}</div>
        <div class="drink-count">◷ ${count} drink moments</div>
      </div></div>
      <div class="hero-side">${this._dayBarsHTML()}
        ${this._config.show_manual!==false?`<div class="hero-actions">
          <button class="add-drink" data-action="new" ${this._busy?'disabled':''}>+ Add drink</button>
        </div>`:''}
      </div>
    </div>`}</div>
   ${this._error?`<div class="error" role="alert">${jdhlEscape(this._error)}</div>`:''}
   ${this._historyHTML()}
   ${this._config.show_export!==false&&this._hass?.user?.is_admin?`<div class="export"><button class="secondary" data-action="export" ${this._busy?'disabled':''}>Export all data to Excel (.xlsx)</button></div>`:''}
   ${this._modalHTML()}
   <footer class="card-version">v1.1.0-beta.11</footer></div></ha-card>`;
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
console.info('jwDaily Hydration Log Card v1.1.0-beta.11');
