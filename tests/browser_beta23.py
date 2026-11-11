"""Chromium actual-rendering checks for beta23, with HA mock and viewport dimensions."""
import json, re, sys
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
JS=str(ROOT/'custom_components/jw_daily_hydration_log/www/jwdaily-hydration-log-card.js')
errors=[]
with sync_playwright() as p:
 chrome = next((path for path in ('/usr/bin/chromium','/usr/bin/google-chrome','/usr/bin/google-chrome-stable') if Path(path).is_file()), None)
 browser=p.chromium.launch(**({'executable_path':chrome} if chrome else {}),headless=True,args=['--no-sandbox','--disable-dev-shm-usage'])
 page=browser.new_page(viewport={'width':1250,'height':1050}, device_scale_factor=1)
 page.on('pageerror',lambda exc: errors.append(str(exc)))
 page.set_content('<html><head><style>body{font-family:Arial,sans-serif;margin:0;background:#eee;}#test{padding:0;width:100%;}ha-card{background:white;border:1px solid #ddd;}</style></head><body><div id="test"></div></body></html>')
 page.add_script_tag(path=JS)
 page.evaluate('''() => {
 const types=[{id:'water',name:'Water',icon_mdi:'mdi:water',custom:false,hidden:false,color:'#79A2E7',color_override:null,default_volume_ml:120},
 {id:'coffee',name:'Coffee',icon_mdi:'mdi:coffee',custom:false,hidden:false,color:'#F2A34A',color_override:null,default_volume_ml:150},
 {id:'tea',name:'Tea',icon_mdi:'mdi:tea',custom:false,hidden:false,color:'#67B69A',color_override:null,default_volume_ml:100}];
 window.testTypes=types;window.wsCalls=[];
 const data={date:null,total_ml:400,entries:[{id:'drink-1',timestamp:new Date().toISOString(),volume_ml:400,liquid_type:'water'}],
 day_summary:{target_ml:2000,consumed_ml:1250,drink_count:5,liquid_breakdown:[{liquid_type:'water',volume_ml:700},{liquid_type:'coffee',volume_ml:400},{liquid_type:'tea',volume_ml:150}]},
 liquid_types:types,volume_buttons:[120,150,300,500]};
 window.testData=data;
 const names=Object.fromEntries(types.map(t=>[t.id,t.name]));
 const colors=Object.fromEntries(types.map(t=>[t.id,t.color]));
 const hours=Array.from({length:24},(_,i)=>({label:String(i+1),total_ml:i===9?500:i===10?250:0,liquids:i===9?{coffee:350,water:150}:i===10?{tea:250}:{} }));
 const days=Array.from({length:7},(_,i)=>({date:`2026-11-${String(i+5).padStart(2,'0')}`,total_ml:i===6?1250:500,liquids:i===6?{water:700,coffee:400,tea:150}:{water:400,coffee:100},has_data:true}));
 const states={
 'sensor.jwdhl_jan_willem_daily_target':{state:'2000',attributes:{target_ml:2000}},
 'sensor.jwdhl_jan_willem_consumed_today':{state:'1250',attributes:{consumed_ml:1250}},
 'sensor.jwdhl_jan_willem_drink_count_today':{state:'5',attributes:{}},
 'sensor.jwdhl_jan_willem_manual_consumed':{state:'1250',attributes:{manual_consumed_ml:1250}},
 'sensor.jwdhl_jan_willem_hourly_intake_today':{state:'750',attributes:{buckets:hours,liquid_names:names,liquid_colors:colors}},
 'sensor.jwdhl_jan_willem_daily_intake_last_7_days':{state:'4250',attributes:{days,liquid_names:names,liquid_colors:colors}}};
 const hass={config:{time_zone:'Europe/Amsterdam'},user:{is_admin:true},states,
 callWS:async msg=>{
  window.wsCalls.push({...msg});
  if(msg.type.endsWith('/capabilities')) return {version:'1.1.0-beta.23'};
  if(msg.type.endsWith('/history')){return {...data,date:msg.date,liquid_types:types.map(x=>({...x}))};}
  if(msg.type.endsWith('/update_liquid_type')){
    const item=types.find(t=>t.id===msg.liquid_type);if(!item)throw new Error('No ID');
    item.name=msg.name;item.color_override=msg.color||null;item.color=msg.color||jdhlLiquidColor(item.id,item.name);
    item.icon_mdi=msg.icon_mdi;item.icon_svg=msg.icon_svg;
    Object.values(states).forEach(st=>{if(st.attributes.liquid_colors){st.attributes.liquid_colors[item.id]=item.color;st.attributes.liquid_names[item.id]=item.name;}});
    return {...item};}
  if(msg.type.endsWith('/add_liquid_type')) {const item={id:'custom_new',name:msg.name,custom:true,hidden:false,color_override:msg.color||null,color:msg.color||jdhlLiquidColor('custom_new',msg.name),icon_mdi:msg.icon_mdi||'mdi:glass-water',icon_svg:msg.icon_svg||'',default_volume_ml:msg.default_volume_ml||null};types.push(item);return item;}
  if(msg.type.endsWith('/export')) return {token:'t'};
  return {ok:true};}
 };
 window.hass=hass;
 const card=document.createElement('jwdaily-hydration-log-card');card.style.display='block';card.style.width='500px';
 document.getElementById('test').appendChild(card);card.hass=hass;card.setConfig({profile:'jan_willem',title:'Hydration Log'});window.card=card;
 const hour=document.createElement('jwdaily-hydration-hourly-card');hour.style.width='600px';document.body.appendChild(hour);hour.hass=hass;hour.setConfig({profile:'jan_willem'});window.hour=hour;
 const week=document.createElement('jwdaily-hydration-weekly-card');week.style.width='600px';document.body.appendChild(week);week.hass=hass;week.setConfig({profile:'jan_willem'});window.week=week;
 }''')
 page.wait_for_function('window.card._history && window.card._history.date===window.card._todayISO()')
 js='''(width) => {
   window.card.style.width=width+'px';window.card._render(true);
   const r=window.card.shadowRoot;
   const rect=s=>{const b=r.querySelector(s)?.getBoundingClientRect();return b?{left:b.left,right:b.right,top:b.top,bottom:b.bottom,width:b.width,height:b.height}:null};
   const css=s=>{const x=r.querySelector(s);return x?getComputedStyle(x).fontSize:null};
   return {w:width,taken:rect('.taken'),glass:rect('.glass-frame'),bars:rect('.hero-side'),export:rect('.export'),version:rect('.card-version'),card:rect('.root'),
     takenSize:css('.taken'),targetSize:css('.cup-target'),remainingSize:css('.cup-remaining'),
     barColor:r.querySelector('.bar-fill')?.style.backgroundColor,dotColor:r.querySelector('.type-dot')?.style.backgroundColor};
 }'''
 print('REAL CHROMIUM RENDERING:')
 geometries=[]
 for w in [280,320,360,405,460,500,720,880]:
  result=page.evaluate(js,w);geometries.append(result)
  print(w,'fonts',result['takenSize'],result['targetSize'],result['remainingSize'],'taken-right',round(result['taken']['right'],1),'cup-left',round(result['glass']['left'],1))
  assert (result['takenSize'],result['targetSize'],result['remainingSize'])==('19px','17px','17px'),result
  assert result['taken']['right'] <= result['glass']['right']+2,'intake far outside glass frame'
  assert result['taken']['right'] >= result['glass']['left']-12,'intake too far left'
  assert result['version']['bottom'] <= result['card']['bottom']+1,'version outside card'
  assert result['export']['right'] <= result['version']['left']+1,'footer overlaps'
  assert result['barColor']==result['dotColor'],'Main bar and dot mismatch'
  assert result['bars']['left'] >= result['glass']['left']+result['glass']['width']*.5 or w<=280,'hero overlaps badly'
 assert geometries[0]['takenSize']=='19px'
 # Original chart palette consistently driven by profile-sensor metadata.
 assert page.evaluate('''() => {
  const h=window.hour.shadowRoot, w=window.week.shadowRoot;
  const fills=[...h.querySelectorAll('rect[fill]')].map(x=>x.getAttribute('fill'));
  const legend=[...h.querySelectorAll('.swatch')].map(x=>x.style.backgroundColor);
  return fills.includes('#F2A34A') && fills.includes('#79A2E7') && legend.includes('rgb(242, 163, 74)') && [...w.querySelectorAll('rect[fill]')].some(x=>x.getAttribute('fill')==='#F2A34A');
 }'''),'default charts wrong'
 page.evaluate('window.card._openNew()')
 page.locator('jwdaily-hydration-log-card').locator('[data-action="manage-liquids"]').click()
 page.locator('jwdaily-hydration-log-card').locator('[data-action="manage-edit"][data-value="coffee"]').click()
 r=page.locator('jwdaily-hydration-log-card')
 assert r.locator('[data-field="color_picker"]').count()==1
 assert r.locator('[data-field="color_hex"]').count()==1
 assert r.locator('.color-preview').count()==1
 # Cancel must not save.
 updates=lambda:page.evaluate('window.wsCalls.filter(x=>x.type.endsWith("/update_liquid_type")).length')
 before=updates();r.locator('[data-field="color_hex"]').fill('#12GG45')
 assert r.locator('.color-error').is_visible()
 r.locator('[data-action="manage-save"]').click()
 assert updates()==before,'Invalid input saved'
 r.locator('[data-action="manage-cancel"]').click()
 assert updates()==before,'Cancel edited liquid saved'
 # Choose a valid color and check immediate synchronized picker + live swatch.
 r.locator('[data-action="manage-edit"][data-value="coffee"]').click()
 r.locator('[data-field="color_hex"]').fill('#1a2b3c')
 r.locator('[data-field="color_hex"]').blur()
 assert r.locator('[data-field="color_hex"]').input_value()=='#1A2B3C'
 assert r.locator('[data-field="color_picker"]').input_value()=='#1a2b3c'
 assert not r.locator('.color-error').is_visible()
 r.locator('[data-action="manage-save"]').click()
 page.wait_for_function('window.card._history?.liquid_types?.find(t=>t.id==="coffee")?.color_override==="#1A2B3C"')
 assert updates()==before+1
 color=page.evaluate('''() => ({main:window.card.shadowRoot.querySelectorAll('.bar-fill')[1]?.style.backgroundColor,
 dot:window.card.shadowRoot.querySelectorAll('.type-dot')[1]?.style.backgroundColor,
 h:window.hour.shadowRoot.querySelectorAll('rect[fill]')[1]?.getAttribute('fill')})''')
 # Chart must rerender on hass push after edit.
 page.evaluate('window.hour.hass=window.hass;window.week.hass=window.hass')
 matches=page.evaluate('''() => ({
 main:[...window.card.shadowRoot.querySelectorAll('.bar-line')].find(x=>x.textContent.includes('Coffee'))?.querySelector('.bar-fill').style.backgroundColor,
 hourly:[...window.hour.shadowRoot.querySelectorAll('rect[fill]')].some(x=>x.getAttribute('fill')==='#1A2B3C'),
 weekly:[...window.week.shadowRoot.querySelectorAll('rect[fill]')].some(x=>x.getAttribute('fill')==='#1A2B3C'),
 details:window.hour.shadowRoot.querySelectorAll('.swatch').length
 })''')
 print('AFTER SAVE:',matches)
 assert matches['main']=='rgb(26, 43, 60)' and matches['hourly'] and matches['weekly'] and matches['details']
 # Return to modal and verify the colored choice button matches, with contrast text and explicit selection outline.
 r.locator('[data-action="manage-cancel"]').click()
 r.locator('[data-action="type"][data-value="coffee"]').click()
 style=page.evaluate('''() => {const el=window.card.shadowRoot.querySelector('[data-action="type"][data-value="coffee"]');const cs=getComputedStyle(el);return {bg:cs.backgroundColor,fg:cs.color,border:cs.borderColor,shadow:cs.boxShadow,pressed:el.getAttribute('aria-pressed')};}''')
 print('COLOR BUTTON:',style)
 assert style['bg']=='rgb(26, 43, 60)' and style['fg']=='rgb(255, 255, 255)' and style['pressed']=='true'
 assert style['shadow']!='none'
 # Reset restores historical beta22 default color and removes personal override.
 r.locator('[data-action="manage-liquids"]').click()
 r.locator('[data-action="manage-edit"][data-value="coffee"]').click()
 r.locator('[data-action="manage-color-reset"]').click()
 assert page.evaluate('window.card._customDraft.color_custom') is False
 r.locator('[data-action="manage-save"]').click()
 page.wait_for_function('window.card._history?.liquid_types?.find(t=>t.id==="coffee")?.color_override===null')
 assert page.evaluate('window.testTypes.find(t=>t.id==="coffee").color')=='#F2A34A'
 assert not errors,errors
 print('BROWSER QA PASS: 8 widths, exact calculated CSS, editing, validation, cancel, picker, reset, profile chart colors, buttons, no pageerrors')
 browser.close()
