"""Real Chromium beta28 card, accessibility, responsive and popup smoke tests."""
import json
import os
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).parents[1]
JS=ROOT/'custom_components/jw_daily_hydration_log/www/jwdaily-hydration-log-card.js'

with sync_playwright() as pw:
    browser_path=next((p for p in ('/usr/bin/chromium','/usr/bin/google-chrome','/usr/bin/google-chrome-stable') if Path(p).is_file()),None)
    b=pw.chromium.launch(headless=True,**({'executable_path':browser_path} if browser_path else {'channel':'chrome'}),args=['--no-sandbox','--disable-dev-shm-usage'])
    page=b.new_page(viewport={'width':1100,'height':1100},accept_downloads=True)
    errors=[]
    page.on('pageerror',lambda err:errors.append(str(err)))
    page.set_content('<!doctype html><html><body style="margin:0;padding:0;background:#eee"><div id="mount"></div></body></html>')
    page.add_script_tag(path=str(JS))
    page.evaluate('''() => {
      const date=new Date();const today=[date.getFullYear(),String(date.getMonth()+1).padStart(2,'0'),String(date.getDate()).padStart(2,'0')].join('-');
      const defs=[
       {id:'coffee',name:'Coffee',icon_mdi:'mdi:coffee',color:'#AE8000',custom:false},
       {id:'water',name:'Water',icon_mdi:'mdi:water',color:'#82C9FA',custom:false},
       {id:'water_beker',name:'Water (beker)',icon_mdi:'mdi:water',color:'#82C9FA',custom:true},
       {id:'tea',name:'Tea',icon_mdi:'mdi:tea',color:'#F0B829',custom:false},
       {id:'milk',name:'Milk',icon_mdi:'mdi:cow',color:'#EEEEEE',custom:false}];
      const entries=[];for(let i=0;i<9;i++){entries.push({id:'record'+i,timestamp:today+'T'+String(11+i).padStart(2,'0')+':05:28+01:00',volume_ml:[180,180,500,180,180,180,180,180,180][i],liquid_type:['tea','coffee','water_beker','coffee','tea','coffee','milk','coffee','coffee'][i],cup_type_id:null});}
      const breakdown=[{liquid_type:'coffee',volume_ml:900},{liquid_type:'water_beker',volume_ml:500},{liquid_type:'tea',volume_ml:360},{liquid_type:'milk',volume_ml:180}];
      window.qaCalls=[];
      window.qaHass={user:{is_admin:true},config:{time_zone:'Europe/Amsterdam'},states:{
       'sensor.jwdhl_jan_willem_consumed_today':{state:'1.94',attributes:{consumed_ml:1940,unit_of_measurement:'L'}},
       'sensor.jwdhl_jan_willem_daily_target':{state:'2',attributes:{target_ml:2000,unit_of_measurement:'L'}},
       'sensor.jwdhl_jan_willem_drink_count_today':{state:'9',attributes:{}},
       'sensor.jwdhl_jan_willem_manual_consumed':{state:'1940',attributes:{manual_consumed_ml:1940}}},
       callWS:async function(msg){window.qaCalls.push(msg);
        if(msg.type.endsWith('/history'))return {profile:'jan_willem',date:today,entries,total_ml:1940,day_summary:{date:today,drink_count:9,consumed_ml:1940,target_ml:2000,liquid_breakdown:breakdown},liquid_types:defs,volume_buttons:[120,180,220,300,500],cup_types:[],quick_buttons:[],profile_settings:{name:'Jan-Willem',age:30,gender:'male',unit:'mL'},backend_version:'1.1.0-beta.28'};
        if(msg.type.endsWith('/capabilities'))return {version:'1.1.0-beta.28',settings_transfer:true,conversion_wizard:true};
        if(msg.type.endsWith('/profiles_list'))return {profiles:[{name:'Jan-Willem',slug:'jan_willem',age:30,gender:'male',unit:'mL',daily_target_ml:2000}]};
        if(msg.type.endsWith('/conversion_preview'))return {profile:'Jan-Willem',revision:'abc',history_revision:'history-fingerprint',record_count:9,consumed_ml:1940,audit:{total_records:9,classified_records:8,unclassified_records:1,cup_assigned_records:4,cup_unknown_records:5,source_ids:4,total_logged_ml:1940},existing_cups:[],cups:[{id:'cup_migrated_180',name:'Cup 180 mL',default_volume_ml:180},{id:'cup_migrated_500',name:'Cup 500 mL',default_volume_ml:500}],sources:[{legacy_id:'water_beker',name:'Water (beker)',record_count:1,default_volume_ml:180,liquid_type_id:'water',cup_type_id:'cup_migrated_180',include:true}],existing_quick_buttons:[],already_converted:false};
        if(msg.type.endsWith('/migration_backup'))return {base64:'e30=',sha256:'00'.repeat(32),filename:'backup.json'};
        if(msg.type.endsWith('/settings_export'))return {base64:'e30=',sha256:'00'.repeat(32),size:2,filename:'settings.json'};
        if(msg.type.endsWith('/settings_import_preview'))return {profile:'Jan-Willem',source_profile:'X',counts:{liquids:9,cups:2,quick_buttons:3},changes:['cup_types'],drink_count:9,old_revision:'a',import_sha256:'b'};
        if(msg.type.endsWith('/settings_import_apply'))return {applied:true};
        if(msg.type.endsWith('/conversion_apply'))return {applied:true};
        return {};}};
      window.qaCard=document.createElement('jwdaily-hydration-log-card');
      window.qaCard.setConfig({profile:'jan_willem',title:'Vocht intake Jan-Willem'});
      window.qaCard.hass=window.qaHass;
      document.querySelector('#mount').appendChild(window.qaCard);
      }''')
    try:page.wait_for_function('document.querySelector(\"jwdaily-hydration-log-card\")?.shadowRoot?.querySelector(\".bar-line\") !== null',timeout=3500)
    except Exception:
        print('DEBUG',page.evaluate('''() => ({today:window.qaCard?._todayISO(),errors:window.qaCard?._error,render:window.qaCard?.shadowRoot?.innerHTML?.slice(-3500),calls:window.qaCalls})'''))
        print('PAGE ERRORS',errors)
        raise
    for width in (360,420,540,720,950):
        page.evaluate('(w)=>document.querySelector("#mount").style.width=w+"px"',width)
        page.wait_for_timeout(80)
        info=page.evaluate('''() => {const root=window.qaCard.shadowRoot;
          const r=x=>{const q=x.getBoundingClientRect();return {left:q.left,right:q.right,top:q.top,bottom:q.bottom,width:q.width}};
          return {rows:[...root.querySelectorAll('.bar-line')].map(e=>({name:r(e.querySelector('span')),bar:r(e.querySelector('.bar-track')),amount:r(e.querySelector('strong'))})),
          actions:[r(root.querySelector('.settings-trigger')),r(root.querySelector('.add-drink'))],
          drink:r(root.querySelector('.drink-count')),labels:[...root.querySelectorAll('.cup-target,.cup-remaining')].map(e=>[e.textContent,getComputedStyle(e).fontSize]),
          headline:root.querySelector('.main-head').textContent,overflow:root.querySelector('ha-card').scrollWidth-root.querySelector('ha-card').clientWidth};}''')
        if width in (360,720) and os.getenv('JDHL_QA_SCREENSHOTS'):
            page.screenshot(path=str(ROOT/f'qa-{width}.png'),full_page=True)
        assert len(info['rows'])==4,(width,info)
        assert max(x['bar']['left'] for x in info['rows'])-min(x['bar']['left'] for x in info['rows'])<1,(width,'Bars do not share the same X coordinate',info['rows'])
        assert max(x['amount']['right'] for x in info['rows'])-min(x['amount']['right'] for x in info['rows'])<1,(width,'Amounts misaligned',info['rows'])
        assert all(abs(x['bar']['top']-x['name']['top'])<12 for x in info['rows']),(width,info['rows'])
        assert all(x['name']['right'] <= x['bar']['left']+2 for x in info['rows']),(width,info['rows'])
        assert all(x['bar']['right']<=x['amount']['left']+2 for x in info['rows']),(width,info['rows'])
        assert info['overflow']<=2,(width,info['overflow'])
        assert info['actions'][0]['top']==info['actions'][1]['top'] or abs(info['actions'][0]['top']-info['actions'][1]['top'])<6
        assert all(x[1]=='14px' for x in info['labels'])
        assert any(x[0]=='60 mL' for x in info['labels']),info['labels']
        print('PASS responsive main',width)
    # Exceptionally long user-defined label must wrap, without moving other bar starts.
    page.evaluate('''() => {const c=window.qaCard;window.originalWaterName=c._history.liquid_types.find(x=>x.id==='water_beker').name;
      c._history.liquid_types.find(x=>x.id==='water_beker').name='Water (very large custom glass with extra name)';c._render(true);}''')
    for w in (360,720):
        page.evaluate("(w)=>document.querySelector('#mount').style.width=w+'px'",w)
        page.wait_for_timeout(80)
        info=page.evaluate('''() => {const r=window.qaCard.shadowRoot;
         const rects=[...r.querySelectorAll('.bar-line .bar-track')].map(x=>x.getBoundingClientRect());
         return {starts:rects.map(x=>x.left),overflow:r.querySelector('ha-card').scrollWidth-r.querySelector('ha-card').clientWidth,
         text:r.querySelector('.liquid-bars').textContent};}''')
        assert max(info['starts'])-min(info['starts'])<1,(w,info)
        assert info['overflow']<=2,(w,info['overflow'])
        assert 'very large custom' in info['text']
    page.evaluate('''() => {const c=window.qaCard;c._history.liquid_types.find(x=>x.id==='water_beker').name=window.originalWaterName;c._render(true);}''')
    print('PASS long custom liquid label wraps without moving shared bar axis')
    root=page.locator('jwdaily-hydration-log-card').locator('.root') # shadow piercing
    root.locator('[data-action="new"]').click()
    assert root.locator('.modal-settings[data-action="settings-open"]').count()==1
    assert root.locator('[data-action="manage-liquids"]').count()==0
    assert root.locator('[data-action="manage-volumes"]').count()==0
    root.locator('.modal-settings[data-action="settings-open"]').click()
    assert root.locator('.settings-nav-item').count()==6
    print('PASS compact settings navigation and popup settings')
    root.locator('[data-action="settings-page"][data-value="advanced"]').click()
    root.locator('[data-action="settings-page"][data-value="transfer"]').click()
    assert root.locator('text=Export settings').count()>0
    assert root.locator('[data-field="settings_import_file"]').count()==1
    print('PASS settings import/export interface')
    root.locator('[data-field="settings_import_file"]').set_input_files({
        'name':'Hydration Settings.json','mimeType':'application/json',
        'buffer':b'{"format":"jwDaily-Hydration-Log-settings","schema":1,"settings":{}}'})
    root.locator('text=Hydration Settings.json').wait_for(timeout=3000)
    root.locator('[data-action="settings-import-preview"]').click()
    assert root.locator('text=Preview for Jan-Willem').count()>0
    root.locator('[data-action="settings-import-apply"]').click()
    assert page.evaluate('window.qaCalls.some(x=>x.type.endsWith("/settings_import_apply") && x.confirm === true)')
    print('PASS JSON file selection, preview and confirmed import request')

    root.locator('[data-action="settings-home"]').click()
    root.locator('[data-action="settings-page"][data-value="convert"]').click()
    page.wait_for_timeout(150)
    assert root.locator('[data-field="convert_cup_name"]').count()==2
    assert root.locator('[data-field="convert_liquid"]').count()==1
    root.locator('[data-field="convert_cup_name"]').first.fill('Beker')
    root.locator('[data-action="settings-conversion-backup"]').click()
    root.locator('[data-action="settings-conversion-confirm"]').click()
    root.locator('[data-action="settings-conversion-apply"]').click()
    assert page.evaluate('window.qaCalls.some(x=>x.type.endsWith("/conversion_apply") && x.confirm === true && x.plan.cups[0].name === "Beker" && x.plan.history_revision === \"history-fingerprint\")')
    print('PASS migration wizard')
    root.locator('[data-action="settings-home"]').click()
    root.locator('[data-action="settings-home"]').click()
    root.locator('[data-action="settings-page"][data-value="profile"]').click()
    page.wait_for_timeout(100)
    root.locator('[data-action="settings-profile-add"]').click()
    assert root.locator('[data-field="copy_from"]').count()==1
    print('PASS profile add/copy interface')
    assert not errors,errors
    print('BROWSER_BETA28_PASS')
    b.close()
