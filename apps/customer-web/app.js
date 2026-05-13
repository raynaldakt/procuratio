const state = {
  token: "",
  cart: null,
  products: [],
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

const loginBtn = document.getElementById("loginBtn");
const loadProductsBtn = document.getElementById("loadProductsBtn");
const addToCartBtn = document.getElementById("addToCartBtn");
const refreshCartBtn = document.getElementById("refreshCartBtn");
const stripeCheckoutBtn = document.getElementById("stripeCheckoutBtn");

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

loginBtn.addEventListener("click", doLogin);
loadProductsBtn.addEventListener("click", loadProducts);
addToCartBtn.addEventListener("click", addToCart);
refreshCartBtn.addEventListener("click", refreshCart);
stripeCheckoutBtn.addEventListener("click", createStripeSession);
