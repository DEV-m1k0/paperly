// Paperly shared utilities. Exposed on window.paperly.
(function () {
  "use strict";

  function getCookie(name) {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop().split(";").shift();
    return "";
  }

  function escapeHtml(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#39;");
  }

  function formatMoney(value, suffix = "₽") {
    const num = Number(value || 0);
    return `${num.toLocaleString("ru-RU")} ${suffix}`;
  }

  function renderStars(rating) {
    const full = Math.round(Number(rating));
    return Array.from({ length: 5 }, (_, index) => {
      return `<i class="bi ${index < full ? "bi-star-fill" : "bi-star"}"></i>`;
    }).join("");
  }

  const PURPOSE_LABELS = {
    school: "Школа",
    office: "Офис",
    creative: "Творчество",
    universal: "Универсально",
  };

  function formatPurpose(value) {
    return PURPOSE_LABELS[value] || value || "—";
  }

  const ORDER_STATUS_LABELS = {
    new: "Новый",
    confirmed: "Подтверждён",
    paid: "Оплачен",
    shipped: "Отгружен",
    done: "Завершён",
    canceled: "Отменён",
  };

  function formatOrderStatus(status) {
    return ORDER_STATUS_LABELS[status] || status;
  }

  // --- Fetch wrapper ---
  async function apiFetch(url, options = {}) {
    const method = (options.method || "GET").toUpperCase();
    const headers = new Headers(options.headers || {});
    const unsafe = ["POST", "PUT", "PATCH", "DELETE"].includes(method);
    if (unsafe && !headers.has("X-CSRFToken")) {
      headers.set("X-CSRFToken", getCookie("csrftoken"));
    }
    if (options.body && !(options.body instanceof FormData) && !headers.has("Content-Type")) {
      headers.set("Content-Type", "application/json");
    }
    const init = {
      credentials: "same-origin",
      ...options,
      method,
      headers,
    };
    if (init.body && typeof init.body === "object" && !(init.body instanceof FormData)) {
      init.body = JSON.stringify(init.body);
    }
    const response = await fetch(url, init);
    return response;
  }

  async function apiJson(url, options = {}) {
    const response = await apiFetch(url, options);
    if (!response.ok) {
      const error = new Error(`HTTP ${response.status}`);
      error.status = response.status;
      try {
        error.data = await response.json();
      } catch {
        error.data = null;
      }
      throw error;
    }
    if (response.status === 204) return null;
    return response.json();
  }

  function unwrapList(payload) {
    if (Array.isArray(payload)) return payload;
    if (payload && Array.isArray(payload.results)) return payload.results;
    return [];
  }

  // --- Cart (localStorage) ---
  const CART_ITEMS_KEY = "paperly_cart_items";
  const CART_COUNT_KEY = "paperly_cart_count";

  function readCartItems() {
    try {
      return JSON.parse(localStorage.getItem(CART_ITEMS_KEY) || "[]");
    } catch {
      return [];
    }
  }

  function saveCartItems(items) {
    localStorage.setItem(CART_ITEMS_KEY, JSON.stringify(items));
    const count = items.reduce((sum, item) => sum + (Number(item.qty) || 0), 0);
    localStorage.setItem(CART_COUNT_KEY, String(count));
    renderCartCount(count);
    return count;
  }

  function renderCartCount(explicit) {
    const node = document.getElementById("cartCount");
    if (!node) return;
    const count = typeof explicit === "number"
      ? explicit
      : (readCartItems().reduce((sum, item) => sum + (Number(item.qty) || 0), 0));
    node.textContent = String(count);
  }

  function addCartItem(product, quantity = 1) {
    const items = readCartItems();
    const id = String(product.id);
    const existing = items.find((item) => String(item.id) === id);
    const qty = Math.max(1, Number(quantity) || 1);
    if (existing) {
      existing.qty += qty;
    } else {
      items.push({
        id,
        title: product.title || "Товар",
        price: Number(product.price) || 0,
        img: product.img || "",
        desc: product.desc || "",
        qty,
      });
    }
    return saveCartItems(items);
  }

  function clearCart() {
    saveCartItems([]);
  }

  // --- Favorites helpers (auth: API, guest: localStorage + merge on login) ---
  const LOCAL_FAV_KEY = "paperly_local_favs";

  function isAuthenticated() {
    return document.body?.dataset.isAuthenticated === "true";
  }

  function readLocalFavorites() {
    try {
      const ids = JSON.parse(localStorage.getItem(LOCAL_FAV_KEY) || "[]");
      return Array.isArray(ids) ? ids.map(String) : [];
    } catch {
      return [];
    }
  }

  function writeLocalFavorites(ids) {
    localStorage.setItem(LOCAL_FAV_KEY, JSON.stringify(ids.map(String)));
  }

  function isLocalFavorite(productId) {
    return readLocalFavorites().includes(String(productId));
  }

  function addLocalFavorite(productId) {
    const ids = readLocalFavorites();
    const id = String(productId);
    if (!ids.includes(id)) ids.unshift(id);
    writeLocalFavorites(ids);
    return ids;
  }

  function removeLocalFavorite(productId) {
    const ids = readLocalFavorites().filter((x) => x !== String(productId));
    writeLocalFavorites(ids);
    return ids;
  }

  function clearLocalFavorites() {
    localStorage.removeItem(LOCAL_FAV_KEY);
  }

  async function fetchFavorites() {
    try {
      const payload = await apiJson("/api/favorites/");
      return unwrapList(payload);
    } catch {
      return [];
    }
  }

  async function updateFavoritesCount() {
    const node = document.getElementById("wishlistCount");
    if (!node) return;
    if (!isAuthenticated()) {
      node.textContent = String(readLocalFavorites().length);
      return;
    }
    const favorites = await fetchFavorites();
    node.textContent = String(favorites.length);
  }

  // Called once on login: upload local favs to server, then clear local.
  async function mergeLocalFavoritesToServer() {
    if (!isAuthenticated()) return;
    const localIds = readLocalFavorites();
    if (!localIds.length) return;
    try {
      const existing = await fetchFavorites();
      const existingIds = new Set(existing.map((f) => String(f.product)));
      for (const id of localIds) {
        if (existingIds.has(String(id))) continue;
        try {
          await apiFetch("/api/favorites/", { method: "POST", body: { product: Number(id) } });
        } catch (error) {
          // ignore per-item failures
        }
      }
      clearLocalFavorites();
      updateFavoritesCount();
    } catch (error) {
      console.error("Merge local favorites error", error);
    }
  }

  // --- Expose ---
  window.paperly = Object.assign(window.paperly || {}, {
    getCookie,
    escapeHtml,
    formatMoney,
    renderStars,
    formatPurpose,
    formatOrderStatus,
    apiFetch,
    apiJson,
    unwrapList,
    // cart
    readCartItems,
    saveCartItems,
    addCartItem,
    clearCart,
    renderCartCount,
    // favorites
    fetchFavorites,
    updateFavoritesCount,
    isAuthenticated,
    readLocalFavorites,
    writeLocalFavorites,
    isLocalFavorite,
    addLocalFavorite,
    removeLocalFavorite,
    clearLocalFavorites,
    mergeLocalFavoritesToServer,
  });
})();
