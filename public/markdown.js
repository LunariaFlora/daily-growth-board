'use strict';
window.renderMarkdown=(text,inline=false)=>DOMPurify.sanitize((inline?marked.parseInline(text||''):marked.parse(text||'',{breaks:true,gfm:true})).replace(/<input[^>]*type="checkbox"[^>]*>/g,tag=>tag.includes('checked')?'☑ ':'☐ '),{FORBID_TAGS:['img','style','input','iframe'],FORBID_ATTR:['style']});
function enhanceMarkdown(){
 document.querySelectorAll('.review-wrap textarea,.add-task input,#motto,#fixed-quote,#name-tech,#name-project,#name-school').forEach(input=>{
  if(input.dataset.markdown)return;
  input.dataset.markdown='true';
  const wrap=document.createElement('div');wrap.className='md-editor';input.before(wrap);wrap.append(input);
  const preview=document.createElement('div');preview.className='md-render md-preview';preview.tabIndex=0;preview.setAttribute('role','button');preview.setAttribute('aria-label','点击编辑 Markdown');wrap.append(preview);
  const refresh=()=>{preview.innerHTML=renderMarkdown(input.value);wrap.classList.toggle('has-content',!!input.value.trim());};
  input.addEventListener('input',refresh);input.addEventListener('focus',()=>wrap.classList.add('editing'));
  input.addEventListener('blur',()=>{wrap.classList.remove('editing');refresh()});
  preview.onclick=e=>{if(e.target.closest('a'))return;wrap.classList.add('editing');input.focus();window.autoSizeReviews?.()};
  preview.onkeydown=e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();wrap.classList.add('editing');input.focus()}};
  input._refreshMarkdown=refresh;refresh();
 });
 document.querySelectorAll('[data-markdown]').forEach(input=>input._refreshMarkdown?.());
}
window.refreshMarkdown=enhanceMarkdown;
window.addEventListener('board-loaded',enhanceMarkdown);
document.addEventListener('input',()=>requestAnimationFrame(enhanceMarkdown));
document.addEventListener('click',()=>requestAnimationFrame(enhanceMarkdown));
enhanceMarkdown();
