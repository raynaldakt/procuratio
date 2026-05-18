const state = {
  token: "",
  me: null,
  currentTicketId: null,
  planning: {
    catalogLoaded: false,
    employees: [],
    servicesById: new Map(),
  },
};

const el = {
  apiBase: document.getElementById("apiBase"),
  email: document.getElementById("email"),
  password: document.getElementById("password"),
  authState: document.getElementById("authState"),
  statsPeriod: document.getElementById("statsPeriod"),

  tabButtons: Array.from(document.querySelectorAll(".tab-btn")),

  refreshAllBtn: document.getElementById("refreshAllBtn"),
  loginBtn: document.getElementById("loginBtn"),
  logoutBtn: document.getElementById("logoutBtn"),

  kpiNetRevenue: document.getElementById("kpiNetRevenue"),
  kpiGrossRevenue: document.getElementById("kpiGrossRevenue"),
  kpiTicketsPaid: document.getElementById("kpiTicketsPaid"),
  kpiAppointments: document.getElementById("kpiAppointments"),
  kpiNewCustomers: document.getElementById("kpiNewCustomers"),
  kpiLoyalty: document.getElementById("kpiLoyalty"),

  ticketsBody: document.getElementById("ticketsBody"),
  appointmentsBody: document.getElementById("appointmentsBody"),
  topProductsPreview: document.getElementById("topProductsPreview"),
  topServicesPreview: document.getElementById("topServicesPreview"),
  statsPreview: document.getElementById("statsPreview"),

  planningView: document.getElementById("planningView"),
  planningDate: document.getElementById("planningDate"),
  planningEmployee: document.getElementById("planningEmployee"),
  planningPrevBtn: document.getElementById("planningPrevBtn"),
  planningTodayBtn: document.getElementById("planningTodayBtn"),
  planningNextBtn: document.getElementById("planningNextBtn"),
  planningLoadBtn: document.getElementById("planningLoadBtn"),
  planningState: document.getElementById("planningState"),
  planningSummary: document.getElementById("planningSummary"),
  planningTimeline: document.getElementById("planningTimeline"),
  planningGrid: document.getElementById("planningGrid"),

  ticketNotes: document.getElementById("ticketNotes"),
  createTicketBtn: document.getElementById("createTicketBtn"),
  ticketState: document.getElementById("ticketState"),
  ticketId: document.getElementById("ticketId"),
  loadTicketBtn: document.getElementById("loadTicketBtn"),
  ticketCustomerId: document.getElementById("ticketCustomerId"),
  setTicketCustomerBtn: document.getElementById("setTicketCustomerBtn"),
  ticketDiscount: document.getElementById("ticketDiscount"),
  setTicketDiscountBtn: document.getElementById("setTicketDiscountBtn"),
  suspendTicketBtn: document.getElementById("suspendTicketBtn"),
  resumeTicketBtn: document.getElementById("resumeTicketBtn"),
  loadPosCatalogBtn: document.getElementById("loadPosCatalogBtn"),
  loadServicesBtn: document.getElementById("loadServicesBtn"),
  posProductSelect: document.getElementById("posProductSelect"),
  posProductQty: document.getElementById("posProductQty"),
  addProductLineBtn: document.getElementById("addProductLineBtn"),
  posServiceSelect: document.getElementById("posServiceSelect"),
  posServiceQty: document.getElementById("posServiceQty"),
  addServiceLineBtn: document.getElementById("addServiceLineBtn"),
  posPaymentMethod: document.getElementById("posPaymentMethod"),
  checkoutTicketBtn: document.getElementById("checkoutTicketBtn"),
  checkoutState: document.getElementById("checkoutState"),
  ticketPreview: document.getElementById("ticketPreview"),

  campaignName: document.getElementById("campaignName"),
  campaignChannel: document.getElementById("campaignChannel"),
  campaignTargetMode: document.getElementById("campaignTargetMode"),
  campaignSubject: document.getElementById("campaignSubject"),
  campaignMessage: document.getElementById("campaignMessage"),
  campaignMinPoints: document.getElementById("campaignMinPoints"),
  sendCampaignBtn: document.getElementById("sendCampaignBtn"),
  sendBirthdayBtn: document.getElementById("sendBirthdayBtn"),
  campaignState: document.getElementById("campaignState"),
  loadCampaignsBtn: document.getElementById("loadCampaignsBtn"),
  campaignsPreview: document.getElementById("campaignsPreview"),
  notifStatus: document.getElementById("notifStatus"),
  loadNotificationsBtn: document.getElementById("loadNotificationsBtn"),
  notifMeta: document.getElementById("notifMeta"),
  notifBody: document.getElementById("notifBody"),
  notifId: document.getElementById("notifId"),
  notifUpdateStatus: document.getElementById("notifUpdateStatus"),
  notifFailureReason: document.getElementById("notifFailureReason"),
  markNotificationBtn: document.getElementById("markNotificationBtn"),
  notifState: document.getElementById("notifState"),
  notifUpdatePreview: document.getElementById("notifUpdatePreview"),

  voucherType: document.getElementById("voucherType"),
  voucherServiceId: document.getElementById("voucherServiceId"),
  voucherAmountCents: document.getElementById("voucherAmountCents"),
  voucherPurchaser: document.getElementById("voucherPurchaser"),
  voucherRecipient: document.getElementById("voucherRecipient"),
  voucherRecipientEmail: document.getElementById("voucherRecipientEmail"),
  voucherEffectiveDate: document.getElementById("voucherEffectiveDate"),
  voucherDurationDays: document.getElementById("voucherDurationDays"),
  createVoucherBtn: document.getElementById("createVoucherBtn"),
  voucherState: document.getElementById("voucherState"),
  voucherStatusFilter: document.getElementById("voucherStatusFilter"),
  voucherCodeFilter: document.getElementById("voucherCodeFilter"),
  loadVouchersBtn: document.getElementById("loadVouchersBtn"),
  vouchersPreview: document.getElementById("vouchersPreview"),
  redeemVoucherId: document.getElementById("redeemVoucherId"),
  redeemAmountCents: document.getElementById("redeemAmountCents"),
  redeemNote: document.getElementById("redeemNote"),
  redeemVoucherBtn: document.getElementById("redeemVoucherBtn"),
  redeemPreview: document.getElementById("redeemPreview"),

  customerUserId: document.getElementById("customerUserId"),
  loadCustomerProfileBtn: document.getElementById("loadCustomerProfileBtn"),
  customerProfilePreview: document.getElementById("customerProfilePreview"),
  customerStaffNotes: document.getElementById("customerStaffNotes"),
  saveCustomerNotesBtn: document.getElementById("saveCustomerNotesBtn"),
  customerState: document.getElementById("customerState"),
  subscriptionPlanName: document.getElementById("subscriptionPlanName"),
  subscriptionAmountCents: document.getElementById("subscriptionAmountCents"),
  subscriptionDurationDays: document.getElementById("subscriptionDurationDays"),
  subscriptionStartsOn: document.getElementById("subscriptionStartsOn"),
  subscriptionPaymentMethod: document.getElementById("subscriptionPaymentMethod"),
  subscriptionBonusPoints: document.getElementById("subscriptionBonusPoints"),
  createSubscriptionBtn: document.getElementById("createSubscriptionBtn"),
  loadSubscriptionsBtn: document.getElementById("loadSubscriptionsBtn"),
  cancelSubscriptionId: document.getElementById("cancelSubscriptionId"),
  cancelSubscriptionBtn: document.getElementById("cancelSubscriptionBtn"),
  subscriptionsPreview: document.getElementById("subscriptionsPreview"),
  subscriptionState: document.getElementById("subscriptionState"),
};

function apiBase() {
  return el.apiBase.value.trim().replace(/\/$/, "");
}

function fmtEur(cents) {
  return `${(Number(cents || 0) / 100).toFixed(2)} EUR`;
}

function safeText(value) {
  return String(value ?? "").replace(/[&<>\"']/g, (ch) => {
    const map = { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" };
    return map[ch] || ch;
  });
}

function setState(node, message, tone = "") {
  node.textContent = message;
  node.classList.remove("ok", "err", "warn");
  if (tone) {
    node.classList.add(tone);
  }
}

function ensureAuth() {
  if (!state.token) {
    throw new Error("Connecte-toi d'abord");
  }
}

function currentTicketId() {
  const raw = Number(el.ticketId.value || "0");
  if (raw > 0) {
    return raw;
  }
  if (state.currentTicketId) {
    return state.currentTicketId;
  }
  throw new Error("Aucun ticket actif");
}

async function api(path, options = {}) {
  const headers = new Headers(options.headers || {});
  headers.set("Content-Type", "application/json");
  if (state.token) {
    headers.set("Authorization", `Bearer ${state.token}`);
  }

  const res = await fetch(`${apiBase()}${path}`, { ...options, headers });
  const text = await res.text();
  let payload = {};
  if (text) {
    try {
      payload = JSON.parse(text);
    } catch {
      payload = { raw: text };
    }
  }

  if (!res.ok) {
    throw new Error(payload.detail || payload.raw || `HTTP ${res.status}`);
  }

  return payload;
}

function switchTab(tabId) {
  el.tabButtons.forEach((btn) => {
    btn.classList.toggle("is-active", btn.dataset.tab === tabId);
  });
  document.querySelectorAll(".tab-pane").forEach((pane) => {
    pane.classList.toggle("is-active", pane.id === tabId);
  });

  if (tabId === "tab-planning" && state.token) {
    loadPlanning().catch((err) => {
      setState(el.planningState, `Planning error: ${err.message}`, "err");
    });
  }
}

function setTableRows(tbody, rows, colCount, rowBuilder, emptyMessage = "Aucune donnee") {
  tbody.innerHTML = "";
  if (!rows || rows.length === 0) {
    const tr = document.createElement("tr");
    const td = document.createElement("td");
    td.colSpan = colCount;
    td.className = "empty";
    td.textContent = emptyMessage;
    tr.appendChild(td);
    tbody.appendChild(tr);
    return;
  }

  rows.forEach((row) => tbody.appendChild(rowBuilder(row)));
}

function td(text) {
  const cell = document.createElement("td");
  cell.textContent = text;
  return cell;
}

function toInputDate(date) {
  const yyyy = date.getFullYear();
  const mm = String(date.getMonth() + 1).padStart(2, "0");
  const dd = String(date.getDate()).padStart(2, "0");
  return `${yyyy}-${mm}-${dd}`;
}

function parseInputDate(value) {
  if (!value) {
    return new Date();
  }
  const [y, m, d] = value.split("-").map((n) => Number(n));
  return new Date(y, (m || 1) - 1, d || 1, 0, 0, 0, 0);
}

function planningRange(view, baseDate) {
  const start = new Date(baseDate);
  start.setHours(0, 0, 0, 0);
  const end = new Date(start);

  if (view === "day") {
    end.setDate(end.getDate() + 1);
    return { start, end, label: start.toLocaleDateString() };
  }

  if (view === "week") {
    const day = (start.getDay() + 6) % 7;
    start.setDate(start.getDate() - day);
    end.setTime(start.getTime());
    end.setDate(end.getDate() + 7);
    const endLabel = new Date(end.getTime() - 1);
    return { start, end, label: `${start.toLocaleDateString()} -> ${endLabel.toLocaleDateString()}` };
  }

  if (view === "month") {
    start.setDate(1);
    end.setFullYear(start.getFullYear(), start.getMonth() + 1, 1);
    return {
      start,
      end,
      label: start.toLocaleDateString(undefined, { month: "long", year: "numeric" }),
    };
  }

  start.setMonth(0, 1);
  end.setFullYear(start.getFullYear() + 1, 0, 1);
  return {
    start,
    end,
    label: String(start.getFullYear()),
  };
}

function shiftPlanningDate(direction) {
  const view = el.planningView.value;
  const current = parseInputDate(el.planningDate.value);
  const next = new Date(current);
  if (view === "day") {
    next.setDate(next.getDate() + direction);
  } else if (view === "week") {
    next.setDate(next.getDate() + 7 * direction);
  } else if (view === "month") {
    next.setMonth(next.getMonth() + direction);
  } else {
    next.setFullYear(next.getFullYear() + direction);
  }
  el.planningDate.value = toInputDate(next);
}

function employeeLabel(userId) {
  if (userId == null) {
    return "Employee unassigned";
  }
  return `Employee #${userId}`;
}

function serviceLabel(serviceOfferingId) {
  if (serviceOfferingId == null) {
    return "Service unknown";
  }
  return state.planning.servicesById.get(serviceOfferingId) || `Service #${serviceOfferingId}`;
}

function appointmentStatusClass(status) {
  return `status-${String(status || "").toLowerCase()}`;
}

function sortByStartAsc(rows) {
  return rows.slice().sort((a, b) => new Date(a.start_at).getTime() - new Date(b.start_at).getTime());
}

async function login() {
  setState(el.authState, "Connexion en cours...");
  try {
    const data = await api("/auth/login", {
      method: "POST",
      body: JSON.stringify({
        email: el.email.value.trim(),
        password: el.password.value,
      }),
    });
    state.token = data.access_token || "";
    state.me = await api("/auth/me");
    state.planning.catalogLoaded = false;
    setState(el.authState, `Connecte: ${state.me.email} (${state.me.role})`, "ok");
    await refreshAll();
  } catch (err) {
    setState(el.authState, `Echec connexion: ${err.message}`, "err");
  }
}

function logout() {
  state.token = "";
  state.me = null;
  state.currentTicketId = null;
  state.planning.catalogLoaded = false;
  setState(el.authState, "Deconnecte", "warn");
}

async function loadStats() {
  try {
    ensureAuth();
    const period = encodeURIComponent(el.statsPeriod.value);
    const payload = await api(`/stats/overview?period=${period}`);
    el.kpiNetRevenue.textContent = fmtEur(payload.net_revenue_cents);
    el.kpiGrossRevenue.textContent = fmtEur(payload.gross_revenue_cents);
    el.kpiTicketsPaid.textContent = String(payload.tickets_paid_count || 0);
    el.kpiAppointments.textContent = String(payload.appointments_count || 0);
    el.kpiNewCustomers.textContent = String(payload.new_customers_count || 0);
    el.kpiLoyalty.textContent = String(payload.loyalty_points_earned || 0);
    el.topProductsPreview.textContent = JSON.stringify(payload.top_products || [], null, 2);
    el.topServicesPreview.textContent = JSON.stringify(payload.top_services || [], null, 2);
    el.statsPreview.textContent = JSON.stringify(payload, null, 2);
  } catch (err) {
    el.statsPreview.textContent = `Erreur stats: ${err.message}`;
  }
}

async function loadTickets() {
  try {
    ensureAuth();
    const rows = await api("/sales/tickets");
    setTableRows(
      el.ticketsBody,
      rows.slice(0, 20),
      4,
      (row) => {
        const tr = document.createElement("tr");
        tr.append(td(`#${row.id}`));
        tr.append(td(row.status || "-"));
        tr.append(td(row.payment_method || "-"));
        tr.append(td(new Date(row.updated_at).toLocaleString()));
        return tr;
      },
      "Aucun ticket",
    );
  } catch (err) {
    setTableRows(el.ticketsBody, [], 4, () => document.createElement("tr"), `Erreur tickets: ${err.message}`);
  }
}

async function loadMyRelatedAppointments() {
  if (!state.me) {
    return;
  }
  try {
    const rows = await api(`/appointments/users/${state.me.id}`);
    setTableRows(
      el.appointmentsBody,
      rows.slice(0, 20),
      4,
      (row) => {
        const tr = document.createElement("tr");
        tr.append(td(`#${row.id}`));
        tr.append(td(row.status || "-"));
        tr.append(td(String(row.customer_user_id)));
        tr.append(td(new Date(row.start_at).toLocaleString()));
        return tr;
      },
      "Aucun rendez-vous",
    );
  } catch (err) {
    setTableRows(el.appointmentsBody, [], 4, () => document.createElement("tr"), `Erreur RDV: ${err.message}`);
  }
}

async function refreshAll() {
  try {
    ensureAuth();
    await Promise.all([loadStats(), loadTickets(), loadMyRelatedAppointments(), loadNotifications()]);
  } catch (err) {
    setState(el.authState, err.message, "err");
  }
}

async function ensurePlanningCatalog() {
  if (state.planning.catalogLoaded) {
    return;
  }
  const [employees, services] = await Promise.all([api("/appointments/employees"), api("/appointments/services")]);
  state.planning.employees = employees;
  state.planning.servicesById = new Map(services.map((svc) => [svc.id, svc.name]));

  const currentValue = el.planningEmployee.value;
  el.planningEmployee.innerHTML = '<option value="">Tous les employes</option>';
  employees.forEach((emp) => {
    const option = document.createElement("option");
    option.value = String(emp.user_id);
    option.textContent = employeeLabel(emp.user_id);
    el.planningEmployee.appendChild(option);
  });

  if (currentValue && employees.some((emp) => String(emp.user_id) === currentValue)) {
    el.planningEmployee.value = currentValue;
  }

  state.planning.catalogLoaded = true;
}

async function fetchPlanningAppointments(selectedEmployeeId) {
  const employeeIds = selectedEmployeeId
    ? [selectedEmployeeId]
    : state.planning.employees.map((emp) => Number(emp.user_id));

  if (employeeIds.length === 0) {
    return [];
  }

  const results = await Promise.all(employeeIds.map((id) => api(`/appointments/users/${id}`)));
  const dedup = new Map();
  results.flat().forEach((row) => {
    dedup.set(row.id, row);
  });

  const rows = Array.from(dedup.values());
  return selectedEmployeeId ? rows.filter((row) => row.employee_user_id === selectedEmployeeId) : rows;
}

function renderPlanningSummary(rows) {
  const counts = {
    total: rows.length,
    scheduled: 0,
    confirmed: 0,
    cancelled: 0,
  };

  rows.forEach((row) => {
    const status = String(row.status || "").toLowerCase();
    if (status in counts) {
      counts[status] += 1;
    }
  });

  el.planningSummary.innerHTML = [
    `<span class="pill">Total: ${counts.total}</span>`,
    `<span class="pill">Scheduled: ${counts.scheduled}</span>`,
    `<span class="pill">Confirmed: ${counts.confirmed}</span>`,
    `<span class="pill">Cancelled: ${counts.cancelled}</span>`,
  ].join("");
}

function renderPlanningTimeline(rows, view, range) {
  el.planningGrid.classList.remove("months");
  el.planningGrid.innerHTML = "";

  if (rows.length === 0) {
    el.planningTimeline.innerHTML = '<p class="empty">Aucun rendez-vous dans cette plage.</p>';
    return;
  }

  const groupedByDay = new Map();
  rows.forEach((row) => {
    const start = new Date(row.start_at);
    const dayKey = toInputDate(start);
    if (!groupedByDay.has(dayKey)) {
      groupedByDay.set(dayKey, []);
    }
    groupedByDay.get(dayKey).push(row);
  });

  const dayKeys = Array.from(groupedByDay.keys()).sort();
  el.planningTimeline.innerHTML = dayKeys
    .map((dayKey) => {
      const dayRows = sortByStartAsc(groupedByDay.get(dayKey) || []);
      const byEmployee = new Map();
      dayRows.forEach((row) => {
        const key = row.employee_user_id == null ? "unassigned" : String(row.employee_user_id);
        if (!byEmployee.has(key)) {
          byEmployee.set(key, []);
        }
        byEmployee.get(key).push(row);
      });

      const employeeBlocks = Array.from(byEmployee.entries())
        .map(([key, appointments]) => {
          const employeeId = key === "unassigned" ? null : Number(key);
          const title = employeeLabel(employeeId);
          const cards = appointments
            .map((appt) => {
              const startAt = new Date(appt.start_at);
              const endAt = new Date(appt.end_at);
              const durationMin = Math.max(5, Math.round((endAt.getTime() - startAt.getTime()) / 60000));
              const statusClass = appointmentStatusClass(appt.status);
              return `
                <article class="planning-card ${statusClass}">
                  <div class="planning-card-top">
                    <span class="planning-card-time">${safeText(startAt.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }))} - ${safeText(endAt.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }))}</span>
                    <span class="planning-status ${statusClass}">${safeText(appt.status)}</span>
                  </div>
                  <div><strong>${safeText(serviceLabel(appt.service_offering_id))}</strong></div>
                  <div>Customer #${safeText(appt.customer_user_id)}</div>
                  <div>Duration: ${safeText(durationMin)} min - Appointment #${safeText(appt.id)}</div>
                </article>
              `;
            })
            .join("");

          return `
            <div class="planning-employee-block">
              <h5>${safeText(title)}</h5>
              <div class="planning-cards">${cards}</div>
            </div>
          `;
        })
        .join("");

      const displayDate = new Date(`${dayKey}T00:00:00`).toLocaleDateString();
      return `
        <section class="planning-day-block">
          <h4>${safeText(displayDate)}</h4>
          ${employeeBlocks}
        </section>
      `;
    })
    .join("");

  if (view === "week" || view === "day") {
    const slots = [];
    const cursor = new Date(range.start);
    while (cursor < range.end) {
      const key = toInputDate(cursor);
      const count = groupedByDay.get(key)?.length || 0;
      slots.push(`
        <article class="planning-cell">
          <h5>${safeText(cursor.toLocaleDateString(undefined, { weekday: "short", day: "2-digit", month: "2-digit" }))}</h5>
          <p>${count} appointment(s)</p>
        </article>
      `);
      cursor.setDate(cursor.getDate() + 1);
    }
    el.planningGrid.innerHTML = slots.join("");
  }
}

function renderPlanningMonthGrid(rows, range) {
  el.planningTimeline.innerHTML = "";
  const countByDay = new Map();
  rows.forEach((row) => {
    const key = toInputDate(new Date(row.start_at));
    countByDay.set(key, (countByDay.get(key) || 0) + 1);
  });

  const cells = [];
  const cursor = new Date(range.start);
  while (cursor < range.end) {
    const key = toInputDate(cursor);
    const count = countByDay.get(key) || 0;
    cells.push(`
      <article class="planning-cell">
        <h5>${safeText(cursor.toLocaleDateString(undefined, { weekday: "short", day: "2-digit" }))}</h5>
        <p>${count} appointment(s)</p>
      </article>
    `);
    cursor.setDate(cursor.getDate() + 1);
  }

  el.planningGrid.classList.remove("months");
  el.planningGrid.innerHTML = cells.join("");
}

function renderPlanningYearGrid(rows, range) {
  el.planningTimeline.innerHTML = "";
  const monthCounts = new Array(12).fill(0);
  rows.forEach((row) => {
    const d = new Date(row.start_at);
    monthCounts[d.getMonth()] += 1;
  });

  el.planningGrid.classList.add("months");
  el.planningGrid.innerHTML = monthCounts
    .map((count, index) => {
      const label = new Date(range.start.getFullYear(), index, 1).toLocaleDateString(undefined, { month: "long" });
      return `
        <article class="planning-cell">
          <h5>${safeText(label)}</h5>
          <p>${count} appointment(s)</p>
        </article>
      `;
    })
    .join("");
}

async function loadPlanning() {
  ensureAuth();
  await ensurePlanningCatalog();

  const view = el.planningView.value;
  const baseDate = parseInputDate(el.planningDate.value);
  const range = planningRange(view, baseDate);
  const selectedEmployeeId = el.planningEmployee.value ? Number(el.planningEmployee.value) : null;

  setState(el.planningState, "Chargement planning...");
  const rows = await fetchPlanningAppointments(selectedEmployeeId);
  const scoped = sortByStartAsc(
    rows.filter((row) => {
      const startAt = new Date(row.start_at).getTime();
      return startAt >= range.start.getTime() && startAt < range.end.getTime();
    }),
  );

  renderPlanningSummary(scoped);

  if (view === "month") {
    renderPlanningMonthGrid(scoped, range);
  } else if (view === "year") {
    renderPlanningYearGrid(scoped, range);
  } else {
    renderPlanningTimeline(scoped, view, range);
  }

  setState(
    el.planningState,
    `${scoped.length} appointment(s) - ${range.label}${selectedEmployeeId ? ` - ${employeeLabel(selectedEmployeeId)}` : " - Tous employes"}`,
    scoped.length ? "ok" : "warn",
  );
}

async function createTicket() {
  try {
    ensureAuth();
    const ticket = await api("/sales/tickets", {
      method: "POST",
      body: JSON.stringify({ notes: el.ticketNotes.value.trim() || null }),
    });
    state.currentTicketId = ticket.id;
    el.ticketId.value = String(ticket.id);
    setState(el.ticketState, `Ticket #${ticket.id} cree`, "ok");
    await loadTicketDetails();
    await loadTickets();
  } catch (err) {
    setState(el.ticketState, `Creation ticket impossible: ${err.message}`, "err");
  }
}

async function loadTicketDetails() {
  try {
    ensureAuth();
    const id = currentTicketId();
    const details = await api(`/sales/tickets/${id}`);
    state.currentTicketId = id;
    el.ticketId.value = String(id);
    el.ticketPreview.textContent = JSON.stringify(details, null, 2);
    setState(el.ticketState, `Ticket #${id} charge`, "ok");
  } catch (err) {
    setState(el.ticketState, `Chargement ticket impossible: ${err.message}`, "err");
  }
}

async function setTicketCustomer() {
  try {
    ensureAuth();
    const id = currentTicketId();
    const customerUserId = Number(el.ticketCustomerId.value || "0") || null;
    const payload = await api(`/sales/tickets/${id}/customer`, {
      method: "PATCH",
      body: JSON.stringify({ customer_user_id: customerUserId }),
    });
    setState(el.ticketState, `Client associe au ticket #${payload.id}`, "ok");
    await loadTicketDetails();
  } catch (err) {
    setState(el.ticketState, `Association client impossible: ${err.message}`, "err");
  }
}

async function setTicketDiscount() {
  try {
    ensureAuth();
    const id = currentTicketId();
    const details = await api(`/sales/tickets/${id}/discount`, {
      method: "PATCH",
      body: JSON.stringify({ discount_cents: Number(el.ticketDiscount.value || "0") }),
    });
    el.ticketPreview.textContent = JSON.stringify(details, null, 2);
    setState(el.ticketState, `Remise appliquee sur ticket #${id}`, "ok");
  } catch (err) {
    setState(el.ticketState, `Remise impossible: ${err.message}`, "err");
  }
}

async function setTicketStatus(action) {
  try {
    ensureAuth();
    const id = currentTicketId();
    const endpoint = action === "suspend" ? "suspend" : "resume";
    const payload = await api(`/sales/tickets/${id}/${endpoint}`, {
      method: "POST",
      body: JSON.stringify({}),
    });
    setState(el.ticketState, `Ticket #${payload.id} -> ${payload.status}`, "ok");
    await loadTicketDetails();
    await loadTickets();
  } catch (err) {
    setState(el.ticketState, `Changement statut impossible: ${err.message}`, "err");
  }
}

async function loadPosProducts() {
  try {
    ensureAuth();
    const products = await api("/sales/products");
    el.posProductSelect.innerHTML = products
      .map((p) => `<option value="${p.id}">#${p.id} ${safeText(p.name)} (${fmtEur(p.price_cents)})</option>`)
      .join("");
    setState(el.ticketState, `${products.length} produit(s) POS charges`, "ok");
  } catch (err) {
    setState(el.ticketState, `Chargement produits POS impossible: ${err.message}`, "err");
  }
}

async function loadServices() {
  try {
    ensureAuth();
    const services = await api("/appointments/services");
    el.posServiceSelect.innerHTML = services
      .map((s) => `<option value="${s.id}">#${s.id} ${safeText(s.name)} (${fmtEur(s.price_cents)})</option>`)
      .join("");
    setState(el.ticketState, `${services.length} service(s) charges`, "ok");
  } catch (err) {
    setState(el.ticketState, `Chargement services impossible: ${err.message}`, "err");
  }
}

async function addProductLine() {
  try {
    ensureAuth();
    const id = currentTicketId();
    const details = await api(`/sales/tickets/${id}/lines/product`, {
      method: "POST",
      body: JSON.stringify({
        product_item_id: Number(el.posProductSelect.value),
        quantity: Number(el.posProductQty.value || "1"),
      }),
    });
    el.ticketPreview.textContent = JSON.stringify(details, null, 2);
    setState(el.ticketState, "Ligne produit ajoutee", "ok");
  } catch (err) {
    setState(el.ticketState, `Ajout produit impossible: ${err.message}`, "err");
  }
}

async function addServiceLine() {
  try {
    ensureAuth();
    const id = currentTicketId();
    const details = await api(`/sales/tickets/${id}/lines/service`, {
      method: "POST",
      body: JSON.stringify({
        service_offering_id: Number(el.posServiceSelect.value),
        quantity: Number(el.posServiceQty.value || "1"),
      }),
    });
    el.ticketPreview.textContent = JSON.stringify(details, null, 2);
    setState(el.ticketState, "Ligne service ajoutee", "ok");
  } catch (err) {
    setState(el.ticketState, `Ajout service impossible: ${err.message}`, "err");
  }
}

async function checkoutTicket() {
  try {
    ensureAuth();
    const id = currentTicketId();
    const receipt = await api(`/sales/tickets/${id}/checkout`, {
      method: "POST",
      body: JSON.stringify({ payment_method: el.posPaymentMethod.value }),
    });
    el.ticketPreview.textContent = JSON.stringify(receipt, null, 2);
    setState(
      el.checkoutState,
      `Ticket #${id} paye - Total ${fmtEur(receipt.total_cents)} - Points ${receipt.loyalty_points_earned}`,
      "ok",
    );
    await loadTickets();
  } catch (err) {
    setState(el.checkoutState, `Checkout impossible: ${err.message}`, "err");
  }
}

async function sendCampaign() {
  try {
    ensureAuth();
    const targetMode = el.campaignTargetMode.value;
    const minPointsRaw = el.campaignMinPoints.value.trim();
    const payload = {
      name: el.campaignName.value.trim(),
      channel: el.campaignChannel.value,
      target_mode: targetMode,
      subject: el.campaignSubject.value.trim() || null,
      message: el.campaignMessage.value.trim(),
      min_points: targetMode === "min_points" && minPointsRaw ? Number(minPointsRaw) : null,
    };
    const result = await api("/campaigns/send", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    setState(el.campaignState, `Campagne envoyee - ${result.queued_notifications} notifications queue`, "ok");
    await loadCampaigns();
    await loadNotifications();
  } catch (err) {
    setState(el.campaignState, `Campagne echouee: ${err.message}`, "err");
  }
}

async function sendBirthdayToday() {
  try {
    ensureAuth();
    const result = await api("/campaigns/birthday/send-today", {
      method: "POST",
      body: JSON.stringify({}),
    });
    setState(el.campaignState, `Anniversaires envoyes - ${result.queued_notifications} notifications`, "ok");
    await loadCampaigns();
    await loadNotifications();
  } catch (err) {
    setState(el.campaignState, `Echec anniversaire: ${err.message}`, "err");
  }
}

async function loadCampaigns() {
  try {
    ensureAuth();
    const rows = await api("/campaigns");
    el.campaignsPreview.textContent = JSON.stringify(rows, null, 2);
  } catch (err) {
    el.campaignsPreview.textContent = `Erreur campagnes: ${err.message}`;
  }
}

async function loadNotifications() {
  try {
    ensureAuth();
    const status = el.notifStatus.value.trim();
    const query = status ? `?status=${encodeURIComponent(status)}` : "";
    const rows = await api(`/campaigns/notifications${query}`);
    el.notifMeta.textContent = `${rows.length} notification(s)`;

    setTableRows(
      el.notifBody,
      rows.slice(0, 30),
      5,
      (row) => {
        const tr = document.createElement("tr");
        tr.append(td(String(row.id)));
        tr.append(td(row.channel || "-"));
        tr.append(td(row.status || "-"));
        tr.append(td(String(row.user_id || "-")));

        const actionCell = document.createElement("td");
        const btn = document.createElement("button");
        btn.className = "ghost";
        btn.textContent = "Selectionner";
        btn.dataset.notificationId = String(row.id);
        btn.addEventListener("click", () => {
          el.notifId.value = String(row.id);
          setState(el.notifState, `Notification #${row.id} selectionnee`, "ok");
        });
        actionCell.appendChild(btn);
        tr.append(actionCell);
        return tr;
      },
      "Aucune notification",
    );
  } catch (err) {
    el.notifMeta.textContent = `Erreur notifications: ${err.message}`;
    setTableRows(el.notifBody, [], 5, () => document.createElement("tr"), "Erreur chargement queue");
  }
}

async function markNotificationStatus() {
  try {
    ensureAuth();
    const notifId = Number(el.notifId.value || "0");
    if (!notifId) {
      throw new Error("ID notification obligatoire");
    }
    const status = el.notifUpdateStatus.value;
    const reason = el.notifFailureReason.value.trim() || null;

    const payload = await api(`/campaigns/notifications/${notifId}/status`, {
      method: "POST",
      body: JSON.stringify({
        status,
        failure_reason: status === "failed" ? reason : null,
      }),
    });

    el.notifUpdatePreview.textContent = JSON.stringify(payload, null, 2);
    setState(el.notifState, `Notification #${notifId} -> ${status}`, "ok");
    await loadNotifications();
  } catch (err) {
    setState(el.notifState, `Update notification impossible: ${err.message}`, "err");
  }
}

async function createVoucher() {
  try {
    ensureAuth();
    const type = el.voucherType.value;
    const serviceIdRaw = Number(el.voucherServiceId.value || "0");
    const amountRaw = Number(el.voucherAmountCents.value || "0");

    const payload = {
      voucher_type: type,
      service_offering_id: type === "service" && serviceIdRaw ? serviceIdRaw : null,
      amount_cents: type === "amount" ? amountRaw : null,
      purchaser_name: el.voucherPurchaser.value.trim(),
      recipient_name: el.voucherRecipient.value.trim(),
      recipient_email: el.voucherRecipientEmail.value.trim() || null,
      effective_date: el.voucherEffectiveDate.value,
      duration_days: Number(el.voucherDurationDays.value || "365"),
    };

    const result = await api("/gifts/vouchers", {
      method: "POST",
      body: JSON.stringify(payload),
    });

    setState(el.voucherState, `Voucher cree: ${result.code}`, "ok");
    await loadVouchers();
  } catch (err) {
    setState(el.voucherState, `Creation voucher impossible: ${err.message}`, "err");
  }
}

async function loadVouchers() {
  try {
    ensureAuth();
    const params = new URLSearchParams();
    if (el.voucherStatusFilter.value.trim()) {
      params.set("status", el.voucherStatusFilter.value.trim());
    }
    if (el.voucherCodeFilter.value.trim()) {
      params.set("code", el.voucherCodeFilter.value.trim());
    }
    const query = params.toString() ? `?${params.toString()}` : "";
    const rows = await api(`/gifts/vouchers${query}`);
    el.vouchersPreview.textContent = JSON.stringify(rows, null, 2);
  } catch (err) {
    el.vouchersPreview.textContent = `Erreur vouchers: ${err.message}`;
  }
}

async function redeemVoucher() {
  try {
    ensureAuth();
    const voucherId = Number(el.redeemVoucherId.value || "0");
    if (!voucherId) {
      throw new Error("ID voucher obligatoire");
    }
    const amountRaw = Number(el.redeemAmountCents.value || "0");

    const payload = await api(`/gifts/vouchers/${voucherId}/redeem`, {
      method: "POST",
      body: JSON.stringify({
        amount_cents: amountRaw || null,
        notes: el.redeemNote.value.trim() || null,
      }),
    });

    el.redeemPreview.textContent = JSON.stringify(payload, null, 2);
    setState(el.voucherState, `Voucher #${voucherId} redeeme`, "ok");
    await loadVouchers();
  } catch (err) {
    setState(el.voucherState, `Redemption impossible: ${err.message}`, "err");
  }
}

async function loadCustomerProfile() {
  try {
    ensureAuth();
    const userId = Number(el.customerUserId.value || "0");
    if (!userId) {
      throw new Error("ID client obligatoire");
    }
    const profile = await api(`/customers/${userId}/profile`);
    el.customerProfilePreview.textContent = JSON.stringify(profile, null, 2);
    el.customerStaffNotes.value = profile.staff_notes || "";
    setState(el.customerState, `Profil client #${userId} charge`, "ok");
  } catch (err) {
    setState(el.customerState, `Chargement profil impossible: ${err.message}`, "err");
  }
}

async function saveCustomerNotes() {
  try {
    ensureAuth();
    const userId = Number(el.customerUserId.value || "0");
    if (!userId) {
      throw new Error("ID client obligatoire");
    }

    const profile = await api(`/customers/${userId}/staff-notes`, {
      method: "PATCH",
      body: JSON.stringify({
        staff_notes: el.customerStaffNotes.value.trim() || null,
      }),
    });

    el.customerProfilePreview.textContent = JSON.stringify(profile, null, 2);
    setState(el.customerState, `Notes staff sauvegardees pour client #${userId}`, "ok");
  } catch (err) {
    setState(el.customerState, `Sauvegarde notes impossible: ${err.message}`, "err");
  }
}

async function loadSubscriptions() {
  try {
    ensureAuth();
    const userId = Number(el.customerUserId.value || "0");
    if (!userId) {
      throw new Error("ID client obligatoire");
    }
    const rows = await api(`/loyalty/users/${userId}/subscriptions`);
    el.subscriptionsPreview.textContent = JSON.stringify(rows, null, 2);
    setState(el.subscriptionState, `${rows.length} abonnement(s) charges`, rows.length ? "ok" : "warn");
  } catch (err) {
    setState(el.subscriptionState, `Chargement abonnements impossible: ${err.message}`, "err");
  }
}

async function createSubscription() {
  try {
    ensureAuth();
    const userId = Number(el.customerUserId.value || "0");
    if (!userId) {
      throw new Error("ID client obligatoire");
    }

    const payload = {
      user_id: userId,
      plan_name: el.subscriptionPlanName.value.trim(),
      amount_cents: Number(el.subscriptionAmountCents.value || "0"),
      duration_days: Number(el.subscriptionDurationDays.value || "30"),
      starts_on: el.subscriptionStartsOn.value || null,
      payment_method: el.subscriptionPaymentMethod.value,
      bonus_points_granted: Number(el.subscriptionBonusPoints.value || "0"),
    };
    const row = await api("/loyalty/subscriptions", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    setState(el.subscriptionState, `Abonnement cree (#${row.id})`, "ok");
    el.cancelSubscriptionId.value = String(row.id);
    await loadSubscriptions();
    await loadCustomerProfile();
  } catch (err) {
    setState(el.subscriptionState, `Creation abonnement impossible: ${err.message}`, "err");
  }
}

async function cancelSubscription() {
  try {
    ensureAuth();
    const subId = Number(el.cancelSubscriptionId.value || "0");
    if (!subId) {
      throw new Error("ID abonnement obligatoire");
    }
    const row = await api(`/loyalty/subscriptions/${subId}/cancel`, {
      method: "POST",
      body: JSON.stringify({}),
    });
    setState(el.subscriptionState, `Abonnement #${row.id} annule`, "ok");
    await loadSubscriptions();
  } catch (err) {
    setState(el.subscriptionState, `Annulation abonnement impossible: ${err.message}`, "err");
  }
}

function setDefaultDates() {
  const today = new Date();
  el.voucherEffectiveDate.value = toInputDate(today);
  el.planningDate.value = toInputDate(today);
  if (el.subscriptionStartsOn) {
    el.subscriptionStartsOn.value = toInputDate(today);
  }
}

function bind() {
  el.tabButtons.forEach((btn) => {
    btn.addEventListener("click", () => switchTab(btn.dataset.tab));
  });

  el.loginBtn.addEventListener("click", login);
  el.logoutBtn.addEventListener("click", logout);
  el.refreshAllBtn.addEventListener("click", refreshAll);

  el.planningLoadBtn.addEventListener("click", () => {
    loadPlanning().catch((err) => setState(el.planningState, err.message, "err"));
  });
  el.planningPrevBtn.addEventListener("click", () => {
    shiftPlanningDate(-1);
    loadPlanning().catch((err) => setState(el.planningState, err.message, "err"));
  });
  el.planningTodayBtn.addEventListener("click", () => {
    el.planningDate.value = toInputDate(new Date());
    loadPlanning().catch((err) => setState(el.planningState, err.message, "err"));
  });
  el.planningNextBtn.addEventListener("click", () => {
    shiftPlanningDate(1);
    loadPlanning().catch((err) => setState(el.planningState, err.message, "err"));
  });
  el.planningView.addEventListener("change", () => {
    loadPlanning().catch((err) => setState(el.planningState, err.message, "err"));
  });
  el.planningEmployee.addEventListener("change", () => {
    loadPlanning().catch((err) => setState(el.planningState, err.message, "err"));
  });
  el.planningDate.addEventListener("change", () => {
    loadPlanning().catch((err) => setState(el.planningState, err.message, "err"));
  });

  el.createTicketBtn.addEventListener("click", createTicket);
  el.loadTicketBtn.addEventListener("click", loadTicketDetails);
  el.setTicketCustomerBtn.addEventListener("click", setTicketCustomer);
  el.setTicketDiscountBtn.addEventListener("click", setTicketDiscount);
  el.suspendTicketBtn.addEventListener("click", () => setTicketStatus("suspend"));
  el.resumeTicketBtn.addEventListener("click", () => setTicketStatus("resume"));
  el.loadPosCatalogBtn.addEventListener("click", loadPosProducts);
  el.loadServicesBtn.addEventListener("click", loadServices);
  el.addProductLineBtn.addEventListener("click", addProductLine);
  el.addServiceLineBtn.addEventListener("click", addServiceLine);
  el.checkoutTicketBtn.addEventListener("click", checkoutTicket);

  el.sendCampaignBtn.addEventListener("click", sendCampaign);
  el.sendBirthdayBtn.addEventListener("click", sendBirthdayToday);
  el.loadCampaignsBtn.addEventListener("click", loadCampaigns);
  el.loadNotificationsBtn.addEventListener("click", loadNotifications);
  el.markNotificationBtn.addEventListener("click", markNotificationStatus);

  el.createVoucherBtn.addEventListener("click", createVoucher);
  el.loadVouchersBtn.addEventListener("click", loadVouchers);
  el.redeemVoucherBtn.addEventListener("click", redeemVoucher);

  el.loadCustomerProfileBtn.addEventListener("click", loadCustomerProfile);
  el.saveCustomerNotesBtn.addEventListener("click", saveCustomerNotes);
  el.createSubscriptionBtn.addEventListener("click", createSubscription);
  el.loadSubscriptionsBtn.addEventListener("click", loadSubscriptions);
  el.cancelSubscriptionBtn.addEventListener("click", cancelSubscription);
}

bind();
setDefaultDates();
switchTab("tab-dashboard");
