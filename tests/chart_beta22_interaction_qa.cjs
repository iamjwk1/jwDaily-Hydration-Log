/* Chrome acceptance: same-colour legends, readable axes, drill-down and missing/zero. */
const assert=require('node:assert/strict'),path=require('node:path');
const puppeteer=require('puppeteer-core');
(async()=>{
 const browser=await puppeteer.launch({headless:true,executablePath:process.env.CHROME_PATH||'/usr/bin/google-chrome',args:['--no-sandbox','--disable-dev-shm-usage']});
 try{
  for(const width of [360,420,720,900]){
   const page=await browser.newPage();let errors=[];page.on('pageerror',e=>errors.push(String(e)));
   await page.setViewport({width,height:1000,deviceScaleFactor:1});
   await page.setContent('<style>body{margin:0;font:16px Arial}ha-card{display:block}</style><jwdaily-hydration-hourly-card></jwdaily-hydration-hourly-card><jwdaily-hydration-weekly-card></jwdaily-hydration-weekly-card>');
   await page.addScriptTag({path:path.resolve(__dirname,'../custom_components/jw_daily_hydration_log/www/jwdaily-hydration-log-card.js')});
   await page.evaluate(()=>{
    const hours=Array.from({length:24},(_,i)=>({hour:String(i).padStart(2,'0')+':00',total_ml:0,liquids:{}}));
    for(const [i,k,v] of [[11,'coffee',360],[12,'milk',180],[14,'tea',180],[18,'coffee',360]]){
     hours[i].total_ml=v;hours[i].liquids[k]=v;
    }
    const dates=Array.from({length:7},(_,i)=>({date:'2026-11-'+String(i+5).padStart(2,'0'),total_logged_ml:0,liquids:{},has_data:false}));
    dates[2].has_data=true;
    dates[3]={date:'2026-11-08',total_logged_ml:2550,liquids:{water_cup:1800,tea:180,milk:180,coffee:390},has_data:true};
    dates[4]={date:'2026-11-09',total_logged_ml:1900,liquids:{water_glass:1200,tea:200,coffee:500},has_data:true};
    dates[5]={date:'2026-11-10',total_logged_ml:2530,liquids:{water_glass:540,tea:720,milk:180,water_cup:800,coffee:290},has_data:true};
    dates[6]={date:'2026-11-11',total_logged_ml:720,liquids:{coffee:360,milk:180,tea:180},has_data:true};
    const names={coffee:'Coffee',milk:'Milk',tea:'Tea',water_cup:'Water (beker)',water_glass:'Water (glas)'};
    const hass={states:{
      'sensor.jwdhl_qa_daily_target':{state:'2000'},
      'sensor.jwdhl_qa_hourly_intake_today':{state:'720',attributes:{buckets:hours,liquid_names:names}},
      'sensor.jwdhl_qa_daily_intake_last_7_days':{state:'7700',attributes:{days:dates,liquid_names:names}}}};
    for(const card of document.querySelectorAll('jwdaily-hydration-hourly-card,jwdaily-hydration-weekly-card')){
      card.setConfig({profile:'qa'});card.hass=hass;
    }
   });
   await new Promise(r=>setTimeout(r,140));
   const data=await page.evaluate(()=>{
    return [...document.querySelectorAll('jwdaily-hydration-hourly-card,jwdaily-hydration-weekly-card')].map(c=>{
     const root=c.shadowRoot,card=root.querySelector('ha-card').getBoundingClientRect();
     const unit=root.querySelector('.axis-unit').getBoundingClientRect();
     const ticks=[...root.querySelectorAll('.axis-text')].map(e=>({t:e.textContent,r:e.getBoundingClientRect()}));
     return {height:card.height,width:card.width,foot:card.bottom-root.querySelector('.foot').getBoundingClientRect().bottom,
      unitRight:unit.right,minYTickX:Math.min(...ticks.filter(x=>/^[0-9,]+$/.test(x.t)&&Number(x.t.replaceAll(',',''))%750===0).map(x=>x.r.left)),
      legend:[...root.querySelectorAll('.legend span')].map(e=>e.textContent.trim()),
      note:root.querySelector('.chart-note')?.textContent,
      ticks:ticks.map(x=>x.t),
      colors:[...root.querySelectorAll('rect[fill]:not(.bucket-hit)')].map(e=>({name:e.querySelector('title')?.textContent||'',color:e.getAttribute('fill')}))};
    });
   });
   assert(!errors.length,errors.join('; '));
   assert(data.every(x=>x.width<=width+2&&x.height<480&&x.foot<=18),'Chart overflow/excess height');
   assert(data.every(x=>x.minYTickX>x.unitRight+5),'Y-axis mL overlaps numeric labels');
   assert(data[1].ticks.includes('3,000'),'Adaptive seven-day scale missing');
   assert(data[0].legend[0]==='Coffee (720 mL)'&&data[1].legend[0]==='Coffee','Main-card legend order must be consistent');
   assert(data[1].note.includes('No data')&&data[1].note.includes('recorded zero'),'Missing/zero distinction');
   for(const name of ['Coffee','Tea','Milk']){
    const col=i=>data[i].colors.find(x=>x.name.startsWith(name+':'))?.color;
    assert(col(0)&&col(0)===col(1),'Liquid color inconsistent: '+name);
   }
   await page.$eval('jwdaily-hydration-hourly-card',el=>el.shadowRoot.querySelector('rect[data-chart-bucket="11"]').dispatchEvent(new MouseEvent('click',{bubbles:true,composed:true})));
   assert((await page.$eval('jwdaily-hydration-hourly-card',el=>el.shadowRoot.querySelector('.detail-panel')?.textContent||'')).includes('360 mL'),'Hourly drill-down');
   await page.$eval('jwdaily-hydration-hourly-card',el=>el.shadowRoot.querySelector('[data-chart-close]').click());
   await page.$eval('jwdaily-hydration-weekly-card',el=>el.shadowRoot.querySelector('rect.bucket-hit[data-chart-bucket="0"]').dispatchEvent(new MouseEvent('click',{bubbles:true,composed:true})));
   assert((await page.$eval('jwdaily-hydration-weekly-card',el=>el.shadowRoot.querySelector('.detail-panel')?.textContent||'')).includes('No data recorded'),'Missing day detail');
   await page.$eval('jwdaily-hydration-weekly-card',el=>el.shadowRoot.querySelector('[data-chart-close]').click());
   await page.$eval('jwdaily-hydration-weekly-card',el=>el.shadowRoot.querySelector('rect.bucket-hit[data-chart-bucket="2"]').dispatchEvent(new MouseEvent('click',{bubbles:true,composed:true})));
   assert((await page.$eval('jwdaily-hydration-weekly-card',el=>el.shadowRoot.querySelector('.detail-panel')?.textContent||'')).includes('0 mL'),'Zero day detail');
   console.log('BETA22_CHART_ACCESSIBILITY_PASS',width);
   await page.close();
  }
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
