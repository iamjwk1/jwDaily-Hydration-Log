"""Beta.37 interactive integration UI regression with fake Home Assistant service.
Use real Chromium; only HA icon picker is stubbed because this harness isn't HA Core.
"""
from playwright.sync_api import sync_playwright
from pathlib import Path
JS=Path(__file__).resolve().parents[1]/'custom_components/jw_daily_hydration_log/www/jwdaily-hydration-log-card.js'
with sync_playwright() as p:
 browser=p.chromium.launch(headless=True,executable_path='/usr/bin/chromium',args=['--no-sandbox','--disable-dev-shm-usage'])
 for width in (360,390,420,540,720,950,1400):
  page=browser.new_page(viewport={'width':width,'height':1050});errors=[]
  page.on('pageerror',lambda e:errors.append(str(e)))
  page.set_content('<html><body style="margin:0;padding:8px;background:#eff2f5"><div id="mount"></div></body></html>')
  page.add_script_tag(path=str(JS))
  page.evaluate('''() => {
    customElements.define('ha-icon-picker',class extends HTMLElement {
      connectedCallback(){this.innerHTML='<input data-picker-search placeholder="Search icons"/><div data-picker-results>mdi:water mdi:coffee mdi:cup</div>';}
      set value(v){this._value=v;}get value(){return this._value;}
    });
    const day=new Date(),iso=[day.getFullYear(),String(day.getMonth()+1).padStart(2,'0'),String(day.getDate()).padStart(2,'0')].join('-');
    const defs=[{id:'coffee',name:'Coffee',icon_mdi:'mdi:coffee',color:'#A87B00',drink_count_all_profiles:3,custom:false,hidden:false,can_delete:false},
      {id:'water',name:'Water',icon_mdi:'mdi:water',color:'#87CBFA',drink_count_all_profiles:1,custom:false,hidden:false,can_delete:false},
      {id:'other',name:'Other',icon_mdi:'mdi:glass-water',color:'#aaaaaa',drink_count_all_profiles:0,custom:false,hidden:false,can_delete:false}];
    const cups=[{id:'cup1',name:'Glazen beker',default_volume_ml:180,icon_mdi:'mdi:cup',drink_count_all_profiles:4,hidden:false,can_delete:false},
      {id:'cup2',name:'Fles',default_volume_ml:500,icon_mdi:'mdi:bottle-soda',drink_count_all_profiles:0,hidden:false,can_delete:true}];
    const entries=[{id:'r1',timestamp:iso+'T10:00:00+01:00',liquid_type:'coffee',cup_type_id:'cup1',volume_ml:180}];
    const quick=[{id:'q1',liquid_type_id:'coffee',cup_type_id:'cup1',label_mode:'automatic',custom_label:'',hidden:false,available:true,default_volume_ml:180,label:'Coffee (Glazen beker)',icon_mdi:'mdi:coffee'}];
    window.calls=[];window.downloads=[];HTMLAnchorElement.prototype.click=function(){window.downloads.push(this.download||'');};
    window.hass={user:{is_admin:true},config:{time_zone:'Europe/Amsterdam'},states:{'sensor.jwdhl_one_consumed_today':{state:'0.18',attributes:{consumed_ml:180,unit_of_measurement:'L'}},'sensor.jwdhl_one_daily_target':{state:'2',attributes:{target_ml:2000,unit_of_measurement:'L'}},'sensor.jwdhl_one_drink_count_today':{state:'1',attributes:{}},'sensor.jwdhl_one_manual_consumed':{state:'180',attributes:{manual_consumed_ml:180}}},callWS:async msg=>{
      window.calls.push(msg);
      if(msg.type.endsWith('/history'))return {profile:msg.profile,date:iso,entries,total_ml:180,count:1,consumed_ml:180,target_ml:2000,day_summary:{date:iso,drink_count:1,consumed_ml:180,target_ml:2000,liquid_breakdown:[{liquid_type:'coffee',volume_ml:180}]},liquid_types:defs,cup_types:cups,quick_buttons:quick,profile_settings:{name:'Jan-Willem',age:58,gender:'male',unit:'L'},data_model_version:2,today_breakdown:[{liquid_type:'coffee',volume_ml:180}],backend_version:'1.1.0-beta.37'};
      if(msg.type.endsWith('/capabilities'))return {version:'1.1.0-beta.37'};
      if(msg.type.endsWith('/profiles_list'))return {profiles:[{slug:'one',name:'Jan-Willem',age:58,gender:'male',unit:'L',daily_target_ml:2000},{slug:'two',name:'Second',age:30,gender:'female',unit:'fl_oz',daily_target_ml:1500}]};
      if(msg.type.endsWith('/export'))return {base64:'UEsDBBQ=',filename:'test beta37.xlsx'};
      return {};
    }};
    window.card=document.createElement('jwdaily-hydration-log-card');card.setConfig({profile:'one',title:'Vocht intake',unit:'mL'});card.hass=window.hass;document.querySelector('#mount').appendChild(card);
  }''')
  root=page.locator('jwdaily-hydration-log-card');page.wait_for_timeout(300)
  assert root.locator('.card-version').inner_text()=='v1.1.0-beta.37'
  assert root.locator('.card-version').evaluate('(n)=>getComputedStyle(n).whiteSpace')=='nowrap'
  assert root.locator('select[data-field="export_profile"]').count()==0
  assert root.locator('.card-footer button[data-action="export-open"]').count()==1
  assert 'L' in root.locator('.taken').inner_text() and 'mL' not in root.locator('.taken').inner_text(),root.locator('.taken').inner_text()
  root.locator('button[data-action="export-open"]').click();assert root.locator('.dialog-excel').count()==1
  assert root.locator('select[data-field="export_profile"]').input_value()=='all'
  assert root.locator('select[data-field="export_profile"] option').all_text_contents()==['All profiles','Jan-Willem','Second']
  root.locator('button[data-action="export-cancel"]').last.click();assert root.locator('.dialog-excel').count()==0
  root.locator('button[data-action="settings-open"]').first.click()
  assert root.locator('.settings-profile-current').count()==0
  assert root.locator('[data-value="advanced"]').count()==0
  assert root.locator('[data-value="transfer"]').count()==1
  root.locator('button[data-action="settings-page"][data-value="transfer"]').click()
  assert 'Migration v3' not in root.locator('.dialog-settings').inner_text()
  assert root.locator('button[data-action="migration-rollback"]').count()==0
  root.locator('button[data-action="settings-home"]').click()
  root.locator('button[data-action="settings-page"][data-value="profile"]').click()
  assert 'jan_willem' not in root.locator('.dialog-settings').inner_text().lower()
  root.locator('button[data-action="settings-profile-edit"]').first.click()
  assert 'Daily target (L)' in root.locator('.dialog-editor').inner_text()
  assert root.locator('[data-field="daily_target_ml"]').input_value()=='2'
  assert root.locator('.profile-quick-section').count()==1
  assert 'Quick buttons' in root.locator('.profile-quick-header').inner_text()
  root.locator('[data-field="unit"]').select_option('fl_oz');assert 'Daily target (fl oz)' in root.locator('.dialog-editor').inner_text()
  assert abs(float(root.locator('[data-field="daily_target_ml"]').input_value())-67.63)<.01
  root.locator('button[data-action="settings-profile-cancel"]').last.click()
  root.locator('button[data-action="settings-home"]').click()
  root.locator('button[data-action="settings-page"][data-value="cups"]').click()
  assert root.locator('.settings-head h3').inner_text()=='Maintain cup types'
  assert root.locator('.cup-row-icon').count()==2
  root.locator('button[data-action="settings-cup-edit"]').first.click()
  assert root.locator('.dialog-editor [data-field="volume_ml"]').input_value()=='0.18'
  root.locator('button[data-action="icon-pick-open"][data-value="cup"]').click()
  assert root.locator('ha-icon-picker[data-icon-library]').count()==1
  root.locator('ha-icon-picker[data-icon-library]').evaluate('el=>el.dispatchEvent(new CustomEvent("value-changed",{detail:{value:"mdi:glass-wine"},bubbles:true,composed:true}))')
  root.locator('button[data-action="icon-pick-apply"]').click()
  assert root.locator('.icon-edit-row ha-icon').first.get_attribute('icon')=='mdi:glass-wine'
  root.locator('button[data-action="settings-discard"]').first.click()
  root.locator('button[data-action="settings-home"]').click()
  root.locator('button[data-action="settings-page"][data-value="liquids"]').click()
  assert root.locator('.saved-liquid').count()==3
  assert root.locator('.saved-liquid button[data-action="manage-remove"]').count()==3
  root.locator('button[data-action="manage-edit"]').first.click()
  assert root.locator('.liquid-icon-hero').count()==1
  assert 'Use default color' in root.locator('.dialog-editor').inner_text()
  root.locator('button[data-action="icon-pick-open"][data-value="liquid"]').click()
  assert root.locator('ha-icon-picker[data-icon-library]').count()==1
  root.locator('button[data-action="icon-pick-cancel"]').last.click()
  root.locator('button[data-action="manage-cancel"]').first.click()
  assert root.locator('.liquid-icon-hero').count()==0
  assert not errors,(width,errors)
  print('BETA37_CHROMIUM_PASS',width)
  page.close()
 browser.close()