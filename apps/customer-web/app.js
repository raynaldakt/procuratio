const state = {
  token: "",
  cart: null,
  products: [],
  services: [],
  employees: [],
  slots: [],
};

const apiBaseInput = document.getElementById("apiBase");
const emailInput = document.getElementById("email");
const passwordInput = document.getElementById("password");
const authState = document.getElementById("authState");
const productSelect = document.getElementById("productSelect");
const quantityInput = document.getElementById("quantity");
const cartPreview = document.getElementById("cartPreview");
const successUrlInput = document.getElementById("successUrl");
const cancelUrlInput = document.getElementById("cancelUrl");
const checkoutState = document.getElementById("checkoutState");
const checkoutLink = document.getElementById("checkoutLink");
const serviceSelect = document.getElementById("serviceSelect");
const employeeSelect = document.getElementById("employeeSelect");
const appointmentDateInput = document.getElementById("appointmentDate");
const appointmentCatalogState = document.getElementById("appointmentCatalogState");
const slotSelect = document.getElementById("slotSelect");
const appointmentNotesInput = document.getElementById("appointmentNotes");
const payInStoreInput = document.getElementById("payInStore");
const bookState = document.getElementById("bookState");
const bookPreview = document.getElementById("bookPreview");
const refreshAppointmentsBtn = document.getElementById("refreshAppointmentsBtn");
const appointmentState = document.getElementById("appointmentState");
const appointmentPreview = document.getElementById("appointmentPreview");
const cancelAppointmentIdInput = document.getElementById("cancelAppointmentId");
const cancelAppointmentBtn = document.getElementById("cancelAppointmentBtn");
const payAppointmentIdInput = document.getElementById("payAppointmentId");
const appointmentSuccessUrlInput = document.getElementById("appointmentSuccessUrl");
const appointmentCancelUrlInput = document.getElementById("appointmentCancelUrl");
const payAppointmentBtn = document.getElementById("payAppointmentBtn");
const appointmentCheckoutLink = document.getElementById("appointmentCheckoutLink");

const loginBtn = document.getElementById("loginBtn");
const loadProductsBtn = document.getElementById("loadProductsBtn");
const addToCartBtn = document.getElementById("addToCartBtn");
const refreshCartBtn = document.getElementById("refreshCartBtn");
const stripeCheckoutBtn = document.getElementById("stripeCheckoutBtn");
const loadAppointmentCatalogBtn = document.getElementById("loadAppointmentCatalogBtn");
const searchAvailabilityBtn = document.getElementById("searchAvailabilityBtn");
const bookAppointmentBtn = document.getElementById("bookAppointmentBtn");

function getApiBase() {
  return apiBaseInput.value.trim().replace(/\/$/, "");
}

async function api(path, options = {}) {
  const headers = new Headers(options.headers || {});
  headers.set("Content-Type", "application/json");
  if (state.token) {
    headers.set("Authorization", `Bearer ${state.token}`);
  }

  const response = await fetch(`${getApiBase()}${path}`, {
    ...options,
    headers,
  });

  const text = await response.text();
  let body = {};
  if (text) {
    try {
      body = JSON.parse(text);
    } catch (_) {
      body = { raw: text };
    }
  }
  if (!response.ok) {
    throw new Error(body.detail || body.raw || `${response.status}`);
  }
  return body;
}

function renderProducts() {
  productSelect.innerHTML = "";
  for (const p of state.products) {
    const option = document.createElement("option");
    option.value = String(p.id);
    option.textContent = `#${p.id} ${p.name} - ${(p.price_cents / 100).toFixed(2)} EUR`;
    productSelect.appendChild(option);
  }
}

function renderCart(payload) {
  state.cart = payload;
  cartPreview.textContent = JSON.stringify(payload, null, 2);
}

function setDefaultAppointmentDate() {
  const tomorrow = new Date();
  tomorrow.setDate(tomorrow.getDate() + 1);
  appointmentDateInput.value = tomorrow.toISOString().slice(0, 10);
}

function renderAppointmentCatalog() {
  serviceSelect.innerHTML = "";
  for (const s of state.services) {
    const option = document.createElement("option");
    option.value = String(s.id);
    option.textContent = `${s.name} (${s.duration_minutes} min)`;
    serviceSelect.appendChild(option);
  }

  employeeSelect.innerHTML = "";
  for (const emp of state.employees) {
    const option = document.createElement("option");
    option.value = String(emp.user_id);
    option.textContent = `Employee #${emp.user_id}`;
    employeeSelect.appendChild(option);
  }
}

function renderSlots() {
  slotSelect.innerHTML = "";
  for (const slot of state.slots) {
    const option = document.createElement("option");
    option.value = slot.start_at;
    option.textContent = new Date(slot.start_at).toLocaleString();
    slotSelect.appendChild(option);
  }
}

async function doLogin() {
  authState.textContent = "Authenticating...";
  try {
    const result = await api("/auth/login", {
      method: "POST",
      body: JSON.stringify({
        email: emailInput.value.trim(),
        password: passwordInput.value,
      }),
      headers: {},
    });
    state.token = result.access_token || "";
    authState.textContent = "Authenticated";
  } catch (err) {
    authState.textContent = `Login failed: ${err.message}`;
  }
}

async function loadProducts() {
  try {
    const products = await api("/shop/products", { method: "GET" });
    state.products = products;
    renderProducts();
    authState.textContent = `Loaded ${products.length} product(s)`;
  } catch (err) {
    authState.textContent = `Load products failed: ${err.message}`;
  }
}

async function ensureCart() {
  const cart = await api("/shop/cart", {
    method: "POST",
    body: JSON.stringify({}),
  });
  return cart;
}

async function addToCart() {
  try {
    await ensureCart();
    const payload = await api("/shop/cart/lines", {
      method: "POST",
      body: JSON.stringify({
        product_item_id: Number(productSelect.value),
        quantity: Number(quantityInput.value || "1"),
      }),
    });
    renderCart(payload);
  } catch (err) {
    cartPreview.textContent = `Add to cart failed: ${err.message}`;
  }
}

async function refreshCart() {
  try {
    const payload = await api("/shop/cart", { method: "GET" });
    renderCart(payload);
  } catch (err) {
    cartPreview.textContent = `Refresh cart failed: ${err.message}`;
  }
}

async function createStripeSession() {
  checkoutState.textContent = "Creating checkout session...";
  checkoutLink.textContent = "";
  checkoutLink.href = "#";
  try {
    const payload = await api("/shop/cart/checkout/stripe-session", {
      method: "POST",
      body: JSON.stringify({
        success_url: successUrlInput.value.trim(),
        cancel_url: cancelUrlInput.value.trim(),
      }),
    });
    checkoutState.textContent = `Session created: ${payload.session_id}`;
    checkoutLink.href = payload.checkout_url;
    checkoutLink.textContent = payload.checkout_url;
  } catch (err) {
    checkoutState.textContent = `Checkout failed: ${err.message}`;
  }
}

async function loadAppointmentCatalog() {
  appointmentCatalogState.textContent = "Loading services and employees...";
  try {
    const [services, employees] = await Promise.all([
      api("/appointments/services", { method: "GET" }),
      api("/appointments/employees", { method: "GET" }),
    ]);
    state.services = services;
    state.employees = employees;
    renderAppointmentCatalog();
    if (services.length === 0) {
      appointmentCatalogState.textContent = "No active services found. Create one from staff/backoffice.";
      return;
    }
    if (employees.length === 0) {
      appointmentCatalogState.textContent = "No bookable employees found. Configure employee profiles.";
      return;
    }
    appointmentCatalogState.textContent = `Loaded ${services.length} service(s), ${employees.length} employee(s)`;
  } catch (err) {
    appointmentCatalogState.textContent = `Catalog load failed: ${err.message}`;
  }
}

async function searchAvailability() {
  appointmentCatalogState.textContent = "Searching availability...";
  try {
    const serviceId = Number(serviceSelect.value);
    const employeeId = Number(employeeSelect.value);
    const targetDate = appointmentDateInput.value;
    if (!serviceId || !employeeId || !targetDate) {
      throw new Error("Pick service, employee and date");
    }

    const query = new URLSearchParams({
      service_offering_id: String(serviceId),
      employee_user_id: String(employeeId),
      target_date: targetDate,
    });
    const slots = await api(`/appointments/availability?${query.toString()}`, { method: "GET" });
    state.slots = slots;
    renderSlots();
    appointmentCatalogState.textContent = `Found ${slots.length} slot(s)`;
  } catch (err) {
    appointmentCatalogState.textContent = `Availability failed: ${err.message}`;
  }
}

async function bookAppointment() {
  bookState.textContent = "Booking appointment...";
  try {
    const payload = await api("/appointments/book", {
      method: "POST",
      body: JSON.stringify({
        service_offering_id: Number(serviceSelect.value),
        employee_user_id: Number(employeeSelect.value),
        start_at: slotSelect.value,
        notes: appointmentNotesInput.value.trim() || null,
        pay_in_store: payInStoreInput.checked,
      }),
    });
    bookState.textContent = `Appointment #${payload.id} booked`;
    bookPreview.textContent = JSON.stringify(payload, null, 2);
    cancelAppointmentIdInput.value = String(payload.id);
    payAppointmentIdInput.value = String(payload.id);
  } catch (err) {
    bookState.textContent = `Booking failed: ${err.message}`;
  }
}

async function refreshAppointments() {
  appointmentState.textContent = "Loading appointments...";
  try {
    const rows = await api("/appointments/me", { method: "GET" });
    appointmentState.textContent = `Loaded ${rows.length} appointment(s)`;
    appointmentPreview.textContent = JSON.stringify(rows, null, 2);
  } catch (err) {
    appointmentState.textContent = `Load failed: ${err.message}`;
  }
}

async function cancelAppointment() {
  appointmentState.textContent = "Cancelling appointment...";
  try {
    const id = Number(cancelAppointmentIdInput.value);
    if (!id) {
      throw new Error("Provide appointment ID");
    }
    const payload = await api(`/appointments/${id}/cancel`, { method: "POST", body: JSON.stringify({}) });
    appointmentState.textContent = `Appointment #${id} cancelled`;
    appointmentPreview.textContent = JSON.stringify(payload, null, 2);
  } catch (err) {
    appointmentState.textContent = `Cancel failed: ${err.message}`;
  }
}

async function payAppointmentOnline() {
  appointmentState.textContent = "Creating appointment checkout session...";
  appointmentCheckoutLink.textContent = "";
  appointmentCheckoutLink.href = "#";
  try {
    const id = Number(payAppointmentIdInput.value);
    if (!id) {
      throw new Error("Provide appointment ID");
    }
    const payload = await api(`/appointments/${id}/checkout/stripe-session`, {
      method: "POST",
      body: JSON.stringify({
        success_url: appointmentSuccessUrlInput.value.trim(),
        cancel_url: appointmentCancelUrlInput.value.trim(),
      }),
    });
    appointmentState.textContent = `Appointment session created: ${payload.session_id}`;
    appointmentCheckoutLink.href = payload.checkout_url;
    appointmentCheckoutLink.textContent = payload.checkout_url;
  } catch (err) {
    appointmentState.textContent = `Appointment payment failed: ${err.message}`;
  }
}

loginBtn.addEventListener("click", doLogin);
loadProductsBtn.addEventListener("click", loadProducts);
addToCartBtn.addEventListener("click", addToCart);
refreshCartBtn.addEventListener("click", refreshCart);
stripeCheckoutBtn.addEventListener("click", createStripeSession);
loadAppointmentCatalogBtn.addEventListener("click", loadAppointmentCatalog);
searchAvailabilityBtn.addEventListener("click", searchAvailability);
bookAppointmentBtn.addEventListener("click", bookAppointment);
refreshAppointmentsBtn.addEventListener("click", refreshAppointments);
cancelAppointmentBtn.addEventListener("click", cancelAppointment);
payAppointmentBtn.addEventListener("click", payAppointmentOnline);

setDefaultAppointmentDate();
