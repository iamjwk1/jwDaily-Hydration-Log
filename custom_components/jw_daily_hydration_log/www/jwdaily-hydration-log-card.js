/* jwDaily Hydration Log v1.0.2. Independent Lovelace card.
 * Derived from the MIT-licensed Personal Hydration Manager by Loryan Strant.
 * Copyright (c) 2026 Loryan Strant (upstream); 2026 jwDaily Hydration Log contributors.
 */
const DHL_TAG = 'jwdaily-hydration-log-card';
const DHL_EDITOR = 'jwdaily-hydration-log-card-editor';
const DHL_DEFAULTS = {profile:'', title:'', show_title:true, show_cup:true,show_countdown:true,
  show_manual:true,show_history:true,show_export:true,unit:'mL',quick_add:[200,300,500]};
const DHL_OZ=29.5735;
const dhlEscape=(s)=>String(s??'').replace(/[&<>"']/g,ch=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
const dhlNum=(value)=>Number.isFinite(Number(value))?Number(value):0;
const dhlFmt=(value,unit='mL')=>unit==='fl_oz'?`${(value/DHL_OZ).toFixed(1)} fl oz`:value>=1000?`${(value/1000).toFixed(2)} L`:`${Math.round(value)} mL`;
const dhlQuick=(input)=>{const a=(Array.isArray(input)?input:[]).map(x=>Number(x)).filter(x=>Number.isFinite(x)&&x>0&&x<=100000);return a.length?a:[200,300,500];};

class DailyHydrationLogCard extends HTMLElement {
  constructor(){
    super();this.attachShadow({mode:'open'});this._hass=null;this._config=null;this._customOpen=false;
    this._customValue='';this._error='';this._status='';this._history=null;this._historyKey='';
    this._pendingHistory=false;this._refreshAgain=false;this._busy=false;this._lastRenderKey='';this._lastSensorKey='';this._refreshTimer=null;
    this.shadowRoot.addEventListener('click',e=>this._onClick(e));
    this.shadowRoot.addEventListener('input',e=>{if(e.target?.id==='dhl-custom-value')this._customValue=e.target.value;});
    this.shadowRoot.addEventListener('keydown',e=>{
      if(e.target?.id!=='dhl-custom-value')return;
      if(e.key==='Enter'){e.preventDefault();this._confirmCustom();}
      if(e.key==='Escape'){e.preventDefault();this._closeCustom();}
    });
  }
  static getStubConfig(hass){
    const profiles=Object.keys(hass?.states||{}).filter(x=>x.startsWith('sensor.jwdhl_')&&x.endsWith('_daily_target'));
    return {type:`custom:${DHL_TAG}`,profile:profiles[0]?.slice(11,-13)||'',title:'Vocht intake',
      show_title:true,show_cup:true,show_countdown:true,show_manual:true,
      show_history:true,show_export:true,unit:'mL',quick_add:[120,150,300,500]};
  }
  static async getConfigElement(){return document.createElement(DHL_EDITOR);}
  setConfig(config){if(!config)throw new Error('Missing configuration');
    this._config={...DHL_DEFAULTS,...config,quick_add:dhlQuick(config.quick_add)};
    this._history=null;this._historyKey='';this._lastRenderKey='';this._lastSensorKey='';this._render();this._fetchHistory();
  }
  set hass(hass){
    this._hass=hass;
    const p=this._config?.profile;
    if(p){
      const state=hass?.states?.[`sensor.jwdhl_${p}_manual_consumed`];
      const count=hass?.states?.[`sensor.jwdhl_${p}_drink_count_today`];
      const key=JSON.stringify([state?.attributes?.manual_consumed_ml,count?.state,new Date().toDateString()]);
      if(key!==this._lastSensorKey){this._lastSensorKey=key;this._fetchHistory();}
    }
    this._render();
    if(!this._refreshTimer){this._refreshTimer=setInterval(()=>{
      if(this._config&&this._hass){
        const key=new Date().toDateString();
        if(this._lastLocalDate!==key){this._lastLocalDate=key;this._fetchHistory();}
        this._render();
      }
    },30000);}
  }
  disconnectedCallback(){if(this._refreshTimer){clearInterval(this._refreshTimer);this._refreshTimer=null;}}
  getCardSize(){return 4+(this._config?.show_history!==false?3:0);}
  _state(key){return this._hass?.states?.[`sensor.jwdhl_${this._config.profile}_${key}`];}
  _millilitres(key,attr){const entity=this._state(key);if(!entity)return 0;
    const exact=entity.attributes?.[attr];if(exact!==undefined&&exact!==null&&Number.isFinite(Number(exact)))return Number(exact);
    const value=dhlNum(entity.state),unit=entity.attributes?.unit_of_measurement;
    return unit==='L'?value*1000:unit==='fl oz'?value*DHL_OZ:value;}
  _showError(message){this._error=String(message?.message||message||'Unknown error');this._status='';this._render(true);}
  async _fetchHistory(){
    if(!this._hass||!this._config?.profile||!this._config.show_history)return;
    if(this._pendingHistory){this._refreshAgain=true;return;}
    this._pendingHistory=true;
    const profile=this._config.profile;
    try{
      const result=await this._hass.callWS({type:'jw_daily_hydration_log/history',profile});
      if(this._config?.profile===profile){this._history=result;this._historyKey=result.date;this._render();}
    }catch(err){if(this._config?.profile===profile)this._showError(err);}
    finally{
      this._pendingHistory=false;
      if(this._refreshAgain){this._refreshAgain=false;this._fetchHistory();}
    }
  }
  async _onClick(e){const btn=e.target?.closest?.('button[data-action]');if(!btn||this._busy)return;
    const action=btn.dataset.action;
    if(action==='custom'){this._customOpen=true;this._customValue='';this._error='';this._render(true);
      requestAnimationFrame(()=>this.shadowRoot.querySelector('#dhl-custom-value')?.focus());return;}
    if(action==='cancel'){this._closeCustom();return;}
    if(action==='confirm'){await this._confirmCustom();return;}
    if(action==='quick'){await this._add(Number(btn.dataset.amount));return;}
    if(action==='export'){await this._export();return;}
  }
  _closeCustom(){this._customOpen=false;this._customValue='';this._error='';this._render(true);}
  async _confirmCustom(){const value=Number(this._customValue);
    if(!Number.isFinite(value)||value<=0){this._showError('Enter a number greater than zero.');return;}
    const inMl=this._config.unit==='fl_oz'?value*DHL_OZ:value;
    if(inMl>100000){this._showError('Maximum volume is 100,000 mL.');return;}
    await this._add(inMl);
    if(!this._error)this._closeCustom();
  }
  async _add(ml){
    if(!Number.isFinite(ml)||ml<=0){this._showError('Invalid drink volume');return;}
    this._busy=true;this._error='';this._status='Recording drink…';this._render(true);
    try{
      await this._hass.callService('jw_daily_hydration_log','log_drink',{
        profile:this._config.profile,volume:ml,unit:'mL',origin:'dashboard'});
      this._status=`Added ${dhlFmt(ml,'mL')}`;
      this._history=null;
      await this._fetchHistory();
    }catch(err){this._showError(err);}
    finally{this._busy=false;this._render(true);}
  }
  async _export(){
    this._busy=true;this._status='Preparing Excel export…';this._error='';this._render(true);
    try{
      const result=await this._hass.callWS({type:'jw_daily_hydration_log/export'});
      const raw=atob(result.base64);
      const data=new Uint8Array(raw.length);
      for(let i=0;i<raw.length;i++)data[i]=raw.charCodeAt(i);
      const blob=new Blob([data],{type:result.mime_type});
      const url=URL.createObjectURL(blob);
      const link=document.createElement('a');link.href=url;
      link.download=result.filename||'jwDaily Hydration Log - All Data.xlsx';
      this.shadowRoot.appendChild(link);link.click();link.remove();
      // Release the object URL after the browser has initiated the download.
      setTimeout(()=>URL.revokeObjectURL(url),15000);
      this._status='Excel export started';
    }catch(err){this._showError(err);}
    finally{this._busy=false;this._render(true);}
  }
  _cup(pct){
    const progress=Math.min(100,Math.max(0,pct));
    const y=192-Math.max(0,(progress/100)*173);
    const has=progress>=0.5;
    return `<div class="dhl-cup-wrap"><svg class="dhl-cup" viewBox="0 0 180 215" role="img" aria-label="${progress.toFixed(0)} percent of daily target">
      <defs><clipPath id="dhl-cup-clip"><path d="M29 16 H151 L140 186 Q139 197 128 197 H52 Q41 197 40 186 Z"/></clipPath>
        <linearGradient id="dhl-wave-grad" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#75cbff"/><stop offset="1" stop-color="#167fcb"/></linearGradient></defs>
      <path d="M29 16 H151 L140 186 Q139 197 128 197 H52 Q41 197 40 186 Z" fill="none" stroke="currentColor" stroke-width="2.6"/>
      ${has?`<g clip-path="url(#dhl-cup-clip)"><rect x="29" y="${y}" width="122" height="215" fill="url(#dhl-wave-grad)"/>
        <path d="M29 ${y} Q58 ${y-3} 90 ${y} T151 ${y} V215 H29 Z" fill="#75cbff" opacity=".45"/></g>`:''}
      <text x="90" y="121" text-anchor="middle" font-size="30" font-weight="700" fill="var(--primary-text-color,#182538)" stroke="var(--card-background-color,#fff)" stroke-width="2" paint-order="stroke">${progress.toFixed(0)}%</text></svg></div>`;
  }
  _historyHtml(){
    if(!this._config.show_history)return '';
    const rows=Array.isArray(this._history?.entries)?[...this._history.entries].reverse():[];
    const table=rows.length?`<table aria-label="Today's drink moments"><thead><tr><th>Time</th><th>Volume</th></tr></thead><tbody>${rows.map(r=>{
      let time='–';try{time=new Date(r.timestamp).toLocaleTimeString('nl-NL',{hour:'2-digit',minute:'2-digit',second:'2-digit'});}catch{}
      return `<tr><td>${dhlEscape(time)}</td><td class="num">+${dhlFmt(Number(r.volume_ml),this._config.unit)}</td></tr>`;
    }).join('')}</tbody></table>`:`<div class="muted empty">${this._history?'No drinks recorded today.':'Loading drink history…'}</div>`;
    const total=this._history?dhlFmt(this._history.total_ml,this._config.unit):'—';
    return `<section class="dhl-history"><div class="dhl-row between"><h3>Today's intake</h3><span class="muted">${rows.length} entries</span></div>
      <div class="dhl-table-wrap">${table}</div><div class="dhl-row between history-total"><strong>Total logged today</strong><strong>${total}</strong></div></section>`;
  }
  _render(force=false){
    if(!this._config||!this._hass)return;
    if(this._customOpen&&!force)return; // Keep the live input node and caret intact.
    const name=this._config.title||this._config.profile||'jwDaily Hydration Log';
    const target=this._millilitres('daily_target','target_ml');
    const consumed=this._millilitres('consumed_today','consumed_ml');
    const remaining=Math.max(0,target-consumed);
    const paceEntity=this._state('hourly_pace');
    const pace=dhlNum(paceEntity?.state)*(paceEntity?.attributes?.unit_of_measurement==='L/h'?1000:paceEntity?.attributes?.unit_of_measurement==='fl_oz/h'?DHL_OZ:1);
    const pct=target>0?Math.min(100,Math.max(0,consumed/target*100)):0;
    const stateKey=JSON.stringify([name,target,consumed,remaining,pace,pct,this._config,
      this._history, this._error,this._status,this._busy,this._customOpen]);
    if(!force&&stateKey===this._lastRenderKey)return;
    this._lastRenderKey=stateKey;
    const quick=this._config.show_manual!==false?`<div class="dhl-quick">${dhlQuick(this._config.quick_add).map(n=>
      `<button type="button" data-action="quick" data-amount="${n}" ${this._busy?'disabled':''}>+ ${dhlFmt(n,this._config.unit)}</button>`).join('')}
      ${this._customOpen?`<div class="dhl-custom"><label><input id="dhl-custom-value" type="number" min="0.01" step="any" inputmode="decimal" aria-label="Custom volume" value="${dhlEscape(this._customValue)}"/> ${this._config.unit==='fl_oz'?'fl oz':'mL'}</label>
        <button data-action="confirm" ${this._busy?'disabled':''}>Add</button><button class="subtle" data-action="cancel">Cancel</button></div>`:
        `<button class="subtle" data-action="custom">+ Custom…</button>`}</div>`:'';
    this.shadowRoot.innerHTML=`<style>
      :host{display:block} ha-card{overflow:hidden}.dhl-root{padding:16px;display:flex;flex-direction:column;gap:12px;color:var(--primary-text-color)}
      header{display:flex;align-items:center;justify-content:space-between;gap:8px} header h2{font-size:1.12rem;margin:0;font-weight:650}
      header .version{font-size:.7rem;color:var(--secondary-text-color)} .dhl-cup-wrap{display:flex;justify-content:center}
      .dhl-cup{width:164px;height:190px}.dhl-total{text-align:center;font-size:1.02rem;font-variant-numeric:tabular-nums}
      .dhl-total strong{font-size:1.17rem}.muted{color:var(--secondary-text-color);font-size:.82rem}
      .dhl-pace{display:flex;justify-content:space-around;gap:12px;border-block:1px solid var(--divider-color);padding:10px 0}
      .dhl-pace>div{text-align:center;flex:1}.dhl-pace strong{font-size:1.17rem;display:block}
      .dhl-quick{display:flex;justify-content:center;gap:8px;flex-wrap:wrap}
      button{font:inherit;font-size:.87rem;border:none;border-radius:18px;background:var(--primary-color,#2196f3);color:white;padding:8px 13px;cursor:pointer}
      button:disabled{opacity:.55;cursor:wait}.subtle{background:var(--secondary-background-color,#e8eef4);color:var(--primary-text-color)}
      .dhl-custom{display:flex;flex-wrap:wrap;gap:8px;align-items:center;justify-content:center;width:100%}
      .dhl-custom label{border:1px solid var(--divider-color);border-radius:15px;padding:4px 8px;font-size:.8rem}
      .dhl-custom input{max-width:100px;background:transparent;color:var(--primary-text-color);border:0;font:inherit}
      .dhl-history{border-top:1px solid var(--divider-color);padding-top:12px}.dhl-row{display:flex;align-items:center;gap:8px}
      .between{justify-content:space-between}.dhl-history h3{font-size:.99rem;margin:0}
      .dhl-table-wrap{max-height:255px;overflow:auto;margin-top:9px}table{width:100%;border-collapse:collapse;font-variant-numeric:tabular-nums;font-size:.91rem}
      th{text-align:left;color:var(--secondary-text-color);font-size:.8rem;font-weight:500}td,th{padding:6px 4px;border-bottom:1px solid var(--divider-color)}
      td.num,th:last-child{text-align:right}.empty{text-align:center;padding:13px 0}.history-total{margin-top:8px;font-size:.91rem}
      .dhl-error{color:var(--error-color,#b00020);font-size:.85rem}.dhl-status{font-size:.82rem;color:var(--secondary-text-color)}
      .dhl-export{display:flex;justify-content:center;border-top:1px solid var(--divider-color);padding-top:11px}
      .dhl-export button{background:var(--secondary-background-color,#e8eef4);color:var(--primary-text-color)}
      </style><ha-card><div class="dhl-root">
      ${this._config.show_title!==false?`<header><h2>${dhlEscape(name)}</h2><span class="version">v1.0.2</span></header>`:''}
      ${this._config.show_cup!==false?this._cup(pct):`<div class="dhl-total">${pct.toFixed(0)}%</div>`}
      <div class="dhl-total"><strong>${dhlFmt(consumed,this._config.unit)}</strong><span class="muted"> / ${dhlFmt(target,this._config.unit)}</span></div>
      ${this._config.show_countdown!==false?`<div class="dhl-pace"><div><strong>${dhlFmt(remaining,this._config.unit)}</strong><span class="muted">left today</span></div><div><strong>${dhlFmt(pace,this._config.unit)}/h</strong><span class="muted">recommended pace</span></div></div>`:''}
      ${quick}${this._error?`<div role="alert" class="dhl-error">${dhlEscape(this._error)}</div>`:''}
      ${this._status?`<div aria-live="polite" class="dhl-status">${dhlEscape(this._status)}</div>`:''}
      ${this._historyHtml()}
      ${this._config.show_export!==false&&this._hass.user?.is_admin?`<div class="dhl-export"><button data-action="export" ${this._busy?'disabled':''}>Export all data to Excel (.xlsx)</button></div>`:''}
      </div></ha-card>`;
  }
}

const DHL_Q_PRESETS=[120,150,200,250,300,500,750,1000];
const DHL_LABELS={profile:'Person',title:'Card title',show_title:'Show the title',show_cup:'Show the cup',
  show_countdown:'Show countdown and pace',show_manual:'Show volume buttons',show_history:'Show today\'s drink history',
  show_export:'Show Excel export (administrators)',unit:'Display units',quick_add:'Volume buttons (always mL)'};
function dhlEditorSchema(profiles){return [
  {name:'profile',selector:{select:{mode:'dropdown',options:profiles}}},
  {name:'title',selector:{text:{}}},
  {name:'',type:'grid',schema:['show_title','show_cup','show_countdown','show_manual','show_history','show_export'].map(name=>({name,selector:{boolean:{}}}))},
  {name:'unit',selector:{select:{options:[{value:'mL',label:'Metric (mL/L)'},{value:'fl_oz',label:'Imperial (fl oz)'}]}}},
  {name:'quick_add',selector:{select:{multiple:true,custom_value:true,options:DHL_Q_PRESETS.map(n=>({value:String(n),label:String(n)}))}}},
];}
class DailyHydrationLogCardEditor extends HTMLElement {
  constructor(){super();this._config=null;this._hass=null;this._form=null;}
  setConfig(c){this._config={...DHL_DEFAULTS,...c};this._render();}
  connectedCallback(){
    if(!customElements.get('ha-form')){const tile=customElements.get('hui-tile-card');
      if(tile?.getConfigElement)tile.getConfigElement();}
  }
  set hass(h){this._hass=h;this._render();}
  _profiles(){return Object.keys(this._hass?.states||{}).filter(x=>x.startsWith('sensor.jwdhl_')&&x.endsWith('_daily_target'))
    .sort().map(id=>({value:id.slice('sensor.jwdhl_'.length,-'_daily_target'.length),
      label:(this._hass.states[id].attributes?.friendly_name||id).replace(/ Daily target$/,'')}));}
  _render(){if(!this._config||!this._hass)return;
    if(!this._form){const form=document.createElement('ha-form');form.computeLabel=s=>DHL_LABELS[s.name]||'';
      form.addEventListener('value-changed',e=>{e.stopPropagation();const data={...e.detail.value};
        if(!data.profile&&this._config.profile)data.profile=this._config.profile;
        data.quick_add=dhlQuick(data.quick_add);this._config=data;
        this.dispatchEvent(new CustomEvent('config-changed',{detail:{config:data},bubbles:true,composed:true}));});
      this.appendChild(form);this._form=form;}
    this._form.hass=this._hass;this._form.schema=dhlEditorSchema(this._profiles());
    this._form.data={...this._config,quick_add:dhlQuick(this._config.quick_add).map(String)};
  }
}
if(!customElements.get(DHL_TAG))customElements.define(DHL_TAG,DailyHydrationLogCard);
if(!customElements.get(DHL_EDITOR))customElements.define(DHL_EDITOR,DailyHydrationLogCardEditor);
window.customCards=window.customCards||[];
if(!window.customCards.some(c=>c.type===DHL_TAG))window.customCards.push({type:DHL_TAG,name:'jwDaily Hydration Log',
  description:'Daily drink tracking with timestamped history and Excel export',preview:true});
console.info('DAILY-HYDRATION-LOG-CARD v1.0.2');
