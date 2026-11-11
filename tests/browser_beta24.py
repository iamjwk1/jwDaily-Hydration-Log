"""Real Chromium QA for v1.1.0-beta.24 card geometry, controls and chart grouping."""
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]
JS=ROOT/'custom_components/jw_daily_hydration_log/www/jwdaily-hydration-log-card.js'
HTML='''<!doctype html><html><head><meta charset="utf-8"><style>body{margin:0;background:#e5e7eb;font-family:Arial,sans-serif;}#mount{margin:12px;max-width:calc(100vw - 24px);}ha-card{background:#fff;border-radius:16px;box-shadow:0 0 0 1px #ddd;}*{box-sizing:border-box}</style></head><body><main id="mount"></main></body></html>'''
INITIAL='''
window.liquids=[
 {id:'water',name:'Water',icon_mdi:'mdi:water',color:'#79A2E7',custom:false,hidden:false},
 {id:'coffee',name:'Coffee',icon_mdi:'mdi:coffee',color:'#F2A34A',custom:false,hidden:false},
 {id:'milk',name:'Milk',icon_mdi:'mdi:cow',color:'#39A8DE',custom:false,hidden:false},
 {id:'water_cup',name:'Water (beker)',icon_mdi:'mdi:water',color:'#9280D0',custom:true,hidden:false},
 {id:'tea',name:'Tea',icon_mdi:'mdi:tea',color:'#67B69A',custom:false,hidden:false}
];
window.cups=[];window.quicks=[];window.counter=0;window.target=2000;
window.entries=[
{id:'h1',timestamp:'2026-11-11T16:19:31+01:00',liquid_type:'water_cup',volume_ml:500},
{id:'h2',timestamp:'2026-11-11T15:00:31+01:00',liquid_type:'coffee',volume_ml:540},
{id:'h3',timestamp:'2026-11-11T14:00:31+01:00',liquid_type:'milk',volume_ml:180},
{id:'h4',timestamp:'2026-11-11T13:00:31+01:00',liquid_type:'tea',volume_ml:180}];
window.hass={user:{is_admin:true},config:{time_zone:'Europe/Amsterdam'},states:{},
 callWS:async function(msg){
 if(msg.type.endsWith('/capabilities'))return {version:'1.1.0-beta.24'};
 if(msg.type.endsWith('/history')){
   const data=[...entries];const parts={};for(const r of data)parts[r.liquid_type]=(parts[r.liquid_type]||0)+r.volume_ml;
   return {date:'2026-11-11',entries:data,total_ml:1400,consumed_ml:1400,target_ml:window.target,backend_version:'1.1.0-beta.24',
    liquid_types:window.liquids,cup_types:window.cups,quick_buttons:window.quicks,volume_buttons:[180,220,500],
    profile_settings:{name:'Jan-Willem',age:40,gender:'male',unit:'mL'},
    day_summary:{date:'2026-11-11',target_ml:window.target,consumed_ml:1400,drink_count:data.length,
    liquid_breakdown:Object.entries(parts).map(([liquid_type,volume_ml])=>({liquid_type,volume_ml}))}};
 }
 if(msg.type.endsWith('/manage_cup')){
  if(msg.action==='add'){const id='cup_'+(++window.counter);window.cups.push({id,name:msg.name,default_volume_ml:msg.volume_ml,icon_mdi:msg.icon_mdi,hidden:false});}
  if(msg.action==='update'){Object.assign(window.cups.find(c=>c.id===msg.cup_id),{name:msg.name,default_volume_ml:msg.volume_ml});}
  if(msg.action==='hide'||msg.action==='restore'){window.cups.find(c=>c.id===msg.cup_id).hidden=msg.action==='hide';}
  if(msg.action==='reorder'){window.cups=msg.order.map(id=>window.cups.find(c=>c.id===id));}
  return {cup_types:window.cups};
 }
 if(msg.type.endsWith('/manage_quick')){
  if(msg.action==='add')window.quicks.push({id:'quick_'+(++window.counter),liquid_type_id:msg.liquid_type_id,cup_type_id:msg.cup_type_id,label_mode:msg.label_mode,custom_label:msg.custom_label,hidden:false});
  if(msg.action==='update')Object.assign(window.quicks.find(q=>q.id===msg.quick_id),{liquid_type_id:msg.liquid_type_id,cup_type_id:msg.cup_type_id,label_mode:msg.label_mode,custom_label:msg.custom_label});
  if(msg.action==='hide'||msg.action==='restore')window.quicks.find(q=>q.id===msg.quick_id).hidden=msg.action==='hide';
  if(msg.action==='reorder')window.quicks=msg.order.map(id=>window.quicks.find(q=>q.id===id));
  return {quick_buttons:window.quicks};
 }
 if(msg.type.endsWith('/migration_preview'))return {record_count:4,total_logged_ml:1400,proposals:[{legacy_id:'water_cup',legacy_name:'Water (beker)',count:1,total_ml:500,
 old_color:'#9280D0',target_color:'#79A2E7',color_conflict:true,proposal:{liquid_type_id:'water',cup_type_id:''}}]};
 if(msg.type.endsWith('/legacy_mapping'))return {};
 if(msg.type.endsWith('/set_target')){window.target=msg.target_ml||2000;return {target_ml:window.target};}
 if(msg.type.endsWith('/add_drink'))return {record_id:'fake_new'};
 return {};
 }};
window.refreshQuick=()=>{window.quicks=window.quicks.map(q=>{const c=window.cups.find(x=>x.id===q.cup_type_id);
 return {...q,label:q.label_mode==='custom'?q.custom_label:(window.liquids.find(x=>x.id===q.liquid_type_id)?.name+' ('+c.name+')'),default_volume_ml:c.default_volume_ml,available:!q.hidden&&!c.hidden};});};
const original=window.hass.callWS;
window.hass.callWS=async msg=>{const result=await original(msg);window.refreshQuick();return result};
window.card=document.createElement('jwdaily-hydration-log-card');document.querySelector('#mount').appendChild(card);
card.setConfig({type:'custom:jwdaily-hydration-log-card',profile:'jan_willem',title:'Vocht intake Jan-Willem',show_history:true});
card._todayISO=()=> '2026-11-11';card.hass=window.hass;
'''
checks=[]
def ck(cond,label):
 assert cond,label
 checks.append(label);print('PASS',label)

def run():
 with sync_playwright() as p:
  chrome = next((f for f in ('/usr/bin/chromium','/usr/bin/google-chrome','/usr/bin/google-chrome-stable') if Path(f).is_file()), None)
  browser=p.chromium.launch(**({'executable_path':chrome} if chrome else {}),headless=True,args=['--no-sandbox','--disable-dev-shm-usage'])
  page=browser.new_page(viewport={'width':760,'height':950},device_scale_factor=1)
  errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
  page.set_content(HTML)
  page.add_script_tag(path=str(JS))
  page.evaluate(INITIAL)
  page.wait_for_function('document.querySelector("jwdaily-hydration-log-card").shadowRoot.querySelectorAll(".bar-line").length===4')
  for width in [360,380,420,470,550,720,920]:
   page.set_viewport_size({'width':width,'height':940})
   result=page.evaluate('''()=>{const host=window.card,root=host.shadowRoot;
     const css=sel=>parseFloat(getComputedStyle(root.querySelector(sel)).fontSize);
     const card=host.getBoundingClientRect();const bars=[...root.querySelectorAll('.bar-line')].map(el=>{
      const a=el.querySelector('span').getBoundingClientRect(), b=el.querySelector('.bar-track').getBoundingClientRect(),
      c=el.querySelector('strong').getBoundingClientRect();return {label:el.querySelector('span').textContent,
       labelRight:a.right, barLeft:b.left,barRight:b.right,volumeRight:c.right,cardRight:card.right,
       available:el.getBoundingClientRect().width,actual:el.scrollWidth};});
     return {width:card.width,fonts:[css('.taken'),css('.cup-target'),css('.cup-remaining')],bars,
      overflow:document.documentElement.scrollWidth>innerWidth+2,
      clipped:[...root.querySelectorAll('.bar-line span')].some(x=>getComputedStyle(x).textOverflow==='ellipsis')};}''')
   ck(result['fonts']==[19,14,14],f'CSS font sizes 19/14/14 at {width}px viewport')
   ck(not result['overflow'] and not result['clipped'],f'No page overflow or truncated liquid-name CSS at {width}px')
   ck(all(b['label'] and b['volumeRight']<=b['cardRight']+1 for b in result['bars']),f'Volume labels within card at {width}px')
  def click(action,value=None):
   sel=f'jwdaily-hydration-log-card >> [data-action="{action}"]'
   if value:sel+=f'[data-value="{value}"]'
   page.locator(sel).first.click()
  click('settings-open');ck(page.locator('jwdaily-hydration-log-card >> .settings-nav').count()==1,'Central settings visible')
  click('settings-page','cups');click('settings-cup-add')
  page.locator('jwdaily-hydration-log-card >> [data-field="name"]').fill('Mug')
  page.locator('jwdaily-hydration-log-card >> [data-field="volume_ml"]').fill('180')
  click('settings-cup-save')
  page.wait_for_function('window.cups.length===1')
  ck(page.locator('jwdaily-hydration-log-card >> .settings-row').count()==1,'Cup saved and list updated')
  click('settings-home');click('settings-page','quick');click('settings-quick-add')
  page.locator('jwdaily-hydration-log-card >> [data-field="liquid_type_id"]').select_option('water')
  page.locator('jwdaily-hydration-log-card >> [data-field="cup_type_id"]').select_option('cup_1')
  click('settings-quick-save');page.wait_for_function('window.quicks.length===1')
  ck('Water (Mug)' in page.locator('jwdaily-hydration-log-card >> .settings-row').inner_text(),'Automatic Quick label rendered')
  click('settings-quick-edit','quick_2')
  page.locator('jwdaily-hydration-log-card >> [data-field="label_mode"]').select_option('custom')
  page.locator('jwdaily-hydration-log-card >> [data-field="custom_label"]').fill('My morning water')
  click('settings-quick-save')
  ck('My morning water' in page.locator('jwdaily-hydration-log-card >> .settings-row').inner_text(),'Custom label shown')
  click('settings-home');click('settings-page','cups');click('settings-cup-edit','cup_1')
  page.locator('jwdaily-hydration-log-card >> [data-field="name"]').fill('Large mug')
  page.locator('jwdaily-hydration-log-card >> [data-field="volume_ml"]').fill('250')
  click('settings-cup-save')
  click('settings-home');click('settings-page','quick')
  ck('My morning water' in page.locator('jwdaily-hydration-log-card >> .settings-row').inner_text(),'Custom label persists after cup rename')
  click('settings-close');click('new')
  ck(page.locator('jwdaily-hydration-log-card >> .quick-choice').count()==1,'Quick choice appears in Add drink')
  click('quick-choice','quick_2')
  state=page.evaluate('''()=>({liquid:card._modal.liquid_type,cup:card._modal.cup_type_id,volume:card._modal.volume_ml})''')
  ck(state=={'liquid':'water','cup':'cup_1','volume':'250'},'Quick selection resolves liquid, cup and latest default')
  click('cancel');click('settings-open');click('settings-page','migration')
  page.wait_for_function('!!window.card._migrationPreview')
  ck(page.locator('jwdaily-hydration-log-card >> .mapping-panel').count()>=1,'Read-only migration preview rendered')
  ck(not errors,'No browser console JavaScript errors: '+str(errors))
  browser.close()
  print(f'BROWSER_BETA24_PASS {len(checks)} checks')

if __name__=='__main__':run()
