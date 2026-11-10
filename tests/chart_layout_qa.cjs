/* Browser acceptance for both chart types; uses actual frontend source. */
const assert=require('node:assert/strict'),path=require('node:path'),puppeteer=require('puppeteer-core');
(async()=>{
 const browser=await puppeteer.launch({headless:true,executablePath:process.env.CHROME_PATH||'/usr/bin/google-chrome',args:['--no-sandbox','--disable-dev-shm-usage']});
 try{
  for(const width of [360,420,720,900]){
   const page=await browser.newPage();
   const errors=[];page.on('pageerror',e=>errors.push(String(e)));
   await page.setViewport({width,height:1050,deviceScaleFactor:1});
   await page.setContent('<style>body{margin:0}ha-card{display:block}</style><jwdaily-hydration-hourly-card></jwdaily-hydration-hourly-card><jwdaily-hydration-weekly-card></jwdaily-hydration-weekly-card>');
   await page.addScriptTag({path:path.resolve(__dirname,'../custom_components/jw_daily_hydration_log/www/jwdaily-hydration-log-card.js')});
   const got=await page.evaluate(()=>{
    const hours=Array.from({length:24},(_,i)=>({hour:String(i).padStart(2,'0')+':00',total_ml:i===11?500:0,liquids:i===11?{coffee:500}:{}}));
    const days=Array.from({length:7},(_,i)=>({date:'2026-11-'+String(i+4).padStart(2,'0'),total_logged_ml:(i+1)*200,liquids:{coffee:(i+1)*200}}));
    const states={'sensor.jwdhl_qa_daily_target':{state:'2000'},'sensor.jwdhl_qa_hourly_intake_today':{state:'500',attributes:{buckets:hours,liquid_names:{coffee:'Coffee'}}},'sensor.jwdhl_qa_daily_intake_last_7_days':{state:'5600',attributes:{days,liquid_names:{coffee:'Coffee'}}}};
    const hass={states,config:{time_zone:'Europe/Amsterdam'}};
    const output=[];
    for(const c of document.querySelectorAll('jwdaily-hydration-hourly-card,jwdaily-hydration-weekly-card')){c.setConfig({profile:'qa'});c.hass=hass;
     const root=c.shadowRoot,card=root.querySelector('ha-card').getBoundingClientRect(),foot=root.querySelector('.foot').getBoundingClientRect();
     output.push({html:root.innerHTML,width:card.width,right:card.right,footRight:foot.right,footBottom:foot.bottom,cardBottom:card.bottom,
      labels:[...root.querySelectorAll('.axis-text')].map(x=>x.textContent),
      columns:root.querySelectorAll('rect').length});
    }
    return output;
   });
   assert.equal(errors.length,0,errors.join('; '));
   assert(got.every(x=>x.width<=width+2&&x.right<=width+2),'Chart horizontal overflow');
   assert(got.every(x=>Math.abs(x.footRight-x.right)<20&&x.cardBottom-x.footBottom<20),'Version not at bottom right');
   assert(got[0].labels.includes('1')&&got[0].labels.includes('24')&&got[0].labels.includes('mL'));
   assert(got[0].html.includes('Coffee (500 mL)')&&got[0].html.includes('Target: 2,000 mL'));
   assert(got[1].labels.includes('7 Nov')&&got[1].html.includes('1,400 mL')&&got[1].labels.includes('mL'));
   assert(got[1].columns>=7);
   console.log('CHART_BROWSER_PASS',width,got.map(x=>({width:x.width,columns:x.columns})));
   await page.close();
  }
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});