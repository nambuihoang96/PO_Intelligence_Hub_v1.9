/* UI-only shell controller. Data, jobs and sources are untouched. */
window.ProductUI=(()=>{
 'use strict';
 const paths={overview:'M3 3h7v7H3z M14 3h7v7h-7z M3 14h7v7H3z M14 14h7v7h-7z',research:'M21 21l-5-5 M18 10a8 8 0 1 1-16 0 8 8 0 0 1 16 0',library:'M3 6c0-4 18-4 18 0s-18 4-18 0v12c0 4 18 4 18 0V6 M3 12c0 4 18 4 18 0',decisions:'M6 3h12v18H6z M9 8h6 M9 12h6 M9 16h4',queue:'M8 4h13v16H3V8 M3 4l2 2 4-4 M7 11h10 M7 15h7',settings:'M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8 M12 2v3 M12 19v3 M2 12h3 M19 12h3 M5 5l2 2 M17 17l2 2 M5 19l2-2 M17 7l2-2'};
 const labels={overview:'Tổng quan',research:'Nghiên cứu',library:'Thư viện dữ liệu',decisions:'Quyết định',queue:'Công việc',settings:'Cài đặt'};
 let dialog,sidebar,home,opener;
 function closeNav(){if(dialog?.open)dialog.close();}
 function init(){sidebar=document.querySelector('#appSidebar');home=sidebar.parentNode;dialog=document.querySelector('#mobileNavigation');opener=document.querySelector('#openNavigation');
  document.querySelectorAll('nav [data-nav]').forEach(b=>{const path=paths[b.dataset.nav];if(path)b.insertAdjacentHTML('afterbegin',`<svg viewBox="0 0 24 24" aria-hidden="true"><path d="${path}"/></svg>`);});
  opener.onclick=()=>{dialog.append(sidebar);dialog.showModal();opener.setAttribute('aria-expanded','true');};
  dialog.addEventListener('close',()=>{home.insertBefore(sidebar,document.querySelector('main'));opener.setAttribute('aria-expanded','false');opener.focus({preventScroll:true});});
  dialog.addEventListener('click',e=>{if(e.target===dialog)closeNav();});
  document.querySelector('#closeNavigation').onclick=closeNav;
  matchMedia('(min-width:768px)').addEventListener('change',e=>{if(e.matches)closeNav();});
  document.addEventListener('keydown',e=>{if(e.key==='Escape')document.querySelectorAll('.action-menu[open]').forEach(d=>{d.open=false;d.querySelector('summary').focus();});});
  document.addEventListener('click',e=>document.querySelectorAll('.action-menu[open]').forEach(d=>{if(!d.contains(e.target))d.open=false;}));
 }
 function navigate(view){closeNav();const el=document.querySelector('#locationName');if(el)el.textContent=labels[view]||view;}
 function polishRun(run){const header=document.querySelector('#page>header');if(!header)return;const titleRow=header.querySelector('.row.between'),toolbar=header.querySelector('.toolbar'),rename=document.querySelector('#rename');if(!toolbar||!titleRow)return;
  const actions=document.createElement('div');actions.className='header-actions';const fresh=document.createElement('button');fresh.type='button';fresh.textContent='Hỏi câu mới';fresh.onclick=()=>document.querySelector('#newResearch').click();actions.append(fresh);
  const menu=document.createElement('details');menu.className='action-menu';menu.innerHTML='<summary aria-label="Thao tác nghiên cứu" title="Thao tác nghiên cứu">⋯</summary><div class="action-menu-list"></div>';const list=menu.querySelector('div');if(rename)list.append(rename);const cancel=toolbar.querySelector('#cancel');if(cancel)actions.append(cancel);while(toolbar.firstChild)list.append(toolbar.firstChild);toolbar.remove();list.addEventListener('click',()=>{menu.open=false;});actions.append(menu);titleRow.append(actions);
  const question=header.querySelector('.question');if(question?.textContent.trim()===header.querySelector('h1')?.textContent.trim())question.hidden=true;
  header.querySelectorAll('small').forEach(el=>{el.classList.add('run-metadata');if(run){const dt=new Date(run.updated_at);el.textContent=(run.mode==='auto'?'Codex Auto':'ChatGPT Manual')+' · Cập nhật '+(Number.isNaN(dt.valueOf())?run.updated_at:new Intl.DateTimeFormat('vi-VN',{dateStyle:'short',timeStyle:'short'}).format(dt));el.title='Phiên kết quả #'+run.id;}});
  const tech=document.querySelector('#page>details:last-of-type');if(tech)tech.classList.add('technical-details');
  const form=document.querySelector('#followupForm');if(form){form.className='followup-box';const textarea=form.querySelector('textarea');textarea.placeholder='Ví dụ: Nên benchmark luồng mở khóa của app nào?';const footer=document.createElement('div');footer.className='followup-footer';footer.innerHTML='<small>Câu hỏi tiếp theo giữ trong nghiên cứu này</small>';const button=form.querySelector('button');button.textContent='Hỏi tiếp';footer.append(button);form.append(footer);}
 }
 function captureRun(id){const page=document.querySelector('#page');if(page.dataset.renderedRun!==String(id))return null;const focused=page.contains(document.activeElement)?document.activeElement:null;return {y:scrollY,focus:focused?.id,selection:focused&&'selectionStart' in focused?[focused.selectionStart,focused.selectionEnd]:null,fields:[...page.querySelectorAll('input[id]:not([type=file]),textarea[id],select[id]')].map(e=>({id:e.id,value:e.value,checked:e.checked})),details:[...page.querySelectorAll('.action-menu[open],.answer-gaps[open],.technical-details[open],.source-detail[open]')].map(e=>({key:e.className,index:[...page.querySelectorAll('.'+e.className.split(' ')[0])].indexOf(e)}))};}
 function restoreRun(saved){if(!saved)return;saved.fields.forEach(v=>{const e=document.getElementById(v.id);if(e){e.value=v.value;if('checked' in e)e.checked=v.checked;}});saved.details.forEach(d=>{const el=document.querySelectorAll('.'+d.key.split(' ')[0])[d.index];if(el)el.open=true;});const e=document.getElementById(saved.focus);if(e){e.focus({preventScroll:true});if(saved.selection&&e.setSelectionRange)try{e.setSelectionRange(...saved.selection);}catch{}}window.scrollTo({top:saved.y,behavior:'instant'});}
 return {init,navigate,polishRun,captureRun,restoreRun};
})();
ProductUI.init();
