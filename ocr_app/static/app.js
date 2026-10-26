'use strict';
const $ = id => document.getElementById(id);
const state = {files: [], reference: null, referenceURL: null, jobs: [], current: null, busy: false, poll: null, view: 'process', deleteId: null};
const statuses = {ready: 'Listo para iniciar', running: 'En proceso', completed: 'Completado', completed_with_errors: 'Completado con incidencias', cancelled: 'Cancelado', failed: 'No completado', interrupted: 'Interrumpido'};
const outcomes = {match: 'Con logotipo', no_match: 'Sin coincidencia', review: 'Revisar', processed: 'Preparado', pending: 'Pendiente', unclassified: 'Sin clasificar', skipped: 'Omitido'};
let limits = {files: 500, file_mb: 50, job_mb: 500, reference_mb: 10};

function node(tag, className, text) { const element = document.createElement(tag); if (className) element.className = className; if (text !== undefined) element.textContent = text; return element; }
function icon(name) { const svg = document.createElementNS('http://www.w3.org/2000/svg','svg'); const use = document.createElementNS('http://www.w3.org/2000/svg','use'); use.setAttribute('href', '#' + name); svg.setAttribute('aria-hidden','true'); svg.append(use); return svg; }
function button(text, handler, className='button') { const b = node('button', className, text); b.type='button'; b.addEventListener('click', handler); return b; }
function badge(code, label) { return node('span', 'badge ' + code, label || outcomes[code] || statuses[code] || code); }
function sizeLabel(bytes) { return bytes < 1024 * 1024 ? Math.max(1, Math.round(bytes / 1024)) + ' KB' : (bytes / 1024 / 1024).toFixed(1) + ' MB'; }
function dateLabel(date) { return new Date(date).toLocaleString('es-CO', {day:'2-digit', month:'short', hour:'2-digit', minute:'2-digit'}); }
function notify(message) { $('notice-text').textContent=message; $('notice').hidden=false; }
function clearNotice() { $('notice').hidden=true; }
async function api(path, options={}) {
  let response;
  try { response=await fetch('/api' + path, options); }
  catch { throw new Error('No se pudo conectar. Comprueba que la ventana de Proyecto OCR siga abierta.'); }
  if (!response.ok) {
    let message='No se pudo completar la operación (' + response.status + ').';
    try { const error=await response.json(); if(typeof error.detail==='string') message=error.detail; } catch {}
    throw new Error(message);
  }
  return response.json();
}
function setBusy(busy, message='Preparar lote') {
  state.busy=busy;
  $('prepare-button').disabled=busy || !state.files.length;
  $('prepare-button').replaceChildren(document.createTextNode(message), icon('arrow'));
  $('demo-button').disabled=busy; $('empty-demo').disabled=busy;
}
function switchView(view) {
  state.view=view;
  document.querySelectorAll('.view').forEach(panel=>panel.hidden=panel.id!=='view-'+view);
  document.querySelectorAll('[data-view]').forEach(item=>{const active=item.dataset.view===view; item.classList.toggle('active',active); if(active) item.setAttribute('aria-current','page'); else item.removeAttribute('aria-current');});
  if(view==='results') refreshHistory().catch(error=>notify(error.message));
}

function chooseFiles(fileList, folder=false) {
  const selected=[], skipped=[];
  for(const file of fileList) {
    if(!/\.(pdf|docx|msg)$/i.test(file.name)) { skipped.push(file.name); continue; }
    let path=file.name;
    if(folder && file.webkitRelativePath) path=file.webkitRelativePath.split('/').slice(1).join('/');
    selected.push({file, path});
  }
  if(selected.length>limits.files) { notify('El máximo es ' + limits.files + ' archivos por lote. Selecciona una carpeta más pequeña.'); return; }
  if(selected.some(item=>item.file.size>limits.file_mb*1024*1024)) { notify('Hay archivos que superan ' + limits.file_mb + ' MB. Selecciona un lote más pequeño.'); return; }
  if(selected.reduce((sum,item)=>sum+item.file.size,0)>limits.job_mb*1024*1024) { notify('El lote supera ' + limits.job_mb + ' MB. Divídelo en varios trabajos.'); return; }
  state.files=selected; renderSelection();
  if(skipped.length) notify(skipped.length+' archivos omitidos por formato no compatible. Solo se incluyen PDF, DOCX y MSG.');
  else clearNotice();
}
function renderSelection() {
  const files=state.files;
  $('selection-summary').hidden=!files.length;
  $('file-count').textContent=files.length ? files.length+' archivos' : 'Sin archivos';
  $('selection-size').textContent=sizeLabel(files.reduce((sum,item)=>sum+item.file.size,0))+' seleccionados';
  const groups=[...new Set(files.map(item=>item.path.includes('/')?item.path.split('/')[0]:'Archivos sueltos'))];
  $('group-summary').textContent='Grupos: '+groups.slice(0,4).join(', ')+(groups.length>4?' y '+(groups.length-4)+' más':'');
  $('file-list').replaceChildren();
  files.slice(0,15).forEach((item,index)=>{
    const extension=item.file.name.split('.').pop().toLowerCase();
    const row=node('li','file-row'); row.append(node('span','file-format '+extension,extension.toUpperCase()));
    const info=node('div','file-info'); info.append(node('div','file-name',item.path),node('span','small muted',sizeLabel(item.file.size))); row.append(info);
    const remove=button('×',()=>{state.files.splice(index,1);renderSelection();},'icon-button'); remove.setAttribute('aria-label','Quitar '+item.path); row.append(remove); $('file-list').append(row);
  });
  $('remaining-files').textContent=files.length>15?'Y '+(files.length-15)+' archivos más en el lote.':'';
  $('prepare-button').disabled=state.busy||!files.length;
}
function getOptions() { const options={}; for(const key of ['convert','extract','recognize','classify','report','evidence']) options[key]=$('opt-'+key).checked; return options; }
function updateRecognition() { const enabled=$('opt-recognize').checked; $('opt-classify').disabled=!enabled; if(!enabled) $('opt-classify').checked=false; $('reference-control').hidden=!enabled; $('opt-evidence').disabled=!enabled; }

async function prepare() {
  const options=getOptions();
  if(options.recognize&&!state.reference) { notify('Selecciona una imagen de referencia para reconocer el logotipo, o desactiva el reconocimiento.'); $('choose-reference').focus(); return; }
  clearNotice(); setBusy(true,'Copiando archivos…');
  const form=new FormData();
  state.files.forEach(item=>form.append('files',item.file,item.file.name));
  form.append('paths',JSON.stringify(state.files.map(item=>item.path)));
  form.append('options',JSON.stringify(options));
  if(state.reference&&options.recognize) form.append('reference',state.reference);
  try { const job=await api('/jobs',{method:'POST',body:form}); await openJob(job.id,job); switchView('results'); }
  catch(error) { notify(error.message); }
  finally { setBusy(false); }
}
async function demo() {
  clearNotice(); setBusy(true);
  try { const job=await api('/demo',{method:'POST'}); await openJob(job.id,job); switchView('results'); }
  catch(error) { notify(error.message); }
  finally { setBusy(false); }
}
async function refreshHistory() {
  state.jobs=await api('/jobs'); $('history-count').textContent=state.jobs.length;
  $('results-empty').hidden=state.jobs.length>0; $('results-content').hidden=!state.jobs.length;
  renderHistory();
  if(!state.current&&state.jobs.length) await openJob(state.jobs[0].id);
}
function renderHistory() {
  $('history-list').replaceChildren();
  for(const job of state.jobs) {
    const item=button('',()=>openJob(job.id).catch(error=>notify(error.message)), 'history-item'+(state.current?.id===job.id?' active':''));
    item.append(node('strong','',job.demo?'Demostración':job.name),node('small','',dateLabel(job.created)),badge(job.status));
    item.setAttribute('aria-label',(job.demo?'Demostración':job.name)+', '+statuses[job.status]);
    if(state.current?.id===job.id) item.setAttribute('aria-current','true');
    $('history-list').append(item);
  }
}
async function openJob(id, existing=null) {
  clearTimeout(state.poll); state.current={id};
  const job=existing||await api('/jobs/'+id);
  if(state.current?.id!==id) return;
  state.current=job; renderJob(job); renderHistory(); schedulePoll(job);
}
function schedulePoll(job) {
  clearTimeout(state.poll);
  if(job.status!=='running') return;
  state.poll=setTimeout(async()=>{
    if(state.current?.id!==job.id) return;
    try {
      const updated=await api('/jobs/'+job.id);
      if(state.current?.id!==job.id) return;
      state.current=updated; renderJob(updated); schedulePoll(updated);
      if(updated.status!=='running') await refreshHistory();
    } catch(error) { notify(error.message); }
  },1000);
}
async function startJob(id) {
  clearNotice();
  const btn=$('start-job'); if(btn) btn.disabled=true;
  try { const job=await api('/jobs/'+id+'/start',{method:'POST'}); state.current=job; renderJob(job); schedulePoll(job); await refreshHistory(); }
  catch(error) { notify(error.message); if(btn) btn.disabled=false; }
}
async function cancelJob(id) {
  try { await api('/jobs/'+id+'/cancel',{method:'POST'}); await openJob(id); }
  catch(error) { notify(error.message); }
}
function downloadLink(job, kind, text) { const link=node('a','button'+(kind==='zip'?' primary':''),text); link.href='/api/jobs/'+job.id+'/download/'+kind; link.append(icon('download')); return link; }

function renderJob(job) {
  const focusId=$('job-detail').contains(document.activeElement)?document.activeElement.id:null;
  const detail=$('job-detail'); detail.replaceChildren();
  const heading=node('div','job-heading'), title=node('div');
  title.append(node('h2','',job.demo?'Demostración con documentos ficticios':job.name),badge(job.status),node('p','small muted',dateLabel(job.created)));
  const remove=button('Borrar trabajo',()=>{state.deleteId=job.id;$('delete-dialog').showModal();$('cancel-delete').focus();},'text-button'); remove.disabled=job.status==='running';
  heading.append(title,remove); detail.append(heading);
  const status=node('section','status-panel'); status.append(node('h3','',job.stage));
  if(job.status==='ready') {
    status.append(node('p','',job.files.length+' archivos originales en '+new Set(job.files.map(file=>file.group)).size+' grupos. Revisa las opciones e inicia cuando estés listo.'));
    const names={convert:'Word a PDF',extract:'Adjuntos PDF de Outlook',recognize:'Reconocimiento',classify:'Clasificación',report:'Excel',evidence:'Evidencias en ZIP'};
    status.append(node('p','small muted',Object.entries(names).filter(([key])=>job.options[key]).map(([,name])=>name).join(' · ')));
    const actions=node('div','status-actions'); const start=button('Iniciar procesamiento',()=>startJob(job.id),'button primary'); start.id='start-job'; start.append(icon('arrow')); actions.append(start); status.append(actions);
  } else if(job.status==='running') {
    const progress=node('progress');
    progress.setAttribute('aria-label',job.stage);
    if(job.progress.total) { progress.max=job.progress.total; progress.value=job.progress.done; }
    status.append(progress,node('p','',job.progress.total?job.progress.done+' de '+job.progress.total+' archivos en esta etapa.':'Preparando la siguiente etapa…'));
    const actions=node('div','status-actions'); const cancel=button(job.cancellation_requested?'Cancelación solicitada':'Cancelar después del archivo actual',()=>cancelJob(job.id)); cancel.id='cancel-job'; cancel.disabled=job.cancellation_requested; actions.append(cancel); status.append(actions);
  } else {
    status.append(node('p','',job.errors.length?job.errors.length+' incidencias registradas. Revisa el detalle antes de usar la clasificación.':'Consulta los archivos y descarga los resultados disponibles.'));
    if(job.artifacts.length) { const actions=node('div','status-actions'); if(job.artifacts.includes('excel'))actions.append(downloadLink(job,'excel','Reporte Excel')); if(job.artifacts.includes('zip'))actions.append(downloadLink(job,'zip','Resultados ZIP')); status.append(actions); }
  }
  detail.append(status);
  if(job.demo) detail.append(node('p','note-box','Demostración: todos los documentos son ficticios. Los resultados se calculan con el mismo motor que procesa tus archivos.'));
  if(job.groups.length) {
    const summary=node('div','job-summary');
    for(const [code,label] of [['match','Grupos con logotipo'],['no_match','Sin coincidencia'],['review','Para revisar']]) { const metric=node('div','summary-item'); metric.append(node('strong','',String(job.groups.filter(g=>g.state===code).length)),node('span','',label)); summary.append(metric); }
    detail.append(summary,node('h3','section-title','Clasificación sugerida por carpeta'));
    const groups=node('div','group-results'); for(const group of job.groups) { const row=node('div','group-row');row.append(node('span','',group.name),badge(group.state));groups.append(row); }detail.append(groups);
  }
  detail.append(node('h3','section-title','Archivos del trabajo ('+job.files.length+')'));
  for(const file of job.files) {
    const row=node('div','result-file'), top=node('div','result-file-top'); top.append(node('strong','',file.relative),badge(file.state));row.append(top);
    row.append(node('p','muted',file.group+' · '+(file.original?'Original':'Generado')+' · '+sizeLabel(file.size)));
    if(file.message) row.append(node('p','muted',file.message));
    if(file.matches?.length) {const links=node('div','evidence-buttons');file.matches.forEach(match=>links.append(button('Ver evidencia · pág. '+match.page,()=>showEvidence(job,file,match),'text-button')));row.append(links);}
    detail.append(row);
  }
  if(job.errors.length) {
    const disclosure=node('details');const summary=node('summary','section-title','Incidencias ('+job.errors.length+')');disclosure.append(summary);
    const list=node('ul','incident-list');for(const error of job.errors)list.append(node('li','',error.file+': '+error.message));disclosure.append(list);detail.append(disclosure);
  }
  if(focusId&&$(focusId)) $(focusId).focus({preventScroll:true});
}
function showEvidence(job,file,match) {
  $('evidence-title').textContent='Coincidencia · página '+match.page;
  $('evidence-description').textContent=file.relative+' · '+match.features+' correspondencias visuales. No es un porcentaje de certeza.';
  $('evidence-image').src='/api/jobs/'+job.id+'/evidence/'+file.id+'/'+encodeURIComponent(match.image);
  $('evidence-dialog').showModal();
}
async function deleteJob() {
  const id=state.deleteId; if(!id)return;
  $('confirm-delete').disabled=true;
  try { await api('/jobs/'+id,{method:'DELETE'});if(state.current?.id===id){clearTimeout(state.poll);state.current=null;}$('delete-dialog').close();await refreshHistory(); }
  catch(error) { $('delete-dialog').close();notify(error.message); }
  finally { $('confirm-delete').disabled=false;state.deleteId=null; }
}

document.querySelectorAll('[data-view]').forEach(button=>button.addEventListener('click',()=>switchView(button.dataset.view)));
$('dismiss-notice').addEventListener('click',clearNotice);
$('choose-folder').addEventListener('click',()=>$('folder-input').click());
$('choose-files').addEventListener('click',()=>$('files-input').click());
$('folder-input').addEventListener('change',event=>{chooseFiles(event.target.files,true);event.target.value='';});
$('files-input').addEventListener('change',event=>{chooseFiles(event.target.files);event.target.value='';});
$('clear-files').addEventListener('click',()=>{state.files=[];renderSelection();});
$('dropzone').addEventListener('dragover',event=>{event.preventDefault();$('dropzone').classList.add('dragging');});
$('dropzone').addEventListener('dragleave',()=>$('dropzone').classList.remove('dragging'));
$('dropzone').addEventListener('drop',event=>{event.preventDefault();$('dropzone').classList.remove('dragging');chooseFiles(event.dataTransfer.files);});
$('choose-reference').addEventListener('click',()=>$('reference-input').click());
$('reference-input').addEventListener('change',event=>{
  const file=event.target.files[0];if(!file)return;
  if(!/\.(png|jpe?g)$/i.test(file.name)||file.size>limits.reference_mb*1024*1024){notify('Selecciona una imagen PNG/JPG de hasta '+limits.reference_mb+' MB.');event.target.value='';return;}
  if(state.referenceURL)URL.revokeObjectURL(state.referenceURL);state.reference=file;state.referenceURL=URL.createObjectURL(file);
  $('reference-preview').src=state.referenceURL;$('reference-preview').hidden=false;$('reference-placeholder').hidden=true;$('reference-name').textContent=file.name;clearNotice();
});
$('opt-recognize').addEventListener('change',updateRecognition);
$('prepare-button').addEventListener('click',prepare);
$('demo-button').addEventListener('click',demo);$('empty-demo').addEventListener('click',demo);
$('refresh-history').addEventListener('click',()=>refreshHistory().catch(error=>notify(error.message)));
$('close-evidence').addEventListener('click',()=>$('evidence-dialog').close());
$('cancel-delete').addEventListener('click',()=>$('delete-dialog').close());
$('confirm-delete').addEventListener('click',deleteJob);
async function boot() {
  try { const health=await api('/health');limits=health.limits;$('connection-status').textContent='Listo para trabajar';$('word-status').textContent=health.word?'Microsoft Word disponible en este equipo':'Requiere Microsoft Word en Windows';if(!health.word){$('opt-convert').checked=false;$('opt-convert').disabled=true;}$('limit-note').textContent='Hasta '+limits.files+' archivos · '+limits.file_mb+' MB por archivo · '+limits.job_mb+' MB por lote';await refreshHistory(); }
  catch(error){$('connection-status').textContent='Sin conexión';notify(error.message);}
}
boot();
