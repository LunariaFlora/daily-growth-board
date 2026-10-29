'use strict';
const $=s=>document.querySelector(s), $$=s=>[...document.querySelectorAll(s)];
const PREVIEW=new URLSearchParams(location.search).has('preview');
if(PREVIEW)document.body.classList.add('preview-page');
const paths={sun:'M12 3v2m0 14v2M3 12h2m14 0h2M5.6 5.6l1.4 1.4m10 10 1.4 1.4M5.6 18.4 7 17M17 7l1.4-1.4M16 12a4 4 0 1 1-8 0 4 4 0 0 1 8 0',moon:'M20.8 13A9 9 0 0 1 11 3.2 9 9 0 1 0 20.8 13Z',plus:'M12 5v14M5 12h14',check:'m5 12 4 4L19 6',trash:'M4 7h16M9 7V4h6v3M7 7l1 13h8l1-13M10 10v7m4-7v7',settings:'M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8M12 2v3m0 14v3M2 12h3m14 0h3M5 5l2 2m10 10 2 2M5 19l2-2M17 7l2-2',palette:'M12 3a9 9 0 0 0 0 18h1a2 2 0 0 0 1-3.7c-1.2-.7-.6-2.3.7-2.3H18a3 3 0 0 0 3-3 9 9 0 0 0-9-9ZM7 10h.01M10 6h.01M16 7h.01M18 11h.01',sync:'M20 7v5h-5M4 17v-5h5M6 6a8 8 0 0 1 13 3M5 15a8 8 0 0 0 13 3',book:'M3 4h6l3 2 3-2h6v15h-6l-3 2-3-2H3ZM12 6v15',close:'m6 6 12 12M18 6 6 18',arrow:'M5 12h14m-6-6 6 6-6 6',download:'M12 3v12m-5-5 5 5 5-5M4 16v5h16v-5'};
function icon(name){return `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="${paths[name]||paths.plus}"/></svg>`}
$$('[data-icon]').forEach(el=>el.innerHTML=icon(el.dataset.icon));
let state, day, next, token, serverToday, timer, saving=false, blocked=false;
const mode={tech:'today',project:'today',school:'today'}, queue=new Map(), baselines=new Map();
const cols=['tech','project','school'];
const status=$('#save-status');
function message(text,error=false){status.textContent=text;status.dataset.error=String(error);const toast=$('#error-toast');if(toast){toast.textContent=error?text:'';toast.hidden=!error}}
function draftKey(date,col,field){return `growth-draft:${date}:${col}:${field}`}
function dataFor(date){return date===day?state.entry:state.nextEntry}
async function api(path,body){if(PREVIEW&&body)throw Error('预览不写入记录');if(body&&!state?.capabilities?.includes('anchored-sync'))throw Error('请运行「更新并打开.cmd」启用固定区域同步，再继续记录。');const r=await fetch(path,body?{method:'POST',headers:{'Content-Type':'application/json','X-Board-Token':token},body:JSON.stringify(body)}:{});const j=await r.json();if(!r.ok)throw Object.assign(Error(j.error||'保存失败'),{status:r.status});return j}
function enqueue(date,col,field,value){const key=draftKey(date,col,field);dataFor(date)[field][col]=structuredClone(value);const item={day:date,column:col,field,value:structuredClone(value),owner:day};queue.set(key,item);try{localStorage.setItem(key,JSON.stringify({...item,base:baselines.get(key)}))}catch{message('浏览器草稿空间不足，请保持页面打开直至保存成功',true)}clearTimeout(timer);timer=setTimeout(flush,650);message('正在保存…')}
async function flush(){
 if(saving||blocked||!state?.capabilities?.includes('anchored-sync'))return; saving=true;
 try{while(queue.size){const [key,item]=queue.entries().next().value;await api('/api/entry',{...item,base:baselines.get(key)});baselines.set(key,structuredClone(item.value));if(queue.get(key)===item){queue.delete(key);localStorage.removeItem(key)}}message('已保存 · 日记将在停笔后更新原位置');}
 catch(e){if(e.status===409){blocked=true;$('#conflict').hidden=false}message(e.message+'（草稿保留在本机）',true)}finally{saving=false}
}
function taskDate(col){return mode[col]==='tomorrow'?next:day}
function taskList(col){const date=taskDate(col);return dataFor(date).tasks[col]}
function renderLane(col){
 const lane=$(`[data-column="${col}"]`), isTomorrow=mode[col]==='tomorrow';
 lane.querySelector('.review-wrap').hidden=isTomorrow;
 lane.querySelector('.lane-body').classList.toggle('is-tomorrow',isTomorrow);
 lane.querySelector('.mode-label').textContent=isTomorrow?'明日计划':'今日复盘';
 lane.querySelector('.task-label').textContent=isTomorrow?'明天要做的事':'今天要做的事';
 lane.querySelectorAll('[data-mode]').forEach(b=>{b.setAttribute('aria-pressed',String(b.dataset.mode===mode[col]));b.classList.toggle('active',b.dataset.mode===mode[col])});
 const list=lane.querySelector('.tasks');list.replaceChildren();
 for(const task of taskList(col)){
  const li=document.createElement('li');li.className=task.done?'done':'';
  const label=document.createElement('label');const check=document.createElement('input');check.type='checkbox';check.checked=task.done;check.setAttribute('aria-label','完成：'+task.text);
  const text=document.createElement('span');text.className="md-render";text.innerHTML=renderMarkdown(task.text);label.append(check,text);
  check.onchange=()=>{const tasks=structuredClone(taskList(col));tasks.find(t=>t.id===task.id).done=check.checked;enqueue(taskDate(col),col,'tasks',tasks);renderLane(col)};
  const remove=document.createElement('button');remove.className='icon task-delete';remove.title='移除任务';remove.setAttribute('aria-label','移除：'+task.text);remove.innerHTML=icon('trash');remove.onclick=()=>{enqueue(taskDate(col),col,'tasks',taskList(col).filter(t=>t.id!==task.id));renderLane(col)};
  li.append(label,remove);list.append(li);
 }
 const n=taskList(col).length,done=taskList(col).filter(t=>t.done).length;lane.querySelector('.count').textContent=n?`${done} / ${n}`:'待落笔';
 lane.querySelector('.add-task input').placeholder=isTomorrow?'明天，从哪一步开始？':'写下一个具体行动…';
 window.autoSizeReviews?.();window.refreshMarkdown?.();
}
async function load(date){
 state=await api('/api/state'+(date?'?day='+date:'')); token=state.token;day=state.day;next=state.next;serverToday=state.today;
 $('#day').value=day;$('#date-label').textContent=new Intl.DateTimeFormat('zh-CN',{month:'long',day:'numeric',weekday:'long',timeZone:'Asia/Shanghai'}).format(new Date(day+'T12:00:00+08:00'));
 $('#quote-text').textContent=state.quote.text;$('#quote-source').textContent=state.quote.source.replace(/\[\[|\]\]/g,'').split('/').pop()||'自己的话';
 for(const date of [day,next])for(const col of cols)for(const field of ['review','tasks']){
  const key=draftKey(date,col,field);baselines.set(key,structuredClone(dataFor(date)[field][col]));
  try{const draft=(PREVIEW||!state.capabilities?.includes('anchored-sync'))?null:JSON.parse(localStorage.getItem(key)||'null');if(draft){dataFor(date)[field][col]=draft.value;queue.set(key,draft);baselines.set(key,draft.base)}}catch{}
 }
 for(const col of cols){const lane=$(`[data-column="${col}"]`);lane.querySelector('textarea').value=state.entry.review[col];renderLane(col)}
 $('#times').value=state.settings.times.join('，');$('#enabled').checked=state.settings.enabled;
 message(state.syncError?'日记同步失败：'+state.syncError:state.pending?'已保存 · 等待更新日记':state.sync?'已更新日记的看板区域':'随时落笔，自动保存',!!state.syncError);
 if(!state.capabilities?.includes('anchored-sync')){message('请先保存旧窗口的记录，再运行「更新并打开.cmd」。新版固定区域同步需要更新服务后启用。',true);$$('.lane textarea,.lane input,.lane button,#sync-now').forEach(e=>e.disabled=true)}else if(queue.size)flush();
 window.dispatchEvent(new Event('board-loaded'));
}
for(const col of cols){
 const lane=$(`[data-column="${col}"]`);
 lane.querySelector('textarea').oninput=e=>{window.autoSizeReviews?.();if(!PREVIEW)enqueue(day,col,'review',e.target.value)};
 lane.querySelectorAll('[data-mode]').forEach(b=>b.onclick=()=>{mode[col]=b.dataset.mode;renderLane(col)});
 lane.querySelector('.add-task').onsubmit=e=>{e.preventDefault();const input=e.target.querySelector('input');const text=input.value.trim();if(!text)return;enqueue(taskDate(col),col,'tasks',[...taskList(col),{id:crypto.randomUUID(),text,done:false}]);input.value='';renderLane(col);input.focus()};
}
async function settle(){clearTimeout(timer);await flush();while(saving)await new Promise(r=>setTimeout(r,70));if(queue.size)throw Error('还有未保存的草稿，请先解决保存错误')}
$('#day').onchange=async e=>{try{await settle();await load(e.target.value)}catch(err){e.target.value=day;message(err.message,true)}};
$$('[data-dialog]').forEach(b=>b.onclick=()=>{if(b.dataset.dialog==='settings')window.openBoardSettings?.();else $('#'+b.dataset.dialog).showModal()});
$$('[data-close]').forEach(b=>b.onclick=()=>b.closest('dialog').close());
$('#settings-form').onsubmit=async e=>{e.preventDefault();const button=e.submitter;button.disabled=true;try{if(!state.capabilities?.includes('anchored-sync')||!('appIcon' in state.settings))throw Error('请先保存记录，再双击「日有所积.exe」启动新版服务，然后重新设置。');await settle();const requested=window.collectBoardSettings();const result=await api('/api/settings',requested);if(!('quoteMode' in result))throw Error('本地服务仍是旧版本。请先保存记录，再运行「更新并打开.cmd」，然后重新设置。');state.settings=result;const updated=await api('/api/state?day='+day);state.quote=updated.quote;window.applyBoardDisplay(result);$('#settings').close();message('设置已保存');if(result.style!==document.body.dataset.style)location.href='/styles/v'+result.style+'/index.html'}catch(err){$('#settings-error').textContent=err.message}finally{button.disabled=false}};
$('#sync-now').onclick=async()=>{try{await settle();const result=await api('/api/sync',{day});message(result.status==='empty'?'今天还没有内容，无需同步':'已更新日记的看板区域')}catch(err){message(err.message,true)}};
$('#quotes-button').onclick=async()=>{try{const result=await api('/api/quotes');$('#quotes-list').replaceChildren();for(const q of result.quotes){const el=document.createElement('blockquote');el.textContent=q.text;const cite=document.createElement('cite');cite.textContent=q.source.replace(/\[\[|\]\]/g,'').split('/').pop();el.append(cite);$('#quotes-list').append(el)}$('#quotes-path').textContent=result.path;$('#quotes-link').onclick=async e=>{e.preventDefault();try{await api('/api/open-quotes',{})}catch(err){message(err.message,true)}};$('#quotes-link').href='/api/open-quotes';$('#quotes').showModal()}catch(err){message(err.message,true)}};
$$('[data-mobile-sync]').forEach(b=>b.onclick=()=>$('#sync-now').click());
$$('[data-mobile-quotes]').forEach(b=>b.onclick=()=>$('#quotes-button').click());
$('#apply-style').onclick=async()=>{try{await settle();await api('/api/settings',{style:document.body.dataset.style});message('已设为每天弹出的界面');$('#styles').close()}catch(err){message(err.message,true)}};
const compareLink=document.createElement('a');compareLink.href='/gallery.html';compareLink.textContent='查看五版完整对比 ↗';compareLink.dataset.styleLink='';const compareLine=document.createElement('p');compareLine.append(compareLink);$('.style-list').after(compareLine);
$$('[data-style-link]').forEach(a=>a.onclick=async e=>{e.preventDefault();try{await settle();location.href=a.href}catch(err){message(err.message,true)}});
$('#export').onclick=async()=>{const data=await api('/api/export');const a=document.createElement('a');a.href=URL.createObjectURL(new Blob([JSON.stringify(data,null,2)],{type:'application/json'}));a.download='成长看板-'+day+'.json';a.click();setTimeout(()=>URL.revokeObjectURL(a.href),1000)};
$('#download-draft').onclick=()=>{const a=document.createElement('a');a.href=URL.createObjectURL(new Blob([JSON.stringify([...queue.values()],null,2)],{type:'application/json'}));a.download='未保存草稿.json';a.click()};
window.addEventListener('beforeunload',e=>{if(queue.size||saving){e.preventDefault();e.returnValue=''}});
document.addEventListener('visibilitychange',()=>{if(document.hidden)flush()});
if(!PREVIEW)setInterval(async()=>{if(!state?.capabilities?.includes('anchored-sync'))return;if(queue.size&&!blocked){flush();return}if(saving||document.hidden)return;try{const latest=await api('/api/state?day='+day);if(latest.today!==serverToday){if(day===serverToday){await load(latest.today);return}serverToday=latest.today}if(latest.syncError)message('日记同步失败：'+latest.syncError,true);else if(latest.pending)message('已保存 · 等待更新日记');else if(latest.sync)message('已更新日记的看板区域');}catch{message('本地服务暂不可用，草稿仍保留',true)}},10000);
load().catch(e=>message('无法读取看板：'+e.message,true));
