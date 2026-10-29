'use strict';
paths.left='M19 12H5m6-6-6 6 6 6';paths.settings='M4 6h16M4 12h16M4 18h16M8 3v6m8 0v6M9 15v6';
$$('[data-icon="left"],[data-icon="settings"],[data-icon="arrow"]').forEach(e=>e.innerHTML=icon(e.dataset.icon));
const DISPLAY_DEFAULTS={motto:'把今天，写进长期。',quoteMode:'daily',fixedQuote:'让每一天，都留下一点积累。',quoteLayout:'poster'};
let pendingPreview=null,previewReady=false,calendarMonth;
window.autoSizeReviews=()=>{
 for(const textarea of $$('.lane textarea')){
  if(!textarea.offsetParent)continue;
  textarea.style.height='auto';textarea.style.height=Math.max(textarea.scrollHeight,parseFloat(getComputedStyle(textarea).minHeight)||60)+'px';
 }
};
let resizeFrame;
window.addEventListener('resize',()=>{cancelAnimationFrame(resizeFrame);resizeFrame=requestAnimationFrame(()=>{autoSizeReviews();sizePreview()})});
window.applyBoardDisplay=settings=>{
 const s={...DISPLAY_DEFAULTS,...settings};
 const favicon=$('#app-favicon');favicon.type='image/png';favicon.setAttribute('sizes','256x256');favicon.href='/icons/icon-'+(s.appIcon||'01')+(s.appIcon==='05'?'-light':'')+'.png?v=6';
 for(const col of cols){const lane=$(`[data-column="${col}"]`),name=s.columnNames?.[col]||{tech:'技术栈积累',project:'实习 / 项目',school:'学校课业'}[col];lane.querySelector('h2').innerHTML=renderMarkdown(name,true);lane.querySelector('textarea').setAttribute('aria-label',name+'今日复盘');lane.querySelector('.add-task input').setAttribute('aria-label',name+'添加任务')}
 $$('[data-motto]').forEach(el=>{el.classList.add('md-render');el.innerHTML=renderMarkdown(s.motto,true);el.hidden=!s.motto.trim()});
 document.body.classList.toggle('quote-hidden',s.quoteLayout==='hidden');document.body.classList.toggle('quote-type',s.quoteLayout==='type');
 const fixed=s.quoteMode==='fixed',text=fixed?s.fixedQuote:state?.quote?.text||'';
 $('#quote-text').classList.add('md-render');$('#quote-text').innerHTML=renderMarkdown(text);
 const source=fixed?'写给自己的提醒':(state?.quote?.source||'').replace(/\[\[|\]\]/g,'').split('/').slice(-2).join(' · ');
 $('#quote-source').textContent=fixed?source:'原话出处 · '+source.replace(/^(\d{2})\.(\d{1,2})复盘/,(_,y,m)=>'20'+y+'年'+m+'月复盘');$('#quote-source').title=source;$('#quote-source').hidden=!source;
 $('.quote-card').dataset.length=text.length>220?'very-long':text.length>85?'long':'normal';
 $('.quote-number').textContent=fixed?'KEEP IN MIND':(day||'').slice(5).replace('-',' / ');
 renderGoal(s);
 requestAnimationFrame(()=>{autoSizeReviews();window.refreshMarkdown?.()});
};
window.collectBoardSettings=()=>({times:$('#times').value.split(/[,，\s]+/).filter(Boolean),enabled:$('#enabled').checked,motto:$('#motto').value,quoteMode:$('#quote-mode').value,fixedQuote:$('#fixed-quote').value,quoteLayout:$('#quote-layout').value,style:$('#theme-choice').value,appIcon:$('input[name=app-icon]:checked')?.value||'01',columnNames:Object.fromEntries(cols.map(c=>[c,$('#name-'+c).value])),goalTitle:$('#goal-title').value,goalDate:$('#goal-date').value,quotesPath:$('#quote-file-path').value,obsidianPath:$('#obsidian-path').value});
function sizePreview(){const viewport=$('.preview-viewport');if(!viewport.clientWidth)return;const scale=viewport.clientWidth/1280;$('#template-preview').style.transform=`scale(${scale})`;viewport.style.height=(960*scale)+'px'}
function refreshPreview(){
 pendingPreview=collectBoardSettings();$('#fixed-quote-wrap').hidden=pendingPreview.quoteMode!=='fixed';
 const frame=$('#template-preview'),src='/styles/v'+pendingPreview.style+'/index.html?preview=1';
 if(frame.getAttribute('src')!==src){previewReady=false;frame.src=src}
 if(previewReady)frame.contentWindow.postMessage({type:'board-display-preview',settings:pendingPreview},location.origin);
 sizePreview();queueRoutePreview();
}
window.openBoardSettings=()=>{
 if(!state)return;const s={...DISPLAY_DEFAULTS,...state.settings};
 $('#goal-title').value=s.goalTitle||'';$('#goal-date').value=s.goalDate||'';
 $('#times').value=s.times.join('，');$('#enabled').checked=s.enabled;$('#motto').value=s.motto;$('#quote-mode').value=s.quoteMode;$('#fixed-quote').value=s.fixedQuote;$('#quote-layout').value=s.quoteLayout;$('#theme-choice').value=document.body.dataset.style;
 $('#settings-error').textContent=(state.capabilities?.includes('anchored-sync')&&('appIcon' in state.settings))?'':'当前服务需要更新。请先保存记录，再双击「日有所积.exe」，随后可使用新增设置。';
 for(const col of cols)$('#name-'+col).value=s.columnNames?.[col]||$(`[data-column="${col}"] h2`).textContent;
 $('#obsidian-path').value=s.obsidianPath||'';$('#quote-file-path').value=s.quotesPath||'';
 $(`input[name=app-icon][value="${s.appIcon||'01'}"]`).checked=true;
 $('#settings').showModal();refreshPreview();window.refreshMarkdown?.();
};
$('#settings-form').addEventListener('input',refreshPreview);$('#settings-form').addEventListener('change',refreshPreview);
window.addEventListener('message',event=>{
 if(event.origin!==location.origin)return;
 if(PREVIEW&&event.source===parent&&event.data?.type==='board-display-preview'){
  if(!state)return;applyBoardDisplay(event.data.settings);return;
 }
 if(!PREVIEW&&event.source===$('#template-preview').contentWindow&&event.data?.type==='board-preview-ready'){
  previewReady=true;if(pendingPreview)$('#template-preview').contentWindow.postMessage({type:'board-display-preview',settings:pendingPreview},location.origin);
 }
});
function onLoaded(){
 if(!state)return;applyBoardDisplay(state.settings);
 if(PREVIEW){
  const examples={tech:'今天弄懂了作用域。\n把一个概念，写成能独立完成的例子。',project:'把一个模糊的问题，拆成下一步。',school:'补上今天没弄懂的一处。'};
  for(const col of cols){const lane=$(`[data-column="${col}"]`);lane.querySelector('textarea').value=examples[col];const li=document.createElement('li'),label=document.createElement('label'),input=document.createElement('input'),span=document.createElement('span');input.type='checkbox';span.textContent={tech:'独立写出一个小练习',project:'验证一个具体结果',school:'完成今天的作业'}[col];label.append(input,span);li.append(label);lane.querySelector('.tasks').replaceChildren(li);lane.querySelector('.count').textContent='0 / 1'}
  $('main').inert=true;requestAnimationFrame(()=>{autoSizeReviews();window.refreshMarkdown?.()});parent.postMessage({type:'board-preview-ready'},location.origin);
 }
}
window.addEventListener('board-loaded',onLoaded);if(state)onLoaded();
function drawCalendar(){
 const year=calendarMonth.getUTCFullYear(),month=calendarMonth.getUTCMonth();$('#calendar-heading').textContent=`${year} 年 ${month+1} 月`;
 const grid=$('#calendar-grid');grid.replaceChildren();const leading=(new Date(Date.UTC(year,month,1)).getUTCDay()+6)%7;
 for(let i=0;i<leading;i++){const blank=document.createElement('span');blank.setAttribute('aria-hidden','true');grid.append(blank)}
 const count=new Date(Date.UTC(year,month+1,0)).getUTCDate();
 for(let n=1;n<=count;n++){
  const value=`${year}-${String(month+1).padStart(2,'0')}-${String(n).padStart(2,'0')}`,b=document.createElement('button');b.className='calendar-day';b.textContent=n;b.classList.toggle('selected',value===day);b.classList.toggle('today',value===serverToday);b.setAttribute('aria-label',value);b.setAttribute('aria-pressed',String(value===day));
  b.onclick=()=>chooseDay(value);grid.append(b);
 }
}
async function chooseDay(value){try{await settle();for(const col of cols)mode[col]='today';await load(value);$('#calendar').close();$('#date-open').focus()}catch(e){message(e.message,true)}}
$('#date-open').onclick=()=>{if(!day)return;calendarMonth=new Date(day.slice(0,7)+'-01T00:00:00Z');drawCalendar();$('#calendar').showModal()};
$('#month-prev').onclick=()=>{calendarMonth.setUTCMonth(calendarMonth.getUTCMonth()-1);drawCalendar()};$('#month-next').onclick=()=>{calendarMonth.setUTCMonth(calendarMonth.getUTCMonth()+1);drawCalendar()};$('#calendar-today').onclick=()=>chooseDay(serverToday);
$('#calendar').addEventListener('keydown',e=>{if(!e.target.classList.contains('calendar-day'))return;const shifts={ArrowLeft:-1,ArrowRight:1,ArrowUp:-7,ArrowDown:7};if(!(e.key in shifts))return;e.preventDefault();const value=new Date(e.target.getAttribute('aria-label')+'T00:00:00Z');value.setUTCDate(value.getUTCDate()+shifts[e.key]);calendarMonth=new Date(Date.UTC(value.getUTCFullYear(),value.getUTCMonth(),1));drawCalendar();$('#calendar-grid').querySelector(`[aria-label="${value.toISOString().slice(0,10)}"]`)?.focus()});
$$('dialog').forEach(dialog=>dialog.addEventListener('click',e=>{if(e.target===dialog){const r=dialog.getBoundingClientRect();if(e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom)dialog.close()}}));

$('#sync-help-toggle').onclick=()=>{const h=$('#sync-help');if(h.open)h.close();else h.showModal();$('#sync-help-toggle').setAttribute('aria-expanded',String(h.open))};
$('#sync-help').addEventListener('close',()=>$('#sync-help-toggle').setAttribute('aria-expanded','false'));

let routeTimer,routeSequence=0;
function queueRoutePreview(){
 clearTimeout(routeTimer);const seq=++routeSequence;
 if(PREVIEW||!state?.capabilities?.includes('anchored-sync'))return;
 routeTimer=setTimeout(async()=>{try{
 const result=await api('/api/diary-target?path='+encodeURIComponent($('#obsidian-path').value)+'&day='+day);
 if(seq===routeSequence){$('#diary-target').textContent=(result.exists?'将更新：':'将新建：')+result.path;$('#diary-target').dataset.error='false'}
 }catch(e){if(seq===routeSequence){$('#diary-target').textContent=e.message;$('#diary-target').dataset.error='true'}}},250);
}

let goalSettings={};
function goalDays(target,now=new Date()){
 const parts=new Intl.DateTimeFormat('en-CA',{timeZone:'Asia/Shanghai',year:'numeric',month:'2-digit',day:'2-digit'}).formatToParts(new Date(now.getTime()-4*3600000));
 const value=k=>parts.find(p=>p.type===k).value;
 return Math.round((Date.parse(target+'T00:00:00Z')-Date.parse(value('year')+'-'+value('month')+'-'+value('day')+'T00:00:00Z'))/86400000);
}
function renderGoal(settings){
 goalSettings=settings;
 let box=$('#focus-goal');
 if(!box){box=document.createElement('section');box.id='focus-goal';box.className='focus-goal';box.setAttribute('aria-label','当前的一个目标');box.innerHTML='<div><small>此刻，只向这一件事靠近</small><h3></h3><time></time></div><div class="goal-counter"><strong></strong><span></span></div><button type="button" class="icon" aria-label="设置近期目标" title="设置近期目标">'+icon('settings')+'</button>';const host=document.body.dataset.style==='05'?$('.quote-cutout'):document.body.dataset.style==='02'?$('.side-print'):$('.quote-card');host.after(box);box.querySelector('button').onclick=()=>openBoardSettings();}
 box.hidden=!settings.goalTitle||!settings.goalDate;
 if(box.hidden)return;
 const n=goalDays(settings.goalDate);if(!Number.isFinite(n)){box.hidden=true;return}
 box.querySelector('h3').textContent=settings.goalTitle;
 box.querySelector('time').textContent=settings.goalDate.replaceAll('-',' . ');
 box.querySelector('strong').textContent=n===0?'今天':Math.abs(n);
 box.querySelector('.goal-counter span').textContent=n===0?'就是目标日':n>0?'天后抵达':'天 · 已过目标日';
 box.classList.toggle('overdue',n<0);
}
setInterval(()=>renderGoal(goalSettings),30000);
window.addEventListener('focus',()=>renderGoal(goalSettings));
