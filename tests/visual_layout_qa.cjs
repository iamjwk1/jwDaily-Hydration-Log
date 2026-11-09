/* Browser geometry acceptance: uses real Chrome on GitHub's Ubuntu runner. */
const path=require('node:path'),assert=require('node:assert/strict');
const puppeteer=require('puppeteer-core');
(async()=>{
 const binary=process.env.CHROME_PATH||'/usr/bin/google-chrome';
 const browser=await puppeteer.launch({headless:true,executablePath:binary,args:['--no-sandbox','--disable-dev-shm-usage']});
 try{
  for(const width of [888,721,412,360]){
   const page=await browser.newPage();
   await page.setViewport({width:Math.max(1100,width+80),height:1050,deviceScaleFactor:1});
   await page.setContent('<style>body{margin:0}ha-card{display:block}</style><div id="mount"></div>');
   await page.addScriptTag({path:path.resolve(__dirname,'../custom_components/jw_daily_hydration_log/www/jwdaily-hydration-log-card.js')});
   await page.evaluate(width=>{
    if(!customElements.get('ha-card'))customElements.define('ha-card',class extends HTMLElement{connectedCallback(){this.style.display='block';}});
   const holder=document.getElementById('mount');holder.style.width=width+'px';
    const c=document.createElement('jwdaily-hydration-log-card');
    holder.appendChild(c);
    const today=new Date();const z=n=>String(n).padStart(2,'0');const d=`${today.getFullYear()}-${z(today.getMonth()+1)}-${z(today.getDate())}`;
    const records=[
     {id:'a',timestamp:d+'T12:00:00+01:00',liquid_type:'water',volume_ml:220},
     {id:'b',timestamp:d+'T13:00:00+01:00',liquid_type:'coffee',volume_ml:180},
     {id:'c',timestamp:d+'T14:00:00+01:00',liquid_type:'milk',volume_ml:180},
     {id:'d',timestamp:d+'T15:00:00+01:00',liquid_type:'water',volume_ml:500}
    ];
    const defs=['water','coffee','tea','milk','soup','wine','other'].map(id=>({id,name:id,icon_mdi:'mdi:water',icon_svg:'',default_volume_ml:null,hidden:false,custom:false}));
    const summary={date:d,consumed_ml:1080,target_ml:2000,drink_count:4,liquid_breakdown:[
      {liquid_type:'water',volume_ml:720},{liquid_type:'coffee',volume_ml:180},{liquid_type:'milk',volume_ml:180}
    ]};
    const hass={user:{is_admin:true},config:{time_zone:'Europe/Amsterdam'},states:{
      'sensor.jwdhl_jan_willem_daily_target':{state:'2000',attributes:{target_ml:2000}},
      'sensor.jwdhl_jan_willem_consumed_today':{state:'1080',attributes:{consumed_ml:1080}},
      'sensor.jwdhl_jan_willem_drink_count_today':{state:'4',attributes:{}}
     },async callWS(msg){
       if(msg.type==='jw_daily_hydration_log/history')return {date:msg.date,entries:records,day_summary:summary,liquid_types:defs,volume_buttons:[120,150,300,500],total_ml:1080};
       if(msg.type==='jw_daily_hydration_log/capabilities')return {version:'1.1.0-beta.9'};
       throw Error('Unexpected: '+msg.type);
     }};
    c.setConfig({profile:'jan_willem',title:'Vocht intake Jan-Willem'});
    c.hass=hass;
   },width);
   await page.waitForFunction(()=>document.querySelector('jwdaily-hydration-log-card')?.shadowRoot?.querySelectorAll('.history-table tbody tr').length===4);
   const x=await page.evaluate(()=>{
    const root=document.querySelector('jwdaily-hydration-log-card').shadowRoot;
    const rect=x=>{const el=root.querySelector(x);if(!el)return null;const a=el.getBoundingClientRect();return {left:a.left,right:a.right,top:a.top,bottom:a.bottom,width:a.width,height:a.height}};
    const rows=[...root.querySelectorAll('.history-table tbody tr')].map(el=>el.getBoundingClientRect().height);
    return {card:rect('ha-card'),hero:rect('.hero'),glass:rect('.glass-frame .glass'),taken:rect('.taken'),
      chart:rect('.liquid-bars'),button:rect('.add-drink'),date:rect('.date-nav input'),export:rect('.export button'),
      count:rect('.drink-count'),rows,bodyScroll:document.documentElement.scrollWidth,fontsize:getComputedStyle(root.querySelector('.date-nav input')).fontSize};
   });
   const right=x.card.right;
   assert(x.chart.left>=x.glass.left-15,'chart starts too far left');
   for(const part of ['glass','taken','chart','button','date','export']){
     const p=x[part];assert(p&&p.left>=x.card.left-4&&p.right<=right+2,part+' outside card: '+JSON.stringify(p));
   }
   assert(x.button.width<235,'Add button must be compact');
   assert(x.chart.left<x.button.left+10,'Add belongs under chart, not outside it');
   assert(x.rows.every(h=>Math.abs(h-x.rows[0])<1),'History table rows vary in height: '+x.rows);
   assert(Number.parseFloat(x.fontsize)>=18,'History date font too small: '+x.fontsize);
   if(width>=721){
    assert(x.taken.right<=x.glass.left+10,'Blue volume too far from glass');
    assert(x.chart.left>x.glass.left,'Graph not to right of glass');
   }
   await page.screenshot({path:path.resolve(__dirname,'layout-beta9-'+width+'.png'),fullPage:true});
   console.log('VISUAL_GEOMETRY_PASS',width,JSON.stringify(x));
   await page.close();
  }
 }finally{await browser.close();}
})().catch(err=>{console.error(err);process.exitCode=1;});
