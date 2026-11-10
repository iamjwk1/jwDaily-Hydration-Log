/* Browser geometry acceptance: uses real Chrome on GitHub's Ubuntu runner. */
const path=require('node:path'),assert=require('node:assert/strict');
const puppeteer=require('puppeteer-core');
(async()=>{
 const binary=process.env.CHROME_PATH||'/usr/bin/google-chrome';
 const browser=await puppeteer.launch({headless:true,executablePath:binary,args:['--no-sandbox','--disable-dev-shm-usage']});
 try{
  for(const width of [888,721,560,412,360]){
   const page=await browser.newPage();
   await page.setViewport({width:width+50,height:1050,deviceScaleFactor:1});
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
       if(msg.type==='jw_daily_hydration_log/capabilities')return {version:'1.1.0-beta.12'};
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
      count:rect('.drink-count'),rows,bodyScroll:document.documentElement.scrollWidth,
      fontsize:getComputedStyle(root.querySelector('.date-nav input')).fontSize,
      intakeFont:getComputedStyle(root.querySelector('.taken')).fontSize,
      activeButtons:[...root.querySelectorAll('button.secondary:not(:disabled)')].length,
      statusVisible:!!root.querySelector('.root > .status'),
      barVolumes:[...root.querySelectorAll('.bar-line strong')].map(el=>{const q=el.getBoundingClientRect();return{left:q.left,right:q.right}}),
      history:rect('.history')};
   });
   console.log('VISUAL_GEOMETRY',width,JSON.stringify(x));
   const right=x.card.right;
   if(width>=560)assert(x.chart.left>=x.glass.right-1,'chart must remain to the RIGHT of glass at card width '+width);
 else assert(x.chart.top>=x.glass.bottom,'narrow cards should stack the chart below glass');
   for(const part of ['glass','taken','chart','button','date','export']){
     const p=x[part];assert(p&&p.left>=x.card.left-4&&p.right<=right+2,part+' outside card: '+JSON.stringify(p));
   }
   assert(x.button.width<235,'Add button must be compact');
   assert(x.chart.left<x.button.left+10,'Add belongs under chart, not outside it');
   assert(x.rows.every(h=>Math.abs(h-38)<1),'History rows not uniformly 38px: '+x.rows);
   assert(Number.parseFloat(x.fontsize)>=18,'History date too small: '+x.fontsize);
   assert(Math.abs(parseFloat(x.intakeFont)-24)<.2,'Blue intake must be exactly 24px on all widths: '+x.intakeFont);
   assert(x.activeButtons>=2,'Enabled secondary controls are unexpectedly absent/disabled');
   assert(!x.statusVisible,'Permanent status message should not consume card height');
   assert(x.count.top>=x.glass.bottom-1 && x.count.top<=x.glass.bottom+12,'Drink moments must stay directly under glass');
   assert(x.export.left>=x.history.left-2 && x.export.left<=x.history.left+2,'Excel button not aligned left with history');
   assert(x.button.bottom<=x.hero.bottom+2 && x.hero.bottom-x.button.bottom<15,'Add drink too high above hero bottom');
   for(const bar of x.barVolumes)assert(bar.left>=x.chart.left && bar.right<=x.card.right+1,'Chart volume clipped');
   if(width>=560){
    assert(x.taken.right<=x.glass.left-6,'Blue intake overlaps or is too close to glass: '+JSON.stringify({taken:x.taken,glass:x.glass}));
    assert(x.glass.left-x.taken.right<=18,'Blue intake too far from glass');
    assert(x.chart.left>=x.glass.right,'Graph not to right of glass');
   }
   // Modal measured after clicking the actual button; no backend mutation.
   await page.evaluate(()=>document.querySelector('jwdaily-hydration-log-card').shadowRoot.querySelector('[data-action="new"]').click());
   await page.waitForFunction(()=>!!document.querySelector('jwdaily-hydration-log-card')?.shadowRoot?.querySelector('.dialog-drink'));
   const normal=await page.evaluate(()=>{
    const root=document.querySelector('jwdaily-hydration-log-card').shadowRoot;
    const color=sel=>getComputedStyle(root.querySelector(sel)).backgroundColor;
    const liquid=root.querySelector('.liquid-choice'),amount=root.querySelector('.volume-choices .amount');
    const font=el=>getComputedStyle(el).fontSize;
    return {add:color('.add-drink'),go:color('[data-action="date-go"]'),
      liquid:color('.liquid-choice'),volume:color('.volume-choices .amount'),
      manage:color('[data-action="manage-liquids"]'),date:color('.date-trigger'),
      liquidFont:font(liquid),volumeFont:font(amount),undo:!!root.querySelector('[data-action="undo"]'),
      dialogWidth:root.querySelector('.dialog-drink').getBoundingClientRect().width,
      liquidHeight:liquid.getBoundingClientRect().height,
      amountHeight:amount.getBoundingClientRect().height};
   });
   const blue='rgb(179, 229, 252)';
   for(const key of ['add','go','liquid','volume'])assert.equal(normal[key],blue,key+' button background does not equal #B3E5FC');
   assert.equal(normal.manage,'rgb(238, 238, 238)','Manage controls should be #EEEEEE');
   assert.equal(normal.date,'rgb(255, 255, 255)','Date picker must be #FFFFFF');
   assert.equal(normal.liquidFont,normal.volumeFont,'Liquid/amount font sizes differ');
   assert(normal.liquidHeight<43&&normal.amountHeight<43,'Quick selection buttons are too tall');
   assert(!normal.undo,'Undo button still exists');
   await page.evaluate(()=>document.querySelector('jwdaily-hydration-log-card').shadowRoot.querySelector('[data-action="manage-liquids"]').click());
   await page.waitForFunction(()=>!!document.querySelector('jwdaily-hydration-log-card')?.shadowRoot?.querySelector('.dialog-manage-liquids'));
   const liquids=await page.evaluate(()=>{
     const root=document.querySelector('jwdaily-hydration-log-card').shadowRoot;
     const dlg=root.querySelector('.dialog-manage-liquids'),rows=[...root.querySelectorAll('.saved-liquid')];
     const rc=x=>{const a=x.getBoundingClientRect();return{left:a.left,right:a.right,width:a.width,height:a.height,top:a.top,bottom:a.bottom}};
     return {dialog:rc(dlg),rows:rows.map(rc),actions:rows.flatMap(x=>[...x.querySelectorAll('button')].map(rc)),
       footer:rc(root.querySelector('.manage .dialog-actions')),viewport:innerWidth};
   });
   assert(liquids.dialog.width<=555+1,'Liquid manager modal too wide');
   assert(liquids.rows.every(r=>r.height<=76),'Liquid manager rows have excess height');
   assert(liquids.actions.every(a=>a.right<=liquids.dialog.right+1),'Liquid manager button overflow');
   await page.evaluate(()=>{
     const c=document.querySelector('jwdaily-hydration-log-card');
     c._manageOpen=false;c._openVolumeManager();
   });
   await page.waitForFunction(()=>!!document.querySelector('jwdaily-hydration-log-card')?.shadowRoot?.querySelector('.dialog-manage-volumes'));
   const volumes=await page.evaluate(()=>{
     const root=document.querySelector('jwdaily-hydration-log-card').shadowRoot;
     const dlg=root.querySelector('.dialog-manage-volumes'),rows=[...root.querySelectorAll('.volume-edit-row')];
     const rect=e=>{let r=e.getBoundingClientRect();return {left:r.left,right:r.right,height:r.height,width:r.width}};
     return {dialog:rect(dlg),rows:rows.map(rect),buttons:rows.flatMap(x=>[...x.querySelectorAll('button')].map(rect))};
   });
   assert(volumes.dialog.width<=451,'Volume manager too wide');
   assert(volumes.rows.every(r=>r.height<=44),'Volume manager must be one 38-44px line per volume');
   assert(volumes.buttons.every(a=>a.right<=volumes.dialog.right+1),'Volume button clipped outside dialog');
   console.log('VISUAL_MODAL_PASS',width,JSON.stringify({normal,liquids,volumes}));
   await page.screenshot({path:path.resolve(__dirname,'layout-beta12-'+width+'.png'),fullPage:true});
   console.log('VISUAL_GEOMETRY_PASS',width,JSON.stringify(x));
   await page.close();
  }
 }finally{await browser.close();}
})().catch(err=>{console.error(err);process.exitCode=1;});
