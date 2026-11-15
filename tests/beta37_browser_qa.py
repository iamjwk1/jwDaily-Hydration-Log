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
      if(msg.type.endsWith('/history'))return {profile:msg.profile,date:iso,entries,total_ml:180,count:1,consumed_ml:180,target_ml:2000,day_summary:{date:iso,drink_count:1,consumed_ml:180,target_ml:2000,liquid_breakdown:[{liquid_type:'coffee',volume_ml:180}]},liquid_types:defs,cup_types:cups,quick_buttons:quick,profile_settings:{name:'Jan-Willem',age:58,gender:'male',unit:'L'},data_model_version:2,today_breakdown:[{liquid_type:'coffee',volume_ml:180}],backend_version:'1.1.0-beta.42'};
      if(msg.type.endsWith('/capabilities'))return {version:'1.1.0-beta.42'};
      if(msg.type.endsWith('/profiles_list'))return {profiles:[{slug:'one',name:'Jan-Willem',age:58,gender:'male',unit:'L',daily_target_ml:2000},{slug:'two',name:'Second',age:30,gender:'female',unit:'fl_oz',daily_target_ml:1500}]};
      if(msg.type.endsWith('/export'))return {base64:'UEsDBBQ=',filename:'test beta38.xlsx'};
      return {};
    }};
    window.card=document.createElement('jwdaily-hydration-log-card');card.setConfig({profile:'one',title:'Vocht intake',unit:'mL'});card.hass=window.hass;document.querySelector('#mount').appendChild(card);
  }''')
  root=page.locator('jwdaily-hydration-log-card');page.wait_for_timeout(300)
  assert root.locator('.card-version').inner_text()=='v1.1.0-beta.42'
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
  assert root.locator('.beta40-transfer .transfer-action-row').count()>=3
  assert root.locator('[data-action="transfer-scope"]').count()==3
  root.locator('[data-action="transfer-scope"][data-value="settings"]').click()
  assert root.locator('[data-action="transfer-scope"][data-value="settings"]').get_attribute("aria-pressed")=="true"
  assert root.locator('.beta40-advanced').count()==0
  assert root.locator('[data-action="settings-export-json"]').count()==0
  assert root.locator('[data-action="data-export-json"]').count()==0
  assert 'Migration v3' not in root.locator('.dialog-settings').inner_text()
  assert root.locator('button[data-action="migration-rollback"]').count()==0
  root.locator('button[data-action="settings-home"]').click()
  root.locator('button[data-action="settings-page"][data-value="profile"]').click()
  assert 'jan_willem' not in root.locator('.dialog-settings').inner_text().lower()
  root.locator('button[data-action="settings-profile-edit"]').first.click()
  assert 'Daily target (L)' in root.locator('.dialog-editor').inner_text()
  assert root.locator('[data-field="daily_target_ml"]').input_value()=='2'
  assert root.locator('.dialog-editor .settings-head h3').inner_text()=='Edit profile - Jan-Willem'
  assert root.locator('.profile-quick-section').count()==1
  assert 'Quick buttons' in root.locator('.profile-quick-header').inner_text()
  assert root.locator('[data-action="settings-profile-quick"] ha-icon').count()==1
  assert root.locator('[data-action="settings-profile-quick"]').get_attribute('title')=='Edit quick buttons'
  assert root.locator('.profile-quick-choices .quick-choice').count()==1
  assert root.locator('.profile-quick-choices .quick-choice').first.evaluate('(n)=>getComputedStyle(n).borderRadius')!='0px'
  assert root.locator('.profile-quick-choices').first.evaluate('(n)=>getComputedStyle(n).flexWrap')=='wrap'

  assert '180' not in root.locator('.profile-quick-choices .quick-choice').first.inner_text()
  root.locator('[data-action="settings-profile-quick"]').click()
  assert root.locator('.settings-head h3').first.inner_text().startswith('Edit Quick Buttons')
  assert root.locator('.quick-settings-row [data-action="settings-quick-toggle"] ha-icon').count()==1
  assert root.locator('.quick-settings-row [data-action="settings-quick-edit"] ha-icon').count()==1
  assert root.locator('.quick-settings-row [data-action="settings-quick-delete"] ha-icon').count()==1
  if width>720:
   header=root.locator('.quick-table-header span');row=root.locator('.quick-settings-row').first
   assert abs(header.nth(0).bounding_box()['x']-row.locator('.quick-col-name').bounding_box()['x'])<9
   for idx,cls in [(1,'.quick-col-cup'),(2,'.quick-col-volume')]:
    hb=header.nth(idx).bounding_box();vb=row.locator(cls).bounding_box()
    assert abs((hb['x']+hb['width']/2)-(vb['x']+vb['width']/2))<8
  root.locator('button[data-action="settings-home"]').last.click()
  assert root.locator('.profile-quick-section').count()==1
  page.evaluate("""() => {
    const q=card._profileQuickHistory.quick_buttons[0];
    card._profileQuickHistory.quick_buttons=[{...q,id:'q0',liquid_type_id:'water',cup_type_id:'cup2',label_mode:'automatic',icon_mdi:'mdi:water'},q];
    card._render(true);
  }""")
  assert root.locator('.profile-quick-choices .quick-choice').count()==2
  assert root.locator('.profile-quick-choices .quick-choice').first.inner_text().startswith('Water (')
  page.evaluate("""() => {card._profileQuickHistory.quick_buttons.splice(0,1);card._render(true);}""")

  root.locator('[data-field="unit"]').select_option('fl_oz');assert 'Daily target (fl oz)' in root.locator('.dialog-editor').inner_text()
  assert abs(float(root.locator('[data-field="daily_target_ml"]').input_value())-67.63)<.01
  root.locator('button[data-action="settings-profile-cancel"]').last.click()
  root.locator('button[data-action="settings-home"]').click()
  root.locator('button[data-action="settings-page"][data-value="cups"]').click()
  assert root.locator('.settings-head h3').inner_text()=='Maintain cup types'
  assert root.locator('.cup-row-icon').count()==2
  assert root.locator('.cup-table-head').count()==1
  assert root.locator('.cup-settings-row [data-action="settings-cup-edit"] ha-icon').count()==2
  assert root.locator('.cup-settings-row [data-action="settings-cup-delete"] ha-icon').count()==2
  assert root.locator('.cup-settings-row [data-action="settings-cup-toggle"] ha-icon').count()==2
  assert root.locator('.cup-settings-row [data-action="settings-cup-up"]').first.get_attribute('title')=='Move cup type up'
  if width>=720:
   head=root.locator('.cup-table-head span').all()
   row=root.locator('.cup-settings-row').first
   for header,cell in [(head[0],row.locator('.row-title')),(head[1],row.locator('.cup-volume-value')),(head[2],row.locator('.used-count'))]:
    hx=header.bounding_box()['x'];cx=cell.bounding_box()['x']
    assert abs(hx-cx)<8,('Cup header misaligned',width,hx,cx)

  assert root.locator('.cup-volume-value').count()==2
  assert root.locator('.cup-settings-row .used-count').count()==2
  for row in root.locator('.cup-settings-row').all():
   use=row.locator('.used-count').bounding_box(); actions=row.locator('.settings-row-actions').bounding_box()
   assert use and actions
   assert use['x']+use['width'] <= actions['x']+1 or actions['y']>=use['y']+use['height']-1,(width,use,actions)

  assert all(x.strip().isdigit() for x in root.locator('.cup-settings-row .used-count').all_text_contents())
  root.locator('button[data-action="settings-cup-edit"]').first.click()
  assert root.locator('.dialog-editor [data-field="volume_ml"]').input_value()=='0.18'
  assert root.locator('[data-field="cup_icon_color_picker"]').count()==1
  assert '#000000' in root.locator('.cup-icon-editor .liquid-icon').first.get_attribute('style').lower()
  root.locator('button[data-action="icon-pick-open"][data-value="cup"]').click()
  assert root.locator('[data-field="icon_color_picker"]').input_value().lower()=='#000000'
  assert root.locator('ha-icon-picker[data-icon-library]').count()==1
  root.locator('ha-icon-picker[data-icon-library]').evaluate('el=>el.dispatchEvent(new CustomEvent("value-changed",{detail:{value:"mdi:glass-wine"},bubbles:true,composed:true}))')
  root.locator('button[data-action="icon-pick-apply"]').click()
  assert root.locator('.icon-edit-row ha-icon').first.get_attribute('icon')=='mdi:glass-wine'
  root.locator('button[data-action="settings-discard"]').first.click()
  root.locator('button[data-action="settings-home"]').click()
  root.locator('button[data-action="settings-page"][data-value="liquids"]').click()
  assert root.locator('.liquid-list-header').count()==1
  assert root.locator('.settings-head h3').first.inner_text()=='Maintain liquid types'
  assert root.locator('.saved-liquid [data-action="manage-up"]').first.get_attribute('title')=='Move liquid type up'
  assert root.locator('.saved-liquid [data-action="manage-down"]').first.get_attribute('title')=='Move liquid type down'
  if width>=720:
   head=root.locator('.liquid-list-header span')
   row=root.locator('.saved-liquid').first
   assert abs(head.nth(0).bounding_box()['x']-row.locator('.liquid-type-name').bounding_box()['x'])<8
   assert abs(head.nth(1).bounding_box()['x']-row.locator('.used-count').bounding_box()['x'])<8

  assert root.locator('.saved-liquid').count()==3
  assert root.locator('.saved-liquid button[data-action="manage-remove"]').count()==3
  root.locator('button[data-action="manage-edit"]').first.click()
  assert root.locator('.liquid-live-section').count()==1
  assert root.locator('.liquid-live-preview').count()==1
  assert '#000000' in root.locator('.liquid-live-preview .liquid-icon').first.get_attribute('style').lower()
  assert root.locator('[data-action="liquid-icon-default"]').count()==1
  assert root.locator('.liquid-name-row input').first.evaluate('(n)=>getComputedStyle(n).fontWeight') in ('400','normal')
  assert root.locator('.liquid-selected-icon').count()==1
  assert 'Use default color' in root.locator('.dialog-editor').inner_text()
  assert root.locator('.dialog-editor .color-preview').count()==0
  assert root.locator('[data-field="liquid_icon_color_picker"]').input_value().lower()=='#000000'
  assert root.locator('.liquid-icon-controls').count()==1
  root.locator('button[data-action="icon-pick-open"][data-value="liquid"]').click()
  assert root.locator('ha-icon-picker[data-icon-library]').count()==1
  assert root.locator('button[data-action="icon-pick-source"]').count()==2
  assert root.locator('[data-field="icon_color_picker"]').input_value().lower()=='#000000'
  root.locator('button[data-action="icon-pick-source"][data-value="svg"]').click()
  assert root.locator('input[data-field="icon_svg_file"]').count()==1
  root.locator('button[data-action="icon-pick-cancel"]').last.click()
  root.locator('button[data-action="manage-cancel"]').first.click()
  assert root.locator('.liquid-live-section').count()==0
  assert not errors,(width,errors)
  # Adaptive mL formatter is restricted to glass quantities; profile unit handling remains unchanged.
  assert page.evaluate('jdhlGlassFmt(999, "mL")')=='999 mL'
  assert page.evaluate('jdhlGlassFmt(1000, "mL")')=='1.0 L'
  assert page.evaluate('jdhlGlassFmt(1250, "mL")')=='1.25 L'
  assert page.evaluate('jdhlGlassFmt(2000, "mL")')=='2.0 L'
  assert page.evaluate('jdhlGlassFmt(2000, "L")')=='2 L'
  print('BETA38_CHROMIUM_PASS',width)
  page.close()
 browser.close()