/* jwDaily Hydration Log v1.1.0-beta.31 - independent Home Assistant Lovelace card.
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

const jdhlHex=v=>/^#[0-9A-Fa-f]{6}$/.test(String(v||''))?String(v).toUpperCase():null;
function jdhlContrastInk(hex){
 const value=jdhlHex(hex);if(!value)return '#14212D';
 const rgb=[1,3,5].map(i=>parseInt(value.slice(i,i+2),16)/255)
  .map(c=>c<=.04045?c/12.92:((c+.055)/1.055)**2.4);
 const light=.2126*rgb[0]+.7152*rgb[1]+.0722*rgb[2];
 const darkRgb=[0x14,0x21,0x2D].map(v=>v/255).map(c=>c<=.04045?c/12.92:((c+.055)/1.055)**2.4);
 const dark=.2126*darkRgb[0]+.7152*darkRgb[1]+.0722*darkRgb[2];
 return 1.05/(light+.05)>(light+.05)/(dark+.05)?'#FFFFFF':'#14212D';
}

class JwDailyHydrationLogCard extends HTMLElement {
 constructor(){
  super();this.attachShadow({mode:'open'});
  this._hass=null;this._config=null;this._history=null;this._viewDate=null;
  this._selectedType=null;this._selectedVolume=null;this._undoId=null;this._modal=null;this._confirmDelete=false;
  this._manageOpen=false;this._customDraft=null;this._editingLiquidId=null;
  this._glassPrevY=179;
  this._managePendingDelete=null;
  this._settingsSection=null;this._settingsDraft=null;this._settingsEditId=null;this._settingsDeleteQuickId=null;
  this._settingsImportContent='';this._settingsImportPreview=null;this._settingsImportFilename='';
  this._dataImportContent='';this._dataImportFilename='';this._dataImportMode='merge';this._dataImportPreview=null;
  this._fullRestoreContent='';this._fullRestoreFilename='';this._fullRestorePreview=null;this._fullBackupSaved=false;
  this._profilesData=null;this._profileDraft=null;this._profileEditSlug='';
  this._calendarOpen=false;this._calendarMonth=null;this._historyCalendarOpen=false;this._historyCalendarMonth=null;
  this._busy=false;this._error='';this._status='';this._lastState='';this._lastRender='';
  this._fetching=false;this._fetchAgain=false;this._tickTimer=null;
  this.shadowRoot.addEventListener('click',e=>this._click(e));
  this.shadowRoot.addEventListener('input',e=>this._field(e));
  this.shadowRoot.addEventListener('change',e=>this._field(e));
  this.shadowRoot.addEventListener('keydown',e=>{
   if(e.key==='Escape'&&this._historyCalendarOpen){this._historyCalendarOpen=false;this._render(true);return;}
   if(e.key==='Escape'&&this._calendarOpen){this._calendarOpen=false;this._render(true);return;}
   if(e.key==='Escape'&&this._settingsSection){this._settingsSection=null;this._settingsDraft=null;
    this._manageOpen=false;this._render(true);return;}
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
  this._glassPrevY=179;
  this._managePendingDelete=null;
  this._settingsSection=null;this._settingsDraft=null;this._settingsEditId=null;this._settingsDeleteQuickId=null;
  this._settingsImportContent='';this._settingsImportPreview=null;this._settingsImportFilename='';
  this._dataImportContent='';this._dataImportFilename='';this._dataImportMode='merge';this._dataImportPreview=null;
  this._fullRestoreContent='';this._fullRestoreFilename='';this._fullRestorePreview=null;this._fullBackupSaved=false;
  this._profilesData=null;this._profileDraft=null;this._profileEditSlug='';
  this._calendarOpen=false;this._calendarMonth=null;this._historyCalendarOpen=false;this._historyCalendarMonth=null;
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
  if(field==='data_import_mode'&&e.type==='change'){
   this._dataImportMode=e.target.value;this._dataImportPreview=null;this._render(true);return;
  }
  if(field==='full_backup_verified'){this._fullBackupSaved=!!e.target.checked;this._render(true);return;}
  if(field==='model_unknown_confirmed'){
   this._modelUnknownConfirmed=!!e.target.checked;return;
  }
  if((field==='data_import_file'||field==='full_restore_file')&&e.type==='change'){
   const file=e.target.files?.[0];if(!file)return;
   const max=field==='data_import_file'?12000000:14000000;
   if(file.size>max){this._alert('Import file exceeds maximum allowed size.');return;}
   try{
    if(field==='data_import_file'){
     this._dataImportContent=await file.text();this._dataImportFilename=file.name;this._dataImportPreview=null;
    }else{
     const b=await file.arrayBuffer();const data=new Uint8Array(b);let chunks=[];
     for(let i=0;i<data.length;i+=8192)chunks.push(String.fromCharCode(...data.subarray(i,i+8192)));
     this._fullRestoreContent=btoa(chunks.join(''));this._fullRestoreFilename=file.name;this._fullRestorePreview=null;
    }
    this._error='';this._render(true);
   }catch(err){this._alert(err);}return;
  }
  if(field==='settings_import_file'&&e.type==='change'){
   const file=e.target.files?.[0];if(!file)return;
   if(file.size>256000){this._alert('Settings file must be 256 KB or smaller.');return;}
   try{this._settingsImportContent=await file.text();this._settingsImportFilename=file.name;
    this._settingsImportPreview=null;this._error='';this._render(true);}
   catch(err){this._alert(err);}return;
  }
  if(this._settingsSection==='profile'&&this._profileDraft&&Object.hasOwn(this._profileDraft,field)){
   this._profileDraft[field]=e.target.type==='checkbox'?e.target.checked:e.target.value;return;
  }
  if(this._settingsSection && this._settingsDraft && Object.hasOwn(this._settingsDraft,field)){
   this._settingsDraft[field]=e.target.value;
   if(field==='label_mode'&&e.type==='change')this._render(true);
   return;
  }
  if(this._manageOpen&&this._customDraft){
   if(field==='color_picker'||field==='color_hex'){
    const draft=this._customDraft;
    const entered=field==='color_picker'?e.target.value:String(e.target.value).trim();
    const color=jdhlHex(entered);
    draft.color_custom=true;
    draft.color_hex=color&&(field==='color_picker'||e.type==='change')?color:entered;
    if(color){
     const picker=this.shadowRoot.querySelector('[data-field="color_picker"]');
     const hexInput=this.shadowRoot.querySelector('[data-field="color_hex"]');
     if(picker&&picker!==e.target)picker.value=color.toLowerCase();
     if(hexInput&&hexInput!==e.target)hexInput.value=color;
     else if(hexInput&&e.type==='change')hexInput.value=color;
    }
    const preview=this.shadowRoot.querySelector('.color-preview');
    if(preview&&color)preview.style.backgroundColor=color;
    const error=this.shadowRoot.querySelector('.color-error');
    if(error){error.textContent=color?'':'Enter a valid color in #RRGGBB format.';
              error.hidden=!!color;}
    return;
   }
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
  JDHL_TYPES.map(([id,name,icon])=>({id,name,icon_mdi:({water:'mdi:water',coffee:'mdi:coffee',tea:'mdi:tea',milk:'mdi:cow',soup:'mdi:bowl-mix',wine:'mdi:glass-wine',other:'mdi:glass-water'})[id],icon_svg:'',custom:false}));}
 _liquidInfo(id){return this._liquidDefs().find(t=>t.id===id);}
 _cupDefs(){return this._history?.cup_types||[];}
 _cupInfo(id){return this._cupDefs().find(c=>c.id===id);}
 _quickDefs(){return this._history?.quick_buttons||[];}
 _liquidName(id){return this._liquidInfo(id)?.name||id||'Unknown';}
 _effectiveQuickLabel(q){return q.label_mode==='custom'?q.custom_label:
  `${this._liquidName(q.liquid_type_id)} (${this._cupInfo(q.cup_type_id)?.name||'Unknown cup'})`;}

 _effectiveColor(t){return jdhlHex(t?.color)||jdhlHex(t?.color_override)||jdhlLiquidColor(t?.id,t?.name);}
 _typeColor(id,name){return this._effectiveColor(this._liquidInfo(id)||{id,name});}
 _liquidIcon(t,tinted=false){if(!t)return '';
  if(t.icon_svg){const src='data:image/svg+xml;charset=utf-8,'+encodeURIComponent(t.icon_svg);
   // Monochrome user SVGs can be tinted as an alpha mask. Preserve intentionally
   // multicolour SVGs exactly as uploaded instead of destroying their artwork.
   const declared=[...String(t.icon_svg).matchAll(/(?:fill|stroke)\s*=\s*["']([^"']+)["']/gi)]
       .map(x=>x[1].toLowerCase()).filter(x=>!['none','currentcolor','transparent'].includes(x));
   if(tinted&&new Set(declared).size<=1)
    return `<span class="liquid-icon svg-icon masked-icon" aria-hidden="true" style="background-color:${this._effectiveColor(t)};mask-image:url(&quot;${jdhlEscape(src)}&quot;);-webkit-mask-image:url(&quot;${jdhlEscape(src)}&quot;)"></span>`;
   return `<img class="liquid-icon svg-icon" alt="" src="${jdhlEscape(src)}"/>`;}
  const icon=/^mdi:[a-z0-9-]+$/.test(t.icon_mdi||'')?t.icon_mdi:'mdi:glass-mug-variant';
  return `<ha-icon class="liquid-icon${tinted?' tinted-liquid-icon':''}" icon="${jdhlEscape(icon)}"
    ${tinted?`style="color:${this._effectiveColor(t)}"`:''} aria-hidden="true"></ha-icon>`;
 }
 _newLiquidDraft(existing=null){return {custom_name:existing?.name||'',icon_mdi:existing?existing.icon_mdi:'mdi:glass-mug-variant',
  icon_svg:existing?.icon_svg||'',
  color_custom:!!jdhlHex(existing?.color_override),
  color_hex:jdhlHex(existing?.color_override)||this._effectiveColor(existing||{id:'',name:''})};}
 async _saveCustomLiquid(){const draft=this._customDraft;if(!draft||!this._hass?.user?.is_admin)return;
  const name=String(draft.custom_name||'').trim();
  if(!name||name.length>48){this._alert('Enter a liquid name of 1-48 characters.');return;}
  const color=draft.color_custom?jdhlHex(draft.color_hex):null;
  if(draft.color_custom&&!color){this._alert('Enter a valid color in #RRGGBB format.');return;}
  const existingId=this._editingLiquidId;
  this._busy=true;this._error='';this._status=existingId?'Updating liquid type…':'Saving liquid type…';
  try{await this._ensureBackend();const saved=await this._hass.callWS({type:existingId?'jw_daily_hydration_log/update_liquid_type':'jw_daily_hydration_log/add_liquid_type',
   profile:this._config.profile,...(existingId?{liquid_type:existingId}:{}),name,
   icon_mdi:draft.icon_mdi||'',icon_svg:draft.icon_svg||'',color:color||''});
   await this._fetchHistory();this._customDraft=null;this._editingLiquidId=null;
   if(!existingId&&this._modal?.mode==='new'){
    this._modal.liquid_type=saved.id;
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
 _buttons(){const values=null;
  return Array.isArray(values)?values:jdhlQuick(this._config?.quick_add);}
 _selectedRecord(id){return (this._history?.entries||[]).find(r=>String(r.id)===id);}
 _openEdit(id){const r=this._selectedRecord(id);if(!r)return;
  const d=new Date(r.timestamp);const parts=this._timeParts(d);this._modal={mode:'edit',id:r.id,
   liquid_type:r.liquid_type==='unknown'?'':r.liquid_type,cup_type_id:r.cup_type_id||'',quick_button_id:'',
   volume_ml:String(r.volume_ml),date:parts.date,time:parts.time};
  this._calendarOpen=false;this._calendarMonth=null;this._historyCalendarOpen=false;this._historyCalendarMonth=null;this._confirmDelete=false;this._render(true);
 }
 _timeParts(d){
  const tz=this._hass?.config?.time_zone||'Europe/Amsterdam';
  const pts=new Intl.DateTimeFormat('en-GB',{timeZone:tz,year:'numeric',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',second:'2-digit',hourCycle:'h23'}).formatToParts(d);
  const p=Object.fromEntries(pts.map(x=>[x.type,x.value]));
  return {date:`${p.day}-${p.month}-${p.year}`,time:`${p.hour}:${p.minute}:${p.second}`};
 }
 _openNew(){this._modal={mode:'new',id:'',liquid_type:'',cup_type_id:'',quick_button_id:'',volume_ml:'',date:jdhlIsoToDate(this._viewDate||this._todayISO()),time:this._nowTime()};this._calendarOpen=false;this._calendarMonth=null;this._historyCalendarOpen=false;this._historyCalendarMonth=null;this._confirmDelete=false;this._render(true);}
 _payload(){const m=this._modal,volume=Number(m?.volume_ml),date=m?.date?.trim(),time=jdhlNormalizeTime(m?.time);
  if(!this._liquidInfo(m?.liquid_type) || (m.mode==='new' && this._liquidInfo(m.liquid_type)?.hidden))throw Error('Select a visible liquid type.');
  if(!Number.isFinite(volume)||volume<=0||volume>100000)throw Error('Enter a volume between 0 and 100,000 mL.');
  if(!/^\d{2}-\d{2}-\d{4}$/.test(date))throw Error('Use DD-MM-YYYY for the date.');
  if(!time)throw Error('Enter a valid 24-hour time: 930 → 09:30, 1430 → 14:30. Hours must be 00–23 and minutes 00–59.');
  const iso=jdhlDateToIso(date);
  if(!iso||!Number.isFinite(Date.parse(`${iso}T12:00:00`))||jdhlIsoDate(new Date(`${iso}T12:00:00`))!==iso)throw Error('Use a valid calendar date.');
  if(iso>this._todayISO())throw Error('Future dates are not allowed; a later time today is allowed.');
  return {volume,liquid_type:m.liquid_type,cup_type_id:m.cup_type_id||'',quick_button_id:m.quick_button_id||'',date,time};
 }
 async _ensureBackend(){
  try{
   const info=await this._hass.callWS({type:'jw_daily_hydration_log/capabilities'});
   if(info?.version!=='1.1.0-beta.31')throw Error(`Frontend v1.1.0-beta.31 is connected to backend ${info?.version||'unknown'}. Restart Home Assistant Core and refresh the dashboard.`);
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
   this._modal.quick_button_id='';
   if(this._cupInfo(this._modal.cup_type_id))this._modal.volume_ml=String(this._cupInfo(this._modal.cup_type_id).default_volume_ml);
   else if(this._cupDefs().length)this._modal.volume_ml='';
   else if(this._modal.mode==='new')this._modal.volume_ml='';
   this._error='';this._render(true);return;}
  if(action==='cup'){if(!this._modal)return;const c=this._cupInfo(el.dataset.value);
   if(!c||c.hidden)return;this._modal.cup_type_id=c.id;this._modal.quick_button_id='';
   this._modal.volume_ml=String(c.default_volume_ml);this._error='';this._render(true);return;}
  if(action==='quick-choice'){if(!this._modal)return;const q=this._quickDefs().find(x=>x.id===el.dataset.value&&x.available);
   if(!q)return;this._modal.liquid_type=q.liquid_type_id;this._modal.cup_type_id=q.cup_type_id;
   this._modal.quick_button_id=q.id;this._modal.volume_ml=String(q.default_volume_ml);
   this._error='';this._render(true);return;}
  if(action==='amount'){if(!this._modal||this._manageOpen)return;
   this._modal.volume_ml=String(el.dataset.value);this._modal.quick_button_id='';this._error='';this._render(true);return;}
  if(action==='manage-liquids'){if(!this._modal||!this._hass?.user?.is_admin)return;
   this._manageOpen=true;this._customDraft=null;this._editingLiquidId=null;this._managePendingDelete=null;this._error='';this._render(true);return;}
  if(action==='manage-add'){this._customDraft=this._newLiquidDraft();this._editingLiquidId=null;this._error='';this._render(true);return;}
  if(action==='manage-edit'){const liquid=this._liquidInfo(el.dataset.value);if(!liquid)return;
   this._managePendingDelete=null;
   this._editingLiquidId=liquid.id;this._customDraft=this._newLiquidDraft(liquid);this._error='';this._render(true);return;}
  if(action==='manage-cancel'){
   if(this._customDraft){this._customDraft=null;this._editingLiquidId=null;}
   else {this._manageOpen=false;if(this._settingsSection==='liquids')this._settingsSection='home';}
   this._managePendingDelete=null;this._error='';this._render(true);return;}
  if(action==='manage-color-reset'){
   if(!this._customDraft)return;
   const liquid=this._liquidInfo(this._editingLiquidId);
   this._customDraft.color_custom=false;
   this._customDraft.color_hex=jdhlLiquidColor(liquid?.id||'',liquid?.name||this._customDraft.custom_name);
   this._error='';this._render(true);return;
  }
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
  if(action==='volume-up'||action==='volume-down'){
   const i=Number(el.dataset.index),to=i+(action==='volume-up'?-1:1);
   if(i>=0&&to>=0&&to<this._volumeDraft.length){[this._volumeDraft[i],this._volumeDraft[to]]=[this._volumeDraft[to],this._volumeDraft[i]];this._render(true);}return;}
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
   this._confirmDelete=false;this._error='';this._render(true);return;}
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
  if(action==='history-calendar-toggle'){
   this._historyCalendarOpen=!this._historyCalendarOpen;
   this._historyCalendarMonth=(this._viewDate||this._todayISO()).slice(0,7);
   this._render(true);return;
  }
  if(action==='history-calendar-prev'||action==='history-calendar-next'){
   const [y,m]=(this._historyCalendarMonth||this._todayISO().slice(0,7)).split('-').map(Number);
   const d=new Date(y,m-1+(action==='history-calendar-prev'?-1:1),1);
   this._historyCalendarMonth=jdhlIsoDate(d).slice(0,7);this._render(true);return;
  }
  if(action==='history-calendar-day'){
   const date=el.dataset.value;
   if(!/^\d{4}-\d{2}-\d{2}$/.test(date)||date>this._todayISO())return;
   this._historyCalendarOpen=false;this._typedHistoryDate=jdhlIsoToDate(date);
   this._viewDate=date===this._todayISO()?null:date;
   this._history=null;this._error='';this._render(true);this._fetchHistory();return;
  }
  if(action==='date-go'){
   const date=jdhlDateToIso(this._typedHistoryDate||'');
   if(!date||!Number.isFinite(Date.parse(`${date}T12:00:00`))||jdhlIsoDate(new Date(`${date}T12:00:00`))!==date){this._alert('Use a real date in DD-MM-YYYY format.');return;}
   if(date>this._todayISO()){this._alert('You cannot view a future date.');return;}
   this._viewDate=date===this._todayISO()?null:date;this._history=null;this._error='';this._render(true);this._fetchHistory();return;
  }
  if(action==='export'){await this._export();return;}
  if(['settings-','data-','full-','model-'].some(prefix=>action.startsWith(prefix))){await this._settingsClick(action,el);return;}
 }
 async _saveModal(){let p;try{p=this._payload();}catch(e){this._alert(e);return;}
  const m=this._modal;this._busy=true;this._error='';this._status='Saving drink…';this._render(true);
  try{await this._ensureBackend();if(m.mode==='new'){
   const saved=await this._hass.callWS({type:'jw_daily_hydration_log/add_drink',
    profile:this._config.profile,volume_ml:p.volume,liquid_type:p.liquid_type,
    date:p.date,time:p.time,...(p.cup_type_id?{cup_type_id:p.cup_type_id}:{}),
    ...(p.quick_button_id?{quick_button_id:p.quick_button_id}:{})});
   this._undoId=saved.record_id||null;
   }else{
    await this._hass.callWS({type:'jw_daily_hydration_log/edit_drink',profile:this._config.profile,
     record_id:m.id,volume_ml:p.volume,liquid_type:p.liquid_type,date:p.date,time:p.time,
     ...(p.cup_type_id?{cup_type_id:p.cup_type_id}:{}),
     ...(p.quick_button_id?{quick_button_id:p.quick_button_id}:{})});
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
   if(!/^UEs/.test(response.base64||''))throw Error('Invalid Excel payload from Home Assistant.');
   /* Use a locally generated data URL; this avoids blob:http mixed-download flags
      in Chromium when HA is accessed through a reverse proxy. No external URL. */
   const link=document.createElement('a');
   link.href='data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,'+response.base64;
   link.download=response.filename||'jwDaily Hydration Log - All Data.xlsx';
   this.shadowRoot.appendChild(link);link.click();link.remove();
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
  const remainingY=p>=92?94:Math.min(154,Math.max(63,(targetY+y)/2));
  return `<div class="glass-viz"><svg class="glass" viewBox="0 0 160 200" role="img" aria-label="${actual.toFixed(0)} percent of daily goal">
   <defs><clipPath id="jdhl-cup"><path d="M32 19 L128 19 L120 175 Q119 185 108 185 L52 185 Q41 185 40 175 Z"/></clipPath></defs>
   <path d="M32 19 L40 175 Q41 185 52 185 L108 185 Q119 185 120 175 L128 19" fill="none"
         stroke="var(--primary-text-color,#233245)" stroke-width="3" stroke-linecap="round"/>
   ${p>0?`<g clip-path="url(#jdhl-cup)"><rect x="32" y="${y}" width="96" height="185" fill="#59baf2" opacity=".9">
      <animate attributeName="y" from="${fromY}" to="${y}" dur="650ms" fill="freeze"/></rect>
      <path d="${w0}" stroke="#a2dcff" stroke-width="3" fill="none">
       <animate attributeName="d" values="${w0};${w1};${w0}" dur="2.7s" repeatCount="indefinite"/></path></g>`:''}
   <path d="M38 ${targetY} L122 ${targetY}" stroke="#fff" stroke-opacity=".95" stroke-width="5" stroke-dasharray="4 5" stroke-linecap="round"/>
   <path d="M38 ${targetY} L122 ${targetY}" stroke="#e04444" stroke-width="2.6" stroke-dasharray="4 5" stroke-linecap="round"/>
  </svg>
  <span class="cup-target">${jdhlEscape(jdhlFmt(target))}</span>
  ${remaining>0?`<span class="cup-remaining" style="top:${(100*remainingY/200).toFixed(2)}%">${jdhlEscape(jdhlFmt(remaining))}</span>`:''}
  </div>`;
 }
 _dayBarsHTML(){
  const date=this._viewDate||this._todayISO(),isToday=date===this._todayISO();
  const ready=this._history?.date===date;
  const all=ready?(this._history?.day_summary?.liquid_breakdown||[]):[];
  const defs=this._liquidDefs();const label=id=>defs.find(t=>t.id===id)?.name||(id==='unknown'?'Unknown':id);
  const data=all.filter(x=>Number(x.volume_ml)>0).sort((a,b)=>Number(b.volume_ml)-Number(a.volume_ml));
  const heading=isToday?'Today by liquid':`By liquid <span class="bars-date">${jdhlIsoToDate(date)}</span>`;
  if(!data.length)return `<div class="liquid-bars"><div class="bars-title">${heading}</div><p class="muted">${ready?'No classified drinks on this day.':'Loading day…'}</p></div>`;
  const high=Math.max(...data.map(x=>Number(x.volume_ml)));
  return `<div class="liquid-bars" aria-label="Volumes by liquid type on selected day"><div class="bars-title">${heading}</div>
   ${data.map(x=>`<div class="bar-line"><span title="${jdhlEscape(label(x.liquid_type))}"><i class="type-dot" style="background:${this._typeColor(x.liquid_type,label(x.liquid_type))}" aria-hidden="true"></i>${jdhlEscape(label(x.liquid_type))}</span>
      <div class="bar-track"><div class="bar-fill" style="background:${this._typeColor(x.liquid_type,label(x.liquid_type))};width:${(100*Number(x.volume_ml)/high).toFixed(2)}%"></div></div>
      <strong>${jdhlFmt(Number(x.volume_ml))}</strong></div>`).join('')}</div>`;
 }
 _historyCalendarHTML(){
  if(!this._historyCalendarOpen)return '';
  const today=this._todayISO();
  const selected=this._viewDate||today;
  const ym=this._historyCalendarMonth||selected.slice(0,7);
  const [year,month]=ym.split('-').map(Number);
  const first=(new Date(year,month-1,1).getDay()+6)%7;
  const days=new Date(year,month,0).getDate();
  const monthTitle=new Intl.DateTimeFormat('en-GB',{month:'long',year:'numeric'}).format(new Date(year,month-1,1));
  const cells=['Mo','Tu','We','Th','Fr','Sa','Su'].map(v=>`<span class="history-cal-weekday">${v}</span>`);
  for(let i=0;i<first;i++)cells.push('<span></span>');
  for(let n=1;n<=days;n++){
    const iso=`${ym}-${String(n).padStart(2,'0')}`;
    cells.push(`<button type="button" class="history-cal-day ${iso===selected?'selected':''}" data-action="history-calendar-day" data-value="${iso}" ${iso>today?'disabled':''}>${n}</button>`);
  }
  return `<div class="history-calendar" role="dialog" aria-label="Select drink history date">
    <div class="history-cal-nav"><button data-action="history-calendar-prev" aria-label="Previous month">‹</button><strong>${jdhlEscape(monthTitle)}</strong><button data-action="history-calendar-next" aria-label="Next month" ${ym>=today.slice(0,7)?'disabled':''}>›</button></div>
    <div class="history-cal-grid">${cells.join('')}</div></div>`;
 }
 _historyHTML(){if(this._config.show_history===false)return '';
  const iso=this._viewDate||this._todayISO(),rows=Array.isArray(this._history?.entries)?[...this._history.entries].reverse():[];
  const total=this._history?jdhlFmt(this._history.total_ml,this._config.unit):'—';
  const canEdit=!!this._hass?.user?.is_admin;
  const table=rows.length?`<div class="history-table"><table><thead><tr><th>Time</th><th>Liquid</th><th>Cup</th><th class="right">Volume</th></tr></thead><tbody>
   ${rows.map(r=>{const time=this._timeParts(new Date(r.timestamp)).time.slice(0,5);
    const liquid=this._liquidName(r.liquid_type),cup=this._cupInfo(r.cup_type_id)?.name||'Unknown';
    return `<tr ${canEdit?`data-action="edit" data-id="${jdhlEscape(r.id)}" title="Edit drink moment" tabindex="0"`:''}>
    <td>${jdhlEscape(time)}</td><td title="${jdhlEscape(liquid)}">${jdhlEscape(liquid)}</td><td title="${jdhlEscape(cup)}">${jdhlEscape(cup)}</td><td class="right">+${jdhlFmt(Number(r.volume_ml),this._config.unit)} ${canEdit?'✎':''}</td></tr>`;}).join('')}
   </tbody></table></div>`:`<p class="muted center">${this._history?'No drinks recorded on this date.':'Loading drink history…'}</p>`;
  return `<section class="history"><div class="history-head"><h3>Drink history</h3><span class="muted">${rows.length} entries</span></div>
   <div class="date-nav"><button data-action="prev" class="small secondary" aria-label="Previous day">‹</button>
   <div class="history-date-selector"><input aria-label="History date, DD-MM-YYYY" data-field="history_date" value="${jdhlEscape(jdhlIsoToDate(iso)||iso)}" placeholder="DD-MM-YYYY" inputmode="numeric" />
   <button type="button" class="history-calendar-button" data-action="history-calendar-toggle" aria-label="Open history calendar" aria-expanded="${this._historyCalendarOpen}">▦</button>
   ${this._historyCalendarHTML()}</div>
   <button data-action="date-go" class="small secondary">Go</button><button data-action="next" class="small secondary" ${iso>=this._todayISO()?'disabled':''} aria-label="Next day">›</button></div>
   ${table}</section>`;
 }
 _manageHTML(){const d=this._customDraft;
  const all=this._liquidDefs();const visible=all.filter(t=>!t.hidden);
  const hidden=all.filter(t=>t.hidden);
  const list=visible.map((t,index)=>`<div class="saved-liquid" data-testid="liquid-manage-row">
   <span class="saved-liquid-icon" title="${this._effectiveColor(t)}">${this._liquidIcon(t,true)}</span> <strong>${jdhlEscape(t.name)}</strong>
   <span class="muted"></span>
   <button class="secondary small" data-action="manage-up" data-value="${jdhlEscape(t.id)}" ${index===0?'disabled':''} aria-label="Move ${jdhlEscape(t.name)} up">↑</button>
   <button class="secondary small" data-action="manage-down" data-value="${jdhlEscape(t.id)}" ${index===visible.length-1?'disabled':''} aria-label="Move ${jdhlEscape(t.name)} down">↓</button>
   <button class="secondary small" data-action="manage-edit" data-value="${jdhlEscape(t.id)}">Edit</button>
   ${t.custom?`<button class="secondary small" data-action="manage-remove" data-value="${jdhlEscape(t.id)}" title="Delete custom type only when unused">Delete</button>`:`<button class="secondary small" data-action="manage-hide" data-value="${jdhlEscape(t.id)}" title="Remove built-in from Add choices; keep drink history">Delete</button>`}
   </div>`).join('');
  return `<div class="manage">
   <h3>Manage liquid types</h3><p class="muted manage-intro">Change names, icons, colors and order. Delete built-in buttons to hide them; prior drinks remain available. Restore hidden types below.</p>
   ${this._error?`<p role="alert" class="error">${jdhlEscape(this._error)}</p>`:''}
   ${d?`<div class="manage-editor"><h4>${this._editingLiquidId?'Edit liquid':'Add liquid'}</h4>
    <div class="manage-form-grid">
     <label>Liquid name<input data-field="custom_name" maxlength="48" value="${jdhlEscape(d.custom_name||'')}" placeholder="e.g. Orange juice"/></label>
     <label>Material Design Icon<input data-field="icon_mdi" value="${jdhlEscape(d.icon_mdi||'')}" placeholder="mdi:glass-mug-variant"/></label>
     <label class="svg-field">Or SVG icon (.svg, max 16 KB)<input data-field="custom_svg_file" type="file" accept=".svg,image/svg+xml"/></label>
    </div>${d.icon_svg?`<p class="status">SVG selected (${new TextEncoder().encode(d.icon_svg).length} bytes)</p>`:''}
    <div class="color-editor" role="group" aria-label="Liquid color">
      <label>Color <input type="color" data-field="color_picker" value="${jdhlHex(d.color_hex)||jdhlLiquidColor(this._editingLiquidId||'',d.custom_name)}" aria-label="Choose liquid color" /></label>
      <label>Hex color <input type="text" data-field="color_hex" value="${jdhlEscape(d.color_hex)}" maxlength="32" spellcheck="false" autocapitalize="characters" aria-label="Hex color code" placeholder="#RRGGBB" /></label>
      <span class="color-preview" style="background:${jdhlHex(d.color_hex)||jdhlLiquidColor(this._editingLiquidId||'',d.custom_name)}" role="img" aria-label="Color preview"></span>
      <button type="button" class="secondary small" data-action="manage-color-reset">Reset to default</button>
    </div><p class="color-error error" role="alert" ${jdhlHex(d.color_hex)?'hidden':''}>${jdhlHex(d.color_hex)?'':'Enter a valid color in #RRGGBB format.'}</p>
    <div class="dialog-actions"><button class="secondary" data-action="manage-cancel">Back</button>
     <button data-action="manage-save" ${this._busy?'disabled':''}>Save liquid</button></div></div>`:
    `<div class="saved-liquids">${list||'<p class="muted">No visible types. Restore one below or add your own.</p>'}</div>
     ${hidden.length?`<h4>Hidden built-in liquid types</h4><div class="hidden-liquids">${hidden.map(t=>
        `<div class="hidden-liquid">${this._liquidIcon(t,true)} <strong>${jdhlEscape(t.name)}</strong>
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
 _settingsOpen(section='home'){
  this._settingsSection=section;this._settingsDraft=null;this._settingsEditId=null;this._settingsDeleteQuickId=null;
  this._manageOpen=section==='liquids';
  this._customDraft=null;this._editingLiquidId=null;this._error='';
  this._render(true);
  if(section==='profile')this._loadProfiles();
 }
 async _loadProfiles(){
  try{this._profilesData=await this._hass.callWS({type:'jw_daily_hydration_log/profiles_list'});this._render(true);}
  catch(e){this._alert(e);}
 }
 _profileHTML(){
  const E=jdhlEscape,profiles=this._profilesData?.profiles||[],d=this._profileDraft;
  return `<div class="settings-section"><h3>Profiles</h3><p class="settings-note">Each profile keeps separate settings and drink history. The dashboard card remains linked to its configured profile.</p>
   ${profiles.map(p=>`<div class="settings-row"><ha-icon icon="mdi:account-circle-outline"></ha-icon><div class="row-title"><strong>${E(p.name)}</strong><small>${E(p.slug)} · ${p.daily_target_ml} mL goal</small></div>
    <button class="secondary small" data-action="settings-profile-edit" data-value="${E(p.slug)}">Edit</button></div>`).join('')}
   ${d?`<div class="settings-edit"><h4>${this._profileEditSlug?'Edit profile':'Add profile'}</h4>
    <label>Name<input data-field="name" maxlength="48" value="${E(d.name)}"/></label>
    <label>Age<input type="number" min="1" max="120" data-field="age" value="${E(d.age)}"/></label>
    <label>Gender<select data-field="gender"><option value="male" ${d.gender==='male'?'selected':''}>Male</option><option value="female" ${d.gender==='female'?'selected':''}>Female</option></select></label>
    <label>Units<select data-field="unit">${['mL','L','fl_oz'].map(v=>`<option value="${v}" ${d.unit===v?'selected':''}>${v}</option>`).join('')}</select></label>
    ${this._profileEditSlug?`<label>Source sensor<input data-field="source_sensor" value="${E(d.source_sensor||'')}"/></label>
      <label>Source mode<select data-field="source_mode">${['absolute','delta','sum'].map(v=>`<option value="${v}" ${d.source_mode===v?'selected':''}>${v}</option>`).join('')}</select></label>`:
      `<label>Copy liquid, cup and Quick button settings from
      <select data-field="copy_from"><option value="">Start with default settings</option>${profiles.map(p=>`<option value="${E(p.slug)}" ${p.slug===d.copy_from?'selected':''}>${E(p.name)}</option>`).join('')}</select></label>`}
    <label class="check-label"><input type="checkbox" data-field="pregnancy" ${d.pregnancy?'checked':''}/> Pregnancy</label>
    <label class="check-label"><input type="checkbox" data-field="lactation" ${d.lactation?'checked':''}/> Lactation</label>
    ${!this._profileEditSlug?'<p class="settings-note">Only configuration is copied. No records, consumed volumes, sensor readings or personal targets are transferred.</p>':'<p class="settings-note">Changing the display name preserves the stable profile slug and entity IDs.</p>'}
    <div class="dialog-actions"><button class="secondary" data-action="settings-profile-cancel">Cancel</button><button data-action="settings-profile-save">${this._profileEditSlug?'Save profile':'Create profile'}</button></div></div>`:''}
   <div class="dialog-actions"><button data-action="settings-profile-add">+ Add profile</button></div></div>`;
 }
 _transferHTML(){
  const E=jdhlEscape,p=this._settingsImportPreview;
  return `<div class="settings-section"><h3>Settings import / export</h3>
   <p class="settings-note">Profile: <strong>${E(this._history?.profile_settings?.name||this._config.profile)}</strong>. Settings JSON contains no drink records, timestamps, consumption totals, entity IDs or sensor readings.</p>
   <div class="settings-row"><ha-icon icon="mdi:download"></ha-icon><div class="row-title"><strong>Export settings</strong><small>Current profile · JSON with SHA-256</small></div><button data-action="settings-export-json">Export JSON</button></div>
   <div class="settings-edit"><h4>Import settings</h4><label>Choose a settings JSON file<input type="file" accept=".json,application/json" data-field="settings_import_file"/></label>
    ${this._settingsImportFilename?`<p>Selected: ${E(this._settingsImportFilename)}</p>`:''}
    <p class="settings-note">Import overwrites only configuration fields after validation and your explicit approval. Your drink history is never part of the file.</p>
    <button class="secondary" data-action="settings-import-preview" ${!this._settingsImportContent?'disabled':''}>Preview import</button>
    ${p?`<div class="migration-summary"><strong>Preview for ${E(p.profile)}</strong><p>Source: ${E(p.source_profile)}</p><p>${p.counts.liquids} liquid definitions · ${p.counts.cups} cups · ${p.counts.quick_buttons} Quick buttons</p>
       <p>Settings to replace: ${E(p.changes.join(', ')||'None')}</p>
       <p>Drink history: unchanged (${p.drink_count} existing records)</p>
       <p class="settings-note">Save an export of your current settings before importing. The import is blocked if settings changed after preview.</p>
       <div class="dialog-actions"><button data-action="settings-import-apply" class="danger">Confirm and import settings</button></div></div>`:''}
   </div>
   <div class="settings-edit"><h4>Data — drink history and snapshots</h4>
     <p class="settings-note">Data JSON contains the original record IDs, drink entries, source measurements and day archives. Settings are never overwritten by Data import.</p>
     <div class="dialog-actions"><button data-action="data-export-json">Export Data JSON</button></div>
     <label>Choose Data JSON<input type="file" accept=".json,application/json" data-field="data_import_file"/></label>
     ${this._dataImportFilename?`<p>Selected: ${E(this._dataImportFilename)}</p>`:''}
     <label>Import mode<select data-field="data_import_mode">
      ${[['merge','Merge — add missing IDs only'],['update','Update existing — update matching IDs'],['replace','Replace all — remove all existing Data first']]
       .map(([v,t])=>`<option value="${v}" ${this._dataImportMode===v?'selected':''}>${t}</option>`).join('')}</select></label>
     <button class="secondary" data-action="data-import-preview" ${!this._dataImportContent?'disabled':''}>Preview Data import</button>
     ${this._dataImportPreview?`<div class="migration-summary"><strong>Data preview — ${E(this._dataImportPreview.mode)}</strong>
      <p>Existing ${this._dataImportPreview.counts.existing_drinks} · Incoming ${this._dataImportPreview.counts.incoming_drinks} · New ${this._dataImportPreview.counts.new_ids} · Matching ${this._dataImportPreview.counts.matching_ids}</p>
      <p>Changed IDs ${this._dataImportPreview.counts.changed_matching_ids} · Final drinks ${this._dataImportPreview.counts.total_result_drinks}</p>
      <p>${E(this._dataImportPreview.warning)}</p>
      ${this._dataImportMode==='replace'?'<p class="delete-warning">REPLACE ALL deletes the current profile Data before restoring the chosen file; this cannot be undone without a backup.</p>':''}
      <p class="settings-note">Download and verify a current Full Backup ZIP before confirming. The saved file must be accessible outside Home Assistant.</p>
      <button data-action="data-import-apply" class="danger" ${!this._fullBackupSaved?'disabled':''}>Confirm Data import</button></div>`:''}
   </div>
   <div class="settings-edit"><h4>Full backup / restore</h4>
    <p class="settings-note">ZIP containing settings.json, data.json and a checksummed manifest. Restore requires the original profile ID and replaces both Settings and Data together.</p>
    <div class="dialog-actions"><button data-action="full-backup-export">Export Full Backup ZIP</button></div>
    <label class="check-label"><input type="checkbox" data-field="full_backup_verified" ${this._fullBackupSaved?'checked':''}/> I verified that the Full Backup ZIP is saved and opens correctly.</label>
    <label>Choose Full Backup ZIP<input type="file" accept=".zip,application/zip" data-field="full_restore_file"/></label>
    ${this._fullRestoreFilename?`<p>Selected: ${E(this._fullRestoreFilename)}</p>`:''}
    <button class="secondary" data-action="full-restore-preview" ${!this._fullRestoreContent?'disabled':''}>Preview Full restore</button>
    ${this._fullRestorePreview?`<div class="migration-summary"><strong>Full restore preview</strong>
      <p>Existing drinks ${this._fullRestorePreview.counts.current_records} → Restore ${this._fullRestorePreview.counts.records}</p>
      <p>Cups ${this._fullRestorePreview.counts.cups} · Quick buttons ${this._fullRestorePreview.counts.quick_buttons}</p>
      <p class="delete-warning">This overwrites the entire current profile. Review your backup and explicitly confirm.</p>
      <button class="danger" data-action="full-restore-apply" ${!this._fullBackupSaved?'disabled':''}>Confirm and restore Full Backup</button></div>`:''}
   </div>
   </div>`;
 }
 _settingsHTML(){const page=this._settingsSection;const draft=this._settingsDraft;
  const nav=[['profile','Manage profiles','Edit, add or copy settings','mdi:account-multiple'],
    ['target','Daily target','Automatic and custom daily goal','mdi:target'],
    ['liquids','Liquid types','Names, icons and colors','mdi:water'],
    ['cups','Cup types','Reusable containers and volumes','mdi:glass-mug-variant'],
    ['quick','Quick buttons','Liquid + cup combinations and labels','mdi:gesture-tap-button'],
    ['advanced','Advanced','Settings, Data and backup transfer','mdi:wrench']];
  const E=jdhlEscape;
  const choice=(items,valueField,labelField,selected,empty='Select')=>`<option value="">${E(empty)}</option>`+
   items.map(t=>`<option value="${E(t[valueField])}" ${t[valueField]===selected?'selected':''}>${E(t[labelField])}</option>`).join('');
  let body='';
  if(page==='home')body=`<div class="settings-profile-current"><ha-icon icon="mdi:account-circle-outline"></ha-icon>
    <div><strong>${E(this._history?.profile_settings?.name||this._config.profile)}</strong><small>Active card profile</small></div></div>
    <div class="settings-category">PROFILE & GOALS</div>
    <div class="settings-nav">${nav.map(([key,name,desc,icon],i)=>`${i===2?'<div class="settings-category">DRINK CONFIGURATION</div>':''}
     ${i===5?'<div class="settings-category">MAINTENANCE</div>':''}
     <button data-action="settings-page" data-value="${key}" class="settings-nav-item secondary">
       <ha-icon icon="${icon}"></ha-icon><span><strong>${E(name)}</strong><small>${E(desc)}</small></span><ha-icon icon="mdi:chevron-right"></ha-icon></button>`).join('')}</div>`;
  else if(page==='liquids')body=this._manageHTML();
  else if(page==='advanced')body=`<div class="settings-section"><h3>Advanced</h3>
   <div class="settings-nav"><button class="settings-nav-item secondary" data-action="settings-page" data-value="transfer"><ha-icon icon="mdi:database-arrow-down-outline"></ha-icon><span><strong>Import & Export</strong><small>Separate Settings and Data, plus Full Backup ZIP</small></span><ha-icon icon="mdi:chevron-right"></ha-icon></button></div></div>`;
  else if(page==='transfer')body=this._transferHTML();
  else if(page==='cups'){
   const cups=this._cupDefs();body=`<div class="settings-section"><p class="settings-note">A cup defines a default volume. Existing drink volumes never change.</p>
    ${draft?`<div class="settings-edit"><label>Cup name<input data-field="name" maxlength="48" value="${E(draft.name)}"/></label>
      <label>Default volume (mL)<input data-field="volume_ml" type="number" step="any" min="0.01" max="100000" value="${E(draft.volume_ml)}"/></label>
      <label>MDI icon<input data-field="icon_mdi" value="${E(draft.icon_mdi)}" placeholder="mdi:cup"/></label></div>
      <div class="dialog-actions"><button class="secondary" data-action="settings-discard">Cancel</button><button data-action="settings-cup-save">Save cup</button></div>`:''}
    ${cups.map((c,i)=>`<div class="settings-row"><div class="row-title"><strong>${E(c.name)}</strong><small>${jdhlFmt(Number(c.default_volume_ml))}${c.hidden?' · Hidden':''}</small></div>
     <button class="secondary small" data-action="settings-cup-up" data-value="${E(c.id)}" ${i===0?'disabled':''} aria-label="Move up">↑</button>
     <button class="secondary small" data-action="settings-cup-down" data-value="${E(c.id)}" ${i===cups.length-1?'disabled':''} aria-label="Move down">↓</button>
     <button class="secondary small settings-hide-button" data-action="settings-cup-toggle" data-value="${E(c.id)}">${c.hidden?'Restore':'Hide'}</button>
     <button class="secondary small" data-action="settings-cup-edit" data-value="${E(c.id)}">Edit</button></div>`).join('')}
    <div class="dialog-actions"><button data-action="settings-cup-add">+ Add cup</button></div></div>`;
  }
  else if(page==='quick'){
   const quick=this._quickDefs(),liquids=this._liquidDefs().filter(t=>!t.hidden),cups=this._cupDefs().filter(c=>!c.hidden);
   body=`<div class="settings-section"><p class="settings-note">Automatic label: Liquid (Cup). Custom labels never change chart grouping.</p>
    ${draft?`<div class="settings-edit"><label>Liquid<select data-field="liquid_type_id">${choice(liquids,'id','name',draft.liquid_type_id,'Choose liquid')}</select></label>
      <label>Cup<select data-field="cup_type_id">${choice(cups,'id','name',draft.cup_type_id,'Choose cup')}</select></label>
      <label>Button label<select data-field="label_mode"><option value="automatic" ${draft.label_mode==='automatic'?'selected':''}>Automatic: Liquid (Cup)</option><option value="custom" ${draft.label_mode==='custom'?'selected':''}>Custom</option></select></label>
      ${draft.label_mode==='custom'?`<label>Custom button text<input data-field="custom_label" maxlength="60" value="${E(draft.custom_label)}"/></label>`:''}</div>
      <div class="dialog-actions"><button class="secondary" data-action="settings-discard">Cancel</button><button data-action="settings-quick-save">Save Quick button</button></div>`:''}
    ${quick.map((q,i)=>`<div class="settings-row quick-settings-row"><div class="row-title"><strong>${E(this._effectiveQuickLabel(q))}</strong>
     <small>${E(this._liquidName(q.liquid_type_id))} · ${E(this._cupInfo(q.cup_type_id)?.name||'Cup unavailable')} · ${jdhlFmt(Number(q.default_volume_ml||0))}${q.hidden?' · Hidden':''}</small></div>
     <div class="settings-row-actions">
     <button class="secondary small" data-action="settings-quick-up" data-value="${E(q.id)}" ${i===0?'disabled':''} aria-label="Move up">↑</button>
     <button class="secondary small" data-action="settings-quick-down" data-value="${E(q.id)}" ${i===quick.length-1?'disabled':''} aria-label="Move down">↓</button>
     <button class="secondary small settings-hide-button" data-action="settings-quick-toggle" data-value="${E(q.id)}">${q.hidden?'Restore':'Hide'}</button>
     <button class="secondary small" data-action="settings-quick-edit" data-value="${E(q.id)}">Edit</button>
     <button class="danger small" data-action="settings-quick-delete" data-value="${E(q.id)}">Delete</button>
     </div></div>`).join('')}
    ${this._settingsDeleteQuickId?`<div class="delete-warning" role="alert"><strong>Delete Quick button?</strong>
      <p>Permanently remove ${E(this._effectiveQuickLabel(quick.find(q=>q.id===this._settingsDeleteQuickId)||{}))}? Drink history and volumes will remain unchanged. The historical button label is preserved.</p>
      <div class="dialog-actions"><button class="secondary small" data-action="settings-quick-delete-cancel">Cancel</button><button class="danger small" data-action="settings-quick-delete-confirm" data-value="${E(this._settingsDeleteQuickId)}">Confirm delete</button></div></div>`:''}
    <div class="dialog-actions"><button data-action="settings-quick-add" ${!liquids.length||!cups.length?'disabled':''}>+ Add Quick button</button></div></div>`;
  }
  else if(page==='target'){
   const value=this._history?.target_ml??this._millilitres('daily_target','target_ml');
   body=`<div class="settings-section"><h3>Daily target</h3><p class="settings-note">Current goal: ${jdhlFmt(Number(value))}. Enter 0 to restore the calculated default.</p>
    <div class="settings-edit"><label>Target (mL)<input data-field="target_ml" type="number" min="0" max="100000" step="1" value="${E(draft?.target_ml??value)}"/></label></div>
    <div class="dialog-actions"><button data-action="settings-target-save">Save target</button></div></div>`;
  }
  else if(page==='profile')body=this._profileHTML();
  else if(page==='export')body=`<div class="settings-section"><h3>Export</h3><p>Export the four-sheet Excel workbook, with liquid, cup and Quick button definitions.</p><button data-action="export">Export to Excel (.xlsx)</button></div>`;
  else body=`<div class="settings-section"><h3>About</h3><p>jwDaily Hydration Log v1.1.0-beta.31</p>
   <p class="settings-note">Each drink record stores independent Liquid and Cup IDs. Settings and Data can be backed up separately.</p></div>`;
  return `<div class="overlay" role="presentation"><section class="dialog dialog-settings" role="dialog" aria-modal="true" aria-label="Settings">
    <div class="settings-head"><h3>${page==='home'?'Settings':nav.find(x=>x[0]===page)?.[1]||({transfer:'Import & Export'}[page]||'Settings')}</h3>
    <button class="secondary small" data-action="settings-close" aria-label="Close settings">✕</button></div>
    ${this._error?`<p class="error" role="alert">${E(this._error)}</p>`:''}
    ${body}
    ${page!=='home'?`<div class="dialog-actions"><button class="secondary" data-action="settings-home">← Back to settings</button></div>`:''}
   </section></div>`;
 }
 async _settingsCall(command, data){
  this._busy=true;this._error='';try{
   await this._ensureBackend();await this._hass.callWS({type:'jw_daily_hydration_log/'+command,profile:this._config.profile,...data});
   await this._fetchHistory();this._settingsDraft=null;this._settingsEditId=null;this._status='Settings saved';
  }catch(e){this._error=String(e?.message||e);}
  finally{this._busy=false;this._render(true);}
 }
 async _settingsClick(action,el){const id=el.dataset.value||'';
  if(action==='settings-open'){this._settingsOpen();return;}
  if(action==='data-export-json'||action==='full-backup-export'){
   try{
    const full=action==='full-backup-export';
    const resp=await this._hass.callWS({type:'jw_daily_hydration_log/'+(full?'full_backup_export':'data_export'),profile:this._config.profile});
    if(!resp.base64||!/^([a-f0-9]{64})$/.test(resp.sha256||''))throw Error('Invalid backup response');
    const a=document.createElement('a');a.href='data:'+(full?'application/zip':'application/json')+';base64,'+resp.base64;
    a.download=resp.filename;this.shadowRoot.appendChild(a);a.click();a.remove();
    if(full)this._fullBackupSaved=false;
    this._status=full?'Full Backup download initiated — verify file before importing':'Data JSON download initiated';this._render(true);
   }catch(e){this._alert(e);}return;
  }
  if(action==='data-import-preview'){
   try{this._dataImportPreview=await this._hass.callWS({type:'jw_daily_hydration_log/data_import_preview',
    profile:this._config.profile,content:this._dataImportContent,mode:this._dataImportMode});
    this._error='';this._render(true);
   }catch(e){this._dataImportPreview=null;this._alert(e);}return;
  }
  if(action==='data-import-apply'){
   if(!this._fullBackupSaved||!this._dataImportPreview)return;
   if(!window.confirm('Import Data in '+this._dataImportMode+' mode? Check your Full Backup first.'))return;
   if(this._dataImportMode==='replace'&&!window.confirm('REPLACE ALL PROFILE DATA? Current drink records and daily snapshots will be replaced.'))return;
   try{await this._hass.callWS({type:'jw_daily_hydration_log/data_import_apply',profile:this._config.profile,
    content:this._dataImportContent,mode:this._dataImportMode,preview:this._dataImportPreview,confirm:true});
    this._dataImportPreview=null;this._dataImportContent='';this._dataImportFilename='';
    this._status='Data imported';this._history=null;await this._fetchHistory();this._render(true);
   }catch(e){this._alert(e);}return;
  }
  if(action==='full-restore-preview'){
   try{this._fullRestorePreview=await this._hass.callWS({type:'jw_daily_hydration_log/full_restore_preview',
     profile:this._config.profile,content_base64:this._fullRestoreContent});this._error='';this._render(true);
   }catch(e){this._fullRestorePreview=null;this._alert(e);}return;
  }
  if(action==='full-restore-apply'){
   if(!this._fullBackupSaved||!this._fullRestorePreview)return;
   if(!window.confirm('Replace this entire profile — Settings AND Data?'))return;
   if(!window.confirm('FINAL CONFIRMATION: restore this full backup over the current profile?'))return;
   try{await this._hass.callWS({type:'jw_daily_hydration_log/full_restore_apply',profile:this._config.profile,
     content_base64:this._fullRestoreContent,preview:this._fullRestorePreview,confirm:true});
    this._fullRestorePreview=null;this._fullRestoreContent='';this._fullRestoreFilename='';this._history=null;
    this._status='Full Backup restored';await this._fetchHistory();this._render(true);
   }catch(e){this._alert(e);}return;
  }
  if(action==='settings-export-json'){
   try{const res=await this._hass.callWS({type:'jw_daily_hydration_log/settings_export',profile:this._config.profile});
    if(!res.base64||!/^([a-f0-9]{64})$/.test(res.sha256)||res.size>256000)throw Error('Invalid settings export');
    const a=document.createElement('a');a.href='data:application/json;base64,'+res.base64;
    a.download=res.filename;this.shadowRoot.appendChild(a);a.click();a.remove();
    this._status='Settings JSON download initiated';this._render(true);
   }catch(e){this._alert(e);}return;
  }
  if(action==='settings-import-preview'){
   try{this._settingsImportPreview=await this._hass.callWS({type:'jw_daily_hydration_log/settings_import_preview',
       profile:this._config.profile,content:this._settingsImportContent});this._error='';this._render(true);}
   catch(e){this._settingsImportPreview=null;this._alert(e);}return;
  }
  if(action==='settings-import-apply'){
   const prev=this._settingsImportPreview;if(!prev)return;
   try{await this._ensureBackend();await this._hass.callWS({type:'jw_daily_hydration_log/settings_import_apply',
     profile:this._config.profile,content:this._settingsImportContent,expected_revision:prev.old_revision,
     import_sha256:prev.import_sha256,confirm:true});
    this._settingsImportPreview=null;this._settingsImportContent='';this._settingsImportFilename='';
    this._status='Settings imported';this._error='';await this._fetchHistory();this._render(true);
   }catch(e){this._alert(e);}return;
  }
  if(action==='settings-profile-add'||action==='settings-profile-edit'){
   const current=this._profilesData?.profiles?.find(p=>p.slug===id);this._profileEditSlug=current?.slug||'';
   this._profileDraft={name:current?.name||'',age:String(current?.age||30),gender:current?.gender||'male',
      unit:current?.unit||'mL',pregnancy:!!current?.pregnancy,lactation:!!current?.lactation,
      source_sensor:current?.source_sensor||'',source_mode:current?.source_mode||'absolute',copy_from:''};
   this._render(true);return;
  }
  if(action==='settings-profile-cancel'){this._profileDraft=null;this._profileEditSlug='';this._render(true);return;}
  if(action==='settings-profile-save'){
   const d=this._profileDraft;if(!d)return;
   if(!d.name.trim()||!Number.isInteger(Number(d.age))||Number(d.age)<1||Number(d.age)>120){
    this._alert('Enter a valid profile name and age between 1 and 120.');return;}
   try{await this._ensureBackend();const editing=!!this._profileEditSlug;
    const req={type:'jw_daily_hydration_log/'+(editing?'profile_edit':'profile_create'),
      ...(editing?{profile:this._profileEditSlug}:{copy_from:d.copy_from||''}),
      name:d.name.trim(),age:Number(d.age),gender:d.gender,unit:d.unit,
      pregnancy:!!d.pregnancy,lactation:!!d.lactation,
      ...(editing?{source_sensor:d.source_sensor||'',source_mode:d.source_mode}: {})};
    await this._hass.callWS(req);this._profileDraft=null;this._profileEditSlug='';
    await this._loadProfiles();await this._fetchHistory();this._render(true);
   }catch(e){this._alert(e);}return;
  }
  if(action==='settings-close'){this._settingsSection=null;this._settingsDraft=null;this._manageOpen=false;this._render(true);return;}
  if(action==='settings-home'){this._settingsOpen(['transfer'].includes(this._settingsSection)?'advanced':'home');return;}
  if(action==='settings-page'){this._settingsOpen(id);return;}
  if(action==='settings-discard'){this._settingsDraft=null;this._settingsEditId=null;this._render(true);return;}
  if(action==='settings-quick-delete'){
   if(!this._quickDefs().some(q=>q.id===id))return;
   this._settingsDeleteQuickId=id;this._render(true);return;
  }
  if(action==='settings-quick-delete-cancel'){
   this._settingsDeleteQuickId=null;this._render(true);return;
  }
  if(action==='settings-quick-delete-confirm'){
   if(!this._settingsDeleteQuickId||id!==this._settingsDeleteQuickId)return;
   await this._settingsCall('manage_quick',{action:'delete',quick_id:id});
   if(!this._error)this._settingsDeleteQuickId=null;
   return;
  }
  if(action==='settings-cup-add'||action==='settings-cup-edit'){
   const c=this._cupInfo(id);this._settingsEditId=c?.id||null;
   this._settingsDraft={name:c?.name||'',volume_ml:String(c?.default_volume_ml||''),icon_mdi:c?.icon_mdi||'mdi:cup'};this._render(true);return;
  }
  if(action==='settings-cup-save'){
   const d=this._settingsDraft||{};const n=Number(d.volume_ml);
   if(!String(d.name||'').trim()||!Number.isFinite(n)||n<=0||n>100000){this._alert('Provide a cup name and positive volume up to 100,000 mL.');return;}
   await this._settingsCall('manage_cup',{action:this._settingsEditId?'update':'add',...(this._settingsEditId?{cup_id:this._settingsEditId}:{}),name:d.name,volume_ml:n,icon_mdi:d.icon_mdi||''});return;
  }
  if(action==='settings-cup-toggle'||action==='settings-quick-toggle'){
   const cup=action==='settings-cup-toggle',item=cup?this._cupInfo(id):this._quickDefs().find(q=>q.id===id);
   if(!item)return;await this._settingsCall(cup?'manage_cup':'manage_quick',{action:item.hidden?'restore':'hide',...(cup?{cup_id:id}:{quick_id:id})});return;
  }
  if(/^settings-(cup|quick)-(up|down)$/.test(action)){
   const cup=action.startsWith('settings-cup'),items=cup?this._cupDefs():this._quickDefs(),ix=items.findIndex(x=>x.id===id),to=ix+(action.endsWith('-up')?-1:1);
   if(ix<0||to<0||to>=items.length)return;
   const order=items.map(x=>x.id);[order[ix],order[to]]=[order[to],order[ix]];
   await this._settingsCall(cup?'manage_cup':'manage_quick',{action:'reorder',order});return;
  }
  if(action==='settings-quick-add'||action==='settings-quick-edit'){
   const q=this._quickDefs().find(x=>x.id===id);this._settingsEditId=q?.id||null;
   this._settingsDraft={liquid_type_id:q?.liquid_type_id||'',cup_type_id:q?.cup_type_id||'',
    label_mode:q?.label_mode||'automatic',custom_label:q?.custom_label||''};this._render(true);return;
  }
  if(action==='settings-quick-save'){
   const d=this._settingsDraft||{};
   if(!this._liquidInfo(d.liquid_type_id)||!this._cupInfo(d.cup_type_id)){
    this._alert('Select a valid liquid and cup type.');return;}
   if(d.label_mode==='custom'&&!String(d.custom_label||'').trim()){
    this._alert('Enter a custom button label.');return;}
   await this._settingsCall('manage_quick',{action:this._settingsEditId?'update':'add',
     ...(this._settingsEditId?{quick_id:this._settingsEditId}:{}),liquid_type_id:d.liquid_type_id,
     cup_type_id:d.cup_type_id,label_mode:d.label_mode,custom_label:d.custom_label||''});return;
  }
  if(action==='settings-target-save'){
   const node=this.shadowRoot.querySelector('[data-field="target_ml"]');
   const n=Number(node?.value??this._settingsDraft?.target_ml);
   if(!Number.isFinite(n)||n<0||n>100000){this._alert('Target must be 0 to 100,000 mL.');return;}
   await this._settingsCall('set_target',{target_ml:n});return;
  }

 }
 _modalHTML(){if(this._settingsSection)return this._settingsHTML();if(!this._modal)return '';
  const m=this._modal;
  const types=this._liquidDefs().filter(t=>!t.hidden||(m.mode==='edit'&&t.id===m.liquid_type)).map(t=>{
   const chosen=jdhlHex(t.color_override);
   return `<button class="liquid-choice ${m.liquid_type===t.id?'selected':''} ${chosen?'custom-liquid-color':''}"
    data-action="type" data-value="${jdhlEscape(t.id)}" aria-pressed="${m.liquid_type===t.id}"
    ${chosen?`style="--liquid-choice-bg:${chosen};--liquid-choice-ink:${jdhlContrastInk(chosen)}"`:''}>
    ${this._liquidIcon(t)}<span>${jdhlEscape(t.name)}</span></button>`;}).join('');
  const amounts=this._buttons().map(v=>`<button class="amount ${Number(m.volume_ml)===v?'selected':''}"
     data-action="amount" data-value="${v}">${jdhlFmt(v)}</button>`).join('');
  return `<div class="overlay" role="presentation"><section class="dialog ${this._manageOpen?'dialog-manage-liquids':'dialog-drink'}" role="dialog" aria-modal="true"
    aria-label="${m.mode==='edit'?'Edit drink moment':'Add drink moment'}">
   ${this._manageOpen?this._manageHTML():`
    <h3>${m.mode==='edit'?'Edit drink moment':'Add drink moment'}</h3>
    ${this._error?`<p class="error" role="alert">${jdhlEscape(this._error)}</p>`:''}
    ${this._quickDefs().some(q=>q.available)?`<div class="modal-heading">Quick buttons</div><div class="quick-choices">
     ${this._quickDefs().filter(q=>q.available).map(q=>`<button class="quick-choice ${m.quick_button_id===q.id?'selected':''}"
      data-action="quick-choice" data-value="${jdhlEscape(q.id)}" aria-pressed="${m.quick_button_id===q.id}"
      style="--quick-color:${this._typeColor(q.liquid_type_id,this._liquidName(q.liquid_type_id))}">${jdhlEscape(this._effectiveQuickLabel(q))}</button>`).join('')}</div>`:''}
    <div class="modal-heading">Liquid type</div><div class="liquid-choices">${types}</div>
    ${this._cupDefs().some(c=>!c.hidden)?`<div class="modal-heading">Cup type</div><div class="cup-choices">
      ${this._cupDefs().filter(c=>!c.hidden||(m.mode==='edit'&&m.cup_type_id===c.id)).map(c=>`<button
       data-action="cup" data-value="${jdhlEscape(c.id)}" class="cup-choice ${m.cup_type_id===c.id?'selected':''}"
       aria-pressed="${m.cup_type_id===c.id}">${jdhlEscape(c.name)} · ${jdhlFmt(Number(c.default_volume_ml))}</button>`).join('')}</div>`:''}

    ${!this._cupDefs().length?`<div class="modal-heading">Legacy volume buttons</div><div class="volume-choices">${amounts}</div>`:''}

    <div class="fields">
     <label>Custom amount (mL)<input data-field="volume_ml" type="number" step="any" min="0.01" max="100000" value="${jdhlEscape(m.volume_ml)}" placeholder="Enter or select"/></label>
     <label>Date (DD-MM-YYYY)<div class="date-select"><button type="button" class="date-trigger secondary" data-action="calendar-toggle" aria-label="Choose date" aria-expanded="${this._calendarOpen}">${jdhlEscape(m.date)} <span aria-hidden="true">▦</span></button>${this._calendarHTML()}</div></label>
     <label>Time (24-hour)<input data-field="time" type="text" inputmode="numeric" autocapitalize="off" autocomplete="off" spellcheck="false" placeholder="1430 → 14:30" title="Type 0930 for 09:30; colon is optional" value="${jdhlEscape(m.time)}"/></label>
    </div>
    ${this._confirmDelete?`<div class="delete-warning">Permanently delete this drink? This cannot be undone.</div>
     <div class="dialog-actions"><button data-action="delete-back" class="secondary">Cancel</button>
      <button data-action="delete-confirm" class="danger" ${this._busy?'disabled':''}>Confirm delete</button></div>`:
     `<div class="dialog-actions">${this._hass?.user?.is_admin?`<button class="secondary modal-settings" data-action="settings-open"><ha-icon icon="mdi:cog-outline"></ha-icon> Settings</button>`:''}${m.mode==='edit'?`<button data-action="delete" class="danger" ${this._busy?'disabled':''}>Delete</button>`:''}
      <button data-action="cancel" class="secondary">Cancel</button>
      <button data-action="save" ${this._busy?'disabled':''}>Save</button></div>`}`}
   </section></div>`;
 }
 _render(force=false){if(!this._config||!this._hass)return;
  if((this._modal||this._settingsSection)&&!force)return; // Preserve typed popup fields.
  const selectedDate=this._viewDate||this._todayISO(),isToday=selectedDate===this._todayISO();
  const daySummary=this._history?.date===selectedDate?this._history?.day_summary:null;
  const pendingPast=!isToday&&!daySummary;
  const target=Number(daySummary?.target_ml??(isToday?this._millilitres('daily_target','target_ml'):0));
  const consumed=Number(daySummary?.consumed_ml??(isToday?this._millilitres('consumed_today','consumed_ml'):0));
  const remaining=Math.max(0,target-consumed),pct=target?consumed/target*100:0;
  const title=this._config.title||'jwDaily Hydration Log';
  const count=Number(daySummary?.drink_count??(isToday?jdhlNum(this._state('drink_count_today')?.state):0));
  const k=JSON.stringify([target,consumed,this._history,this._modal,this._calendarOpen,this._calendarMonth,this._historyCalendarOpen,this._historyCalendarMonth,this._manageOpen,this._customDraft,this._settingsSection,this._settingsDraft,this._confirmDelete,this._busy,this._error,this._status,this._viewDate,this._undoId,this._config]);
  if(!force&&this._lastRender===k)return;this._lastRender=k;
  this.shadowRoot.innerHTML=`<style>

/* beta.16 unified responsive layout with stable 2-column hero and compact history/footer */
:host{display:block;min-width:0;width:100%;max-width:100%}
ha-card{display:block;box-sizing:border-box;max-width:100%;overflow:hidden}
.root{box-sizing:border-box;display:flex;flex-direction:column;gap:4px;min-width:0;padding:18px 20px 12px;color:var(--primary-text-color,#202a32)}
header h2{font-size:1.15rem;font-weight:650;margin:0;min-width:0;overflow-wrap:anywhere}
.main-head{display:flex;align-items:flex-start;justify-content:space-between;gap:8px}
.settings-trigger{flex:none;font-size:.75rem!important;padding:4px 7px!important}
@container jdhl-card (max-width:420px){.settings-trigger span{display:none}}
.muted{color:var(--secondary-text-color,#63717d)}
.error{color:var(--error-color,#b52027);font-size:.86rem}
.center{text-align:center}
/* The glass and charts form ONE two-column hero; a width-dependent glass scale
   replaces the former fixed 274px glass and premature 455px stacking. */
.hero-shell{container:jdhl-card / inline-size;width:100%;min-width:0}
.hero{display:grid;grid-template-columns:clamp(185px,39%,260px) minmax(0,1fr);column-gap:9px;align-items:start;width:100%;min-width:0}
.glass-side{grid-column:1;grid-row:1;min-width:0;width:100%}
.glass-stack{display:grid;grid-template-columns:minmax(72px,30%) minmax(0,70%);grid-template-rows:auto 20px;align-items:start;width:100%;min-width:0}
.taken-slot{position:relative;grid-column:1;grid-row:1;height:100%;min-width:0}
.taken{position:absolute;right:-26px;top:var(--fill-y);transform:translateY(-50%);color:#168dd1;font-size:19px;font-weight:700;line-height:1.13;white-space:nowrap;text-align:right}
.glass-frame{grid-column:2;grid-row:1;min-width:0;width:100%;transform:translateX(-7px)}
.glass-viz{position:relative;width:100%;aspect-ratio:4/5}
.glass{display:block;position:absolute;inset:0;width:100%;height:100%;margin:0}
.cup-target,.cup-remaining{position:absolute;left:50%;transform:translate(-50%,-50%);font-size:14px;line-height:1.1;white-space:nowrap;text-align:center;pointer-events:none;text-shadow:1px 1px 1px white,-1px 1px 1px white,1px -1px 1px white,-1px -1px 1px white}
.cup-target{top:11.8%;color:#e03535;font-weight:650}
.cup-remaining{color:var(--primary-text-color,#172b3b);font-weight:500}
.drink-count{grid-column:2;grid-row:2;min-width:0;width:100%;margin:0;text-align:center;white-space:nowrap;font-size:.86rem;line-height:1.4;overflow:visible}
.hero-side{grid-column:2;grid-row:1;align-self:stretch;min-width:0;width:100%;min-height:0;display:flex;flex-direction:column;padding:1px 0 0;box-sizing:border-box}
.liquid-bars{align-self:stretch;width:100%;min-width:0;overflow:visible}
.bars-title{font-size:.88rem;font-weight:650;margin:0 0 9px -10px;line-height:1.3}
.bars-date{font-size:.74rem;font-weight:450}
.bar-line{display:grid;grid-template-columns:minmax(0,auto) minmax(12px,1fr) max-content;gap:4px;align-items:center;width:100%;min-width:0;margin:8px 0;font-size:.77rem}
.bar-line span{overflow:visible;white-space:normal;overflow-wrap:anywhere;min-width:0;display:inline-flex;align-items:center;gap:5px;margin-left:-10px}
.bar-line strong{font-size:.76rem;font-weight:600;white-space:nowrap;text-align:right;justify-self:end;font-variant-numeric:tabular-nums}
.bar-track{height:11px;min-width:0;border-radius:8px;background:var(--secondary-background-color,#e5e7eb);overflow:hidden}
.bar-fill{height:100%;background:#34a5dc;border-radius:8px;min-width:2px}
/* Keep every ordinary label, bar and amount on ONE row, even at narrow widths. */
.bar-line{grid-template-columns:minmax(0,max-content) minmax(9px,1fr) max-content;column-gap:5px;}
.bar-line span{min-width:0;max-width:min(160px,52%);white-space:nowrap;overflow:visible;display:inline-flex;}
.bar-line .bar-track{grid-column:2;grid-row:1;min-width:9px}
.bar-line strong{grid-column:3;grid-row:1}
.bar-track{outline:1px solid color-mix(in srgb,var(--primary-text-color,#222) 7%,transparent)}
.action-row.hero-actions{position:static;transform:none;width:100%;margin-top:2px;display:flex;justify-content:space-between;align-items:center;gap:8px;padding:6px 0 8px;margin-top:2px}
.action-row button{display:inline-flex;align-items:center;justify-content:center;gap:5px}
.action-row ha-icon{--mdc-icon-size:16px;width:16px;height:16px}
.action-row .settings-trigger{background:#EEEEEE;color:#242a30;border-color:#c8ccd0}
.action-row .settings-trigger:hover{background:#dedede}
.modal-settings{margin-right:auto!important;background:#EEEEEE!important;border-color:#c8ccd0!important;color:#242a30!important;display:inline-flex;align-items:center;gap:5px}
.modal-settings ha-icon{--mdc-icon-size:17px}
.settings-profile-current{border:1px solid var(--divider-color,#ddd);background:var(--secondary-background-color,#f7f9fa);border-radius:11px;padding:12px;display:flex;align-items:center;gap:10px}
.settings-profile-current ha-icon{--mdc-icon-size:26px}
.settings-profile-current small{display:block;color:var(--secondary-text-color)}
.settings-category{margin:13px 0 4px;font-size:.68rem;letter-spacing:.07em;font-weight:750;color:var(--secondary-text-color,#65707a)}
.settings-nav{display:flex;flex-direction:column;gap:0}
button.settings-nav-item,button.settings-nav-item.secondary{width:100%;background:transparent;border:0;border-radius:0;border-bottom:1px solid var(--divider-color,#e5e5e5);color:var(--primary-text-color,#222);padding:11px 5px;display:flex;align-items:center;text-align:left;gap:12px;min-height:54px}
.settings-nav-item ha-icon{--mdc-icon-size:22px;flex:none}
.settings-nav-item span{display:block;flex:1;min-width:0}
.settings-nav-item strong{display:block;font-size:.89rem;font-weight:650}
.settings-nav-item small{display:block;font-size:.73rem;line-height:1.3;color:var(--secondary-text-color)}
.settings-nav-item:hover{background:var(--secondary-background-color,#f4f7f9)!important}
.settings-edit{background:var(--secondary-background-color,#f7f9fa);border-radius:10px;padding:10px;margin:10px 0;display:grid;gap:9px}
.settings-edit label{display:flex;flex-direction:column;gap:4px}
.settings-edit input,.settings-edit select,.convert-row select,.convert-row input:not([type=checkbox]){box-sizing:border-box;width:100%;min-width:0;border:1px solid #b8c4cc;border-radius:7px;background:var(--card-background-color,#fff);color:var(--primary-text-color,#222);padding:8px}
.settings-edit .check-label,.convert-row .check-label{display:flex;flex-direction:row;align-items:center;gap:8px}
.settings-edit .check-label input,.convert-row .check-label input{width:auto}
.convert-row{display:grid;grid-template-columns:minmax(120px,1.2fr) minmax(95px,1fr) minmax(95px,1fr);gap:8px;padding:10px 0;border-bottom:1px solid var(--divider-color,#ddd)}
.convert-row label{display:flex;flex-direction:column;min-width:0;gap:4px;font-size:.78rem}
.convert-row label.check-label{flex-direction:row}
.migration-summary{background:var(--secondary-background-color,#f6f8f9);border:1px solid var(--divider-color,#ddd);border-radius:10px;padding:10px;margin:12px 0}
@media(max-width:560px){.convert-row{grid-template-columns:minmax(0,1fr);gap:7px}}

.type-dot{width:6px;height:6px;min-width:6px;border-radius:50%;display:inline-block;flex:none}
.hero-actions{position:static;margin-top:auto;display:flex;justify-content:flex-end;align-items:flex-end;width:100%;padding:8px 0 0;min-width:0;transform:translateY(-10px)}
.hero-actions .add-drink{font-size:.86rem;font-weight:650;min-width:0;max-width:100%;padding:7px 12px;line-height:1.2;border-radius:13px;white-space:nowrap}
.day-loading{font-size:.93rem;color:var(--secondary-text-color);padding:22px 8px;min-height:140px}
/* Exactly five 38px data rows are visible, with a separately sticky 35px header.
   Older records scroll inside the table, without clipping the first or last row. */
.history{border-top:1px solid var(--divider-color,#ddd);padding-top:8px;margin-top:0;min-width:0}
.history-head{display:flex;justify-content:space-between;align-items:center;gap:10px}
.history h3{font-size:1.05rem;font-weight:650;margin:0}
.history-head .muted{font-size:.88rem}
.date-nav{display:flex;align-items:center;justify-content:flex-start;gap:5px;margin:5px 0 6px}
.date-nav input{width:160px;max-width:48%;box-sizing:border-box;text-align:center;font:inherit;font-size:1.23rem;font-weight:700;line-height:1.2;padding:7px 8px;color:var(--primary-text-color);background:#fff;border:1px solid var(--divider-color,#bbb);border-radius:9px}
.date-nav button{font-size:1rem;padding:6px 10px;min-height:34px}
.history-date-selector{position:relative;display:flex;align-items:stretch;min-width:0;flex:0 0 auto}
.history-date-selector input{border-radius:9px 0 0 9px;width:94px;flex:0 0 94px;max-width:none;font-size:.90rem;padding:5px 3px;font-weight:650}
.history-calendar-button{border-radius:0 9px 9px 0;min-width:30px;flex:0 0 30px;font-size:1rem;padding:5px}
.history-calendar{position:absolute;top:100%;left:0;z-index:20;width:258px;padding:10px;box-sizing:border-box;border:1px solid #b5c2cb;border-radius:11px;background:var(--card-background-color,#fff);box-shadow:0 8px 24px #0003}
.history-cal-nav{display:flex;align-items:center;justify-content:space-between;gap:4px;font-size:.85rem;margin-bottom:8px}
.history-cal-nav button{padding:4px 7px;min-height:28px}
.history-cal-grid{display:grid;grid-template-columns:repeat(7,minmax(0,1fr));gap:2px}
.history-cal-weekday{text-align:center;font-size:.7rem;color:var(--secondary-text-color,#667);padding:4px 0}
.history-cal-day{padding:4px 0!important;font-size:.76rem!important;min-height:28px;border-radius:5px!important}

.history-table{max-height:170px;overflow-y:auto;overflow-x:hidden;scrollbar-width:thin;scrollbar-color:#aab0b5 transparent}
.history-table table{border-collapse:separate;border-spacing:0;table-layout:fixed;width:100%;min-width:0}
.history-table thead tr{height:30px}
.history-table th{height:30px;box-sizing:border-box;position:sticky;top:0;z-index:2;padding:0 6px;border-bottom:1px solid var(--divider-color,#ddd);font-size:.88rem;font-weight:500;color:var(--secondary-text-color,#667);text-align:left;background:var(--card-background-color,#fff)}
.history-table tbody tr{height:28px;max-height:28px;min-height:28px}
.history-table tbody td{height:28px;box-sizing:border-box;padding:0 6px;line-height:20px;font-size:.88rem;vertical-align:middle;font-variant-numeric:tabular-nums;border-bottom:1px solid var(--divider-color,#ddd);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.history-table th:nth-child(1),.history-table td:nth-child(1){width:17%}
.history-table th:nth-child(2),.history-table td:nth-child(2){width:25%}
.history-table th:nth-child(3),.history-table td:nth-child(3){width:32%}
.history-table th:nth-child(4),.history-table td:nth-child(4){width:26%}
@container (max-width:430px){.history-table th,.history-table td{padding-inline:3px!important;font-size:.77rem!important}}

.history-table td.right,.history-table th.right{text-align:right;white-space:nowrap}
.history-table tr[data-action]{cursor:pointer}
.history-table tr[data-action]:hover{background:color-mix(in srgb,#b3e5fc 30%,white)}
.card-footer{display:flex;align-items:flex-end;justify-content:space-between;gap:10px;border:0;padding:4px 0 0;min-height:0;margin-left:-5px;margin-right:-13px}.export{margin:0;padding:0;text-align:left}
.export button{font-size:.72rem;padding:4px 8px;line-height:1.25;min-height:28px;max-width:100%}
.card-version{margin-left:auto;align-self:flex-end;font-size:.72rem;color:var(--secondary-text-color,#666);padding-bottom:0;transform:translateY(5px)}
/* beta.21: compact footer geometry remains authoritative; intake, cup and right-edge alignment tuned. */
.card-footer .export button.secondary{font-size:.76rem;line-height:1.05;height:28px;min-height:28px;max-height:28px;padding:3px 8px;box-sizing:border-box;border-radius:9px;white-space:nowrap}
/* Centralized controls. Disabled and manage actions are deliberately different. */
button,button.secondary,button.small,button.liquid-choice,button.amount,button.danger{
 font:inherit;cursor:pointer;background:#B3E5FC;color:#18374b;
 border:1px solid #71b4d2;border-radius:11px;padding:6px 10px;
 box-sizing:border-box;transition:background-color .14s ease,border-color .14s ease,box-shadow .14s ease}
button:hover:not(:disabled){background:#95d9f9;border-color:#3e96c2}
button:active:not(:disabled){background:#80cfee}
button:focus-visible{outline:2px solid #0578b3;outline-offset:2px}
button.selected,button.liquid-choice.selected,button.amount.selected{background:#B3E5FC;color:#092e48;border-color:#046eac;box-shadow:inset 0 0 0 2px #046eac;font-weight:650}
button:disabled{opacity:.39;filter:grayscale(.32);cursor:not-allowed;box-shadow:none}
button.small{padding:5px 8px;border-radius:9px;font-size:.85rem}
button.danger{color:#9a2525;border-color:#bd7a7a}
button.manage-control,button.manage-control:not(:disabled){background:#EEEEEE;border-color:#c8ccd0;color:#242a30}
button.manage-control:hover:not(:disabled){background:#dcdcdc;border-color:#9e9e9e}
/* Modal and compact managers */
.overlay{position:fixed;inset:0;z-index:10000;background:rgba(0,0,0,.4);display:flex;align-items:center;justify-content:center;padding:14px;box-sizing:border-box}
.dialog{width:min(660px,100%);box-sizing:border-box;max-height:calc(100vh - 28px);overflow-y:auto;background:var(--card-background-color,#fff);color:var(--primary-text-color,#222);border-radius:15px;padding:18px;box-shadow:0 15px 45px #0004}
.dialog.dialog-manage-liquids{width:min(555px,100%)}
.dialog.dialog-manage-volumes{width:min(450px,100%)}
.dialog h3{margin:0 0 11px;font-size:1.19rem}
.modal-heading{font-size:.95rem;font-weight:650;margin:11px 0 6px}
.liquid-choices,.volume-choices,.cup-choices,.quick-choices{display:flex;flex-wrap:wrap;gap:6px;align-items:center}
.liquid-choice,.volume-choices .amount,.cup-choice,.quick-choice{font-size:.93rem!important;line-height:1.2;min-height:34px;padding:5px 9px!important}
.liquid-choice{display:inline-flex;align-items:center;gap:5px}
button.liquid-choice.custom-liquid-color{background:var(--liquid-choice-bg);color:var(--liquid-choice-ink);border-color:var(--liquid-choice-ink)}
button.liquid-choice.custom-liquid-color:hover:not(:disabled){background:var(--liquid-choice-bg);color:var(--liquid-choice-ink);border-color:var(--liquid-choice-ink);box-shadow:0 0 0 2px var(--liquid-choice-ink)}
button.liquid-choice.custom-liquid-color.selected{background:var(--liquid-choice-bg);color:var(--liquid-choice-ink);border-color:var(--liquid-choice-ink);box-shadow:inset 0 0 0 2px var(--liquid-choice-ink),0 0 0 1px var(--liquid-choice-bg);font-weight:750}
button.liquid-choice.custom-liquid-color:focus-visible{outline:3px solid var(--focus-color,#0578b3);outline-offset:3px}
button.liquid-choice.custom-liquid-color .svg-icon{filter:brightness(0)}
button.liquid-choice.custom-liquid-color[style*="#FFFFFF"] .svg-icon{filter:brightness(0) invert(1)}
.liquid-icon{width:23px;height:23px;min-width:23px;--mdc-icon-size:23px;display:inline-block;object-fit:contain}
.volume-choices{margin-bottom:8px}
.cup-choices,.quick-choices{gap:6px;flex-wrap:wrap}
.quick-choice{--quick-color:#B3E5FC;border-left:5px solid var(--quick-color)!important}
.tinted-liquid-icon{color:inherit}
.masked-icon{mask-size:contain;mask-repeat:no-repeat;mask-position:center;-webkit-mask-size:contain;-webkit-mask-repeat:no-repeat;-webkit-mask-position:center}
.settings-head{display:flex;align-items:center;justify-content:space-between;gap:8px}
.settings-nav{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px}
.settings-nav button{text-align:left;padding:12px!important;min-height:54px}
.settings-section{min-height:0}.settings-section h3{margin:0 0 8px}
.settings-note{font-size:.84rem;color:var(--secondary-text-color,#667);margin:6px 0}
.settings-row{display:grid;grid-template-columns:minmax(0,1fr) auto auto auto;gap:5px;align-items:center;border-bottom:1px solid #ddd;padding:6px 0}
.settings-row .row-title{min-width:0;overflow-wrap:anywhere}
.settings-row .row-title small{display:block;color:#677;font-size:.78rem}
/* Compact Hide/Restore before Edit; Quick controls stay grouped on small screens. */
.settings-row .settings-hide-button{font-size:.71rem!important;padding:3px 6px!important;min-height:28px}
.settings-row.quick-settings-row{grid-template-columns:minmax(0,1fr) auto;gap:8px}
.settings-row-actions{display:flex;flex-wrap:wrap;gap:4px;justify-content:flex-end;align-items:center;max-width:100%}
.settings-row-actions button{min-height:29px}
@media(max-width:540px){.settings-row.quick-settings-row{grid-template-columns:minmax(0,1fr)}.settings-row.quick-settings-row .settings-row-actions{justify-content:flex-start}}

.settings-edit{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px;margin:10px 0}
.settings-edit label{display:flex;flex-direction:column;gap:4px;font-size:.85rem;min-width:0}
.settings-edit input,.settings-edit select,.mapping-grid select{font:inherit;width:100%;min-width:0;padding:8px;border:1px solid #aab8c2;border-radius:8px;background:var(--card-background-color,#fff);color:var(--primary-text-color,#222);box-sizing:border-box}
.mapping-panel{border:1px solid #ccd7dc;border-radius:9px;padding:9px;margin:8px 0}
.mapping-panel p{margin:5px 0}.mapping-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px}
.settings-head button{background:#EEEEEE!important}
.settings-nav button:focus-visible,.settings-row button:focus-visible{outline:3px solid #0578b3;outline-offset:2px}
@media(max-width:440px){.settings-nav,.settings-edit,.mapping-grid{grid-template-columns:1fr}.settings-row{grid-template-columns:minmax(0,1fr) auto auto}}
.add-type,.manage-volumes{margin-top:7px;font-size:.86rem}
.fields{display:grid;grid-template-columns:repeat(3,minmax(0,165px));gap:10px;justify-content:start;margin-top:8px}
.fields label{min-width:0;display:flex;flex-direction:column;gap:5px;font-size:.91rem}
.fields input,.fields select{min-width:0;width:100%;box-sizing:border-box;background:#fff;color:#222;border:1px solid #b8c4cc;border-radius:8px;padding:9px 8px;font:inherit;font-size:1.08rem}
.date-select{position:relative}
button.date-trigger,button.date-trigger:not(:disabled),button.date-trigger:hover:not(:disabled){display:flex;justify-content:space-between;align-items:center;gap:8px;width:100%;background:#FFFFFF;color:#222;border:1px solid #b8c4cc;border-radius:8px;text-align:left;font-size:1.08rem;padding:9px 8px;line-height:1.3}
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
.saved-liquid-icon{position:relative;width:23px;height:25px;display:inline-flex;align-items:center;color:var(--primary-text-color)}
.manage-color-dot{width:8px;height:8px;border-radius:50%;border:1px solid #526070;box-sizing:border-box;flex:0 0 8px}
.saved-liquid-icon .manage-color-dot{position:absolute;right:-1px;bottom:0}
.hidden-liquid .manage-color-dot{margin-left:-7px}
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
.color-editor{display:grid;grid-template-columns:50px minmax(115px,1fr) 26px auto;gap:7px;align-items:end;margin-top:9px}
.color-editor label{display:flex;flex-direction:column;gap:3px;min-width:0;font-size:.77rem}
.color-editor input[type=color]{width:42px;height:32px;padding:2px;border:1px solid #9cabb4;border-radius:7px;background:#fff;cursor:pointer}
.color-editor input[type=text]{height:32px;padding:5px 8px;width:100%;min-width:0;box-sizing:border-box;border:1px solid #9cabb4;border-radius:7px;text-transform:uppercase;font-size:.88rem;background:#fff;color:#222}
.color-preview{width:25px;height:30px;border:1px solid #728390;border-radius:5px;box-sizing:border-box}
.color-editor button{font-size:.74rem!important;white-space:nowrap;padding:6px 7px!important}
.color-error{font-size:.8rem;margin:4px 0 0}.color-error[hidden]{display:none}
.color-editor input:focus-visible{outline:2px solid #0578b3;outline-offset:2px}
.volume-rows{display:flex;flex-direction:column;gap:2px}
.volume-edit-row{display:grid;grid-template-columns:minmax(0,1fr) 32px 32px 75px;gap:5px;align-items:center;border-bottom:1px solid var(--divider-color,#ddd);padding:2px 0;height:42px;min-height:42px;max-height:42px;box-sizing:border-box}
.volume-edit-row label{font-size:.78rem;display:flex;flex-direction:row;align-items:center;justify-content:space-between;gap:6px;min-width:0;white-space:nowrap}
.volume-edit-row input{width:78px;max-width:48%;height:32px;min-width:0;box-sizing:border-box;border:1px solid #bbb;border-radius:8px;background:#fff;color:#222;font:inherit;font-size:.9rem;padding:4px 6px}
.volume-edit-row button{height:32px;padding:3px 4px!important;font-size:.78rem!important}
.delete-warning{margin-top:12px;padding:9px;border:1px solid #b54242;border-radius:8px;color:#9b2121;font-size:.88rem}
.status{font-size:.82rem;color:var(--secondary-text-color)}
/* A 720px screenshot may correspond to only 360 CSS pixels when the browser is zoomed.
   Keep the charts alongside the cup at all practical dashboard card widths. */
@container jdhl-card (max-width:279px){
 .hero{grid-template-columns:minmax(0,1fr);row-gap:6px}
 .glass-side{grid-column:1;grid-row:1;width:min(260px,100%);margin:0 auto}
 .hero-side{grid-column:1;grid-row:2;min-height:0}
 .hero-actions{margin-top:6px}
 .hero-side{padding-bottom:0}
 .taken{right:0}
 .card-footer{margin-left:0;margin-right:0}
}
@container jdhl-card (min-width:280px) and (max-width:560px){
 .hero{grid-template-columns:clamp(132px,39%,198px) minmax(0,1fr);column-gap:6px}
 .glass-stack{grid-template-columns:minmax(48px,32%) minmax(0,68%)}
 .hero-side{min-height:0}
 .bar-line{grid-template-columns:minmax(0,auto) minmax(12px,1fr) max-content;gap:3px;margin:6px 0;font-size:.72rem}
 .bar-line strong{font-size:.69rem;justify-self:end}
 .taken{font-size:19px;right:-16px}
 .drink-count{font-size:clamp(.75rem,2.1cqw,.88rem)}
}
/* At narrow card widths keep the 24px total clear of the cup outline.
   The cup shifts within its left column only; the right chart stays fixed. */
@container jdhl-card (max-width:460px) and (min-width:280px){
 .glass-frame{transform:translateX(6px)}
}
@media(max-width:570px){.dialog.dialog-manage-liquids{width:min(98vw,555px)}}
@media(max-width:475px){
 .color-editor{grid-template-columns:45px minmax(100px,1fr) 26px;row-gap:4px}
 .color-editor button{grid-column:1/-1;justify-self:end}
 .saved-liquid{grid-template-columns:25px minmax(90px,1fr) minmax(65px,auto);row-gap:4px}
 .saved-liquid button{grid-row:2}
 .volume-edit-row{grid-template-columns:minmax(95px,1fr) 32px 32px 70px}
 .volume-edit-row label{font-size:.73rem}
 .volume-edit-row input{width:65px}
 .fields{grid-template-columns:repeat(2,minmax(0,1fr))}
}
@container jdhl-card (max-width:390px){
 .bar-line{grid-template-columns:minmax(0,max-content) minmax(9px,1fr) max-content;gap:3px;margin:7px 0;font-size:.65rem}
 .bar-line span{grid-column:1;grid-row:1;font-size:.65rem;max-width:115px;white-space:nowrap}
 .bar-track{grid-column:2;grid-row:1}
 .bar-line strong{grid-column:3;grid-row:1;font-size:.61rem}
}
@container jdhl-card (max-width:355px){.history-date-selector input{width:88px;flex-basis:88px;font-size:.76rem}.date-nav{gap:3px}.date-nav button{padding:5px 6px}}
@media(max-width:380px){.root{padding:12px}.fields{grid-template-columns:1fr}.dialog{padding:12px}}


/* beta.27: ONE SHARED THREE-COLUMN GRID for all Today by liquid rows.
   Independent row grids caused the right bars to begin at different X positions. */
.liquid-bars:has(.bar-line){display:grid;grid-template-columns:fit-content(52%) minmax(12px,1fr) max-content;
 column-gap:5px;row-gap:11px;align-items:center;min-width:0}
.liquid-bars .bars-title{grid-column:1/-1;margin:0 0 2px -10px}
.liquid-bars .bar-line{display:contents}
.liquid-bars .bar-line>span{grid-column:1;grid-row:auto;min-width:0;max-width:none;white-space:normal;
 overflow-wrap:anywhere;margin-left:-10px;display:inline-flex;align-items:center;font-size:.72rem}
.liquid-bars .bar-line>.bar-track{grid-column:2;grid-row:auto;min-width:12px;width:100%;margin:0}
.liquid-bars .bar-line>strong{grid-column:3;grid-row:auto;justify-self:end;white-space:nowrap;font-size:.72rem}
@container jdhl-card (max-width:390px){
 .liquid-bars:has(.bar-line){grid-template-columns:fit-content(53%) minmax(12px,1fr) max-content;
  column-gap:3px;row-gap:10px}
 .liquid-bars .bar-line>span{font-size:.65rem}
 .liquid-bars .bar-line>strong{font-size:.64rem}
}

   </style><ha-card><div class="root">
   <header class="main-head">${this._config.show_title!==false?`<h2>${jdhlEscape(title)}</h2>`:'<span></span>'}

   </header>
   <div class="hero-shell">
    ${pendingPast?`<p class="day-loading">Loading ${jdhlEscape(jdhlIsoToDate(selectedDate))}…</p>`:`
    <div class="hero">
      <div class="glass-side"><div class="glass-stack">
        <div class="taken-slot"><span class="taken" style="--fill-y:${(100*(pct>100?19:179-(179-39)*Math.min(100,Math.max(0,pct))/100)/200).toFixed(2)}%">${jdhlFmt(consumed)}</span></div>
        <div class="glass-frame">${this._config.show_cup!==false?this._glass(pct,remaining,target):''}</div>
        <div class="drink-count">◷ ${count} drink moments</div>
      </div></div>
      <div class="hero-side">${this._dayBarsHTML()}</div>
    </div>`}
    <div class="hero-actions action-row">
     ${this._hass?.user?.is_admin?`<button class="secondary settings-trigger" data-action="settings-open"><ha-icon icon="mdi:cog-outline"></ha-icon> Settings</button>`:'<span></span>'}
     ${this._config.show_manual!==false?`<button class="add-drink" data-action="new" ${this._busy?'disabled':''}><ha-icon icon="mdi:plus"></ha-icon> Add drink</button>`:''}
    </div></div>
   ${this._error?`<div class="error" role="alert">${jdhlEscape(this._error)}</div>`:''}
   ${this._historyHTML()}
   ${this._modalHTML()}
   <footer class="card-footer">
    ${this._config.show_export!==false&&this._hass?.user?.is_admin?`<div class="export"><button class="secondary" data-action="export" aria-label="Export all data to Excel (.xlsx)" ${this._busy?'disabled':''}>Export to Excel (.xlsx)</button></div>`:''}
    <span class="card-version">v1.1.0-beta.31</span>
   </footer></div></ha-card>`;
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
/* Independently selectable Lovelace chart cards backed by actual jwDaily sensors.
   No ApexCharts dependency, no synthetic records and no additional HA storage. */
const JDHL_CHART_KINDS=[
 {tag:'jwdaily-hydration-hourly-card',name:'jwDaily Hydration – Today by hour',key:'hourly_intake_today',title:'Today by hour',days:false},
 {tag:'jwdaily-hydration-weekly-card',name:'jwDaily Hydration – Last 7 days',key:'daily_intake_last_7_days',title:'Last 7 days',days:true}
];
const JDHL_PALETTE=['#39A8DE','#F2A34A','#67B69A','#9280D0','#DD7BA6','#79A2E7','#C6AD63','#82B5CB'];
/* Shared stable color assignment: the exact same drink uses the exact same
   color on hourly and weekly charts, independent of data/legend order. */
function jdhlLiquidColor(id,name){
 const key=String(id||'').trim().toLowerCase();
 const label=String(name||id||'').trim().toLowerCase();
 const pair=key+' '+label;
 if(/water/.test(pair)&&/(beker|cup)/.test(pair))return '#9280D0';
 if(/water/.test(pair)&&/(glas|glass)/.test(pair))return '#DD7BA6';
 if(/coffee|koffie/.test(pair))return '#F2A34A';
 if(/tea|thee/.test(pair))return '#67B69A';
 if(/milk|melk/.test(pair))return '#39A8DE';
 if(/orange|sinaasappel/.test(pair))return '#D45A38';
 if(/wine|wijn/.test(pair))return '#C6AD63';
 if(/soup|soep/.test(pair))return '#82B5CB';
 if(key==='water'||label==='water')return '#79A2E7';
 if(key==='other'||label==='other'||label==='overige')return '#B89D83';
 let hash=2166136261;for(const ch of key){hash=Math.imul(hash^ch.charCodeAt(0),16777619)>>>0;}
 return JDHL_PALETTE[hash%JDHL_PALETTE.length];
}
function jdhlChartProfile(hass){
 const prefix='sensor.jwdhl_',suffix='_daily_target';
 return Object.keys(hass?.states||{}).filter(v=>v.startsWith(prefix)&&v.endsWith(suffix)).sort().map(v=>v.slice(prefix.length,-suffix.length))[0]||'';
}
class JwDailyHydrationChartCard extends HTMLElement {
 constructor(){
  super();this.attachShadow({mode:'open'});this._config=null;this._hass=null;
  this._kind=this.constructor.chartKind||JDHL_CHART_KINDS[0];this._selectedBucket=null;
  this.shadowRoot.addEventListener('click',e=>{
   const close=e.target.closest('[data-chart-close]');
   if(close){this._selectedBucket=null;this._render();return;}
   const hit=e.target.closest('[data-chart-bucket]');
   if(hit){this._selectedBucket=Number(hit.dataset.chartBucket);this._render();}
  });
  this.shadowRoot.addEventListener('keydown',e=>{
   if(e.key==='Escape'&&this._selectedBucket!==null){this._selectedBucket=null;this._render();}
   if(e.key!=='Enter'&&e.key!==' ')return;
   const hit=e.target.closest('[data-chart-bucket]');
   if(hit){e.preventDefault();this._selectedBucket=Number(hit.dataset.chartBucket);this._render();}
  });
 }
 static getStubConfig(hass){return {type:`custom:${this.chartKind.tag}`,profile:jdhlChartProfile(hass),title:this.chartKind.title};}
 setConfig(config){if(!config)throw Error('Missing chart card configuration');this._config={...config};this._selectedBucket=null;this._render();}
 set hass(hass){this._hass=hass;this._render();}
 getCardSize(){return 3;}
 connectedCallback(){
  if(typeof ResizeObserver!=='undefined'&&!this._resizer){
   this._resizer=new ResizeObserver(()=>{const w=Math.round(this.getBoundingClientRect().width);
    if(w>0&&Math.abs(w-(this._lastWidth||0))>=4){this._lastWidth=w;this._render();}});
   this._resizer.observe(this);
  }
 }
 disconnectedCallback(){this._resizer?.disconnect();this._resizer=null;}
 _render(){if(!this._config||!this._hass)return;
  const profile=this._config.profile||jdhlChartProfile(this._hass);
  const entity=this._hass.states?.[`sensor.jwdhl_${profile}_${this._kind.key}`];
  const input=entity?.attributes?.[this._kind.days?'days':'buckets'];
  const list=Array.isArray(input)?input:[];
  const shortMonths=['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
  const records=list.map((row,i)=>{
   const original=String(row.date||'');
   const parts=original.split('-');
   const formatted=(parts.length===3&&Number(parts[1])>=1&&Number(parts[1])<=12)?`${Number(parts[2])} ${shortMonths[Number(parts[1])-1]}`:original;
   const liquidValues=row.liquids&&typeof row.liquids==='object'?row.liquids:{};
   const liquids=Object.fromEntries(Object.entries(liquidValues).map(([k,v])=>[k,Math.max(0,Number(v)||0)]));
   const total=Math.max(0,Number(row.total_logged_ml??row.total_ml??0));
   return {label:this._kind.days?formatted:String(i+1),rawDate:original,liquids,total,hasData:!this._kind.days||row.has_data!==false};
  });
  const names=entity?.attributes?.liquid_names||{};
  const totals={};for(const r of records)for(const [k,v] of Object.entries(r.liquids))totals[k]=(totals[k]||0)+v;
  const latest=records.at(-1)?.liquids||{};
  // Current day totals determine order in both graphs (same as the main card).
  // Historical-only types come after today's types, ordered by period volume.
  const keys=Object.keys(totals).sort((a,b)=>(latest[b]||0)-(latest[a]||0)||(totals[b]||0)-(totals[a]||0)||String(names[a]||a).localeCompare(String(names[b]||b)));
  const total=records.reduce((a,r)=>a+r.total,0);
  const highest=Math.max(1,...records.map(r=>r.total));
  const rawTick=highest/4;
  const power=Math.pow(10,Math.floor(Math.log10(rawTick)));
  const niceTicks=[1,1.25,1.5,2,2.5,3,4,5,7.5,10];
  const step=niceTicks.find(n=>n*power>=rawTick-1e-9)*power;
  const max=step*4;
  const fmt=v=>Math.round(v).toLocaleString('en-US');
  const style=`<style>
  :host{display:block;min-width:0}ha-card{display:flex;flex-direction:column;box-sizing:border-box;padding:16px 15px 10px;min-height:0;height:auto;color:var(--primary-text-color,#172c39)}
  h3{margin:0 0 6px;font-weight:650;font-size:1rem}.notice{font-size:.87rem;color:var(--secondary-text-color,#687783)}
  .summary{font-size:.79rem;margin:0 0 3px;color:var(--secondary-text-color,#526474)}
  .chart{width:100%;height:auto;display:block;overflow:visible}
  .axis-text{font-family:inherit;font-size:13px;fill:var(--secondary-text-color,#657784)}
  .axis-unit{font-family:inherit;font-size:13px;fill:var(--secondary-text-color,#657784)}
  .bucket-hit{cursor:pointer;outline:none}
  .bucket-hit:focus-visible{stroke:#036caa;stroke-width:2}
  .empty-marker{font-family:inherit;font-size:12px;fill:var(--secondary-text-color,#7a8b95)}
  .chart-note{font-size:.74rem;margin:7px 0 0;color:var(--secondary-text-color,#657784)}
  .detail-panel{margin:9px 0 0;padding:9px 11px;border:1px solid var(--divider-color,#d1dce2);border-radius:9px;font-size:.83rem;background:var(--secondary-background-color,#f6f9fb)}
  .detail-head{display:flex;align-items:center;justify-content:space-between;gap:8px}
  .detail-head button{background:transparent;border:0;font-size:1rem;color:var(--primary-text-color,#263746);cursor:pointer;padding:1px 5px}
  .detail-items{display:flex;flex-wrap:wrap;gap:4px 12px;margin:5px 0 0}
  .detail-items span{white-space:nowrap}
  .grid-line{stroke:var(--divider-color,#d2dbe0);stroke-width:.8;stroke-dasharray:2 3}
  .legend{display:flex;flex-wrap:wrap;gap:5px 12px;margin:8px 0 0;font-size:.81rem}
  .legend span{display:inline-flex;align-items:center;gap:5px;white-space:nowrap}
  .swatch{width:10px;height:10px;border-radius:2px;display:inline-block}
  .foot{font-size:.72rem;color:var(--secondary-text-color,#687783);margin-top:7px;padding-top:0;align-self:flex-end;text-align:right}
  </style>`;
  const title=jdhlEscape(this._config.title||this._kind.title);
  if(!records.length){this.shadowRoot.innerHTML=`${style}<ha-card><h3>${title}</h3><p class="notice">${jdhlEscape(entity?'No recorded intake for this period.':'The jwDaily chart sensor is not available for this profile.')}</p><div class="foot">v1.1.0-beta.31</div></ha-card>`;return;}
  const colorSettings=entity?.attributes?.liquid_colors||{};
  const colors=new Map(keys.map(key=>[key,jdhlHex(colorSettings[key])||jdhlLiquidColor(key,names[key])]));
  /* Explicit SVG coordinate system gives a genuine Y axis, labeled gridlines,
     24 x-axis hours (1-24) or seven local day labels, plus daily sum labels. */
  const displayWidth=Math.round(this.getBoundingClientRect().width)||720;
  const viewWidth=Math.max(440,Math.min(750,displayWidth)),left=69,right=12,top=this._kind.days?32:16,bottom=33,graphH=230;
  const graphW=viewWidth-left-right, plotBottom=top+graphH, groupW=graphW/Math.max(1,records.length);
  const barW=Math.min(this._kind.days?64:22,groupW*(this._kind.days?.78:.82));
  let art='';
  for(let tick=0;tick<=4;tick++){
   const value=step*tick,y=plotBottom-graphH*tick/4;
   art+=`<line class="grid-line" x1="${left}" x2="${viewWidth-right}" y1="${y}" y2="${y}"/>`;
   art+=`<text class="axis-text" x="${left-8}" y="${y+4}" text-anchor="end">${fmt(value)}</text>`;
  }
  art+=`<text class="axis-unit" x="13" y="${top+graphH/2}" text-anchor="middle" transform="rotate(-90 13 ${top+graphH/2})">mL</text>`;
  records.forEach((r,i)=>{
   const cx=left+(i+.5)*groupW,x=cx-barW/2;
   let bottomY=plotBottom;
   for(const key of keys){
    const amount=r.liquids[key]||0;
    if(amount<=0)continue;
    const height=graphH*amount/max;
    bottomY-=height;
    art+=`<rect x="${x.toFixed(2)}" y="${bottomY.toFixed(2)}" width="${barW.toFixed(2)}" height="${height.toFixed(2)}" rx="1" fill="${colors.get(key)}" data-chart-bucket="${i}" tabindex="0" role="button" aria-label="Show ${jdhlEscape(r.label)} breakdown"><title>${jdhlEscape(names[key]||key)}: ${fmt(amount)} mL. Tap for details</title></rect>`;
   }
   if(this._kind.days&&r.total===0){
    const message=r.hasData?'0':'—';
    art+=`<text class="empty-marker" x="${cx.toFixed(2)}" y="${plotBottom-8}" text-anchor="middle">${message}</text>`;
    // Larger tap target for missing/zero days, no fake colored bar.
    art+=`<rect class="bucket-hit" x="${(cx-groupW*.38).toFixed(2)}" y="${top}" width="${(groupW*.76).toFixed(2)}" height="${graphH}" fill="transparent" data-chart-bucket="${i}" tabindex="0" role="button" aria-label="Details for ${jdhlEscape(r.label)}" />`;
   }
   if(this._kind.days&&r.total>0){
    const y=Math.max(13,plotBottom-graphH*r.total/max-6);
    art+=`<text x="${cx.toFixed(2)}" y="${y.toFixed(2)}" text-anchor="middle" font-size="13" font-weight="600" fill="var(--primary-text-color,#243746)">${fmt(r.total)} mL</text>`;
   }
   if(this._kind.days||displayWidth>=640||i%2===1){
    art+=`<text class="axis-text" x="${cx.toFixed(2)}" y="${plotBottom+19}" text-anchor="middle" font-size="${this._kind.days?13:11}">${jdhlEscape(r.label)}</text>`;
   }
  });
  const legends=keys.map(k=>`<span><i class="swatch" style="background:${colors.get(k)}"></i>${jdhlEscape(names[k]||k)}${this._kind.days?'':` (${fmt(totals[k])} mL)`}</span>`).join('');
  const anyMissing=this._kind.days&&records.some(r=>!r.hasData);
  const anyZero=this._kind.days&&records.some(r=>r.hasData&&r.total===0);
  const missingNote=this._kind.days&&(anyMissing||anyZero)?`<div class="chart-note">${anyMissing?'— No data recorded':''}${anyMissing&&anyZero?' · ':''}${anyZero?'0 = recorded zero intake':''}</div>`:'';
  const selected=Number.isInteger(this._selectedBucket)?records[this._selectedBucket]:null;
  const detailLabel=selected?(this._kind.days?selected.label:`Hour ${this._selectedBucket+1} (${String(this._selectedBucket).padStart(2,'0')}:00–${String(this._selectedBucket).padStart(2,'0')}:59)`):'';
  const selectedKeys=selected?Object.keys(selected.liquids).filter(k=>selected.liquids[k]>0).sort((a,b)=>selected.liquids[b]-selected.liquids[a]):[];
  const details=!selected?'':`<section class="detail-panel" role="status"><div class="detail-head"><strong>${jdhlEscape(detailLabel)} · ${selected.hasData?`${fmt(selected.total)} mL`:'No data recorded'}</strong><button type="button" data-chart-close aria-label="Close chart details">×</button></div>${selectedKeys.length?`<div class="detail-items">${selectedKeys.map(k=>`<span><i class="swatch" style="display:inline-block;vertical-align:middle;background:${colors.get(k)}"></i> ${jdhlEscape(names[k]||k)}: ${fmt(selected.liquids[k])} mL</span>`).join('')}</div>`:selected.hasData?'<p>No drinks recorded.</p>':'<p>No history is available for this date.</p>'}</section>`;

  const targetEntity=this._hass.states?.[`sensor.jwdhl_${profile}_daily_target`];
  const target=Number(targetEntity?.state);
  const summary=this._kind.days?'':`<p class="summary">Total: ${fmt(total)} mL${Number.isFinite(target)&&target>0?` / Target: ${fmt(target)} mL (${Math.round(total/target*100)}%)`:''}</p>`;
  this.shadowRoot.innerHTML=`${style}<ha-card><h3>${title}</h3>${summary}<svg class="chart" role="img" aria-label="${jdhlEscape(this._kind.title)} chart, y-axis in milliliters" viewBox="0 0 ${viewWidth} ${plotBottom+bottom}">${art}</svg><div class="legend">${legends}</div>${missingNote}${details}<div class="foot">v1.1.0-beta.31</div></ha-card>`;
 }
}
for(const kind of JDHL_CHART_KINDS){
 class Chart extends JwDailyHydrationChartCard {}
 Chart.chartKind=kind;
 Object.defineProperty(Chart,'name',{value:'JwDailyHydration'+(kind.days?'Weekly':'Hourly')+'Card'});
 Chart.prototype._kind=kind;
 if(!customElements.get(kind.tag))customElements.define(kind.tag,Chart);
}
if(!customElements.get(JDHL_TAG))customElements.define(JDHL_TAG,JwDailyHydrationLogCard);
if(!customElements.get(JDHL_EDITOR))customElements.define(JDHL_EDITOR,JwDailyHydrationLogCardEditor);
window.customCards=window.customCards||[];
for(const kind of JDHL_CHART_KINDS){if(!window.customCards.some(c=>c.type===kind.tag))window.customCards.push({type:kind.tag,name:kind.name,description:'Live chart from jwDaily Hydration Log sensors',preview:true});}
if(!window.customCards.some(c=>c.type===JDHL_TAG))window.customCards.push({type:JDHL_TAG,name:'jwDaily Hydration Log',description:'Editable individual liquid tracking with Excel export',preview:true});
console.info('jwDaily Hydration Log Card v1.1.0-beta.31');