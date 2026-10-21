import {
  STORAGE_KEY, DEMO_PASSWORD, USERS, ROOMS, BookingError, localDate, shiftDate,
  initialDate, authenticate, createState, canCancel, visibleReservations,
  minutes, reserve, cancelReservation, notificationsFor, markNotificationsRead,
} from './agenda-demo-data.mjs';

const app = document.querySelector('#app');
const dialog = document.querySelector('#details-dialog');
const toastElement = document.querySelector('#toast');
const paths = {
  calendar: '<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M16 3v4M8 3v4M3 11h18M8 15h2M14 15h2"/>',
  grid: '<rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/>',
  door: '<path d="M4 21h16M6 21V4l11-2v19M17 5h3v16M13 12h.01"/>',
  bell: '<path d="M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9M10 21h4"/>',
  shield: '<path d="m12 3 8 3v6c0 5-8 9-8 9s-8-4-8-9V6zM9 12l2 2 4-4"/>',
  user: '<circle cx="12" cy="8" r="4"/><path d="M4 21v-2a8 8 0 0 1 16 0v2"/>',
  users: '<circle cx="9" cy="8" r="3"/><path d="M3 20v-2a6 6 0 0 1 12 0v2M16 5a3 3 0 0 1 0 6M17 14a5 5 0 0 1 4 5v1"/>',
  monitor: '<rect x="2" y="3" width="20" height="14" rx="2"/><path d="M8 21h8M12 17v4"/>',
  presentation: '<path d="M3 3h18M5 3v13h14V3M12 16v5M8 21l4-3 4 3M8 8h8M8 11h5"/>',
  book: '<path d="M12 6c-3-3-7-3-10-2v15c3-1 7-1 10 2 3-3 7-3 10-2V4c-3-1-7-1-10 2v15"/>',
  location: '<path d="M20 10c0 6-8 12-8 12S4 16 4 10a8 8 0 1 1 16 0"/><circle cx="12" cy="10" r="2.5"/>',
  plus: '<path d="M12 5v14M5 12h14"/>',
  arrow: '<path d="M5 12h14m-5-5 5 5-5 5"/>',
  left: '<path d="m14 6-6 6 6 6"/>',
  right: '<path d="m10 6 6 6-6 6"/>',
  clock: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
  check: '<path d="m5 12 4 4L19 6"/>',
  checkCircle: '<circle cx="12" cy="12" r="9"/><path d="m8 12 3 3 5-6"/>',
  lock: '<rect x="5" y="10" width="14" height="11" rx="2"/><path d="M8 10V6a4 4 0 0 1 8 0v4M12 14v3"/>',
  logout: '<path d="M9 4H4v16h5M10 12h11m-4-4 4 4-4 4"/>',
  eye: '<path d="M2 12s4-7 10-7 10 7 10 7-4 7-10 7-10-7-10-7"/><circle cx="12" cy="12" r="3"/>',
  close: '<path d="m6 6 12 12M6 18 18 6"/>',
  info: '<circle cx="12" cy="12" r="9"/><path d="M12 11v6M12 7h.01"/>',
  alert: '<path d="m12 3 10 18H2zM12 9v5M12 17h.01"/>',
  building: '<path d="M4 21V5l8-3 8 3v16M2 21h20M9 21v-5h6v5M8 7h1M15 7h1M8 11h1M15 11h1"/>',
  help: '<circle cx="12" cy="12" r="9"/><path d="M9 9a3 3 0 1 1 5 2c-2 1-2 1-2 3M12 17h.01"/>',
  menu: '<path d="M4 6h16M4 12h16M4 18h16"/>',
  trash: '<path d="M3 6h18M9 6V3h6v3M5 6l1 15h12l1-15M10 10v7M14 10v7"/>',
};
const icon = name => `<svg class="icon" viewBox="0 0 24 24" aria-hidden="true">${paths[name] || paths.calendar}</svg>`;
const escape = value => String(value ?? '').replace(/[&<>"']/g, char => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[char]));
const brand = () => `<div class="brand"><div class="brand-symbol">${icon('door')}</div><div><div class="brand-name">Sala<span>Fácil</span>!</div><div class="brand-caption">UNIFIP · Campus Patos</div></div></div>`;
const roomFor = id => ROOMS.find(room => room.id === id);
const ownerFor = id => USERS.find(user => user.id === id);
const dateLabel = (date, options = {}) => new Intl.DateTimeFormat('pt-BR', options).format(new Date(`${date}T12:00:00`));
const shortDate = date => dateLabel(date, { day: '2-digit', month: '2-digit', year: 'numeric' });
let storageWarning = '';
let state = readState();
let user = readSession();
let view = 'agenda';
let date = state.demoDate || initialDate();
let form = { roomId: 'lab01', date, start: '10:30', end: '11:30', title: '' };
let roomFilter = '';
let statusFilter = 'all';
let feedback = null;
let toastTimer;

function readState() {
  try {
    const saved = JSON.parse(localStorage.getItem(STORAGE_KEY));
    if (saved?.version === 1 && Array.isArray(saved.reservations) && Array.isArray(saved.notifications)) return saved;
  } catch {
    storageWarning = 'O armazenamento está indisponível. Seus testes durarão apenas nesta sessão.';
  }
  return createState();
}
function readSession() {
  try { return USERS.find(item => item.id === sessionStorage.getItem('salafacil-frontend-preview-session')) || null; }
  catch { return null; }
}
function refreshState() {
  try {
    const saved = JSON.parse(localStorage.getItem(STORAGE_KEY));
    if (saved?.version === 1 && Array.isArray(saved.reservations) && Array.isArray(saved.notifications)) state = saved;
  } catch { /* The in-memory demonstration still works when storage is unavailable. */ }
}
function persist() {
  try { localStorage.setItem(STORAGE_KEY, JSON.stringify(state)); }
  catch { storageWarning = 'Armazenamento indisponível: os dados ficam apenas nesta sessão.'; }
}
function toast(message) {
  clearTimeout(toastTimer);
  toastElement.textContent = message;
  toastElement.hidden = false;
  toastTimer = setTimeout(() => { toastElement.hidden = true; }, 4500);
}
function badge(item) {
  return item.status === 'confirmed'
    ? '<span class="tag green"><i class="dot"></i>Confirmada</span>'
    : '<span class="tag grey">Cancelada</span>';
}
function errorNotice(message) {
  return `<div class="notice error" role="alert">${icon('alert')}<div>${escape(message)}</div></div>`;
}
function render() {
  app.innerHTML = user ? shell() : login();
  if (user && view === 'agenda') {
    const calendar = document.querySelector('.calendar-scroll');
    if (calendar) calendar.scrollTop = 40;
  }
}
function login() {
  return `<section class="login-shell"><div class="login-layout">
    <section class="login-brand-panel"><div class="brand-content">
      <h1 class="brand-title">Sala<span>Fácil</span>!</h1>
      <p class="brand-description">Agende salas e auditórios de forma simples, fácil e eficiente.</p>
      <p class="preview-brand-note">UNIFIP · Demonstração do frontend</p>
    </div></section>
    <section class="login-form-panel"><div class="form-content" id="app-content">
      <header class="login-header"><h2>Explore a sua agenda</h2><p>Escolha uma conta de teste para conhecer as telas.</p></header>
      <div id="login-error" class="login-error"></div>
      <form id="login-form">
        <label for="email">E-mail da conta de demonstração</label>
        <input id="email" name="email" type="email" placeholder="joao@unifip.edu.br" autocomplete="off" required>
        <label for="password">Senha de demonstração</label>
        <div class="password-wrap"><input id="password" name="password" type="password" placeholder="Use a senha de teste abaixo" autocomplete="off" required><button type="button" class="password-toggle" data-action="toggle-password" aria-label="Mostrar senha">${icon('eye')}</button></div>
        <button type="submit" class="login-submit-button">Entrar na demonstração</button>
      </form>
      <div class="login-divider"><span>contas de teste</span></div>
      <div class="demo-buttons"><button class="demo-btn" data-action="fill-login" data-user="joao">${icon('user')}<span><strong>Usuário</strong><small>Reservar uma sala</small></span></button><button class="demo-btn" data-action="fill-login" data-user="admin">${icon('shield')}<span><strong>Administrador</strong><small>Gerenciar reservas</small></span></button></div>
      <div class="demo-password">Senha de teste: <code>${DEMO_PASSWORD}</code></div>
      <p class="preview-login-note">Salas, contas e reservas fictícias. Os dados ficam neste navegador. Esta tela simula o acesso e não utiliza a autenticação do projeto.</p>
    </div></section>
  </div></section>`;
}

function shell() {
  const unread = notificationsFor(state, user).filter(item => !item.read).length;
  const nav = (name, label, glyph, extra = '') => `<button class="nav-item ${view === name ? 'active' : ''}" data-action="navigate" data-view="${name}" ${view === name ? 'aria-current="page"' : ''}>${icon(glyph)}${label}${extra}</button>`;
  const labels = { agenda: 'Agenda de salas', mine: 'Minhas reservas', notifications: 'Notificações', admin: 'Gestão de reservas' };
  return `<aside class="sidebar" id="sidebar">${brand()}<nav aria-label="Navegação principal"><div class="nav-label">SEU CAMPUS, ORGANIZADO</div>
      ${nav('agenda', 'Agenda de salas', 'calendar')}${nav('mine', 'Minhas reservas', 'grid')}${nav('notifications', 'Notificações', 'bell', unread ? `<span class="count-badge">${unread}</span>` : '')}
      ${user.role === 'admin' ? nav('admin', 'Administração', 'shield') : ''}
    </nav><div class="sidebar-foot"><div class="campus-card">${icon('building')}<div><strong>UNIFIP</strong>Campus Patos · Paraíba</div></div><p class="prototype-note"><i class="dot"></i>Protótipo interativo<br>Dados fictícios · frontend</p></div></aside>
    <div class="workspace"><header class="topbar"><div class="breadcrumb">${icon('building')} UNIFIP <span>/</span> <strong>${labels[view]}</strong></div>
      <div class="mobile-brand"><button class="menu-toggle" data-action="menu" aria-label="Abrir navegação">${icon('menu')}</button><div>Sala<span>Fácil</span>!</div></div>
      <div class="topbar-right"><span class="private-label">${icon('lock')} Prévia local</span><div class="user-info"><div class="avatar">${escape(user.name.split(' ').slice(0,2).map(part=>part[0]).join(''))}</div><div><strong>${escape(user.name)}</strong><small>${user.role === 'admin' ? 'Administrador' : 'Usuário'}</small></div></div><button class="logout" data-action="logout" aria-label="Sair da demonstração">${icon('logout')}<span>Sair</span></button></div>
    </header><div id="app-content" class="main-content" role="region" aria-label="Conteúdo da demonstração"><div class="page-heading"><div><div class="eyebrow">${view === 'admin' ? 'ÁREA ADMINISTRATIVA' : 'AGENDAMENTO DE ESPAÇOS'}</div><h1>${labels[view]}</h1><p>${({agenda:'Encontre um espaço e faça o próximo encontro acontecer.',mine:'Seus próximos encontros, todos em um só lugar.',notifications:'Acompanhe as confirmações e alterações das suas reservas.',admin:'Acompanhe as reservas e mantenha a agenda organizada.'})[view]}</p></div><div class="heading-actions"><button class="btn soft compact" data-action="test-guide">${icon('help')} Roteiro de teste</button>${view !== 'notifications' ? `<button class="btn primary compact" data-action="new-reservation">${icon('plus')} Nova reserva</button>` : ''}</div></div>
      ${storageWarning ? `<div class="notice error" role="alert">${escape(storageWarning)}</div>` : ''}
      ${view === 'agenda' ? agenda() : view === 'mine' ? reservationList(false) : view === 'admin' ? reservationList(true) : notificationList()}
      <footer class="page-footer"><span>SalaFácil! · Um campus com mais possibilidades.</span><span>Horários de Brasília (UTC−3) · Demonstração</span></footer>
    </div></div>`;
}
function agenda() {
  const active = state.reservations.filter(item => item.date === date && item.status === 'confirmed');
  return `<section class="room-grid" aria-label="Salas disponíveis no protótipo">${ROOMS.map(room => {
    const count = active.filter(item => item.roomId === room.id).length;
    return `<button class="room-card ${roomFilter === room.id ? 'selected' : ''}" data-action="select-room" data-room="${room.id}" aria-pressed="${roomFilter === room.id}"><div class="room-top"><div class="room-icon">${icon(room.icon)}</div><span class="room-type">${room.type}</span></div><h3>${room.name}</h3><p>${room.location}</p><div class="room-bottom"><span>${icon('users')}${room.capacity} pessoas</span><span class="room-count">${count ? `${count} reserva${count > 1 ? 's' : ''} no dia` : 'Agenda livre no dia'}</span></div></button>`;
  }).join('')}</section>
    <div class="booking-layout"><section class="card calendar-card" aria-label="Agenda por sala e horário"><div class="calendar-toolbar"><div><h2>Agenda do dia</h2><small>Escolha um horário livre para reservar</small></div><div class="date-control"><button class="today-btn" data-action="today">Hoje</button><button class="icon-btn" data-action="previous-date" aria-label="Dia anterior">${icon('left')}</button><input class="date-input" type="date" id="agenda-date" aria-label="Data da agenda" value="${date}"><button class="icon-btn" data-action="next-date" aria-label="Próximo dia">${icon('right')}</button></div></div>
      <div class="calendar-subbar"><div class="date-title">${dateLabel(date,{weekday:'long',day:'numeric',month:'long'})}</div><div class="legend"><span><i class="legend-square"></i>Sua reserva</span><span><i class="legend-square other"></i>Ocupado</span></div></div>
      <div class="calendar-scroll" tabindex="0" aria-label="Grade de horários das 07 às 22 horas, role para ver mais">${calendar(active)}</div><div class="calendar-footer">${icon('info')} Toque em um espaço livre para preencher sua reserva. Horários de 30 minutos.</div>
    </section><aside class="booking-aside"><section class="card reserve-panel" id="reserve-panel"><div class="panel-title"><h2>Reserve seu espaço</h2>${icon('calendar')}</div><p>Escolha os detalhes. A confirmação é imediata.</p>${reservationForm()}</section><div class="help-card">${icon('shield')}<div><h3>Sem choque de horários</h3><p>A mesma sala não pode ter duas reservas no mesmo intervalo. O SalaFácil! verifica isso para você.</p></div></div></aside></div>`;
}
function calendar(active) {
  const times = Array.from({length:30}, (_, index) => `${String(7 + Math.floor(index / 2)).padStart(2,'0')}:${index % 2 ? '30' : '00'}`);
  const headers = ROOMS.map(room => `<div>${room.short}</div>`).join('');
  return `<div class="calendar-head"><div class="time-zone">UTC−3</div>${headers}</div><div class="timeline"><div class="time-axis">${times.map(time => `<div class="time-label">${time.endsWith(':00') ? time : ''}</div>`).join('')}</div>${ROOMS.map(room => `<div class="room-column" aria-label="${room.name}">${times.map(time => `<button class="slot" data-action="select-slot" data-room="${room.id}" data-time="${time}" aria-label="Reservar ${room.name}, ${time}, ${shortDate(date)}"></button>`).join('')}${active.filter(item => item.roomId === room.id).map(item => `<button class="event ${item.ownerId === user.id ? 'mine' : ''}" style="top:${(minutes(item.start)-420)/30*33}px;height:${(minutes(item.end)-minutes(item.start))/30*33-3}px" data-action="details" data-id="${escape(item.id)}" aria-label="Reserva ${escape(item.title)}, ${item.start} às ${item.end}"><span class="event-time">${item.start} – ${item.end}</span><strong>${escape(item.title)}</strong>${minutes(item.end)-minutes(item.start)>=60 ? `<small>${item.ownerId === user.id ? 'Sua reserva' : escape(ownerFor(item.ownerId)?.name)}</small>` : ''}</button>`).join('')}</div>`).join('')}</div>`;
}
function timeOptions(current, isEnd = false) {
  return Array.from({length:30}, (_, index) => {
    const value = 420 + (index + (isEnd ? 1 : 0)) * 30;
    const time = `${String(Math.floor(value / 60)).padStart(2,'0')}:${value % 60 ? '30' : '00'}`;
    return `<option value="${time}" ${time === current ? 'selected' : ''}>${time}</option>`;
  }).join('');
}
function reservationForm() {
  return `<form id="reservation-form"><div class="field"><label for="room">Sala</label><select id="room" name="roomId" required>${ROOMS.map(room => `<option value="${room.id}" ${room.id === form.roomId ? 'selected' : ''}>${room.name}</option>`).join('')}</select></div>
    <div class="panel-room-info">${icon('users')} Até ${roomFor(form.roomId).capacity} pessoas · ${roomFor(form.roomId).type}</div>
    <div class="field"><label for="reservation-date">Data</label><input type="date" id="reservation-date" name="date" value="${form.date}" min="${localDate()}" required></div>
    <div class="form-row"><div class="field"><label for="start">Início</label><select id="start" name="start" required>${timeOptions(form.start)}</select></div><div class="field"><label for="end">Término</label><select id="end" name="end" required>${timeOptions(form.end, true)}</select></div></div>
    <div class="field"><label for="purpose">Finalidade</label><input id="purpose" name="title" placeholder="Ex.: Reunião do projeto SalaFácil!" maxlength="100" required value="${escape(form.title)}"></div>
    <button class="btn primary full" id="reservation-submit" type="submit">${icon('check')} Confirmar reserva</button><div class="instant-note">${icon('checkCircle')} Sem espera por aprovação</div>
    <div id="booking-feedback" class="booking-feedback" tabindex="-1">${feedbackHtml()}</div>
  </form>`;
}
function feedbackHtml() {
  if (!feedback) return '';
  if (feedback.type === 'error') return errorNotice(feedback.message);
  return `<div class="notice success" role="status">${icon('checkCircle')}<div><strong>Reserva confirmada!</strong>${escape(feedback.message)}<br><button type="button" data-action="details" data-id="${escape(feedback.id)}">Ver reserva</button></div></div>`;
}
function reservationList(all) {
  if (all && user.role !== 'admin') return errorNotice('Acesso restrito a administradores.');
  const records = visibleReservations(state,user,all);
  const filtered = records.filter(item => statusFilter === 'all' || item.status === statusFilter).sort((a,b) => `${a.date}${a.start}`.localeCompare(`${b.date}${b.start}`));
  const count = records.filter(item => item.status === 'confirmed').length;
  return `${all ? `<div class="admin-banner">${icon('shield')} Você pode consultar e cancelar reservas de qualquer usuário.</div><div class="summary-strip"><div class="summary-item"><span>Reservas confirmadas</span><strong>${count}</strong></div><div class="summary-item"><span>Salas no campus</span><strong>${ROOMS.length}</strong></div><div class="summary-item"><span>Reservas canceladas</span><strong>${records.length-count}</strong></div></div>` : ''}
    <section class="card"><div class="list-toolbar"><h2>${all ? 'Todas as reservas' : 'Suas reservas'} <span class="muted small">(${records.length})</span></h2><select class="filter-select" id="status-filter" aria-label="Filtrar por situação"><option value="all" ${statusFilter==='all'?'selected':''}>Todas as situações</option><option value="confirmed" ${statusFilter==='confirmed'?'selected':''}>Confirmadas</option><option value="cancelled" ${statusFilter==='cancelled'?'selected':''}>Canceladas</option></select></div>
    ${filtered.length ? `<div class="table-wrap"><table class="reservations-table"><thead><tr><th>Sala / Finalidade</th><th>Data e horário</th>${all?'<th>Responsável</th>':''}<th>Situação</th><th><span class="muted">Detalhes</span></th></tr></thead><tbody>${filtered.map(item => `<tr><td><strong>${roomFor(item.roomId)?.name}</strong><small>${escape(item.title)}</small></td><td>${shortDate(item.date)}<small>${item.start} – ${item.end}</small></td>${all?`<td>${escape(ownerFor(item.ownerId)?.name)}</td>`:''}<td>${badge(item)}</td><td><button class="btn compact" data-action="details" data-id="${escape(item.id)}">Ver reserva ${icon('right')}</button></td></tr>`).join('')}</tbody></table></div>` : empty('calendar', statusFilter==='all'?'Sua próxima reserva começa aqui':'Nenhuma reserva nesta situação',statusFilter==='all'?'Escolha uma sala na agenda e confirme seu horário.':'Altere o filtro para consultar as outras reservas.',true)}
    </section>`;
}
function empty(glyph,title,message,action=false) {
  return `<div class="empty-state"><div class="empty-icon">${icon(glyph)}</div><h3>${title}</h3><p>${message}</p>${action?`<button class="btn primary compact" data-action="new-reservation">${icon('plus')} Reservar uma sala</button>`:''}</div>`;
}
function notificationList() {
  const items = notificationsFor(state,user);
  const unread = items.some(item => !item.read);
  return `<section class="card"><div class="list-toolbar"><h2>Suas atualizações</h2><button class="btn text small" data-action="mark-read" ${unread?'':'disabled'}>${icon('check')} Marcar todas como lidas</button></div>${items.length ? items.map(item => `<article class="notification-row ${!item.read?'unread':''}"><div class="notification-icon">${icon(item.title.includes('confirmada')?'checkCircle':'calendar')}</div><div><h3>${escape(item.title)}</h3><p>${escape(item.message)}</p><small>${new Intl.DateTimeFormat('pt-BR',{dateStyle:'short',timeStyle:'short',timeZone:'America/Fortaleza'}).format(new Date(item.createdAt))}</small><button class="btn text small" data-action="details" data-id="${escape(item.reservationId)}">Ver reserva ${icon('right')}</button></div>${!item.read?'<span class="unread-dot" aria-label="Não lida"></span>':''}</article>`).join('') : empty('bell','Tudo tranquilo por aqui','Confirmações e cancelamentos aparecerão nesta página.')}</section>`;
}
function showDialog(content) {
  dialog.innerHTML = content;
  if (!dialog.open) dialog.showModal();
}
function modalHeader(title) {
  return `<div class="dialog-header"><h2 id="dialog-title">${title}</h2><button class="icon-btn" data-action="close-dialog" aria-label="Fechar">${icon('close')}</button></div>`;
}
function showDetails(id) {
  const item = state.reservations.find(record => record.id === id);
  if (!item) return toast('Reserva não encontrada.');
  showDialog(`${modalHeader('Detalhes da reserva')}<div class="dialog-body">${badge(item)}<h3>${roomFor(item.roomId)?.name}</h3><p>${escape(item.title)}</p><dl class="detail-grid"><div><dt>Data</dt><dd>${shortDate(item.date)}</dd></div><div><dt>Horário</dt><dd>${item.start} – ${item.end}</dd></div><div><dt>Responsável</dt><dd>${escape(ownerFor(item.ownerId)?.name)}</dd></div><div><dt>Protocolo</dt><dd>${escape(item.id)}</dd></div></dl>
      ${!canCancel(user,item) && item.status==='confirmed' ? '<div class="notice info">Somente o responsável ou um administrador pode cancelar esta reserva.</div>' : ''}
      ${item.status==='cancelled' ? '<div class="notice info">A reserva foi cancelada e o horário está disponível para novas reservas.</div>' : ''}
      <div class="dialog-actions wrap">${item.status==='confirmed'?`<button class="btn compact" data-action="try-conflict" data-id="${escape(item.id)}">Testar este horário</button>`:''}${canCancel(user,item)?`<button class="btn compact" data-action="confirm-cancel" data-id="${escape(item.id)}">${icon('trash')} Cancelar reserva</button>`:''}<button class="btn primary compact" data-action="close-dialog">Fechar</button></div></div>`);
}
function showCancel(id) {
  const item = state.reservations.find(record => record.id === id);
  if (!item || !canCancel(user,item)) return toast('Você não pode cancelar esta reserva.');
  showDialog(`${modalHeader('Cancelar esta reserva?')}<div class="dialog-body"><p class="cancel-note">${roomFor(item.roomId).name} · ${shortDate(item.date)} · ${item.start}–${item.end}</p><p style="margin-top:12px">O horário será liberado imediatamente. O responsável receberá uma notificação no sistema.</p><div class="dialog-actions"><button class="btn compact" data-action="details" data-id="${escape(id)}">Manter reserva</button><button class="btn danger compact" data-action="cancel" data-id="${escape(id)}">Confirmar cancelamento</button></div></div>`);
}
function showGuide() {
  showDialog(`${modalHeader('Teste o SalaFácil!')}<ol class="test-steps"><li><strong>Faça uma reserva.</strong><br>Escolha uma sala, uma data futura, início, término e finalidade. Clique em “Confirmar reserva”.</li><li><strong>Tente um conflito.</strong><br>Abra uma reserva na agenda e clique em “Testar este horário”. Confirme novamente: o sistema bloqueia o intervalo.</li><li><strong>Cancele e reserve de novo.</strong><br>Abra sua reserva em “Minhas reservas”, cancele e tente o mesmo horário. Ele estará livre.</li><li><strong>Compare os perfis.</strong><br>Saia e entre como administrador. Em “Administração”, ele também pode cancelar reservas de outros usuários.</li></ol><div class="test-note">Usuário: <code>joao@unifip.edu.br</code><br>Administrador: <code>admin@unifip.edu.br</code><br>Senha: <code>${DEMO_PASSWORD}</code><br>As notificações ficam no sistema. Os dados são locais a este navegador.</div><div class="dialog-actions"><button class="btn primary compact" data-action="close-dialog">Começar o teste ${icon('arrow')}</button></div>`);
}
function readForm() {
  const element = document.querySelector('#reservation-form');
  if (element) form = Object.fromEntries(new FormData(element));
}
function focusForm() {
  const panel = document.querySelector('#reserve-panel');
  panel?.scrollIntoView({behavior:'smooth',block:'nearest'});
  document.querySelector('#purpose')?.focus({preventScroll:true});
}
function selectDate(value) {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(value)) return;
  readForm(); date = value; form.date = value; feedback = null; render();
}

// Actions are delegated so rerendering never duplicates event handlers.
document.addEventListener('click', event => {
  const button = event.target.closest('[data-action]');
  if (!button) return;
  const action = button.dataset.action;
  if (action === 'fill-login') {
    const account = USERS.find(item => item.id === button.dataset.user);
    document.querySelector('#email').value = account.email;
    document.querySelector('#password').value = DEMO_PASSWORD;
    document.querySelector('#login-error').innerHTML = '';
    document.querySelector('#login-form button[type="submit"]').focus();
    return;
  }
  if (action === 'toggle-password') {
    const input = document.querySelector('#password');
    input.type = input.type === 'password' ? 'text' : 'password';
    button.setAttribute('aria-label',input.type==='password'?'Mostrar senha':'Ocultar senha');
    return;
  }
  if (action === 'close-dialog') { dialog.close(); return; }
  if (!user) return;
  if (action === 'logout') {
    user = null; try { sessionStorage.removeItem('salafacil-frontend-preview-session'); } catch {}
    view = 'agenda'; feedback = null; dialog.close(); toastElement.hidden = true; render(); return;
  }
  if (action === 'menu') { document.querySelector('#sidebar').classList.toggle('open'); return; }
  if (action === 'navigate') {
    if (button.dataset.view === 'admin' && user.role !== 'admin') return toast('Acesso restrito a administradores.');
    readForm(); view = button.dataset.view; statusFilter = 'all'; render(); return;
  }
  if (action === 'test-guide') return showGuide();
  if (action === 'new-reservation') { readForm(); view='agenda'; feedback=null; render(); focusForm(); return; }
  if (action === 'previous-date') return selectDate(shiftDate(date,-1));
  if (action === 'next-date') return selectDate(shiftDate(date,1));
  if (action === 'today') return selectDate(localDate());
  if (action === 'select-room') { readForm(); roomFilter=button.dataset.room; form.roomId=roomFilter; feedback=null; render(); focusForm(); return; }
  if (action === 'select-slot') {
    readForm(); form.roomId=button.dataset.room; roomFilter=form.roomId; form.date=date; form.start=button.dataset.time;
    const end=minutes(form.start)+60;
    form.end=`${String(Math.floor(Math.min(end,1320)/60)).padStart(2,'0')}:${Math.min(end,1320)%60?'30':'00'}`;
    feedback=null; render(); focusForm(); return;
  }
  if (action === 'details') return showDetails(button.dataset.id);
  if (action === 'confirm-cancel') return showCancel(button.dataset.id);
  if (action === 'try-conflict') {
    const item=state.reservations.find(record=>record.id===button.dataset.id);
    form={roomId:item.roomId,date:item.date,start:item.start,end:item.end,title:'Teste de conflito'};
    date=item.date; roomFilter=item.roomId; view='agenda'; feedback=null; dialog.close(); render();
    document.querySelector('#reservation-submit')?.focus();
    toast('Horário preenchido. Confirme a reserva para testar o bloqueio.'); return;
  }
  if (action === 'cancel') {
    try { refreshState(); cancelReservation(state,user,button.dataset.id); persist(); dialog.close(); feedback=null; render(); toast('Reserva cancelada. O horário foi liberado.'); }
    catch(error) { toast(error instanceof BookingError?error.message:'Não foi possível cancelar a reserva.'); }
    return;
  }
  if (action === 'mark-read') { refreshState(); markNotificationsRead(state,user); persist(); render(); toast('Notificações marcadas como lidas.'); }
});

document.addEventListener('submit',event=>{
  if(event.target.id==='login-form') {
    event.preventDefault();
    const data=new FormData(event.target);
    try {
      user=authenticate(data.get('email'),data.get('password'));
      try { sessionStorage.setItem('salafacil-frontend-preview-session',user.id); } catch {}
      refreshState(); view='agenda'; render(); toast(`Bem-vindo${user.role==='admin'?'':' de volta'}, ${user.name}!`);
    } catch(error) {
      document.querySelector('#login-error').innerHTML=errorNotice(error.message);
      document.querySelector('#password').value=''; document.querySelector('#password').focus();
    }
  }
  if(event.target.id==='reservation-form') {
    event.preventDefault(); readForm();
    try {
      refreshState(); const item=reserve(state,user,form); persist(); date=form.date;
      feedback={type:'success',message:`${roomFor(item.roomId).name} · ${item.start}–${item.end}`,id:item.id};
      render(); toast('Reserva confirmada imediatamente.');
    } catch(error) {
      feedback={type:'error',message:error instanceof BookingError?error.message:'Não foi possível confirmar a reserva.'};
      document.querySelector('#booking-feedback').innerHTML=feedbackHtml();
    }
    document.querySelector('#booking-feedback')?.focus({preventScroll:false});
  }
});
document.addEventListener('change',event=>{
  if(event.target.id==='agenda-date') selectDate(event.target.value);
  if(event.target.id==='status-filter') { statusFilter=event.target.value; render(); }
  if(event.target.closest('#reservation-form')) {
    readForm(); feedback=null;
    document.querySelector('#booking-feedback').innerHTML='';
    if(event.target.id==='room') {
      roomFilter=form.roomId;
      document.querySelector('.panel-room-info').innerHTML=`${icon('users')} Até ${roomFor(form.roomId).capacity} pessoas · ${roomFor(form.roomId).type}`;
      document.querySelectorAll('.room-card').forEach(card=>{card.classList.toggle('selected',card.dataset.room===form.roomId);card.setAttribute('aria-pressed',card.dataset.room===form.roomId);});
    }
    if(event.target.id==='start' && form.end<=form.start) {
      const value=Math.min(minutes(form.start)+60,1320);
      form.end=`${String(Math.floor(value/60)).padStart(2,'0')}:${value%60?'30':'00'}`;
      document.querySelector('#end').value=form.end;
    }
  }
});
window.addEventListener('storage',event=>{
  if(event.key===STORAGE_KEY) { readForm(); refreshState(); if(user) render(); }
});
render();
