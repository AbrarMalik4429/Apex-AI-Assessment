const $ = id => document.getElementById(id);
const state = {token: sessionStorage.getItem('apex-session'), doctors: [], doctor: null, slot: null, mode: 'book', booking: null, busy: false, proposal: null, confirmation: null, uncertain: false, sequence: 0};
const el = (tag, text, cls) => { const n = document.createElement(tag); if(text !== undefined) n.textContent = text; if(cls) n.className = cls; return n; };
const pretty = value => value.replaceAll('_', ' ');
const dayLabel = value => new Date(value + 'T12:00:00').toLocaleDateString(undefined, {weekday:'short', month:'short', day:'numeric'});
const timeLabel = value => value.slice(0,5);
function notice(message, error=false) { $('notice').textContent=message; $('notice').className=error?'error':''; $('notice').hidden=false; }
async function api(path, body) {
 const response = await fetch(path, {method:body?'POST':'GET', headers:{'Content-Type':'application/json', ...(state.token?{Authorization:`Bearer ${state.token}`}:{})}, ...(body?{body:JSON.stringify(body)}:{})});
 const data = await response.json();
 if(!response.ok) { const error = new Error(data.message || (typeof data.detail==='string'?data.detail:'The request could not be completed. Please try again.')); error.status=response.status; error.data=data; throw error; }
 return data;
}
function doctorName(id) { return state.doctors.find(d=>d.doctor_id===id)?.doctor_name || 'Your doctor'; }
function renderDoctors() {
 $('doctors').replaceChildren();
 state.doctors.forEach((d,i)=>{const b=el('button',undefined,'doctor'+(state.doctor===d.doctor_id?' selected':''));b.type='button';b.setAttribute('aria-pressed',state.doctor===d.doctor_id);b.disabled=state.busy || (state.mode!=='book' && state.doctor!==d.doctor_id);const icon=el('span',i===0?'AD':'SD','doctor-icon');const copy=el('span',undefined,'doctor-copy');copy.append(el('strong',d.doctor_name),el('small',d.specialties.join(' · ')));b.append(icon,copy,el('span',undefined,'radio'));b.onclick=()=>{state.doctor=d.doctor_id;renderDoctors();loadSlots();};$('doctors').append(b);});
}
async function loadSlots() {
 const seq=++state.sequence;state.slot=null;$('review').disabled=true;$('selection').hidden=true;
 if(!state.doctor)return;
 $('date').disabled=state.busy;$('schedule-subtitle').textContent=doctorName(state.doctor);$('slots').replaceChildren(el('p','Finding available times…','muted'));
 try {const params=new URLSearchParams({doctor_id:state.doctor,start:$('date').value,end:$('date').value,limit:'100'});if(state.mode==='reschedule')params.set('exclude_booking_id',state.booking.booking_id);const data=await api('/availability?'+params);if(seq!==state.sequence)return;$('timezone').textContent=data.timezone;$('slots').replaceChildren();
 if(!data.slots.length)$('slots').append(el('p','No times available on this day. Try another date.','muted'));
 data.slots.forEach(s=>{const b=el('button',timeLabel(s.start_time),'time');b.type='button';b.setAttribute('aria-pressed','false');b.onclick=()=>{if(state.busy)return;state.slot=s;document.querySelectorAll('.time').forEach(n=>{n.classList.remove('selected');n.setAttribute('aria-pressed','false');});b.classList.add('selected');b.setAttribute('aria-pressed','true');$('selection').hidden=false;$('selection').textContent=`${dayLabel(s.appointment_date)} · ${timeLabel(s.start_time)}–${timeLabel(s.end_time)}`;$('review').disabled=false;};$('slots').append(b);});
 }catch(e){if(seq===state.sequence){$('slots').replaceChildren(el('p',e.message,'muted'));notice(e.message,true);}}
}
async function loadAppointments() {
 const data=await api('/appointments');$('appointment-list').replaceChildren();
 const rank={confirmed:0,pending_scheduling:1,completed:2,cancelled:3,rescheduled:4,no_show:5};
 data.appointments.sort((a,b)=>(rank[a.status]-rank[b.status]) || (a.appointment_date||'').localeCompare(b.appointment_date||''));
 if(!data.appointments.length)$('appointment-list').append(el('p','No appointments yet. Choose a doctor to get started.','muted'));
 data.appointments.forEach(a=>{const row=el('article',undefined,'appointment');const tile=el('div',a.appointment_date?a.appointment_date.slice(8):'↗','date-tile');tile.append(el('small',a.appointment_date?new Date(a.appointment_date+'T12:00:00').toLocaleDateString('en',{month:'short'}).toUpperCase():'NEXT'));const info=el('div',undefined,'appointment-main');info.append(el('strong',doctorName(a.doctor_id)),el('p',a.appointment_date?`${dayLabel(a.appointment_date)} · ${timeLabel(a.start_time)}–${timeLabel(a.end_time)} · ${a.type}`:'Follow-up · Choose a time to continue your care'));row.append(tile,info,el('span',pretty(a.status),'badge '+a.status));const actions=el('div',undefined,'appointment-actions');
 function action(label,fn){const b=el('button',label);b.disabled=state.busy;b.onclick=fn;actions.append(b);}
 if(a.status==='confirmed'){action('Reschedule',()=>setMode('reschedule',a));action('Cancel',()=>propose('cancel',a));}
 if(a.status==='pending_scheduling')action('Schedule follow-up',()=>setMode('follow_up',a));
 row.append(actions);$('appointment-list').append(row);});
}
function setMode(mode='book', booking=null){if(state.busy)return;state.mode=mode;state.booking=booking;if(booking)state.doctor=booking.doctor_id;$('schedule-title').textContent=mode==='book'?'Choose your time':mode==='reschedule'?'Choose a new time':'Schedule your follow-up';$('exit-mode').hidden=mode==='book';renderDoctors();loadSlots();$('booking').scrollIntoView({behavior:'smooth',block:'start'});}
function lock(value){state.busy=value;$('review').disabled=value || !state.slot;$('date').disabled=value || !state.doctor;$('refresh').disabled=value;document.querySelectorAll('.appointment-actions button,.time').forEach(b=>b.disabled=value);renderDoctors();}
async function propose(action=state.mode, booking=state.booking){if(state.busy)return;lock(true);try{const s=state.slot;const body={request_id:crypto.randomUUID(),action,booking_id:booking?.booking_id||null,...(action==='cancel'?{}:{doctor_id:s.doctor_id,appointment_date:s.appointment_date,start_time:s.start_time})};const result=await api('/booking/propose',body);if(result.status!=='confirmation_required'){notice(result.message,true);lock(false);return;}
 state.proposal=result;state.confirmation=null;state.uncertain=false;$('confirm').hidden=false;$('dialog-title').textContent=action==='cancel'?'Cancel this appointment?':action==='reschedule'?'Review your new time':'Review your appointment';$('dialog-message').textContent=result.message;$('dialog-error').textContent='';$('confirm').textContent=action==='cancel'?'Confirm cancellation':'Confirm appointment →';$('confirm').disabled=false;
 const detail=result.data.candidate||result.data.booking;$('dialog-details').replaceChildren();if(detail){$('dialog-details').append(el('strong',doctorName(detail.doctor_id)),el('div',`${dayLabel(detail.appointment_date)} · ${timeLabel(detail.start_time)}–${timeLabel(detail.end_time)}`),el('div',$('timezone').textContent));}$('confirm-dialog').showModal();
 }catch(e){notice(e.message,true);lock(false);}}
function closeDialog(){if(state.uncertain)return;$('confirm-dialog').close();lock(false);}
async function confirm(){if($('confirm').disabled)return;$('confirm').disabled=true;$('close-dialog').disabled=true;$('back').disabled=true;state.uncertain=true;
 if(!state.confirmation)state.confirmation={request_id:crypto.randomUUID(),message:'confirm',confirmation_token:state.proposal.confirmation_token};
 try {const result=await api('/assistant/message',state.confirmation);state.uncertain=false;if(result.status!=='success'){$('dialog-error').textContent=result.message;$('confirm').hidden=true;return;}$('confirm-dialog').close();lock(false);notice(result.message);state.mode='book';state.booking=null;$('schedule-title').textContent='Choose your time';$('exit-mode').hidden=true;await Promise.all([loadAppointments(),loadSlots()]).catch(()=>notice(result.message+' Refresh the page to update the list.'));}
 catch(e){state.uncertain=!e.status || e.data?.status==='outcome_unknown';$('dialog-error').textContent=state.uncertain?'The result is not yet known. Use Retry to check the same request safely.':e.message;$('confirm').textContent='Retry confirmation';$('confirm').disabled=false;$('confirm').hidden=!state.uncertain;}
 finally{$('close-dialog').disabled=state.uncertain;$('back').disabled=state.uncertain;}
}
$('review').onclick=()=>{$('confirm').hidden=false;propose();};$('confirm').onclick=confirm;$('back').onclick=closeDialog;$('close-dialog').onclick=closeDialog;$('confirm-dialog').addEventListener('cancel',e=>{e.preventDefault();closeDialog();});$('date').onchange=loadSlots;$('exit-mode').onclick=()=>setMode();$('refresh').onclick=async()=>{try{await Promise.all([loadAppointments(),loadSlots()]);}catch(e){notice(e.message,true);}};
async function init(){try{const config=await api('/demo/config');if(!config.demo_enabled)throw new Error('The synthetic demo is disabled on this server.');$('date').min=config.today;$('date').value=config.today;const max=new Date(config.today+'T12:00:00Z');max.setUTCDate(max.getUTCDate()+config.horizon_days);$('date').max=max.toISOString().slice(0,10);$('timezone').textContent=config.timezone;$('footer-zone').textContent=config.timezone;
 if(state.token){try{state.doctors=(await api('/doctors')).doctors;}catch(e){if(e.status!==401)throw e;state.token=null;}}
 if(!state.token){state.token=(await api('/demo/session',{})).access_token;sessionStorage.setItem('apex-session',state.token);state.doctors=(await api('/doctors')).doctors;}
 state.doctor=state.doctors[0]?.doctor_id;$('connection').textContent='● Connected to your demo patient account · Guided booking is ready';renderDoctors();await Promise.all([loadSlots(),loadAppointments()]);
 }catch(e){$('connection').textContent='Connection needs attention';notice(e.message,true);const retry=el('button','Retry connection','secondary');retry.onclick=()=>location.reload();$('connection').append(' ',retry);}}
init();
