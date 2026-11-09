/* jwDaily beta8 browser-shell regression: single popup, custom types & target line. */
const fs=require('fs'),vm=require('vm'),path=require('path'),assert=require('assert');
const src=fs.readFileSync(path.join(__dirname,'../custom_components/jw_daily_hydration_log/www/jwdaily-hydration-log-card.js'),'utf8');
const els={},downloads=[],wsCalls=[];
class Shadow{constructor(){this.innerHTML='';this.listeners={};} addEventListener(n,fn){this.listeners[n]=fn;} appendChild(){} }
class Node{attachShadow(){this.shadowRoot=new Shadow();return this.shadowRoot;} appendChild(){} dispatchEvent(){return true;}}
const sandbox={HTMLElement:Node,customElements:{get:k=>els[k],define:(k,c)=>els[k]=c},
 window:{customCards:[]},console,setInterval(){return 1;},clearInterval(){},setTimeout(f){f();},TextEncoder,
 Blob,URL:{createObjectURL:()=> 'blob:test',revokeObjectURL:()=>{}},
 document:{createElement:()=>({click(){downloads.push(this.download);},remove(){},addEventListener(){}})},
 atob,btoa,Date,CustomEvent:class{},Intl};
vm.createContext(sandbox);vm.runInContext(src,sandbox);
const click=(action,value)=>({target:{closest:()=>({dataset:{action,value}})}});
const history=[];let seq=0;let storedVolumes=null;
const catalog=[
 ['water','Water','mdi:water'],['coffee','Coffee','mdi:coffee'],['tea','Tea','mdi:tea'],
 ['milk','Milk','mdi:cow'],['soup','Soup','mdi:bowl-mix'],['wine','Wine','mdi:glass-wine'],['other','Other','mdi:glass-water']
].map(([id,name,icon_mdi])=>({id,name,icon_mdi,icon_svg:'',default_volume_ml:null,custom:false,hidden:false}));
const hass={user:{is_admin:true},config:{time_zone:'Europe/Amsterdam'},states:{
 'sensor.jwdhl_jan_willem_daily_target':{state:'3000',attributes:{target_ml:3000}},
 'sensor.jwdhl_jan_willem_consumed_today':{state:'0',attributes:{consumed_ml:0}},
 'sensor.jwdhl_jan_willem_manual_consumed':{state:'0',attributes:{manual_consumed_ml:0}},
 'sensor.jwdhl_jan_willem_drink_count_today':{state:'0',attributes:{}}},
 async callWS(msg){
  wsCalls.push({...msg});
  if(msg.type==='jw_daily_hydration_log/capabilities')return {version:'1.1.0-beta.8',add_drink:true,edit_drink:true,custom_liquid_types:true};
  if(msg.type==='jw_daily_hydration_log/history'){
   const breakdown=history.reduce((a,r)=>{let x=a.find(t=>t.liquid_type===r.liquid_type);if(!x){x={liquid_type:r.liquid_type,volume_ml:0};a.push(x);}x.volume_ml+=r.volume_ml;return a;},[]);
   const total=history.reduce((a,r)=>a+r.volume_ml,0);
   return {date:msg.date,entries:history.map(x=>({...x})),
    total_ml:total,liquid_types:catalog.map(x=>({...x})),
    day_summary:{date:msg.date,consumed_ml:total,target_ml:3000,drink_count:history.length,liquid_breakdown:breakdown},
    today_breakdown:breakdown,volume_buttons:storedVolumes,backend_version:'1.1.0-beta.8'};
  }
  if(msg.type==='jw_daily_hydration_log/add_liquid_type'){
   const item={id:'custom_'+(++seq),name:msg.name,icon_mdi:msg.icon_mdi||'',icon_svg:msg.icon_svg||'',
     default_volume_ml:msg.default_volume_ml??null,custom:true};catalog.push(item);return item;
  }
  if(msg.type==='jw_daily_hydration_log/update_liquid_type'){
   const item=catalog.find(x=>x.id===msg.liquid_type);assert(item);
   Object.assign(item,{name:msg.name,icon_mdi:msg.icon_mdi||'',icon_svg:msg.icon_svg||'',default_volume_ml:msg.default_volume_ml??null});return {...item};}
  if(msg.type==='jw_daily_hydration_log/set_liquid_order'){
   const keys=msg.order;assert.strictEqual(keys.length,catalog.length);
   const old=[...catalog];catalog.splice(0,catalog.length,...keys.map(k=>old.find(x=>x.id===k)));
   return {order:keys};}
  if(msg.type==='jw_daily_hydration_log/set_builtin_liquid_visibility'){
   const found=catalog.find(x=>x.id===msg.liquid_type && !x.custom);
   assert(found,'Known built-in liquid');found.hidden=!msg.visible;return {...found};}
  if(msg.type==='jw_daily_hydration_log/set_volume_buttons'){
   storedVolumes=[...msg.volumes];return {volumes:storedVolumes};}
  if(msg.type==='jw_daily_hydration_log/delete_liquid_type'){
   const i=catalog.findIndex(x=>x.id===msg.liquid_type);assert(i>=0);
   assert(!history.some(x=>x.liquid_type===msg.liquid_type));catalog.splice(i,1);return {deleted:true};}
  if(msg.type==='jw_daily_hydration_log/add_drink'){
   const n=String(++seq),volume=msg.volume_ml;
   history.push({id:n,timestamp:'2026-11-08T16:30:20+01:00',volume_ml:volume,liquid_type:msg.liquid_type,origin:'dashboard'});
   this.states['sensor.jwdhl_jan_willem_consumed_today'].attributes.consumed_ml+=volume;
   this.states['sensor.jwdhl_jan_willem_manual_consumed'].attributes.manual_consumed_ml+=volume;
   this.states['sensor.jwdhl_jan_willem_drink_count_today'].state=String(history.length);
   return {record_id:n};}
  if(msg.type==='jw_daily_hydration_log/edit_drink'){
   const r=history.find(x=>x.id===msg.record_id);assert(r);const before=r.volume_ml;
   r.volume_ml=msg.volume_ml;r.liquid_type=msg.liquid_type;
   r.timestamp=`${msg.date.slice(6)}-${msg.date.slice(3,5)}-${msg.date.slice(0,2)}T${msg.time}+01:00`;
   this.states['sensor.jwdhl_jan_willem_consumed_today'].attributes.consumed_ml+=msg.volume_ml-before;
   return {saved:true};}
  if(msg.type==='jw_daily_hydration_log/delete_drink'){
   const i=history.findIndex(x=>x.id===msg.record_id);assert(i>=0);const [r]=history.splice(i,1);
   this.states['sensor.jwdhl_jan_willem_consumed_today'].attributes.consumed_ml-=r.volume_ml;
   this.states['sensor.jwdhl_jan_willem_drink_count_today'].state=String(history.length);return {deleted:true};}
  if(msg.type==='jw_daily_hydration_log/export')return {filename:'jwDaily Hydration Log - All Data.xlsx',
   mime_type:'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',base64:btoa('PK')};
  throw Error('Unexpected WebSocket '+JSON.stringify(msg));
 }};
async function main(){
 const Card=els['jwdaily-hydration-log-card'];assert(Card);
 const c=new Card();c.setConfig({type:'custom:jwdaily-hydration-log-card',profile:'jan_willem',quick_add:[120,150,300,500]});
 c.hass=hass;await Promise.resolve();await Promise.resolve();
 assert(c.shadowRoot.innerHTML.includes('+ Add drink'));
 assert(!c.shadowRoot.innerHTML.includes('1. Select a liquid'));
 assert(!c.shadowRoot.innerHTML.includes('2. Select a volume'));
 assert(c.shadowRoot.innerHTML.includes('class="card-version">v1.1.0-beta.8'));
 console.log('PASS: single Add button, no exterior selection controls, version bottom-right');
 const layout=c.shadowRoot.innerHTML;
 assert(layout.includes('class="hero-shell"') && layout.includes('class="glass-frame"'), 'Glass and taken amount share a frame');
 assert(layout.includes('grid-template-columns:minmax(0,min(320px,50%)) minmax(0,1fr)'), 'Two responsive columns use container width');
 assert(layout.includes('container-type:inline-size'), 'Card-size breakpoints rather than viewport breakpoints');
 assert(layout.includes('width:69%;max-width:69%'), 'Cup size is bounded by responsive column');
 assert(layout.includes('class="hero-side"') && layout.includes('class="hero-actions"'), 'Chart and Add grouped right');
 assert(layout.includes('min-width:0;min-height:100%;display:flex;flex-direction:column'), 'Right chart can shrink');
 assert(layout.includes('white-space:nowrap;text-align:right'), 'Bar values never wrap');
 assert(layout.includes('margin-top:auto;padding:10px 0 0 9px'), 'Compact Add below chart');
 assert(layout.includes('font-size:1.07rem') && layout.includes('font-size:1.05rem'), 'History date and moments larger');
 assert(layout.includes('class="card-version">v1.1.0-beta.8'), 'New beta version footer');
 assert(!layout.includes('<div class="register">'), 'No full-width Add row');
 console.log('PASS: two-column container-responsive glass/chart, Add placement and larger history text');

 assert(c.shadowRoot.innerHTML.includes('M38 39 L122 39'));
 assert(c.shadowRoot.innerHTML.includes('stroke-dasharray="4 5"'));
 assert(c._glass(10,2700,3000).includes('attributeName="y"'));
 assert(c._glass(10,2700,3000).includes('repeatCount="indefinite"'));
 assert(!c.shadowRoot.innerHTML.toLowerCase().includes('recommended pace'));
 assert(c._glass(100,0,3000).includes('y="39"'));
 assert(c._glass(101,0,3000).includes('y="19"'));
 assert(c._glass(250,0,3000).includes('y="19"'));
 const overflow=c._glass(250,0,3000);
 assert(overflow.includes('aria-label="250 percent of daily goal"'));
 assert(overflow.includes('M38 39 L122 39'));
 assert(overflow.indexOf('fill="#59baf2"')<overflow.indexOf('stroke="#e04444"'));
 assert(overflow.includes('paint-order="stroke"'));
 console.log('PASS: over-target level fills open rim, stays capped, red target overlay visible');

 console.log('PASS: dashed red target line 16 SVG units lower, 100% fill reaches target, animation present');
 await c._click(click('new'));assert(c._modal.mode==='new');
 assert.strictEqual(c._modal.liquid_type,'');assert.strictEqual(c._modal.volume_ml,'');
 assert(c.shadowRoot.innerHTML.includes('class="liquid-choices"'));
 assert(c.shadowRoot.innerHTML.includes('class="volume-choices"'));
 assert(c.shadowRoot.innerHTML.includes('data-action="manage-liquids"'));
 assert(c.shadowRoot.innerHTML.includes('Save'));assert(c.shadowRoot.innerHTML.includes('Cancel'));
 console.log('PASS: Add opens popup with explicit liquid and volume selection, date and time');
 assert(c.shadowRoot.innerHTML.includes('data-action="calendar-toggle"'));
 await c._click(click('calendar-toggle'));
 assert(c._calendarOpen && c.shadowRoot.innerHTML.includes('data-action="calendar-day"'));
 await c._click(click('calendar-day','2026-11-07'));
 assert.strictEqual(c._modal.date,'07-11-2026');assert.strictEqual(c._calendarOpen,false);
 console.log('PASS: date picker selects real calendar day in DD-MM-YYYY');
 c._modal.date='08-11-2026';

 await c._click(click('type','water'));assert.strictEqual(c._modal.liquid_type,'water');
 assert.strictEqual(c._modal.volume_ml,'');
 await c._click(click('amount','120'));assert.strictEqual(c._modal.volume_ml,'120');
 // Reject any future calendar day; accept 23:59 today even if later than now.
 const initialDate=c._modal.date;
 const nextDay=new Date(`${c._todayISO()}T12:00:00`);
 nextDay.setDate(nextDay.getDate()+1);
 c._modal.date=`${String(nextDay.getDate()).padStart(2,'0')}-${String(nextDay.getMonth()+1).padStart(2,'0')}-${nextDay.getFullYear()}`;
 c._modal.time='00:00:00';
 assert.throws(()=>c._payload(),/Future dates are not allowed/);
 c._modal.date=c._todayPretty();c._modal.time='23:59:59';
 assert.strictEqual(c._payload().time,'23:59:59');
 c._modal.date=initialDate;
 console.log('PASS: future calendar date blocked, later clock time today allowed');
 console.log('PASS: standard types never prefill volume, type and amount are explicit');
 await c._click(click('manage-liquids'));assert(c._manageOpen);assert(c.shadowRoot.innerHTML.includes('Manage liquid types'));
 assert(c.shadowRoot.innerHTML.includes('data-action="manage-edit"'));
 assert(c.shadowRoot.innerHTML.includes('data-action="manage-hide"'), 'Built-ins have a Delete button');
 await c._click(click('manage-hide','milk'));
 assert(c.shadowRoot.innerHTML.includes('Confirm delete'));
 assert(c.shadowRoot.innerHTML.includes('History and Excel remain intact'));
 await c._click(click('manage-delete-cancel'));assert(!c._managePendingDelete);
 await c._click(click('manage-hide','milk'));await c._click(click('manage-delete-confirm'));
 assert(catalog.find(x=>x.id==='milk').hidden===true);
 assert(c.shadowRoot.innerHTML.includes('Hidden built-in liquid types'));
 assert(c.shadowRoot.innerHTML.includes('data-action="manage-restore"'));
 console.log('PASS: Delete installed Milk removes its Add choice, preserves catalog and offers Restore');
 await c._click(click('manage-cancel'));
 assert(!c.shadowRoot.innerHTML.includes('data-action="type" data-value="milk"'),'Milk removed from Add');
 await c._click(click('type','milk'));assert.strictEqual(c._modal.liquid_type,'water');
 await c._click(click('manage-liquids'));
 await c._click(click('manage-restore','milk'));
 assert(catalog.find(x=>x.id==='milk').hidden===false);
 console.log('PASS: hidden builtin can be restored without losing historical IDs');

 assert(c.shadowRoot.innerHTML.includes('data-action="manage-up"'));
 await c._click(click('manage-add'));assert(c.shadowRoot.innerHTML.includes('Add liquid'));
 assert(c.shadowRoot.innerHTML.includes('data-field="custom_svg_file"'));
 c._customDraft.custom_name='Fresh juice';c._customDraft.icon_svg='<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><circle cx="12" cy="12" r="11"/></svg>';
 c._customDraft.icon_mdi='';c._customDraft.custom_default_volume_ml='250';
 await c._click(click('manage-save'));
 assert(c._manageOpen);assert(c._modal.liquid_type.startsWith('custom_'));
 assert(c.shadowRoot.innerHTML.includes('Fresh juice'));
 await c._click(click('manage-edit','custom_1'));
 assert(c._customDraft.custom_name==='Fresh juice');
 c._customDraft.custom_name='Fresh juice XL';c._customDraft.custom_default_volume_ml='275';
 await c._click(click('manage-save'));
 assert(catalog.find(x=>x.id==='custom_1').name==='Fresh juice XL');
 assert(catalog.find(x=>x.id==='custom_1').default_volume_ml===275);
 await c._click(click('manage-up','custom_1'));
 assert(wsCalls.some(x=>x.type==='jw_daily_hydration_log/set_liquid_order'));
 await c._click(click('manage-edit','water'));
 c._customDraft.custom_name='Spring water';c._customDraft.custom_default_volume_ml='330';
 await c._click(click('manage-save'));
 assert(catalog.find(x=>x.id==='water').name==='Spring water');
 console.log('PASS: existing custom and built-in liquid labels, icons, defaults, ordering editable');
 await c._click(click('manage-cancel'));
 assert(!c._manageOpen);
 assert.strictEqual(c._modal.volume_ml,'250');
 assert(c.shadowRoot.innerHTML.includes('Fresh juice'));
 assert(c.shadowRoot.innerHTML.includes('data:image/svg+xml'));
 await c._click(click('manage-volumes'));assert(c._volumeManageOpen);
 assert(c.shadowRoot.innerHTML.includes('data-action="volume-remove"'));
 c._volumeDraft=['333','120','250'];await c._click(click('volume-save'));
 assert(!c._volumeManageOpen);assert.deepStrictEqual(storedVolumes,[333,120,250]);
 assert(c.shadowRoot.innerHTML.includes('333 mL'));
 console.log('PASS: quick volume buttons added, modified, removed and persisted on profile');
 console.log('PASS: custom SVG liquid with name and 250mL default persists via WS and auto-selects');
 c._modal.date='08-11-2026';c._modal.time='16:25:25';
 await c._click(click('save'));
 assert.strictEqual(history.length,1);assert.strictEqual(history[0].volume_ml,250);
 assert.strictEqual(history[0].liquid_type,'custom_1');
 console.log('PASS: chosen custom liquid/volume recorded; subsequent Add starts empty');
 assert(c.shadowRoot.innerHTML.includes('Today by liquid'));
 assert(c.shadowRoot.innerHTML.includes('Fresh juice XL'));
 assert(c.shadowRoot.innerHTML.includes('300') || c.shadowRoot.innerHTML.includes('250'));
 console.log('PASS: responsive today-by-liquid bar chart tracks backend breakdown');
 await c._click(click('new'));
 assert.strictEqual(c._modal.liquid_type,'');assert.strictEqual(c._modal.volume_ml,'');
 await c._click(click('type','custom_1'));assert.strictEqual(c._modal.volume_ml,'275');
 await c._click(click('cancel'));assert.strictEqual(c._modal,null);
 console.log('PASS: selection is never remembered, but custom default volume auto-fills on selection');
 c._openEdit(history[0].id);assert(c.shadowRoot.innerHTML.includes('Delete'));
 c._modal.volume_ml='300';c._modal.liquid_type='water';c._modal.date='08-11-2026';c._modal.time='16:20:20';
 await c._click(click('save'));assert.strictEqual(history[0].volume_ml,300);
 assert.strictEqual(history[0].liquid_type,'water');
 console.log('PASS: clicking history opens same edit popup with Save / Delete / Cancel');
 c._openEdit(history[0].id);await c._click(click('delete'));
 assert(c.shadowRoot.innerHTML.includes('Confirm delete'));
 await c._click(click('delete-confirm'));
 assert.strictEqual(history.length,0);
 console.log('PASS: popup Delete confirms and removes entry');
 await c._click(click('new'));await c._click(click('manage-liquids'));
 await c._click(click('manage-remove','custom_1'));
 assert(c._managePendingDelete?.id==='custom_1');
 await c._click(click('manage-delete-confirm'));
 assert(!catalog.some(x=>x.id==='custom_1'));
 console.log('PASS: unused custom liquid can be removed');
 await c._click(click('manage-cancel'));await c._click(click('cancel'));
 await c._click(click('export'));assert.deepStrictEqual(downloads,['jwDaily Hydration Log - All Data.xlsx']);
 console.log('PASS: admin Excel export retained');
 const past='2026-11-07';
 c._viewDate=past;
 c._history={date:past,total_ml:850,entries:[],day_summary:{date:past,consumed_ml:850,target_ml:2500,drink_count:2,
    liquid_breakdown:[{liquid_type:'coffee',volume_ml:650},{liquid_type:'milk',volume_ml:200}]},
    liquid_types:catalog.map(x=>({...x})),volume_buttons:storedVolumes};
 c._render(true);
 assert(c.shadowRoot.innerHTML.includes('850 mL'), 'Past selected day updates blue total');
 assert(c.shadowRoot.innerHTML.includes('2.50 L'), 'Past selected day updates red target');
 assert(c.shadowRoot.innerHTML.includes('1.65 L'), 'Past selected day updates remaining inside glass');
 assert(c.shadowRoot.innerHTML.includes('◷ 2 drink moments'), 'Past selected day updates drink count');
 assert(c.shadowRoot.innerHTML.includes('By liquid'), 'Past selected day updates bar chart title');
 assert(c.shadowRoot.innerHTML.includes('07-11-2026'), 'Past date shown');
 assert(c.shadowRoot.innerHTML.includes('650 mL'), 'Past-day coffee amount appears in chart');
 assert(!c.shadowRoot.innerHTML.includes('Today by liquid'), 'Past day does not show today chart');
 console.log('PASS: switching date updates glass, daily total, target, remaining, count and liquid bars');
 c._viewDate=null;c._history=null;c._render(true);await c._fetchHistory();
 assert(c.shadowRoot.innerHTML.includes('Today by liquid'), 'Today chart restored when date reset');
 console.log('PASS: returning to current day restores current-day summary and bars');
 const fresh=new Card();fresh.setConfig({profile:'jan_willem'});fresh.hass=hass;
 assert.strictEqual(fresh._modal,null);
 console.log('PASS: new card instance does not remember popup selections');
 const stale=new Card();stale.setConfig({profile:'jan_willem'});
 stale.hass={...hass,callWS:async msg=>{if(msg.type==='jw_daily_hydration_log/capabilities')throw Error('Unknown command.');return hass.callWS(msg);}};
 await stale._click(click('new'));stale._modal.liquid_type='water';stale._modal.volume_ml='120';
 stale._modal.date='08-11-2026';stale._modal.time='17:00:00';
 const before=history.length;
 await stale._click(click('save'));
 assert.strictEqual(history.length,before);
 assert(stale.shadowRoot.innerHTML.includes('Restart Home Assistant Core'));
 console.log('PASS: incompatible running backend blocks writes with actionable restart message');
}
main().catch(e=>{console.error(e);process.exitCode=1;});
