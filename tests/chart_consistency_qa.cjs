/* beta.18: category color consistency, responsive axes and scale; real Chrome. */
const assert=require('node:assert/strict'),path=require('node:path');
const puppeteer=require('puppeteer-core');
(async()=>{
 const browser=await puppeteer.launch({headless:true,executablePath:process.env.CHROME_PATH||'/usr/bin/google-chrome',args:['--no-sandbox','--disable-dev-shm-usage']});
 try{
  for(const width of [360,720,900]){
   const page=await browser.newPage();let errors=[];page.on('pageerror',e=>errors.push(String(e)));
   await page.setViewport({width,height:1120,deviceScaleFactor:1});
   await page.setContent('<style>body{margin:0;font-family:Roboto,Arial,sans-serif}ha-card{display:block}</style><jwdaily-hydration-hourly-card></jwdaily-hydration-hourly-card><jwdaily-hydration-weekly-card></jwdaily-hydration-weekly-card>');
   await page.addScriptTag({path:path.resolve(__dirname,'../custom_components/jw_daily_hydration_log/www/jwdaily-hydration-log-card.js')});
   await page.evaluate(()=>{
    const names={coffee:'Coffee',tea:'Tea',milk:'Milk',water_cup:'Water (beker)',water_glass:'Water (glas)'};
    const hours=Array.from({length:24},(_,i)=>({hour:String(i).padStart(2,'0')+':00',total_ml:0,liquids:{}}));
    for(const [i,k,v] of [[11,'coffee',360],[14,'tea',540],[15,'water_glass',500],[16,'water_cup',180],[18,'coffee',360],[21,'milk',180],[22,'tea',180]]){
     hours[i].total_ml+=v;hours[i].liquids[k]=(hours[i].liquids[k]||0)+v;
    }
    const days=Array.from({length:7},(_,i)=>({date:'2026-11-'+String(i+4).padStart(2,'0'),total_logged_ml:0,liquids:{}}));
    days[4]={date:'2026-11-08',total_logged_ml:2550,liquids:{water_cup:1800,tea:180,milk:180,coffee:390}};
    days[5]={date:'2026-11-09',total_logged_ml:1900,liquids:{water_glass:1200,tea:200,coffee:500}};
    days[6]={date:'2026-11-10',total_logged_ml:2300,liquids:{water_glass:500,tea:720,milk:180,water_cup:180,coffee:720}};
    const hass={config:{time_zone:'Europe/Amsterdam'},states:{
     'sensor.jwdhl_qa_daily_target':{state:'2000'},
     'sensor.jwdhl_qa_hourly_intake_today':{state:'2300',attributes:{buckets:hours,liquid_names:names}},
     'sensor.jwdhl_qa_daily_intake_last_7_days':{state:'6750',attributes:{days,liquid_names:names}}
    }};
    for(const card of document.querySelectorAll('jwdaily-hydration-hourly-card,jwdaily-hydration-weekly-card')){
     card.setConfig({profile:'qa'});card.hass=hass;
    }
   });
   await new Promise(r=>setTimeout(r,180));
   const result=await page.evaluate(()=>{
    return [...document.querySelectorAll('jwdaily-hydration-hourly-card,jwdaily-hydration-weekly-card')].map(card=>{
     const root=card.shadowRoot;
     const c=root.querySelector('ha-card').getBoundingClientRect(),foot=root.querySelector('.foot').getBoundingClientRect();
     return {height:c.height,width:c.width,bottom:c.bottom,footerGap:c.bottom-foot.bottom,overflow:document.documentElement.scrollWidth,
      ticks:[...root.querySelectorAll('.axis-text')].map(el=>el.textContent.trim()),
      legend:[...root.querySelectorAll('.legend span')].map(el=>el.textContent.trim()),
      bars:[...root.querySelectorAll('rect')].map(el=>({label:el.querySelector('title')?.textContent||'',fill:el.getAttribute('fill')}))};
    });
   });
   assert.equal(errors.length,0,errors.join('; '));
   assert(result.every(x=>x.width<=width+2&&x.overflow<=width+2),'Chart horizontally overflowed');
   assert(result.every(x=>x.footerGap<=16),'Footer too far above card bottom');
   assert(result.every(x=>x.height<500),'Chart cards must not have excess vertical whitespace');
   assert(result[0].ticks.includes('1')&&result[0].ticks.includes('24'),'Hour axis not 1..24');
   assert(result[1].ticks.includes('3,000'),'7-day axis should end at 3,000 mL for max 2,550 mL');
   assert(result[1].ticks.includes('10 Nov'),'Seven-day date labels missing');
   assert(result[0].legend.includes('Coffee (720 mL)')&&result[0].legend.includes('Tea (720 mL)'),'Hourly per-liquid total legend missing');
   for(const name of ['Coffee','Tea','Milk','Water (beker)','Water (glas)']){
    const color=i=>result[i].bars.find(v=>v.label.startsWith(name+':'))?.fill;
    assert(color(0)&&color(0)===color(1),'Inconsistent color across charts for '+name);
   }
   await page.screenshot({path:path.resolve(__dirname,'layout-beta21-chart-'+width+'.png'),fullPage:true});
   console.log('CHART_CONSISTENCY_PASS',width,JSON.stringify(result.map(x=>({height:x.height,footerGap:x.footerGap,ticks:x.ticks.slice(0,5)}))));
   await page.close();
  }
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
