/* Standalone browser-shell test for card click flow and Excel interaction. */
const fs=require('fs');
const vm=require('vm');
const assert=require('assert');
const target=fs.readFileSync(require('path').join(__dirname,'../custom_components/jw_daily_hydration_log/www/jwdaily-hydration-log-card.js'),'utf8');
const classes={};
const downloads=[];
class FakeShadow{
  constructor(){this.innerHTML='';this.listeners={};}
  addEventListener(name,fn){this.listeners[name]=fn;}
  querySelector(){return {focus(){}};}
  appendChild(){ }
}
class FakeHTMLElement{
  attachShadow(){return this.shadowRoot=new FakeShadow();}
  dispatchEvent(){return true;}
  appendChild(){return true;}
}
const sandbox={
 HTMLElement:FakeHTMLElement,
 customElements:{get:k=>classes[k],define:(k,c)=>classes[k]=c},
 window:{customCards:[]},
 console,
 setInterval(){return 1;},clearInterval(){},setTimeout(fn){fn();},
 requestAnimationFrame:fn=>fn(),
 Blob,
 URL:{createObjectURL:()=> 'blob:test',revokeObjectURL:()=>{}},
 document:{createElement:(tag)=>({href:'',download:'',click(){downloads.push(this.download)},remove(){}})},
 atob,
 Date,
 CustomEvent:class{}
};
vm.createContext(sandbox);vm.runInContext(target,sandbox);
async function main(){
 let entries=[];let calls=[];
 assert(classes['jwdaily-hydration-log-card']);
 assert(!classes['jw-daily-hydration-log-card']);
 const c=new classes['jwdaily-hydration-log-card']();
 c.setConfig({type:'custom:jwdaily-hydration-log-card',profile:'jan_willem',quick_add:[120,150,300,500],show_countdown:false});
 const hass={user:{is_admin:true},states:{
  'sensor.jwdhl_jan_willem_daily_target':{state:'3000',attributes:{target_ml:3000}},
  'sensor.jwdhl_jan_willem_consumed_today':{state:'0',attributes:{consumed_ml:0}},
  'sensor.jwdhl_jan_willem_manual_consumed':{state:'0',attributes:{manual_consumed_ml:0}},
  'sensor.jwdhl_jan_willem_drink_count_today':{state:'0',attributes:{}}},
  async callService(domain,service,data){
    calls.push({domain,service,data});entries.push({id:String(calls.length),timestamp:'2026-11-08T15:00:00+01:00',volume_ml:data.volume,origin:data.origin});
    hass.states['sensor.jwdhl_jan_willem_manual_consumed'].attributes.manual_consumed_ml+=data.volume;
    hass.states['sensor.jwdhl_jan_willem_consumed_today'].attributes.consumed_ml+=data.volume;
  },
  async callWS(message){
    if(message.type==='jw_daily_hydration_log/history')return {date:'2026-11-08',entries, total_ml:entries.reduce((a,r)=>a+r.volume_ml,0),consumed_ml:0,target_ml:3000};
    if(message.type==='jw_daily_hydration_log/export')return {filename:'jwDaily Hydration Log - All Data.xlsx',
       mime_type:'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',base64:btoa('PK')};
    throw Error('Unexpected WebSocket API');
  }};
 c.hass=hass;
 await new Promise(r=>process.nextTick(r));
 for(const v of [120,150,300,500])await c._onClick({target:{closest:()=>({dataset:{action:'quick',amount:String(v)}})}});
 assert.strictEqual(calls.length,4);
 assert.strictEqual(entries.reduce((a,r)=>a+r.volume_ml,0),1070);
 assert(calls.every(x=>x.domain==='jw_daily_hydration_log'&&x.service==='log_drink'&&x.data.profile==='jan_willem'));
 console.log('PASS: four distinct quick actions + 1070 mL + isolated service');
 assert(c.shadowRoot.innerHTML.includes('Today\'s intake'));
 console.log('PASS: history section rendered');
 await c._onClick({target:{closest:()=>({dataset:{action:'export'}})}});
 assert.deepStrictEqual(downloads,['jwDaily Hydration Log - All Data.xlsx']);
 console.log('PASS: admin Excel export started with correct .xlsx filename');
 const pre=calls.length;
 await c._onClick({target:{closest:()=>({dataset:{action:'custom'}})}});
 c._customValue='80';
 await c._confirmCustom();
 assert.strictEqual(calls.length,pre+1);
 assert.strictEqual(calls.at(-1).data.volume,80);
 console.log('PASS: inline custom volume is registered');
}
main().catch(e=>{console.error(e);process.exitCode=1;});
