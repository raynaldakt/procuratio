const state = { token: "", me: null };

const el = {
  apiBase: document.getElementById("apiBase"),
  email: document.getElementById("email"),
  password: document.getElementById("password"),
  authState: document.getElementById("authState"),
  statsPeriod: document.getElementById("statsPeriod"),
  statsPreview: document.getElementById("statsPreview"),
  notifStatus: document.getElementById("notifStatus"),
  notifMeta: document.getElementById("notifMeta"),
  notifBody: document.getElementById("notifBody"),
  ticketsBody: document.getElementById("ticketsBody"),
  appointmentsBody: document.getElementById("appointmentsBody"),
  topProductsPreview: document.getElementById("topProductsPreview"),
  topServicesPreview: document.getElementById("topServicesPreview"),
  kpiNetRevenue: document.getElementById("kpiNetRevenue"),
  kpiGrossRevenue: document.getElementById("kpiGrossRevenue"),
  kpiTicketsPaid: document.getElementById("kpiTicketsPaid"),
  kpiAppointments: document.getElementById("kpiAppointments"),
  kpiNewCustomers: document.getElementById("kpiNewCustomers"),
  kpiLoyalty: document.getElementById("kpiLoyalty"),
  loginBtn: document.getElementById("loginBtn"),
  refreshAllBtn: document.getElementById("refreshAllBtn"),
  loadStatsBtn: document.getElementById("loadStatsBtn"),
  loadNotificationsBtn: document.getElementById("loadNotificationsBtn"),
};

function fmtEur(cents) {
  return `${(Number(cents || 0) / 100).toFixed(2)} EUR`;
}

function apiBase() {
  return el.apiBase.value.trim().replace(/\/$/, "");
}

function setTableRows(tbody, rows, emptyMessage, rowFn) {
  tbody.innerHTML = "";
  if (!rows || rows.length === 0) {
    const tr = document.createElement("tr");
    const td = document.createElement("td");
    td.colSpan = 5;
    td.textContent = emptyMessage;
    tr.appendChild(td);
    tbody.appendChild(tr);
    return;
  }
  for (const row of rows) {
    tbody.appendChild(rowFn(row));
  }
}

function td(text) {
  const cell = document.createElement("td");
  cell.textContent = text;
  return cell;
}

async function api(path, options = {}) {
  const headers = new Headers(options.headers || {});
  headers.set("Content-Type", "application/json");
  if (state.token) headers.set("Authorization", `Bearer ${state.token}`);

  const response = await fetch(`${apiBase()}${path}`, { ...options, headers });
  const text = await response.text();
  let payload = {};
  if (text) {
    try {
      payload = JSON.parse(text);
    } catch (_) {
      payload = { raw: text };
    }
  }
  if (!response.ok) {
    throw new Error(payload.detail || payload.raw || `${response.status}`);
  }
  return payload;
}

async function login() {
  el.authState.textContent = "Authenticating...";
  try {
    const res = await api("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email: el.email.value.trim(), password: el.password.value }),
      headers: {},
    });
    state.token = res.access_token || "";
    state.me = await api("/auth/me", { method: "GET" });
    el.authState.textContent = `Authenticated as ${state.me.email} (${state.me.role})`;
  } catch (err) {
    el.authState.textContent = `Login failed: ${err.message}`;
  }
}

async function loadStats() {
  el.statsPreview.textContent = "Loading stats...";
  try {
    const period = encodeURIComponent(el.statsPeriod.value);
    const payload = await api(`/stats/overview?period=${period}`, { method: "GET" });
    el.kpiNetRevenue.textContent = fmtEur(payload.net_revenue_cents);
    el.kpiGrossRevenue.textContent = fmtEur(payload.gross_revenue_cents);
    el.kpiTicketsPaid.textContent = String(payload.tickets_paid_count);
    el.kpiAppointments.textContent = String(payload.appointments_count);
    el.kpiNewCustomers.textContent = String(payload.new_customers_count);
    el.kpiLoyalty.textContent = String(payload.loyalty_points_earned);
    el.topProductsPreview.textContent = JSON.stringify(payload.top_products, null, 2);
    el.topServicesPreview.textContent = JSON.stringify(payload.top_services, null, 2);
    el.statsPreview.textContent = JSON.stringify(payload, null, 2);
  } catch (err) {
    el.statsPreview.textContent = `Stats error: ${err.message}`;
  }
}

async function loadNotifications() {
  el.notifMeta.textContent = "Loading queue...";
  try {
    const status = encodeURIComponent(el.notifStatus.value);
    const query = status ? `?status=${status}` : "";
    const payload = await api(`/campaigns/notifications${query}`, { method: "GET" });
    const rows = payload.slice(0, 30);
    el.notifMeta.textContent = `${payload.length} notifications loaded`;
    setTableRows(el.notifBody, rows, "No notifications", (row) => {
      const tr = document.createElement("tr");
      tr.append(td(String(row.id)));
      tr.append(td(row.channel || "-"));
      tr.append(td(row.kind || "-"));
      tr.append(td(row.status || "-"));
      tr.append(td(new Date(row.scheduled_for).toLocaleString()));
      return tr;
    });
  } catch (err) {
    el.notifMeta.textContent = `Queue error: ${err.message}`;
  }
}

async function loadTickets() {
  try {
    const payload = await api("/sales/tickets", { method: "GET" });
    const rows = payload.slice(0, 20);
    setTableRows(el.ticketsBody, rows, "No tickets", (row) => {
      const tr = document.createElement("tr");
      tr.append(td(String(row.id)));
      tr.append(td(row.status || "-"));
      tr.append(td(fmtEur(row.discount_cents)));
      tr.append(td(row.payment_method || "-"));
      tr.append(td(new Date(row.updated_at).toLocaleString()));
      return tr;
    });
  } catch (err) {
    setTableRows(el.ticketsBody, [], `Ticket error: ${err.message}`, () => document.createElement("tr"));
  }
}

async function loadAppointments() {
  if (!state.me) return;
  try {
    const payload = await api(`/appointments/users/${state.me.id}`, { method: "GET" });
    const rows = payload.slice(0, 20);
    setTableRows(el.appointmentsBody, rows, "No appointments", (row) => {
      const tr = document.createElement("tr");
      tr.append(td(String(row.id)));
      tr.append(td(row.status || "-"));
      tr.append(td(String(row.customer_user_id)));
      tr.append(td(String(row.employee_user_id ?? "-")));
      tr.append(td(new Date(row.start_at).toLocaleString()));
      return tr;
    });
  } catch (err) {
    setTableRows(el.appointmentsBody, [], `Appointments error: ${err.message}`, () => document.createElement("tr"));
  }
}

async function refreshAll() {
  if (!state.token) {
    el.authState.textContent = "Login first";
    return;
  }
  await Promise.all([loadStats(), loadNotifications(), loadTickets(), loadAppointments()]);
}

el.loginBtn.addEventListener("click", login);
el.refreshAllBtn.addEventListener("click", refreshAll);
el.loadStatsBtn.addEventListener("click", loadStats);
el.loadNotificationsBtn.addEventListener("click", loadNotifications);
