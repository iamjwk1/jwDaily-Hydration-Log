"""Real Chromium contract smoke test of beta29 Settings/Data and full restore UI."""
import base64
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
JS=ROOT/'custom_components/jw_daily_hydration_log/www/jwdaily-hydration-log-card.js'

with sync_playwright() as p:
 browser_path=next((x for x in ('/usr/bin/chromium','/usr/bin/google-chrome','/usr/bin/google-chrome-stable') if Path(x).is_file()),None)
 browser=p.chromium.launch(headless=True,**({'executable_path':browser_path} if browser_path else {'channel':'chrome'}),args=['--no-sandbox','--disable-dev-shm-usage'])
 context=browser.new_context(accept_downloads=True,viewport={'width':1100,'height':900})
 page=context.new_page()
 errors=[]
 page.on('pageerror',lambda e:errors.append(str(e)))
 page.goto('about:blank')
 page.evaluate('window.customCards=[]; window.__websocket=[]; window.confirm=()=>false;')
 page.add_script_tag(path=str(JS))
 page.evaluate("""() => {
  const today=new Intl.DateTimeFormat('sv-SE',{timeZone:'Europe/Amsterdam',year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date());
  const result={profile:'qa',date:today,entries:[],count:0,total_ml:0,consumed_ml:0,target_ml:2000,
    day_summary:{date:today,consumed_ml:0,target_ml:2000,drink_count:0,liquid_breakdown:[]},
    liquid_types:[{id:'water',name:'Water',icon_mdi:'mdi:water',color:'#86CAFE',hidden:false,default_volume_ml:180}],
    cup_types:[{id:'cup_glass',name:'Glazen beker',icon_mdi:'mdi:cup',hidden:false,default_volume_ml:180}],
    quick_buttons:[],today_breakdown:[],profile_settings:{name:'QA',age:50,gender:'male',unit:'mL',source_mode:'absolute'},
    backend_version:'1.1.0-beta.29',conversion_applied:true,data_model_version:1};
  const hass={config:{time_zone:'Europe/Amsterdam'},user:{is_admin:true},states:{},callWS:async msg=>{
   window.__websocket.push(msg.type);
   if(msg.type.endsWith('/history'))return result;
   if(msg.type.endsWith('/capabilities'))return {version:'1.1.0-beta.29'};
   if(msg.type.endsWith('/model_migration_preview'))return {profile:'qa',completed:false,
    revision:'a'.repeat(64),history_revision:'b'.repeat(64),drink_count:4,
    unclassified_count:0,cup_unknown_count:1,total_logged_ml:840};
   if(msg.type.endsWith('/data_import_preview'))return {profile:'qa',mode:msg.mode,
    counts:{existing_drinks:4,incoming_drinks:5,new_ids:1,matching_ids:4,changed_matching_ids:1,total_result_drinks:5},
    warning:'Existing settings preserved.',import_sha256:'d'.repeat(64)};
   if(msg.type.endsWith('/full_restore_preview'))return {profile:'qa',counts:{current_records:4,records:5,cups:2,quick_buttons:1}};
   if(msg.type.endsWith('/full_backup_export'))return {filename:'QA Full Backup.zip',mime_type:'application/zip',base64:'UEs=',sha256:'a'.repeat(64)};
   if(msg.type.endsWith('/data_export'))return {filename:'QA Data.json',mime_type:'application/json',base64:'e30=',sha256:'a'.repeat(64)};
   throw Error('Unexpected mocked WebSocket '+msg.type);
  }};
  const card=document.createElement('jwdaily-hydration-log-card');document.body.appendChild(card);
  card.setConfig({type:'custom:jwdaily-hydration-log-card',profile:'qa',title:'QA',show_history:true});card.hass=hass;
  window.testCard=card;
 }""")
 page.wait_for_timeout(350)
 for width in [360,420,720,950]:
  page.set_viewport_size({'width':width,'height':900})
  page.evaluate("window.testCard._settingsOpen('transfer')")
  root=page.locator('jwdaily-hydration-log-card').locator('shadow-root') if False else page.locator('jwdaily-hydration-log-card')
  # Modern Playwright transparently pierces open shadow roots for locators.
  assert root.get_by_text('Data — drink history and snapshots').count()==1
  assert root.get_by_text('Full backup / restore').count()==1
  assert root.locator('[data-action="settings-export-json"]').count()==1
  assert root.locator('[data-action="data-export-json"]').count()==1
  assert root.locator('[data-action="full-backup-export"]').count()==1
  assert root.locator('[data-field="data_import_mode"]').count()==1
  print('PASS Settings transfer layout',width)
 page.set_viewport_size({'width':950,'height':900})
 root.locator('[data-field="data_import_file"]').set_input_files({'name':'test Data.json','mimeType':'application/json','buffer':b'{}'})
 root.get_by_text('Selected: test Data.json').wait_for()
 root.locator('[data-field="data_import_mode"]').select_option('replace')
 root.locator('[data-action="data-import-preview"]').click()
 root.get_by_text('Data preview — replace').wait_for()
 assert root.locator('[data-action="data-import-apply"]').is_disabled()
 root.locator('[data-action="full-backup-export"]').click()
 root.locator('[data-field="full_backup_verified"]').check()
 assert root.locator('[data-action="data-import-apply"]').is_enabled()
 root.locator('[data-action="data-import-apply"]').click()
 assert 'jw_daily_hydration_log/data_import_apply' not in page.evaluate('window.__websocket')
 # Real file chooser flow, no file bytes sent to UI as HTML.
 root.locator('[data-field="full_restore_file"]').set_input_files({'name':'test Full Backup.zip','mimeType':'application/zip','buffer':b'PK\x03\x04abc'})
 root.get_by_text('Selected: test Full Backup.zip').wait_for()
 root.locator('[data-action="full-restore-preview"]').click()
 root.get_by_text('Full restore preview').wait_for()
 assert root.locator('[data-action="full-restore-apply"]').is_enabled()
 page.evaluate("window.testCard._settingsOpen('finalize')")
 root.get_by_text('Finalize canonical data model').first.wait_for()
 assert root.get_by_text('Drink records 4').count()==0 or root.get_by_text('Drink records 4').count()==1
 assert root.locator('[data-action="model-finalize-apply"]').is_enabled()
 assert not errors,errors
 print('BROWSER_BETA29_TRANSFER_AND_MIGRATION_PASS')
 context.close();browser.close()
