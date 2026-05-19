const state = {
  token: "",
  products: [],
  cart: null,
  selectedSlot: "",
  services: [],
  employees: [],
  appointments: [],
  lastVoucherPrintableText: "",
};
const API_BASE_STORAGE_KEY = "procuratio_api_base_url";

const els = {
  apiBase: document.getElementById("apiBase"),
  email: document.getElementById("email"),
  password: document.getElementById("password"),
  authState: document.getElementById("authState"),

  tabButtons: Array.from(document.querySelectorAll(".tab-btn")),

  searchQuery: document.getElementById("searchQuery"),
  searchBrand: document.getElementById("searchBrand"),
  searchType: document.getElementById("searchType"),
  searchMinPrice: document.getElementById("searchMinPrice"),
  searchMaxPrice: document.getElementById("searchMaxPrice"),
  productState: document.getElementById("productState"),
  productList: document.getElementById("productList"),

  cartSummary: document.getElementById("cartSummary"),
  cartLinesBody: document.getElementById("cartLinesBody"),
  purchaseState: document.getElementById("purchaseState"),
  reserveState: document.getElementById("reserveState"),
  reservationHours: document.getElementById("reservationHours"),
  successUrl: document.getElementById("successUrl"),
  cancelUrl: document.getElementById("cancelUrl"),
  checkoutState: document.getElementById("checkoutState"),
  checkoutLink: document.getElementById("checkoutLink"),
  giftVoucherType: document.getElementById("giftVoucherType"),
  giftVoucherAmountCents: document.getElementById("giftVoucherAmountCents"),
  giftVoucherServiceId: document.getElementById("giftVoucherServiceId"),
  giftVoucherRecipientName: document.getElementById("giftVoucherRecipientName"),
  giftVoucherRecipientEmail: document.getElementById("giftVoucherRecipientEmail"),
  giftVoucherDurationDays: document.getElementById("giftVoucherDurationDays"),
  giftVoucherState: document.getElementById("giftVoucherState"),

  serviceSelect: document.getElementById("serviceSelect"),
  employeeSelect: document.getElementById("employeeSelect"),
  appointmentDate: document.getElementById("appointmentDate"),
  appointmentCatalogState: document.getElementById("appointmentCatalogState"),
  slotState: document.getElementById("slotState"),
  slotList: document.getElementById("slotList"),
  appointmentNotes: document.getElementById("appointmentNotes"),
  payInStore: document.getElementById("payInStore"),
  bookState: document.getElementById("bookState"),
  bookPreview: document.getElementById("bookPreview"),

  appointmentsBody: document.getElementById("appointmentsBody"),
  ordersPreview: document.getElementById("ordersPreview"),
  reservationsPreview: document.getElementById("reservationsPreview"),
  giftVouchersPreview: document.getElementById("giftVouchersPreview"),
  payAppointmentId: document.getElementById("payAppointmentId"),
  appointmentSuccessUrl: document.getElementById("appointmentSuccessUrl"),
  appointmentCancelUrl: document.getElementById("appointmentCancelUrl"),
  appointmentState: document.getElementById("appointmentState"),
  appointmentCheckoutLink: document.getElementById("appointmentCheckoutLink"),

  loginBtn: document.getElementById("loginBtn"),
  logoutBtn: document.getElementById("logoutBtn"),
  loadProductsBtn: document.getElementById("loadProductsBtn"),
  refreshCartBtn: document.getElementById("refreshCartBtn"),
  payCardBtn: document.getElementById("payCardBtn"),
  payTransferBtn: document.getElementById("payTransferBtn"),
  payWalletBtn: document.getElementById("payWalletBtn"),
  reserveBtn: document.getElementById("reserveBtn"),
  stripeCheckoutBtn: document.getElementById("stripeCheckoutBtn"),
  purchaseGiftVoucherBtn: document.getElementById("purchaseGiftVoucherBtn"),
  printGiftVoucherBtn: document.getElementById("printGiftVoucherBtn"),

  loadAppointmentCatalogBtn: document.getElementById("loadAppointmentCatalogBtn"),
  searchAvailabilityBtn: document.getElementById("searchAvailabilityBtn"),
  bookAppointmentBtn: document.getElementById("bookAppointmentBtn"),

  refreshAppointmentsBtn: document.getElementById("refreshAppointmentsBtn"),
  refreshOrdersBtn: document.getElementById("refreshOrdersBtn"),
  refreshReservationsBtn: document.getElementById("refreshReservationsBtn"),
  refreshGiftVouchersBtn: document.getElementById("refreshGiftVouchersBtn"),
  printLastGiftVoucherBtn: document.getElementById("printLastGiftVoucherBtn"),
  payAppointmentBtn: document.getElementById("payAppointmentBtn"),
};

function apiBase() {
  return els.apiBase.value.trim().replace(/\/$/, "");
}

function normalizeApiBase(raw) {
  const trimmed = String(raw || "").trim().replace(/\/$/, "");
  if (!trimmed) {
    return trimmed;
  }
  if (trimmed.startsWith("http://") || trimmed.startsWith("https://")) {
    return trimmed;
  }
  return `https://${trimmed}`;
}

function initializeApiBaseInput() {
  let stored = "";
  try {
    stored = window.localStorage.getItem(API_BASE_STORAGE_KEY) || "";
  } catch {
    stored = "";
  }

  const params = new URLSearchParams(window.location.search);
  const queryApi = normalizeApiBase(params.get("api") || "");
  const preferred = queryApi || normalizeApiBase(stored) || normalizeApiBase(els.apiBase.value);
  if (preferred) {
    els.apiBase.value = preferred;
  }

  const persist = () => {
    const value = normalizeApiBase(els.apiBase.value);
    if (value) {
      els.apiBase.value = value;
    }
    try {
      if (value) {
        window.localStorage.setItem(API_BASE_STORAGE_KEY, value);
      } else {
        window.localStorage.removeItem(API_BASE_STORAGE_KEY);
      }
    } catch {
      // Ignore localStorage failures (private mode, browser policy, etc.)
    }
  };

  if (queryApi) {
    try {
      window.localStorage.setItem(API_BASE_STORAGE_KEY, queryApi);
    } catch {
      // Ignore localStorage failures
    }
  }

  els.apiBase.addEventListener("change", persist);
  els.apiBase.addEventListener("blur", persist);
}

function money(cents) {
  return `${(cents / 100).toFixed(2)} EUR`;
}

function setState(el, message, tone = "") {
  el.textContent = message;
  el.classList.remove("ok", "warn", "err");
  if (tone) {
    el.classList.add(tone);
  }
}

function safeText(value) {
  return String(value ?? "").replace(/[&<>\"']/g, (ch) => {
    const map = {
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      '"': "&quot;",
      "'": "&#39;",
    };
    return map[ch] || ch;
  });
}

function requireAuth() {
  if (!state.token) {
    throw new Error("Connecte-toi d'abord");
  }
}

async function request(path, options = {}) {
  const headers = new Headers(options.headers || {});
  headers.set("Content-Type", "application/json");
  if (state.token) {
    headers.set("Authorization", `Bearer ${state.token}`);
  }

  const response = await fetch(`${apiBase()}${path}`, {
    ...options,
    headers,
  });

  const text = await response.text();
  let body = {};
  if (text) {
    try {
      body = JSON.parse(text);
    } catch {
      body = { raw: text };
    }
  }

  if (!response.ok) {
    throw new Error(body.detail || body.raw || `HTTP ${response.status}`);
  }

  return body;
}

function switchTab(targetId) {
  els.tabButtons.forEach((btn) => {
    btn.classList.toggle("is-active", btn.dataset.tab === targetId);
  });

  document.querySelectorAll(".tab-pane").forEach((pane) => {
    pane.classList.toggle("is-active", pane.id === targetId);
  });
}

async function login() {
  setState(els.authState, "Connexion en cours...");
  try {
    const data = await request("/auth/login", {
      method: "POST",
      body: JSON.stringify({
        email: els.email.value.trim(),
        password: els.password.value,
      }),
    });
    state.token = data.access_token || "";
    setState(els.authState, "Connecte", "ok");
    await Promise.all([loadProducts(), refreshCart()]);
  } catch (err) {
    setState(els.authState, `Echec connexion: ${err.message}`, "err");
  }
}

function logout() {
  state.token = "";
  state.cart = null;
  state.appointments = [];
  renderCart(null);
  renderAppointments([]);
  setState(els.authState, "Deconnecte", "warn");
}

function productQuery() {
  const params = new URLSearchParams();
  const q = els.searchQuery.value.trim();
  const brand = els.searchBrand.value.trim();
  const type = els.searchType.value.trim();
  const min = els.searchMinPrice.value.trim();
  const max = els.searchMaxPrice.value.trim();

  if (q) params.set("q", q);
  if (brand) params.set("brand", brand);
  if (type) params.set("product_type", type);
  if (min) params.set("min_price_cents", min);
  if (max) params.set("max_price_cents", max);

  const suffix = params.toString();
  return suffix ? `/shop/products?${suffix}` : "/shop/products";
}

async function loadProducts() {
  try {
    const products = await request(productQuery());
    state.products = products;
    renderProducts();
    setState(els.productState, `${products.length} produit(s) charge(s)`, "ok");
  } catch (err) {
    setState(els.productState, `Echec chargement produits: ${err.message}`, "err");
  }
}

function renderProducts() {
  if (state.products.length === 0) {
    els.productList.innerHTML = '<p class="state warn">Aucun produit trouve.</p>';
    return;
  }

  els.productList.innerHTML = state.products
    .map((p) => {
      const stockLabel = p.stock_quantity > 0 ? `Stock: ${p.stock_quantity}` : "Rupture";
      const stockClass = p.stock_quantity > 0 ? "ok" : "err";
      return `
        <article class="product-card" data-product-id="${p.id}">
          <div class="product-meta">
            <span>${safeText(p.brand || "Sans marque")}</span>
            <span class="${stockClass}">${stockLabel}</span>
          </div>
          <h4>${safeText(p.name)}</h4>
          <p>${safeText(p.description || "Description indisponible")}</p>
          <p><strong>${money(p.price_cents)}</strong></p>
          <div class="row two">
            <input type="number" min="1" value="1" class="qty-input" />
            <button class="add-cart-btn" ${p.stock_quantity <= 0 ? "disabled" : ""}>Ajouter</button>
          </div>
        </article>
      `;
    })
    .join("");
}

async function ensureCart() {
  await request("/shop/cart", {
    method: "POST",
    body: JSON.stringify({}),
  });
}

async function refreshCart() {
  try {
    requireAuth();
    const data = await request("/shop/cart");
    state.cart = data;
    renderCart(data);
  } catch (err) {
    renderCart(null, `Echec panier: ${err.message}`);
  }
}

function renderCart(data, errorMessage = "") {
  if (!data) {
    els.cartSummary.textContent = errorMessage || "Panier vide";
    els.cartLinesBody.innerHTML = '<tr><td colspan="6" class="empty">Aucune ligne</td></tr>';
    return;
  }

  const order = data.order;
  const lines = data.lines || [];
  els.cartSummary.innerHTML = `Commande #${order.id} - Statut: <strong>${safeText(order.status)}</strong> - Total: <strong>${money(order.total_cents)}</strong>`;

  if (lines.length === 0) {
    els.cartLinesBody.innerHTML = '<tr><td colspan="6" class="empty">Aucune ligne</td></tr>';
    return;
  }

  els.cartLinesBody.innerHTML = lines
    .map(
      (line) => `
      <tr>
        <td>#${line.id}</td>
        <td>${line.product_item_id}</td>
        <td>${line.quantity}</td>
        <td>${money(line.unit_price_cents)}</td>
        <td>${money(line.total_price_cents)}</td>
        <td><button class="ghost remove-line-btn" data-line-id="${line.id}">Retirer</button></td>
      </tr>
    `,
    )
    .join("");
}

async function addToCart(productId, quantity) {
  try {
    requireAuth();
    await ensureCart();
    const data = await request("/shop/cart/lines", {
      method: "POST",
      body: JSON.stringify({
        product_item_id: Number(productId),
        quantity: Number(quantity),
      }),
    });
    state.cart = data;
    renderCart(data);
    setState(els.productState, "Produit ajoute au panier", "ok");
  } catch (err) {
    setState(els.productState, `Ajout panier impossible: ${err.message}`, "err");
  }
}

async function removeCartLine(lineId) {
  try {
    requireAuth();
    const data = await request(`/shop/cart/lines/${lineId}`, { method: "DELETE" });
    state.cart = data;
    renderCart(data);
  } catch (err) {
    setState(els.purchaseState, `Suppression impossible: ${err.message}`, "err");
  }
}

async function purchase(method) {
  try {
    requireAuth();
    const data = await request("/shop/cart/checkout/purchase", {
      method: "POST",
      body: JSON.stringify({ payment_method: method }),
    });
    setState(
      els.purchaseState,
      `Achat confirme (#${data.order.id}) - Points gagnes: ${data.loyalty_points_earned}`,
      "ok",
    );
    await refreshCart();
    await refreshOrders();
  } catch (err) {
    setState(els.purchaseState, `Paiement echoue: ${err.message}`, "err");
  }
}

async function reserveCart() {
  try {
    requireAuth();
    const data = await request("/shop/cart/checkout/reserve", {
      method: "POST",
      body: JSON.stringify({
        expires_in_hours: Number(els.reservationHours.value || "48"),
      }),
    });
    setState(
      els.reserveState,
      `Reservation creee pour la commande #${data.order.id}`,
      "ok",
    );
    await refreshCart();
    await refreshReservations();
  } catch (err) {
    setState(els.reserveState, `Reservation echouee: ${err.message}`, "err");
  }
}

async function createCartStripeSession() {
  els.checkoutLink.textContent = "";
  els.checkoutLink.href = "#";
  try {
    requireAuth();
    const data = await request("/shop/cart/checkout/stripe-session", {
      method: "POST",
      body: JSON.stringify({
        success_url: els.successUrl.value.trim(),
        cancel_url: els.cancelUrl.value.trim(),
      }),
    });
    setState(els.checkoutState, `Session Stripe creee (${data.session_id})`, "ok");
    els.checkoutLink.href = data.checkout_url;
    els.checkoutLink.textContent = data.checkout_url;
  } catch (err) {
    setState(els.checkoutState, `Stripe indisponible: ${err.message}`, "err");
  }
}

function printVoucherText(text) {
  if (!text) {
    setState(els.giftVoucherState, "Aucun voucher a imprimer", "warn");
    return;
  }
  const win = window.open("", "_blank", "width=820,height=640");
  if (!win) {
    setState(els.giftVoucherState, "Popup bloquee: autorise les popups pour imprimer", "err");
    return;
  }
  const safe = safeText(text).replace(/\n/g, "<br />");
  win.document.write(`
    <html lang="fr">
      <head>
        <title>Gift Voucher - Procuratio</title>
        <style>
          body { font-family: Arial, sans-serif; margin: 24px; color: #111827; }
          h1 { margin: 0 0 12px; }
          .voucher { border: 2px dashed #0f766e; border-radius: 12px; padding: 16px; font-size: 15px; line-height: 1.5; }
        </style>
      </head>
      <body>
        <h1>Gift Voucher Procuratio</h1>
        <div class="voucher">${safe}</div>
      </body>
    </html>
  `);
  win.document.close();
  win.focus();
  win.print();
}

async function purchaseGiftVoucher() {
  try {
    requireAuth();
    const payload = {
      voucher_type: els.giftVoucherType.value,
      service_offering_id: els.giftVoucherServiceId.value ? Number(els.giftVoucherServiceId.value) : null,
      amount_cents: Number(els.giftVoucherAmountCents.value || "0"),
      recipient_name: els.giftVoucherRecipientName.value.trim(),
      recipient_email: els.giftVoucherRecipientEmail.value.trim() || null,
      duration_days: Number(els.giftVoucherDurationDays.value || "365"),
      payment_method: "card",
    };
    const data = await request("/shop/gift-vouchers/purchase", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    state.lastVoucherPrintableText = data.printable_text || "";
    setState(
      els.giftVoucherState,
      `Voucher ${data.voucher.code} achete - email queue: ${data.email_queued_for.length}`,
      "ok",
    );
    els.giftVouchersPreview.textContent = JSON.stringify([data.voucher], null, 2);
  } catch (err) {
    setState(els.giftVoucherState, `Achat voucher impossible: ${err.message}`, "err");
  }
}

async function refreshGiftVouchers() {
  try {
    requireAuth();
    const rows = await request("/shop/gift-vouchers/me");
    els.giftVouchersPreview.textContent = JSON.stringify(rows, null, 2);
    setState(els.giftVoucherState, `${rows.length} voucher(s) charge(s)`, rows.length ? "ok" : "warn");
  } catch (err) {
    els.giftVouchersPreview.textContent = `Echec vouchers: ${err.message}`;
    setState(els.giftVoucherState, `Echec vouchers: ${err.message}`, "err");
  }
}

async function loadAppointmentCatalog() {
  try {
    requireAuth();
    const [services, employees] = await Promise.all([
      request("/appointments/services"),
      request("/appointments/employees"),
    ]);

    state.services = services;
    state.employees = employees;

    els.serviceSelect.innerHTML = services
      .map((svc) => `<option value="${svc.id}">${safeText(svc.name)} (${svc.duration_minutes} min)</option>`)
      .join("");

    els.employeeSelect.innerHTML = employees
      .map((emp) => `<option value="${emp.user_id}">Employe #${emp.user_id}</option>`)
      .join("");

    setState(
      els.appointmentCatalogState,
      `${services.length} service(s), ${employees.length} employe(s) charges`,
      "ok",
    );
  } catch (err) {
    setState(els.appointmentCatalogState, `Chargement catalogue impossible: ${err.message}`, "err");
  }
}

async function searchAvailability() {
  try {
    requireAuth();
    const serviceId = Number(els.serviceSelect.value);
    const employeeId = Number(els.employeeSelect.value);
    const targetDate = els.appointmentDate.value;

    if (!serviceId || !employeeId || !targetDate) {
      throw new Error("Selectionne service, employe et date");
    }

    const query = new URLSearchParams({
      service_offering_id: String(serviceId),
      employee_user_id: String(employeeId),
      target_date: targetDate,
    });

    const slots = await request(`/appointments/availability?${query.toString()}`);
    renderSlots(slots);
    setState(els.slotState, `${slots.length} disponibilite(s) trouvee(s)`, slots.length ? "ok" : "warn");
  } catch (err) {
    setState(els.slotState, `Recherche indisponibilites: ${err.message}`, "err");
  }
}

function renderSlots(slots) {
  state.selectedSlot = "";
  if (!slots.length) {
    els.slotList.innerHTML = '<p class="state warn">Aucun slot.</p>';
    return;
  }

  els.slotList.innerHTML = slots
    .map((slot, index) => {
      const iso = slot.start_at;
      const label = new Date(iso).toLocaleString();
      return `<button class="slot-btn ${index === 0 ? "is-selected" : ""}" data-slot="${iso}">${safeText(label)}</button>`;
    })
    .join("");

  state.selectedSlot = slots[0].start_at;
}

async function bookAppointment() {
  try {
    requireAuth();
    if (!state.selectedSlot) {
      throw new Error("Choisis un slot de disponibilite");
    }

    const payload = await request("/appointments/book", {
      method: "POST",
      body: JSON.stringify({
        service_offering_id: Number(els.serviceSelect.value),
        employee_user_id: Number(els.employeeSelect.value),
        start_at: state.selectedSlot,
        notes: els.appointmentNotes.value.trim() || null,
        pay_in_store: els.payInStore.checked,
      }),
    });

    setState(els.bookState, `Rendez-vous #${payload.id} confirme`, "ok");
    els.bookPreview.textContent = JSON.stringify(payload, null, 2);
    els.payAppointmentId.value = String(payload.id);
    await refreshAppointments();
  } catch (err) {
    setState(els.bookState, `Reservation impossible: ${err.message}`, "err");
  }
}

function renderAppointments(items) {
  if (!items.length) {
    els.appointmentsBody.innerHTML = '<tr><td colspan="4" class="empty">Aucun rendez-vous</td></tr>';
    return;
  }

  els.appointmentsBody.innerHTML = items
    .map((appt) => {
      const when = new Date(appt.start_at).toLocaleString();
      return `
        <tr>
          <td>#${appt.id}</td>
          <td>${safeText(when)}</td>
          <td>${safeText(appt.status)}</td>
          <td><button class="ghost cancel-appt-btn" data-appointment-id="${appt.id}">Annuler</button></td>
        </tr>
      `;
    })
    .join("");
}

async function refreshAppointments() {
  try {
    requireAuth();
    const rows = await request("/appointments/me");
    state.appointments = rows;
    renderAppointments(rows);
    setState(els.appointmentState, `${rows.length} rendez-vous charges`, "ok");
  } catch (err) {
    setState(els.appointmentState, `Echec chargement RDV: ${err.message}`, "err");
  }
}

async function cancelAppointment(appointmentId) {
  try {
    requireAuth();
    await request(`/appointments/${appointmentId}/cancel`, {
      method: "POST",
      body: JSON.stringify({}),
    });
    setState(els.appointmentState, `Rendez-vous #${appointmentId} annule`, "ok");
    await refreshAppointments();
  } catch (err) {
    setState(els.appointmentState, `Annulation impossible: ${err.message}`, "err");
  }
}

async function createAppointmentStripeSession() {
  els.appointmentCheckoutLink.textContent = "";
  els.appointmentCheckoutLink.href = "#";
  try {
    requireAuth();
    const id = Number(els.payAppointmentId.value);
    if (!id) {
      throw new Error("Entre un ID de rendez-vous");
    }

    const data = await request(`/appointments/${id}/checkout/stripe-session`, {
      method: "POST",
      body: JSON.stringify({
        success_url: els.appointmentSuccessUrl.value.trim(),
        cancel_url: els.appointmentCancelUrl.value.trim(),
      }),
    });

    setState(els.appointmentState, `Session Stripe RDV creee (${data.session_id})`, "ok");
    els.appointmentCheckoutLink.href = data.checkout_url;
    els.appointmentCheckoutLink.textContent = data.checkout_url;
  } catch (err) {
    setState(els.appointmentState, `Paiement RDV impossible: ${err.message}`, "err");
  }
}

async function refreshOrders() {
  try {
    requireAuth();
    const rows = await request("/shop/orders/me");
    els.ordersPreview.textContent = JSON.stringify(rows, null, 2);
  } catch (err) {
    els.ordersPreview.textContent = `Echec commandes: ${err.message}`;
  }
}

async function refreshReservations() {
  try {
    requireAuth();
    const rows = await request("/shop/reservations/me");
    els.reservationsPreview.textContent = JSON.stringify(rows, null, 2);
  } catch (err) {
    els.reservationsPreview.textContent = `Echec reservations: ${err.message}`;
  }
}

function setDefaultDate() {
  const nextDay = new Date();
  nextDay.setDate(nextDay.getDate() + 1);
  els.appointmentDate.value = nextDay.toISOString().slice(0, 10);
}

function bindEvents() {
  els.tabButtons.forEach((btn) => {
    btn.addEventListener("click", () => switchTab(btn.dataset.tab));
  });

  els.loginBtn.addEventListener("click", login);
  els.logoutBtn.addEventListener("click", logout);

  els.loadProductsBtn.addEventListener("click", loadProducts);
  [els.searchQuery, els.searchBrand, els.searchType, els.searchMinPrice, els.searchMaxPrice].forEach((input) => {
    input.addEventListener("change", loadProducts);
  });

  els.productList.addEventListener("click", (event) => {
    const target = event.target;
    if (!(target instanceof HTMLElement)) {
      return;
    }

    if (target.classList.contains("add-cart-btn")) {
      const card = target.closest(".product-card");
      if (!card) {
        return;
      }
      const qtyInput = card.querySelector(".qty-input");
      const productId = Number(card.dataset.productId);
      const qty = qtyInput instanceof HTMLInputElement ? Number(qtyInput.value || "1") : 1;
      addToCart(productId, qty);
    }
  });

  els.cartLinesBody.addEventListener("click", (event) => {
    const target = event.target;
    if (!(target instanceof HTMLElement)) {
      return;
    }
    if (target.classList.contains("remove-line-btn")) {
      const lineId = Number(target.dataset.lineId);
      if (lineId) {
        removeCartLine(lineId);
      }
    }
  });

  els.refreshCartBtn.addEventListener("click", refreshCart);
  els.payCardBtn.addEventListener("click", () => purchase("card"));
  els.payTransferBtn.addEventListener("click", () => purchase("transfer"));
  els.payWalletBtn.addEventListener("click", () => purchase("wallet"));
  els.reserveBtn.addEventListener("click", reserveCart);
  els.stripeCheckoutBtn.addEventListener("click", createCartStripeSession);
  els.purchaseGiftVoucherBtn.addEventListener("click", purchaseGiftVoucher);
  els.printGiftVoucherBtn.addEventListener("click", () => printVoucherText(state.lastVoucherPrintableText));

  els.loadAppointmentCatalogBtn.addEventListener("click", loadAppointmentCatalog);
  els.searchAvailabilityBtn.addEventListener("click", searchAvailability);
  els.bookAppointmentBtn.addEventListener("click", bookAppointment);

  els.slotList.addEventListener("click", (event) => {
    const target = event.target;
    if (!(target instanceof HTMLElement)) {
      return;
    }
    if (!target.classList.contains("slot-btn")) {
      return;
    }

    els.slotList.querySelectorAll(".slot-btn").forEach((btn) => btn.classList.remove("is-selected"));
    target.classList.add("is-selected");
    state.selectedSlot = target.dataset.slot || "";
  });

  els.refreshAppointmentsBtn.addEventListener("click", refreshAppointments);
  els.refreshOrdersBtn.addEventListener("click", refreshOrders);
  els.refreshReservationsBtn.addEventListener("click", refreshReservations);
  els.refreshGiftVouchersBtn.addEventListener("click", refreshGiftVouchers);
  els.printLastGiftVoucherBtn.addEventListener("click", () => printVoucherText(state.lastVoucherPrintableText));

  els.appointmentsBody.addEventListener("click", (event) => {
    const target = event.target;
    if (!(target instanceof HTMLElement)) {
      return;
    }
    if (target.classList.contains("cancel-appt-btn")) {
      const id = Number(target.dataset.appointmentId);
      if (id) {
        cancelAppointment(id);
      }
    }
  });

  els.payAppointmentBtn.addEventListener("click", createAppointmentStripeSession);
}

bindEvents();
initializeApiBaseInput();
setDefaultDate();
switchTab("tab-shop");
