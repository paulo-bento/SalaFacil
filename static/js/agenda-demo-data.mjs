// Dados e regras simulados; substituir por integração com o backend Django.
export const STORAGE_KEY = 'salafacil-frontend-preview-v1';
export const DEMO_PASSWORD = 'SalaFacil123!';
export const USERS = Object.freeze([
  { id: 'joao', name: 'João Paulo', email: 'joao@unifip.edu.br', role: 'user' },
  { id: 'admin', name: 'Administrador', email: 'admin@unifip.edu.br', role: 'admin' },
  { id: 'marina', name: 'Marina Costa', email: 'marina@unifip.edu.br', role: 'user' },
]);
export const ROOMS = Object.freeze([
  { id: 'lab01', name: 'Laboratório 01', short: 'Lab. 01', type: 'Informática', location: 'Bloco de Medicina · 1º andar', capacity: 32, resources: 'Computadores · Projetor', icon: 'monitor' },
  { id: 'sala02', name: 'Sala Multiuso 02', short: 'Multiuso 02', type: 'Sala de aula', location: 'Bloco A · Térreo', capacity: 24, resources: 'Projetor · Quadro branco', icon: 'presentation' },
  { id: 'sala03', name: 'Sala de Estudos 03', short: 'Estudos 03', type: 'Estudo em grupo', location: 'Biblioteca · 1º andar', capacity: 12, resources: 'Mesa de reunião · Quadro branco', icon: 'book' },
]);

export class BookingError extends Error {
  constructor(message, code = 'invalid') {
    super(message);
    this.name = 'BookingError';
    this.code = code;
  }
}

export function localDate(now = new Date()) {
  return new Intl.DateTimeFormat('en-CA', {
    timeZone: 'America/Fortaleza', year: 'numeric', month: '2-digit', day: '2-digit',
  }).format(now);
}

export function shiftDate(date, days) {
  const value = new Date(`${date}T12:00:00Z`);
  value.setUTCDate(value.getUTCDate() + days);
  return value.toISOString().slice(0, 10);
}

export function initialDate(now = new Date()) {
  let date = shiftDate(localDate(now), 1);
  while ([0, 6].includes(new Date(`${date}T12:00:00Z`).getUTCDay())) date = shiftDate(date, 1);
  return date;
}

export function authenticate(email, password) {
  const normalized = email.trim().toLowerCase();
  const user = USERS.find(item => item.email === normalized);
  if (!user || password !== DEMO_PASSWORD) throw new BookingError('E-mail ou senha incorretos. Use uma das contas de demonstração.', 'credentials');
  return user;
}

export function authenticatedUser(actor) {
  const user = USERS.find(item => item.id === actor?.id);
  if (!user) throw new BookingError('Entre na sua conta para continuar.', 'unauthorized');
  return user;
}

export function createState(date = initialDate()) {
  return {
    version: 1,
    demoDate: date,
    reservations: [
      { id: 'SF-1001', roomId: 'lab01', date, start: '09:00', end: '10:30', title: 'Aula de Desenvolvimento Web', ownerId: 'marina', status: 'confirmed', createdAt: new Date().toISOString() },
      { id: 'SF-1002', roomId: 'sala02', date, start: '14:00', end: '15:30', title: 'Reunião de projeto', ownerId: 'admin', status: 'confirmed', createdAt: new Date().toISOString() },
    ],
    notifications: [],
  };
}

export function canCancel(actor, reservation) {
  const user = USERS.find(item => item.id === actor?.id);
  return Boolean(user && reservation.status === 'confirmed' && (user.role === 'admin' || reservation.ownerId === user.id));
}

export function visibleReservations(state, actor, all = false) {
  const user = authenticatedUser(actor);
  if (all && user.role !== 'admin') throw new BookingError('Apenas administradores podem gerenciar todas as reservas.', 'forbidden');
  return state.reservations.filter(item => all || item.ownerId === user.id);
}

function validDate(value) {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(value)) return false;
  const date = new Date(`${value}T12:00:00Z`);
  return !Number.isNaN(date.valueOf()) && date.toISOString().slice(0, 10) === value;
}

export function minutes(time) {
  const [hours, mins] = time.split(':').map(Number);
  return hours * 60 + mins;
}

export function findConflict(state, roomId, date, start, end) {
  return state.reservations.find(item => item.status === 'confirmed' && item.roomId === roomId && item.date === date && start < item.end && end > item.start);
}

function notify(state, userId, title, message, reservationId) {
  state.notifications.unshift({ id: crypto.randomUUID(), userId, title, message, reservationId, read: false, createdAt: new Date().toISOString() });
}

export function reserve(state, actor, data, now = new Date()) {
  const user = authenticatedUser(actor);
  if (!ROOMS.some(room => room.id === data.roomId)) throw new BookingError('Selecione uma sala válida.');
  if (!validDate(data.date)) throw new BookingError('Selecione uma data válida.');
  if (data.date < localDate(now)) throw new BookingError('Escolha uma data a partir de hoje.');
  if (![data.start, data.end].every(time => /^(?:[01]\d|2[0-3]):(?:00|30)$/.test(time))) throw new BookingError('Use horários em intervalos de 30 minutos.');
  if (data.start < '07:00' || data.end > '22:00' || data.start >= data.end) throw new BookingError('O término deve ser após o início, entre 07:00 e 22:00.');
  if (new Date(`${data.date}T${data.start}:00-03:00`) <= now) throw new BookingError('Esse horário já passou. Escolha um horário futuro.');
  const title = String(data.title ?? '').trim();
  if (!title || title.length > 100) throw new BookingError('Informe uma finalidade de até 100 caracteres.');
  if (findConflict(state, data.roomId, data.date, data.start, data.end)) throw new BookingError('Horário indisponível. Já existe uma reserva para esta sala nesse intervalo. Escolha outro horário ou outra sala.', 'conflict');
  const reservation = {
    id: `SF-${crypto.randomUUID().slice(0, 8).toUpperCase()}`,
    roomId: data.roomId, date: data.date, start: data.start, end: data.end,
    title, ownerId: user.id, status: 'confirmed', createdAt: now.toISOString(),
  };
  state.reservations.push(reservation);
  const room = ROOMS.find(item => item.id === data.roomId);
  notify(state, user.id, 'Reserva confirmada', `${room.name} · ${data.date.split('-').reverse().join('/')} · ${data.start}–${data.end}`, reservation.id);
  return reservation;
}

export function cancelReservation(state, actor, id) {
  const user = authenticatedUser(actor);
  const reservation = state.reservations.find(item => item.id === id);
  if (!reservation) throw new BookingError('Reserva não encontrada.');
  if (!canCancel(user, reservation)) throw new BookingError('Você não tem permissão para cancelar esta reserva ou ela já foi cancelada.', 'forbidden');
  reservation.status = 'cancelled';
  reservation.cancelledBy = user.id;
  reservation.cancelledAt = new Date().toISOString();
  const room = ROOMS.find(item => item.id === reservation.roomId);
  const message = `${room.name} · ${reservation.date.split('-').reverse().join('/')} · ${reservation.start}–${reservation.end}. O horário foi liberado.`;
  notify(state, reservation.ownerId, 'Reserva cancelada', message, reservation.id);
  if (user.id !== reservation.ownerId) notify(state, user.id, 'Cancelamento realizado', message, reservation.id);
  return reservation;
}

export function notificationsFor(state, actor) {
  const user = authenticatedUser(actor);
  return state.notifications.filter(item => item.userId === user.id);
}

export function markNotificationsRead(state, actor) {
  notificationsFor(state, actor).forEach(item => { item.read = true; });
}
