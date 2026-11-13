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
          const defs=[{id:'coffee',name:'Coffee',icon_mdi:'mdi:coffee',color:'#A87B00',hidden:false},{id:'tea',name:'Tea',icon_mdi:'mdi:tea',color:'#EDB92C',hidden:false},{id:'water',name:'Water',icon_mdi:'mdi:water',color:'#86CAFE',hidden:false},{id:'milk',name:'Milk',icon_mdi:'mdi:cow',color:'#F2F2F2',hidden:false}];
          const cups=[{id:'cup1',name:'Glazen beker',default_volume_ml:180,icon_mdi:'mdi:cup',hidden:false},{id:'cup2',name:'Fles',default_volume_ml:500,icon_mdi:'mdi:bottle-soda',hidden:false}];
          const entries=[{id:'rec1',timestamp:iso+'T21:11:40+01:00',liquid_type:'water',cup_type_id:'cup1',volume_ml:180},{id:'rec2',timestamp:iso+'T20:30:00+01:00',liquid_type:'tea',cup_type_id:'cup1',volume_ml:180},{id:'rec3',timestamp:iso+'T19:11:00+01:00',liquid_type:'coffee',cup_type_id:'cup1',volume_ml:180},{id:'rec4',timestamp:iso+'T18:39:00+01:00',liquid_type:'milk',cup_type_id:null,volume_ml:360}];
          const quick=[{id:'quick_tea',liquid_type_id:'tea',cup_type_id:'cup1',label_mode:'automatic',custom_label:'',hidden:false,available:true,label:'Tea (Glazen beker)',default_volume_ml:180},{id:'quick_coffee',liquid_type_id:'coffee',cup_type_id:'cup1',label_mode:'automatic',custom_label:'',hidden:false,available:true,label:'Coffee (Glazen beker)',default_volume_ml:180}];
          window.qaCalls=[];
          const breakdown=[{liquid_type:'coffee',volume_ml:180},{liquid_type:'water',volume_ml:180},{liquid_type:'tea',volume_ml:180},{liquid_type:'milk',volume_ml:360}];
          window.qaHass={user:{is_admin:true},config:{time_zone:'Europe/Amsterdam'},states:{'sensor.jwdhl_sample_consumed_today':{state:'0.9',attributes:{consumed_ml:900,unit_of_measurement:'L'}},'sensor.jwdhl_sample_daily_target':{state:'2',attributes:{target_ml:2000,unit_of_measurement:'L'}},'sensor.jwdhl_sample_drink_count_today':{state:'4',attributes:{}},'sensor.jwdhl_sample_manual_consumed':{state:'900',attributes:{manual_consumed_ml:900}}},callWS:async function(msg){window.qaCalls.push(msg);
             if(msg.type.endsWith('/manage_quick')){if(msg.action==='delete'){const ix=quick.findIndex(q=>q.id===msg.quick_id);if(ix<0)throw Error('missing');quick.splice(ix,1);}else if(msg.action==='hide'||msg.action==='restore'){const q=quick.find(q=>q.id===msg.quick_id);q.hidden=msg.action==='hide';q.available=!q.hidden;}return {quick_buttons:quick};}
             if(msg.type.endsWith('/capabilities'))return {version:'1.1.0-beta.32',settings_transfer:true,native_model:true};
             if(msg.type.endsWith('/history'))return {profile:'sample',date:iso,entries,total_ml:900,count:4,consumed_ml:900,target_ml:2000,day_summary:{date:iso,drink_count:4,consumed_ml:900,target_ml:2000,liquid_breakdown:breakdown},liquid_types:defs,cup_types:cups,quick_buttons:quick,profile_settings:{name:'Sample',age:58,gender:'male',unit:'mL'},data_model_version:2,today_breakdown:breakdown,backend_version:'1.1.0-beta.32'};
             if(msg.type.endsWith('/profiles_list'))return {profiles:[]};
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
        # Four columns occupy stable widths; right volume aligns with right edge.
        xs=[x.bounding_box()['x'] for x in root.locator('.history-table thead th').all()]
        assert xs==sorted(xs),(width,xs)
        root.locator('button[data-action="settings-open"]').click()
        root.locator('button[data-action="settings-page"][data-value="advanced"]').click()
        shadow=root.locator('.settings-section').inner_text()
        assert 'Import & Export' in shadow and 'Convert existing data' not in shadow and 'Finalize data model' not in shadow and 'Original volume buttons' not in shadow
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
        assert f1 < f2,(width,f1,f2)
        root.locator('button[data-action="settings-home"]').click()
        root.locator('button[data-action="settings-page"][data-value="quick"]').click()
        assert root.locator('.settings-head h3').inner_text()=='Quick buttons'
        assert root.locator('.settings-section > h3').count()==0
        qrow=root.locator('.settings-row.quick-settings-row').first
        actions=qrow.locator('button').evaluate_all('(nodes)=>nodes.map(n=>n.dataset.action)')
        assert actions == ['settings-quick-up','settings-quick-down','settings-quick-toggle','settings-quick-edit','settings-quick-delete'],(width,actions)
        f1=float(qrow.locator('[data-action="settings-quick-toggle"]').evaluate('(n)=>getComputedStyle(n).fontSize.replace("px","")'))
        f2=float(qrow.locator('[data-action="settings-quick-edit"]').evaluate('(n)=>getComputedStyle(n).fontSize.replace("px","")'))
        assert f1 < f2,(width,f1,f2)
        dialog=root.locator('.dialog-settings'); db=dialog.bounding_box()
        assert db and db['x'] >= -1 and db['x']+db['width']<=width+1,(width,db)
        btns=root.locator('.quick-settings-row button').all()
        assert all((b.bounding_box()['x'] >= db['x']-1 and b.bounding_box()['x']+b.bounding_box()['width'] <= db['x']+db['width']+1) for b in btns),(width,'overflow')
        root.locator('[data-action="settings-quick-delete"]').first.click()
        assert root.locator('[data-action="settings-quick-delete-confirm"]').count()==1
        root.locator('[data-action="settings-quick-delete-cancel"]').click()
        assert not page.evaluate("window.qaCalls.some(c=>c.type.endsWith('/manage_quick')&&c.action==='delete')")
        root.locator('[data-action="settings-quick-delete"]').first.click()
        root.locator('[data-action="settings-quick-delete-confirm"]').click()
        page.wait_for_timeout(80)
        assert page.evaluate("window.qaCalls.filter(c=>c.type.endsWith('/manage_quick')&&c.action==='delete').length")==1
        assert root.locator('.settings-row.quick-settings-row').count()==1
        assert root.locator('.history-table tbody tr').count()==4
        assert not errors,(width,errors)
        print('BETA31_CHROMIUM_LAYOUT_AND_DELETE_PASS',width,'px',headers)
        page.close()
    browser.close()
