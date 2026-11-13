"""Chromium UI regression for native Drink history columns and settings retirement."""
from playwright.sync_api import sync_playwright
from pathlib import Path
JS=Path(__file__).resolve().parents[1]/'custom_components/jw_daily_hydration_log/www/jwdaily-hydration-log-card.js'
with sync_playwright() as p:
    browser=p.chromium.launch(headless=True,**({'executable_path':'/usr/bin/chromium'} if Path('/usr/bin/chromium').is_file() else {'channel':'chrome'}),args=['--no-sandbox','--disable-dev-shm-usage'])
    for width in (360,420,540,720,950):
        page=browser.new_page(viewport={'width':width,'height':1100})
        errors=[]
        page.on('pageerror',lambda e:errors.append(str(e)))
        page.set_content('<html><body style="margin:0;padding:12px;background:#f0f2f5"><div id="mount"></div></body></html>')
        page.add_script_tag(path=str(JS))
        page.evaluate('''() => {
          const today=new Date();const iso=[today.getFullYear(),String(today.getMonth()+1).padStart(2,'0'),String(today.getDate()).padStart(2,'0')].join('-');
          const defs=[{drink_count_all_profiles:2,id:'coffee',name:'Coffee',icon_mdi:'mdi:coffee',color:'#A87B00',hidden:false},{id:'tea',name:'Tea',icon_mdi:'mdi:tea',color:'#EDB92C',hidden:false},{id:'water',name:'Water',icon_mdi:'mdi:water',color:'#86CAFE',hidden:false},{id:'milk',name:'Milk',icon_mdi:'mdi:cow',color:'#F2F2F2',hidden:false}];
          const cups=[{drink_count_all_profiles:4,id:'cup1',name:'Glazen beker',default_volume_ml:180,icon_mdi:'mdi:cup',hidden:false},{id:'cup2',name:'Fles',default_volume_ml:500,icon_mdi:'mdi:bottle-soda',hidden:false}];
          const entries=[{id:'rec1',timestamp:iso+'T21:11:40+01:00',liquid_type:'water',cup_type_id:'cup1',volume_ml:180},{id:'rec2',timestamp:iso+'T20:30:00+01:00',liquid_type:'tea',cup_type_id:'cup1',volume_ml:180},{id:'rec3',timestamp:iso+'T19:11:00+01:00',liquid_type:'coffee',cup_type_id:'cup1',volume_ml:180},{id:'rec4',timestamp:iso+'T18:39:00+01:00',liquid_type:'milk',cup_type_id:null,volume_ml:360}];
          const quick=[{id:'quick_tea',liquid_type_id:'tea',cup_type_id:'cup1',label_mode:'automatic',custom_label:'',hidden:false,available:true,label:'Tea (Glazen beker)',default_volume_ml:180},{id:'quick_coffee',liquid_type_id:'coffee',cup_type_id:'cup1',label_mode:'automatic',custom_label:'',hidden:false,available:true,label:'Coffee (Glazen beker)',default_volume_ml:180}];
          window.qaCalls=[];window.qaDownloads=[];
          HTMLAnchorElement.prototype.click=function(){window.qaDownloads.push({filename:this.download,href:this.href.slice(0,36)});};
          const breakdown=[{liquid_type:'coffee',volume_ml:180},{liquid_type:'water',volume_ml:180},{liquid_type:'tea',volume_ml:180},{liquid_type:'milk',volume_ml:360}];
          window.qaHass={user:{is_admin:true},config:{time_zone:'Europe/Amsterdam'},states:{'sensor.jwdhl_sample_consumed_today':{state:'0.9',attributes:{consumed_ml:900,unit_of_measurement:'L'}},'sensor.jwdhl_sample_daily_target':{state:'2',attributes:{target_ml:2000,unit_of_measurement:'L'}},'sensor.jwdhl_sample_drink_count_today':{state:'4',attributes:{}},'sensor.jwdhl_sample_manual_consumed':{state:'900',attributes:{manual_consumed_ml:900}}},callWS:async function(msg){window.qaCalls.push(msg);
             if(msg.type.endsWith('/manage_quick')){if(msg.action==='delete'){const ix=quick.findIndex(q=>q.id===msg.quick_id);if(ix<0)throw Error('missing');quick.splice(ix,1);}else if(msg.action==='hide'||msg.action==='restore'){const q=quick.find(q=>q.id===msg.quick_id);q.hidden=msg.action==='hide';q.available=!q.hidden;}return {quick_buttons:quick};}
             if(msg.type.endsWith('/migration_status'))return {status:'active',schema:3,profile_count:2,backup_verified:true,catalog_sha256:'a'.repeat(64)};
             if(msg.type.endsWith('/migration_backup_export'))return {filename:'test original migration backup.zip',base64:'UEsDBBQ=',sha256:'b'.repeat(64),bytes:5};
             if(msg.type.endsWith('/capabilities'))return {version:'1.1.0-beta.34',settings_transfer:true,native_model:true};
             if(msg.type.endsWith('/history'))return {profile:'sample',date:iso,entries,total_ml:900,count:4,consumed_ml:900,target_ml:2000,day_summary:{date:iso,drink_count:4,consumed_ml:900,target_ml:2000,liquid_breakdown:breakdown},liquid_types:defs,cup_types:cups,quick_buttons:quick,profile_settings:{name:'Sample',age:58,gender:'male',unit:'mL'},data_model_version:2,today_breakdown:breakdown,backend_version:'1.1.0-beta.34'};
             if(msg.type.endsWith('/profiles_list'))return {profiles:[{slug:'sample',name:'Sample',age:58,gender:'male',unit:'mL',daily_target_ml:2000},{slug:'second',name:'Second profile',age:35,gender:'female',unit:'mL',daily_target_ml:2400}]};
             return {};
          }};
          window.qaCard=document.createElement('jwdaily-hydration-log-card');window.qaCard.setConfig({profile:'sample',title:'Vocht intake Sample'});window.qaCard.hass=window.qaHass;document.querySelector('#mount').appendChild(window.qaCard);
        }''')
        root=page.locator('jwdaily-hydration-log-card')
        page.wait_for_timeout(400)
        headers=[x.strip() for x in root.locator('.history-table th').all_text_contents()]
        assert headers==['Time','Liquid','Cup','Volume'],(width,headers)
        cells=root.locator('.history-table tbody tr').first.locator('td')
        assert cells.count()==4 and cells.nth(1).inner_text()=='Milk' and cells.nth(2).inner_text()=='Unknown',(width,cells.all_text_contents())
        rowcup=root.locator('.history-table tbody tr').nth(1)
        assert rowcup.locator('td').nth(1).inner_text()=='Coffee'
        assert rowcup.locator('td').nth(2).inner_text()=='Glazen beker'
        table=root.locator('.history-table table').bounding_box();
        assert table and table['width']>180,(width,table)
        # Export scope defaults to All profiles; all registered profiles are options.
        scope=root.locator('select[data-field="export_profile"]')
        assert scope.count()==1,(width,'export dropdown missing')
        assert scope.input_value()=='all'
        assert scope.locator('option').all_text_contents()==['All profiles','Sample','Second profile']
        assert root.locator('label[for="jwdhl-export-profile"]').inner_text()=='Export hydration data:'
        scope.select_option('second')
        assert page.evaluate("window.qaCard._exportProfile")=='second'
        scope.select_option('all')
        # Four columns occupy stable widths; right volume aligns with right edge.
        xs=[x.bounding_box()['x'] for x in root.locator('.history-table thead th').all()]
        assert xs==sorted(xs),(width,xs)
        root.locator('button[data-action="settings-open"]').click()
        root.locator('button[data-action="settings-page"][data-value="advanced"]').click()
        shadow=root.locator('.settings-section').inner_text()
        assert 'Import & Export' in shadow and 'Convert existing data' not in shadow and 'Finalize data model' not in shadow and 'Original volume buttons' not in shadow
        # Regression: beta.32 did not dispatch migration-* clicks to _settingsClick.
        # Verify actual mouse clicks invoke the authenticated status and ZIP APIs.
        root.locator('button[data-action="settings-page"][data-value="transfer"]').click()
        root.locator('button[data-action="migration-status"]').click()
        page.wait_for_timeout(80)
        assert page.evaluate("window.qaCalls.filter(c=>c.type==='jw_daily_hydration_log/migration_status').length")==1,(width,'migration status not routed')
        assert 'Status: active' in root.locator('.settings-section').inner_text()
        assert 'Backup: Verified' in root.locator('.settings-section').inner_text()
        assert root.locator('button[data-action="migration-rollback"]').is_disabled()
        root.locator('button[data-action="migration-backup-export"]').click()
        page.wait_for_timeout(80)
        assert page.evaluate("window.qaCalls.filter(c=>c.type==='jw_daily_hydration_log/migration_backup_export').length")==1,(width,'migration backup not routed')
        assert page.evaluate("window.qaDownloads.filter(d=>d.filename==='test original migration backup.zip'&&d.href.startsWith('data:application/zip;base64,')).length")==1,(width,'migration download not triggered')
        assert not page.evaluate("window.qaCalls.some(c=>c.type==='jw_daily_hydration_log/migration_rollback')"),'migration rollback was unexpectedly invoked'
        root.locator('button[data-action="settings-home"]').click()
        print('BETA33_CHROMIUM_MIGRATION_BUTTONS_PASS',width,'px')
        # Both headings appear only once (the modal header is authoritative).
        root.locator('button[data-action="settings-home"]').click()
        root.locator('button[data-action="settings-page"][data-value="cups"]').click()
        assert root.locator('.settings-head h3').inner_text()=='Cup types'
        assert root.locator('.settings-section > h3').count()==0
        cuprow=root.locator('.settings-row').first
        actions=cuprow.locator('button').evaluate_all('(nodes)=>nodes.map(n=>n.dataset.action)')
        assert actions.index('settings-cup-toggle')<actions.index('settings-cup-edit'),(width,actions)
        f1=float(cuprow.locator('[data-action="settings-cup-toggle"]').evaluate('(n)=>getComputedStyle(n).fontSize.replace("px","")'))
        f2=float(cuprow.locator('[data-action="settings-cup-edit"]').evaluate('(n)=>getComputedStyle(n).fontSize.replace("px","")'))
        assert abs(f1-f2)<0.11,(width,'buttons should use consistent font size',f1,f2)
        assert root.locator('.cup-settings-row').count()==2
        assert 'Used: 4' in root.locator('.cup-settings-row').first.inner_text()
        for cr in root.locator('.cup-settings-row').all():
            heights=[round(b.bounding_box()['y']) for b in cr.locator('.settings-row-actions button').all()]
            assert max(heights)-min(heights)<=2,(width,'cup action buttons wrapped',heights)
        root.locator('.cup-settings-row [data-action="settings-cup-edit"]').first.click()
        assert root.locator('.editor-overlay .dialog-editor').count()==1
        assert root.locator('.cup-settings-row').count()==2
        assert root.locator('.editor-overlay [data-field="name"]').input_value()=='Glazen beker'
        root.locator('.editor-overlay [data-action="settings-discard"]').first.click()
        assert root.locator('.editor-overlay').count()==0
        assert root.locator('.cup-settings-row').count()==2
        print('BETA34_CUP_POPUP_USAGE_PASS',width)

        root.locator('button[data-action="settings-home"]').click()
        root.locator('button[data-action="settings-page"][data-value="profile"]').click()
        root.locator('button[data-action="settings-profile-edit"][data-value="sample"]').click()
        root.locator('button[data-action="settings-profile-quick"]').click()
        assert root.locator('.settings-head h3').inner_text()=='Quick buttons'
        assert root.locator('.settings-section > h3').count()==0
        qrow=root.locator('.settings-row.quick-settings-row').first
        actions=qrow.locator('button').evaluate_all('(nodes)=>nodes.map(n=>n.dataset.action)')
        assert actions == ['settings-quick-up','settings-quick-down','settings-quick-toggle','settings-quick-edit','settings-quick-delete'],(width,actions)
        f1=float(qrow.locator('[data-action="settings-quick-toggle"]').evaluate('(n)=>getComputedStyle(n).fontSize.replace("px","")'))
        f2=float(qrow.locator('[data-action="settings-quick-edit"]').evaluate('(n)=>getComputedStyle(n).fontSize.replace("px","")'))
        assert abs(f1-f2)<0.11,(width,'buttons should use consistent font size',f1,f2)
        qys=[round(b.bounding_box()['y']) for b in root.locator('.quick-settings-row').first.locator('.settings-row-actions button').all()]
        assert max(qys)-min(qys)<=2,(width,'quick buttons wrapped',qys)
        root.locator('.quick-settings-row [data-action="settings-quick-edit"]').first.click()
        assert root.locator('.editor-overlay .dialog-editor').count()==1
        assert root.locator('.quick-settings-row').count()==2
        root.locator('.editor-overlay [data-action="settings-discard"]').first.click()
        assert root.locator('.editor-overlay').count()==0
        print('BETA34_QUICK_POPUP_PASS',width)

        dialog=root.locator('.dialog-settings'); db=dialog.bounding_box()
        assert db and db['x'] >= -1 and db['x']+db['width']<=width+1,(width,db)
        btns=root.locator('.quick-settings-row button').all()
        assert all((b.bounding_box()['x'] >= db['x']-1 and b.bounding_box()['x']+b.bounding_box()['width'] <= db['x']+db['width']+1) for b in btns),(width,'overflow')
        root.locator('[data-action="settings-quick-delete"]').first.click()
        assert root.locator('[data-action="settings-quick-delete-confirm"]').count()==1
        root.locator('[data-action="settings-quick-delete-cancel"]').last.click()
        assert not page.evaluate("window.qaCalls.some(c=>c.type.endsWith('/manage_quick')&&c.action==='delete')")
        root.locator('[data-action="settings-quick-delete"]').first.click()
        root.locator('[data-action="settings-quick-delete-confirm"]').click()
        page.wait_for_timeout(80)
        assert page.evaluate("window.qaCalls.filter(c=>c.type.endsWith('/manage_quick')&&c.action==='delete').length")==1
        assert root.locator('.settings-row.quick-settings-row').count()==1
        assert root.locator('.history-table tbody tr').count()==4
        root.locator('button[data-action="settings-home"]').click()
        assert root.locator('.editor-overlay').count()==1
        root.locator('.editor-overlay [data-action="settings-profile-cancel"]').first.click()
        assert root.locator('.editor-overlay').count()==0
        assert root.locator('.settings-head h3').inner_text()=='Manage profiles'
        assert root.locator('.settings-section > h3').count()==0
        assert 'Each profile keeps separate settings and drink history.' in root.locator('.settings-section').inner_text()
        assert root.locator('button[data-action="settings-profile-edit"]').count()==2
        assert root.locator('button[data-action="settings-profile-add"]').count()==1
        assert root.locator('button[data-action="settings-home"]').count()==1
        root.locator('button[data-action="settings-profile-edit"][data-value="sample"]').click()
        assert root.locator('[data-field="daily_target_ml"]').input_value()=='2000'
        assert root.locator('.editor-overlay').count()==1
        assert root.locator('.profile-settings-row').count()==2
        for obsolete in ('source_sensor','source_mode','pregnancy','lactation'):
            assert root.locator('[data-field="'+obsolete+'"]').count()==0,(width,obsolete)
        assert root.locator('button[data-action="settings-profile-quick"]').count()>=1
        root.locator('button[data-action="settings-profile-save"]').click()
        page.wait_for_timeout(80)
        assert page.evaluate("window.qaCalls.some(c=>c.type.endsWith('/profile_edit')&&c.daily_target_ml===2000)")
        # Liquid editing is a separate dialog; parent list and per-type counts remain.
        root.locator('button[data-action="settings-home"]').click()
        root.locator('button[data-action="settings-page"][data-value="liquids"]').click()
        assert root.locator('.settings-head h3').inner_text()=='Liquid types'
        assert root.locator('.manage > h3').count()==0
        assert 'Back to drink' not in root.locator('.dialog-settings').inner_text()
        assert 'Used: 2' in root.locator('.saved-liquid').filter(has_text='Coffee').first.inner_text()
        for row in root.locator('.saved-liquid').all():
            ys=[round(b.bounding_box()['y']) for b in row.locator('.settings-row-actions button').all()]
            assert max(ys)-min(ys)<=2,(width,'liquid actions wrapped',ys)
        root.locator('.saved-liquid [data-action="manage-edit"]').first.click()
        assert root.locator('.editor-overlay').count()==1
        assert root.locator('.saved-liquid').count()==4
        root.locator('.editor-overlay [data-action="manage-cancel"]').first.click()
        assert root.locator('.editor-overlay').count()==0
        assert root.locator('.saved-liquid').count()==4
        print('BETA34_LIQUID_POPUP_USAGE_PASS',width)
        assert not errors,(width,errors)
        print('BETA32_CHROMIUM_PROFILE_TARGET_EXPORT_SCOPE_PASS',width,'px')
        print('BETA31_CHROMIUM_LAYOUT_AND_DELETE_PASS',width,'px',headers)
        page.close()
    browser.close()
