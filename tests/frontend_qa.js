/* Browser-shell integration test: deliberate selection, popup CRUD, XLSX. */
const fs=require('fs'),vm=require('vm'),path=require('path'),assert=require('assert');
const src=fs.readFileSync(path.join(__dirname,'../custom_components/jw_daily_hydration_log/www/jwdaily-hydration-log-card.js'),'utf8');
const els={},downloads=[],services=[],wsCalls=[];
class Shadow{constructor(){this.innerHTML='';this.listeners={};} addEventListener(n,fn){this.listeners[n]=fn;} appendChild(){} }
class Node{attachShadow(){this.shadowRoot=new Shadow();return this.shadowRoot;} appendChild(){} dispatchEvent(){return true;}}
const sandbox={HTMLElement:Node,customElements:{get:k=>els[k],define:(k,c)=>els[k]=c},
 window:{customCards:[]},console,setInterval(){return 1;},clearInterval(){},setTimeout(f){f();},
 Blob,URL:{createObjectURL:()=> 'blob:demo',revokeObjectURL:()=>{}},
 document:{createElement:()=>({click(){downloads.push(this.download);},remove(){},addEventListener(){}})},
 atob,btoa,Date,CustomEvent:class{},Intl};
vm.createContext(sandbox);vm.runInContext(src,sandbox);
const fakeClick=data=>({target:{closest:()=>({dataset:data})}});
const history=[];
const hass={user:{is_admin:true},config:{time_zone:'Europe/Amsterdam'},states:{
 'sensor.jwdhl_jan_willem_daily_target':{state:'3000',attributes:{target_ml:3000}},
 'sensor.jwdhl_jan_willem_consumed_today':{state:'0',attributes:{consumed_ml:0}},
 'sensor.jwdhl_jan_willem_manual_consumed':{state:'0',attributes:{manual_consumed_ml:0}},
 'sensor.jwdhl_jan_willem_drink_count_today':{state:'0',attributes:{}}},
 async callService(domain,service,payload){
  assert.strictEqual(domain,'jw_daily_hydration_log');assert.strictEqual(service,'log_drink');
  services.push({...payload});const n=String(services.length);const volume=payload.volume;
  history.push({id:n,timestamp:'2026-11-08T16:30:20+01:00',volume_ml:volume,
   liquid_type:payload.liquid_type,origin:payload.origin});
  this.states['sensor.jwdhl_jan_willem_consumed_today'].attributes.consumed_ml+=volume;
  this.states['sensor.jwdhl_jan_willem_manual_consumed'].attributes.manual_consumed_ml+=volume;
  this.states['sensor.jwdhl_jan_willem_drink_count_today'].state=String(history.length);
 },
 async callWS(msg){
  wsCalls.push({...msg});
  if(msg.type==='jw_daily_hydration_log/add_drink'){
   const n=String(history.length+1);const volume=msg.volume_ml;
   history.push({id:n,timestamp:'2026-11-08T16:30:20+01:00',volume_ml:volume,
    liquid_type:msg.liquid_type,origin:'dashboard'});
   this.states['sensor.jwdhl_jan_willem_consumed_today'].attributes.consumed_ml+=volume;
   this.states['sensor.jwdhl_jan_willem_manual_consumed'].attributes.manual_consumed_ml+=volume;
   this.states['sensor.jwdhl_jan_willem_drink_count_today'].state=String(history.length);
   return {record_id:n};
  }
  if(msg.type==='jw_daily_hydration_log/history')return {date:msg.date,entries:history.map(x=>({...x})),
   total_ml:history.reduce((a,r)=>a+r.volume_ml,0)};
  if(msg.type==='jw_daily_hydration_log/edit_drink'){
   const r=history.find(x=>x.id===msg.record_id);assert(r);
   const before=r.volume_ml;r.volume_ml=msg.volume_ml;r.liquid_type=msg.liquid_type;
   r.timestamp=`${msg.date.slice(6)}-${msg.date.slice(3,5)}-${msg.date.slice(0,2)}T${msg.time}+01:00`;
   this.states['sensor.jwdhl_jan_willem_consumed_today'].attributes.consumed_ml+=msg.volume_ml-before;
   return {saved:true};}
  if(msg.type==='jw_daily_hydration_log/delete_drink'){
   const i=history.findIndex(x=>x.id===msg.record_id);assert(i>=0);
   const [r]=history.splice(i,1);
   this.states['sensor.jwdhl_jan_willem_consumed_today'].attributes.consumed_ml-=r.volume_ml;
   return {deleted:true};}
  if(msg.type==='jw_daily_hydration_log/export')return {filename:'jwDaily Hydration Log - All Data.xlsx',
   mime_type:'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',base64:btoa('PK')};
  throw Error('Unexpected WebSocket '+JSON.stringify(msg));
 }};
async function main(){
 const Card=els['jwdaily-hydration-log-card'];assert(Card);
 const c=new Card();c.setConfig({type:'custom:jwdaily-hydration-log-card',profile:'jan_willem',quick_add:[120,150,300,500]});
 c.hass=hass;await Promise.resolve();await Promise.resolve();
 assert.strictEqual(c._selectedType,null);assert.strictEqual(c._selectedVolume,null);
 assert(c.shadowRoot.innerHTML.includes('Select both options to enable Add drink'));
 await c._click(fakeClick({action:'register'}));assert.strictEqual(wsCalls.filter(x=>x.type==='jw_daily_hydration_log/add_drink').length,0);
 await c._click(fakeClick({action:'amount',value:'120'}));
 await c._click(fakeClick({action:'register'}));assert.strictEqual(wsCalls.filter(x=>x.type==='jw_daily_hydration_log/add_drink').length,0);
 console.log('PASS: no default selection and no logging with only an amount');
 await c._click(fakeClick({action:'type',value:'water'}));
 await c._click(fakeClick({action:'register'}));
 assert.strictEqual(wsCalls.filter(x=>x.type==='jw_daily_hydration_log/add_drink').length,1);
 assert.strictEqual(wsCalls.find(x=>x.type==='jw_daily_hydration_log/add_drink').liquid_type,'water');assert.strictEqual(history[0].volume_ml,120);
 assert.strictEqual(c._selectedType,null);assert.strictEqual(c._selectedVolume,null);
 console.log('PASS: only deliberate type + volume logs, then selections reset');
 await c._click(fakeClick({action:'type',value:'coffee'}));await c._click(fakeClick({action:'amount',value:'150'}));
 await c._click(fakeClick({action:'register'}));assert.strictEqual(history.length,2);assert.strictEqual(history[1].liquid_type,'coffee');
 assert(c.shadowRoot.innerHTML.includes('Coffee'));assert.strictEqual(c._undoId,'2');
 assert(c.shadowRoot.innerHTML.includes('Undo last drink'));
 console.log('PASS: coffee saved separately and appears in history');
 c._openEdit('1');assert(c._modal.mode==='edit');assert(c.shadowRoot.innerHTML.includes('Save'));
 assert(c.shadowRoot.innerHTML.includes('Delete'));assert(c.shadowRoot.innerHTML.includes('Cancel'));
 c._modal.volume_ml='180';c._modal.liquid_type='tea';c._modal.date='08-11-2026';c._modal.time='16:25:15';
 await c._click(fakeClick({action:'save'}));assert.strictEqual(history[0].volume_ml,180);
 assert.strictEqual(history[0].liquid_type,'tea');
 assert(wsCalls.some(x=>x.type==='jw_daily_hydration_log/edit_drink'&&x.time==='16:25:15'));
 console.log('PASS: popup save edits same record and uses DD-MM-YYYY / HH:MM:SS');
 c._openEdit('2');await c._click(fakeClick({action:'delete'}));
 assert.strictEqual(history.length,2);assert(c.shadowRoot.innerHTML.includes('Confirm delete'));
 await c._click(fakeClick({action:'delete-confirm'}));
 assert.strictEqual(history.length,1);assert.strictEqual(history[0].id,'1');
 console.log('PASS: popup delete requires confirmation and permanently removes record');
 await c._click(fakeClick({action:'new'}));assert.strictEqual(c._modal.liquid_type,'');assert.strictEqual(c._modal.volume_ml,'');
 assert(c._modal.date.match(/^\d{2}-\d{2}-\d{4}$/));assert(c._modal.time.match(/^\d{2}:\d{2}:\d{2}$/));
 console.log('PASS: manual date/time popup has no default liquid or volume');
 await c._click(fakeClick({action:'cancel'}));
 await c._click(fakeClick({action:'export'}));assert.deepStrictEqual(downloads,['jwDaily Hydration Log - All Data.xlsx']);
 console.log('PASS: Excel export still works');
 await c._click(fakeClick({action:'type',value:'milk'}));await c._click(fakeClick({action:'amount',value:'500'}));
 await c._click(fakeClick({action:'register'}));
 assert.strictEqual(c._undoId,'2');
 await c._click(fakeClick({action:'undo'}));
 assert.strictEqual(history.length,1);assert.strictEqual(c._undoId,null);
 console.log('PASS: Undo last drink hard-deletes only the latest saved record');
 assert(c.shadowRoot.innerHTML.includes('stroke-dasharray="4 5"'));
 assert(!c.shadowRoot.innerHTML.includes('recommended pace'));
 console.log('PASS: open-top glass with red dashed target line and no pace');
 const fresh=new Card();fresh.setConfig({profile:'jan_willem'});fresh.hass=hass;
 assert.strictEqual(fresh._selectedType,null);assert.strictEqual(fresh._selectedVolume,null);
 console.log('PASS: reopening card does not remember selections');
}
main().catch(e=>{console.error(e);process.exitCode=1;});
