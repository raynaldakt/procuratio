const state = {
  token: "",
  me: null,
  currentTicketId: null,
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

function setDefaultDates() {
  const today = new Date();
  el.voucherEffectiveDate.value = today.toISOString().slice(0, 10);
}

function bind() {
  el.tabButtons.forEach((btn) => {
    btn.addEventListener("click", () => switchTab(btn.dataset.tab));
  });

  el.loginBtn.addEventListener("click", login);
  el.logoutBtn.addEventListener("click", logout);
  el.refreshAllBtn.addEventListener("click", refreshAll);

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
}

bind();
setDefaultDates();
switchTab("tab-dashboard");
