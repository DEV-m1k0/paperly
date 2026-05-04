document.addEventListener("DOMContentLoaded", () => {
  const P = window.paperly;
  const { apiJson, apiFetch, unwrapList, formatMoney } = P;
  let isAuthenticated = document.body?.dataset.isAuthenticated === "true";
  let pendingDoneRedirect = "/catalog/";

  const searchForm = document.getElementById("searchForm");
  const cartItemsNode = document.getElementById("cartItems");
  const cartEmpty = document.getElementById("cartEmpty");
  const checkoutBlock = document.getElementById("checkoutBlock");
  const summaryNode = document.getElementById("summary");
  const checkoutForm = document.getElementById("checkoutForm");
  const phoneInput = document.getElementById("phone");
  const deliveryTypeSelect = document.getElementById("deliveryType");
  const pickupPointSelect = document.getElementById("pickupPoint");

  // ---------- State ----------
  let items = P.readCartItems();
  let deliveryTariffs = [];
  let pickupPoints = [];
  let serverCart = null; // { id, items: [{id, product, quantity, price_snapshot}] }
  let appliedPromo = null; // { code, discount, free_shipping, message, discount_type }
  let pendingSbpToken = null;
  let pendingSbpConfirmUrl = "";
  let sbpFinalizing = false;

  // ---------- Helpers ----------
  function totalQty() {
    return items.reduce((sum, item) => sum + item.qty, 0);
  }

  function totalAmount() {
    return items.reduce((sum, item) => sum + item.price * item.qty, 0);
  }

  function selectedDeliveryType() {
    return deliveryTypeSelect?.value || "courier";
  }

  function formatRussianPhone(value) {
    const digits = String(value || "").replace(/\D/g, "");
    if (!digits) return "";

    let normalized = digits;
    if (normalized.startsWith("8")) normalized = `7${normalized.slice(1)}`;
    if (!normalized.startsWith("7")) normalized = `7${normalized}`;
    normalized = normalized.slice(0, 11);

    const country = normalized.slice(0, 1);
    const code = normalized.slice(1, 4);
    const first = normalized.slice(4, 7);
    const second = normalized.slice(7, 9);
    const third = normalized.slice(9, 11);

    let result = `+${country}`;
    if (code) result += ` (${code}`;
    if (code.length === 3) result += ")";
    if (first) result += ` ${first}`;
    if (second) result += `-${second}`;
    if (third) result += `-${third}`;
    return result;
  }

  function bindPhoneMask() {
    if (!phoneInput) return;

    const applyMask = () => {
      phoneInput.value = formatRussianPhone(phoneInput.value);
    };

    phoneInput.addEventListener("input", applyMask);
    phoneInput.addEventListener("focus", () => {
      if (!phoneInput.value.trim()) phoneInput.value = "+7";
    });
    phoneInput.addEventListener("blur", () => {
      if (phoneInput.value === "+7") phoneInput.value = "";
    });

    applyMask();
  }

  function getDeliveryPrice() {
    if (!items.length) return 0;
    const type = selectedDeliveryType();
    const tariff = deliveryTariffs.find((t) => t.delivery_type === type);
    if (!tariff) return 0;
    const base = Number(tariff.price) || 0;
    const freeFrom = Number(tariff.free_from_amount) || 0;
    if (freeFrom > 0 && totalAmount() >= freeFrom) return 0;
    return base;
  }

  function renderSummary() {
    const amount = totalAmount();
    let delivery = getDeliveryPrice();
    const rows = [
      `<div class="summary-row"><span>Товары (${totalQty()} шт)</span><strong>${formatMoney(amount)}</strong></div>`,
    ];

    if (appliedPromo?.free_shipping) {
      rows.push(`<div class="summary-row"><span>Доставка</span><strong>Бесплатно</strong></div>`);
      delivery = 0;
    } else {
      rows.push(`<div class="summary-row"><span>Доставка</span><strong>${delivery ? formatMoney(delivery) : "0 ₽"}</strong></div>`);
    }

    let total = amount + delivery;
    if (appliedPromo && !appliedPromo.free_shipping && appliedPromo.discount > 0) {
      rows.push(`<div class="summary-row summary-row--discount"><span>Промокод ${appliedPromo.code}</span><strong>−${formatMoney(appliedPromo.discount)}</strong></div>`);
      total = Math.max(0, total - appliedPromo.discount);
    }

    rows.push(`<div class="summary-row"><span>Итого</span><strong>${formatMoney(total)}</strong></div>`);
    summaryNode.innerHTML = rows.join("");
  }

  // ---------- Promo code ----------
  function renderPromoUI() {
    const appliedBlock = document.getElementById("promoApplied");
    const applyBtn = document.getElementById("promoApplyBtn");
    const inputEl = document.getElementById("promoCodeInput");
    const codeEl = document.getElementById("promoAppliedCode");
    const msgEl = document.getElementById("promoAppliedMessage");
    const statusEl = document.getElementById("promoStatus");

    if (appliedPromo) {
      if (inputEl) { inputEl.value = appliedPromo.code; inputEl.disabled = true; }
      if (applyBtn) applyBtn.hidden = true;
      if (appliedBlock) appliedBlock.hidden = false;
      if (codeEl) codeEl.textContent = appliedPromo.code;
      if (msgEl) msgEl.textContent = appliedPromo.message || "Скидка применена";
      if (statusEl) statusEl.hidden = true;
    } else {
      if (inputEl) inputEl.disabled = false;
      if (applyBtn) applyBtn.hidden = false;
      if (appliedBlock) appliedBlock.hidden = true;
    }
  }

  function cartPayloadForPromo() {
    return {
      items: items
        .filter((it) => /^\d+$/.test(String(it.id)))
        .map((it) => ({ product: Number(it.id), quantity: it.qty, unit_price: it.price })),
      delivery_price: getDeliveryPrice(),
      email: (document.getElementById("email")?.value || "").trim(),
    };
  }

  async function applyPromoCode(rawCode) {
    const code = (rawCode || "").trim().toUpperCase();
    const statusEl = document.getElementById("promoStatus");
    const applyBtn = document.getElementById("promoApplyBtn");
    if (!code) {
      if (statusEl) { statusEl.hidden = false; statusEl.className = "promo-box__status is-error"; statusEl.textContent = "Введите промокод."; }
      return;
    }
    if (!items.length) {
      if (statusEl) { statusEl.hidden = false; statusEl.className = "promo-box__status is-error"; statusEl.textContent = "Корзина пуста."; }
      return;
    }

    if (statusEl) { statusEl.hidden = false; statusEl.className = "promo-box__status is-pending"; statusEl.textContent = "Проверяем промокод..."; }
    if (applyBtn) applyBtn.disabled = true;

    try {
      const response = await apiFetch("/api/promo-codes/validate/", {
        method: "POST",
        body: { code, ...cartPayloadForPromo() },
      });
      const data = await response.json().catch(() => ({}));
      if (response.ok && data.valid) {
        appliedPromo = {
          code: data.code,
          discount: Number(data.discount || 0),
          free_shipping: Boolean(data.free_shipping),
          discount_type: data.discount_type,
          message: data.message,
        };
        if (statusEl) statusEl.hidden = true;
        renderPromoUI();
        renderSummary();
      } else {
        appliedPromo = null;
        if (statusEl) {
          statusEl.hidden = false;
          statusEl.className = "promo-box__status is-error";
          statusEl.textContent = data.message || "Не удалось применить промокод.";
        }
        renderPromoUI();
        renderSummary();
      }
    } catch {
      appliedPromo = null;
      if (statusEl) { statusEl.hidden = false; statusEl.className = "promo-box__status is-error"; statusEl.textContent = "Сетевая ошибка. Попробуйте ещё раз."; }
    } finally {
      if (applyBtn) applyBtn.disabled = false;
    }
  }

  function removePromoCode() {
    appliedPromo = null;
    const inputEl = document.getElementById("promoCodeInput");
    if (inputEl) inputEl.value = "";
    const statusEl = document.getElementById("promoStatus");
    if (statusEl) statusEl.hidden = true;
    renderPromoUI();
    renderSummary();
  }

  function renderItems() {
    const cartHeader = document.getElementById("cartHeader");
    if (items.length === 0) {
      cartItemsNode.innerHTML = "";
      cartEmpty.hidden = false;
      checkoutBlock.hidden = true;
      if (cartHeader) cartHeader.hidden = true;
      P.saveCartItems(items);
      renderSummary();
      renderHeaderCount();
      return;
    }

    cartEmpty.hidden = true;
    checkoutBlock.hidden = false;
    if (cartHeader) cartHeader.hidden = false;

    cartItemsNode.innerHTML = items
      .map((item) => {
        const imgMarkup = item.img
          ? `<img class="item__img" src="${item.img}" alt="${P.escapeHtml(item.title)}">`
          : `<div class="item__img item__img--placeholder"><i class="bi bi-bag" aria-hidden="true"></i></div>`;
        const maxQty = Math.max(0, Number(item.maxQty) || 0);
        // max-атрибут инпута + подпись «макс. N шт» — чтобы пользователь
        // видел предел до того, как упрётся в него.
        const maxAttr = maxQty > 0 ? ` max="${maxQty}"` : "";
        const hint = maxQty > 0
          ? `<small class="item__limit" style="display:block;margin-top:6px;color:var(--color-muted,#64748b);font-size:12px;">Макс. ${maxQty} шт. в заказе</small>`
          : "";
        return `
          <article class="item" data-id="${item.id}">
            ${imgMarkup}
            <div class="item__info">
              <h3><a href="/product/?id=${item.id}">${P.escapeHtml(item.title)}</a></h3>
              ${item.desc ? `<p>${P.escapeHtml(item.desc)}</p>` : ""}
              <span class="item__unit">${formatMoney(item.price)} <small>/ шт.</small></span>
            </div>
            <div class="item__controls">
              <div class="item__qty qty">
                <button data-act="minus" type="button" aria-label="Уменьшить"><i class="bi bi-dash"></i></button>
                <input type="number" min="1"${maxAttr} value="${item.qty}" data-act="input" aria-label="Количество">
                <button data-act="plus" type="button" aria-label="Увеличить"><i class="bi bi-plus"></i></button>
              </div>
              ${hint}
              <strong class="item__sum">${formatMoney(item.price * item.qty)}</strong>
              <button class="item__remove" data-act="remove" type="button" aria-label="Удалить">
                <i class="bi bi-x-lg" aria-hidden="true"></i>
              </button>
            </div>
          </article>
        `;
      })
      .join("");

    P.saveCartItems(items);
    renderSummary();
    renderHeaderCount();
  }

  function renderHeaderCount() {
    const headerCount = document.getElementById("cartHeaderCount");
    if (!headerCount) return;
    const count = totalQty();
    const plural = count === 1
      ? "товар"
      : count >= 2 && count <= 4 && (count % 100 < 10 || count % 100 >= 20)
        ? "товара"
        : "товаров";
    headerCount.textContent = `${count} ${plural}`;
  }

  // ---------- Cart mutations ----------
  async function persistCart() {
    P.saveCartItems(items);
    if (!isAuthenticated) return;
    try {
      await syncItemsToServer();
    } catch (error) {
      console.error("Cart sync error", error);
    }
  }

  function changeQty(id, nextQty) {
    items = items.map((item) => {
      if (item.id !== id) return item;
      const max = Math.max(0, Number(item.maxQty) || 0);
      let clamped = Math.max(1, nextQty);
      let hitLimit = false;
      if (max > 0 && clamped > max) {
        clamped = max;
        hitLimit = true;
      }
      if (hitLimit && nextQty > max) {
        // Уведомляем только если пользователь реально пытался выйти за лимит
        // (а не при авто-обрезке при загрузке корзины с устаревшими данными).
        alert(`Максимум ${max} шт. «${item.title}» в одном заказе.`);
      }
      return { ...item, qty: clamped };
    });
    renderItems();
    persistCart();
    // Re-check the promo (new subtotal may cross min-order thresholds).
    if (appliedPromo) applyPromoCode(appliedPromo.code);
  }

  function removeItem(id) {
    items = items.filter((item) => item.id !== id);
    renderItems();
    persistCart();
    if (appliedPromo) applyPromoCode(appliedPromo.code);
  }

  cartItemsNode.addEventListener("click", (event) => {
    const actionEl = event.target.closest("[data-act]");
    if (!actionEl) return;
    const itemNode = actionEl.closest(".item");
    const id = itemNode?.dataset.id;
    const item = items.find((x) => x.id === id);
    if (!item) return;
    const act = actionEl.dataset.act;
    if (act === "minus") changeQty(id, item.qty - 1);
    if (act === "plus") changeQty(id, item.qty + 1);
    if (act === "remove") removeItem(id);
  });

  cartItemsNode.addEventListener("change", (event) => {
    const input = event.target.closest("input[data-act='input']");
    if (!input) return;
    const itemNode = input.closest(".item");
    const id = itemNode?.dataset.id;
    changeQty(id, Number(input.value || 1));
  });

  function applyDeliveryTypeVisibility() {
    const type = selectedDeliveryType();
    document.querySelectorAll("[data-delivery-field]").forEach((node) => {
      const applies = node.dataset.deliveryField === type;
      node.hidden = !applies;
      // Toggle `required` + disabled so hidden inputs don't block form validation.
      node.querySelectorAll("input, select, textarea").forEach((ctrl) => {
        if (applies) {
          ctrl.disabled = false;
          if (ctrl.dataset.origRequired === "true") ctrl.required = true;
        } else {
          if (ctrl.required) ctrl.dataset.origRequired = "true";
          ctrl.required = false;
          ctrl.disabled = true;
        }
      });
    });
  }

  deliveryTypeSelect?.addEventListener("change", () => {
    applyDeliveryTypeVisibility();
    // Re-validate promo because delivery change can alter min-order math / free-shipping.
    if (appliedPromo) applyPromoCode(appliedPromo.code);
    else renderSummary();
  });

  // Wire promo-code UI (buttons + enter key)
  document.getElementById("promoApplyBtn")?.addEventListener("click", () => {
    applyPromoCode(document.getElementById("promoCodeInput")?.value || "");
  });
  document.getElementById("promoCodeInput")?.addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      event.preventDefault();
      applyPromoCode(event.currentTarget.value);
    }
  });
  document.getElementById("promoRemoveBtn")?.addEventListener("click", removePromoCode);

  // Sync payment radio -> hidden input
  document.querySelectorAll('input[name="paymentType"]').forEach((radio) => {
    radio.addEventListener("change", () => {
      const hidden = document.getElementById("paymentType");
      if (hidden && radio.checked) hidden.value = radio.value;
    });
  });

  // Account creation toggle: reveal password field on checkbox
  const createAccountCheckbox = document.getElementById("createAccount");
  const accountPasswordWrap = document.getElementById("accountPasswordWrap");
  createAccountCheckbox?.addEventListener("change", () => {
    if (accountPasswordWrap) {
      accountPasswordWrap.hidden = !createAccountCheckbox.checked;
    }
    if (createAccountCheckbox.checked) {
      setTimeout(() => document.getElementById("accountPassword")?.focus(), 50);
    }
  });

  // ---------- Server cart sync ----------
  async function loadDeliveryTariffs() {
    try {
      const payload = await apiJson("/api/delivery-tariffs/");
      deliveryTariffs = unwrapList(payload);
    } catch (error) {
      console.error("Delivery tariffs error", error);
      deliveryTariffs = [];
    }
  }

  async function loadPickupPoints() {
    if (!pickupPointSelect) return;
    try {
      const payload = await apiJson("/api/pickup-points/");
      pickupPoints = unwrapList(payload).filter((p) => p.is_active !== false);
    } catch (error) {
      console.error("Pickup points error", error);
      pickupPoints = [];
    }
    if (!pickupPoints.length) {
      pickupPointSelect.innerHTML = '<option value="">Нет активных пунктов</option>';
      return;
    }
    pickupPointSelect.innerHTML = [
      '<option value="">— Выберите пункт —</option>',
      ...pickupPoints.map((p) => {
        const label = `${p.name} — ${p.address}${p.city ? ", " + p.city : ""}`;
        return `<option value="${p.id}">${label.replace(/[<>]/g, "")}</option>`;
      }),
    ].join("");
  }

  async function ensureServerCart() {
    if (!isAuthenticated) return null;
    try {
      const payload = await apiJson("/api/carts/");
      const rows = unwrapList(payload);
      if (rows.length) {
        serverCart = rows[0];
        return serverCart;
      }
      const created = await apiJson("/api/carts/", { method: "POST", body: {} });
      serverCart = { ...created, items: created.items || [] };
      return serverCart;
    } catch (error) {
      console.error("Cart load error", error);
      return null;
    }
  }

  function serverItemsToLocal(serverItems) {
    return serverItems
      .filter((item) => item.product)
      .map((item) => ({
        id: String(item.product),
        serverId: item.id,
        title: item.product_title || "Товар",
        desc: item.product_short_description || "",
        price: Number(item.price_snapshot) || 0,
        qty: Number(item.quantity) || 1,
        img: item.product_image || "",
        // maxQty подтянется через enrichItemsWithLimits() — CartItem сам его не
        // хранит, лимит живёт на Product.max_order_quantity.
        maxQty: 0,
      }));
  }

  // Подтягиваем max_order_quantity из /api/products/{id}/ для тех позиций, где
  // maxQty отсутствует — нужно после загрузки корзины с сервера или для
  // гостевых item'ов, сохранённых в localStorage до внедрения этого лимита.
  async function enrichItemsWithLimits() {
    const needIds = items
      .filter((item) => /^\d+$/.test(String(item.id)) && !Number(item.maxQty))
      .map((item) => String(item.id));
    if (!needIds.length) return false;
    const results = await Promise.all(
      needIds.map((id) => apiJson(`/api/products/${id}/`).catch(() => null))
    );
    const byId = new Map();
    results.forEach((product) => {
      if (product?.id != null) byId.set(String(product.id), product);
    });
    let anyChanged = false;
    items = items.map((item) => {
      const product = byId.get(String(item.id));
      if (!product) return item;
      const maxQty = Math.max(0, Number(product.max_order_quantity) || 0);
      let qty = Number(item.qty) || 1;
      if (maxQty > 0 && qty > maxQty) {
        qty = maxQty;
        anyChanged = true;
      }
      if (maxQty !== Number(item.maxQty) || qty !== Number(item.qty)) {
        anyChanged = true;
      }
      return { ...item, maxQty, qty };
    });
    return anyChanged;
  }

  async function syncItemsToServer() {
    if (!isAuthenticated || !serverCart) return;
    const productIds = new Set(items.filter((item) => /^\d+$/.test(item.id)).map((item) => item.id));
    const existing = new Map((serverCart.items || []).map((row) => [String(row.product), row]));

    // upsert
    for (const local of items) {
      if (!/^\d+$/.test(local.id)) continue; // skip local-only (string) ids
      const row = existing.get(local.id);
      const body = {
        cart: serverCart.id,
        product: Number(local.id),
        quantity: local.qty,
        price_snapshot: local.price,
      };
      if (row) {
        if (Number(row.quantity) !== Number(local.qty) || Number(row.price_snapshot) !== Number(local.price)) {
          await apiFetch(`/api/cart-items/${row.id}/`, { method: "PATCH", body });
        }
      } else {
        await apiFetch(`/api/cart-items/`, { method: "POST", body });
      }
    }

    // delete removed
    for (const [pid, row] of existing) {
      if (!productIds.has(pid)) {
        await apiFetch(`/api/cart-items/${row.id}/`, { method: "DELETE" });
      }
    }

    const reloaded = await apiJson(`/api/carts/${serverCart.id}/`).catch(() => null);
    if (reloaded) serverCart = reloaded;
  }

  async function hydrateFromServer() {
    if (!isAuthenticated) return;
    const cart = await ensureServerCart();
    if (!cart) return;

    if (!items.length && cart.items?.length) {
      items = serverItemsToLocal(cart.items);
      renderItems();
      return;
    }
    if (items.length) {
      // push local to server
      await syncItemsToServer();
    }
  }

  // Подтягиваем лимит, если его не хватает, и перерисовываем/синкаем при
  // изменениях. Важно для двух случаев: (1) корзина пришла с сервера, где
  // CartItem не содержит max_order_quantity; (2) гость заходит с корзиной,
  // которая лежала в localStorage ещё до внедрения лимитов.
  async function refreshLimits() {
    const changed = await enrichItemsWithLimits();
    if (changed) {
      renderItems();
      persistCart();
    }
  }

  // ---------- Order submission & payment ----------
  function showError(form, text) {
    form.querySelectorAll(".form-error").forEach((node) => node.remove());
    const p = document.createElement("p");
    p.className = "form-error full";
    p.textContent = text;
    form.append(p);
  }

  function extractErrorMessage(errData) {
    if (!errData) return "";
    // DRF: top-level .detail or non-field errors
    if (typeof errData === "string") return errData;
    if (errData.detail) return String(errData.detail);
    if (errData.message) return String(errData.message);
    if (Array.isArray(errData.non_field_errors) && errData.non_field_errors.length) {
      return errData.non_field_errors.join(" ");
    }
    // DRF field errors: {field: [msg1, msg2]} — prefer the most user-facing ones.
    const fieldOrder = ["email", "account_password", "phone", "full_name", "address", "city", "items", "pickup_point", "delivery_type", "payment_type"];
    for (const field of fieldOrder) {
      const val = errData[field];
      if (Array.isArray(val) && val.length) return val.join(" ");
      if (typeof val === "string" && val) return val;
    }
    // Fallback: first message we find.
    for (const key of Object.keys(errData)) {
      const val = errData[key];
      if (Array.isArray(val) && val.length && typeof val[0] === "string") return val[0];
      if (typeof val === "string") return val;
    }
    return "";
  }

  async function submitOrder(orderData) {
    try {
      return await apiJson("/api/orders/", { method: "POST", body: orderData });
    } catch (error) {
      const message = extractErrorMessage(error.data) || "Ошибка при создании заказа. Попробуйте ещё раз.";
      throw new Error(message);
    }
  }

  const overlay = document.getElementById("paymentOverlay");
  const stepProcessing = document.getElementById("paymentStepProcessing");
  const stepCard = document.getElementById("paymentStepCard");
  const stepSbp = document.getElementById("paymentStepSbp");
  const stepCash = document.getElementById("paymentStepCash");
  const stepSuccess = document.getElementById("paymentStepSuccess");
  const steps = [stepProcessing, stepCard, stepSbp, stepCash, stepSuccess];

  function hideAllSteps() {
    steps.forEach((s) => { if (s) s.hidden = true; });
  }

  function showModal(step) {
    hideAllSteps();
    step.hidden = false;
    overlay.hidden = false;
  }

  function closeModal() {
    overlay.hidden = true;
    hideAllSteps();
    resetSbpSessionUi();
  }

  document.getElementById("paymentClose")?.addEventListener("click", closeModal);
  overlay?.addEventListener("click", (event) => { if (event.target === overlay) closeModal(); });

  function clearSbpWatchers() {
    if (window._sbpTimerInterval) clearInterval(window._sbpTimerInterval);
    if (window._sbpPollInterval) clearInterval(window._sbpPollInterval);
    window._sbpTimerInterval = null;
    window._sbpPollInterval = null;
  }

  function resetSbpSessionUi() {
    clearSbpWatchers();
    pendingSbpToken = null;
    pendingSbpConfirmUrl = "";
    sbpFinalizing = false;

    const qrContainer = document.getElementById("paymentQr");
    const sbpLink = document.getElementById("paymentSbpLink");
    const sbpBtn = document.getElementById("sbpSimulateBtn");
    const timerEl = document.getElementById("sbpTimer");

    if (qrContainer) qrContainer.innerHTML = "";
    if (sbpLink) {
      sbpLink.hidden = true;
      sbpLink.removeAttribute("href");
    }
    if (sbpBtn) {
      sbpBtn.disabled = false;
      sbpBtn.textContent = "Подтвердить оплату";
    }
    if (timerEl) timerEl.textContent = "02:00";
  }

  function startSbpTimer(onExpire) {
    let seconds = 120;
    const timerEl = document.getElementById("sbpTimer");
    window._sbpTimerInterval = setInterval(() => {
      seconds--;
      const m = String(Math.floor(seconds / 60)).padStart(2, "0");
      const s = String(seconds % 60).padStart(2, "0");
      if (timerEl) timerEl.textContent = `${m}:${s}`;
      if (seconds <= 0) {
        clearSbpWatchers();
        onExpire();
      }
    }, 1000);
  }

  async function pollSbpStatus() {
    if (!pendingSbpToken || sbpFinalizing) return;
    try {
      const statusData = await apiJson(`/api/sbp-payments/${pendingSbpToken}/`);
      if (statusData.status === "paid") {
        sbpFinalizing = true;
        clearSbpWatchers();
        const sbpBtn = document.getElementById("sbpSimulateBtn");
        if (sbpBtn) {
          sbpBtn.disabled = true;
          sbpBtn.textContent = "Оплата получена";
        }
        processPayment(sbpBtn || document.getElementById("checkoutSubmit"), 600);
      }
    } catch (error) {
      if (error?.status === 404 || error?.data?.status === "expired") {
        closeModal();
        showError(checkoutForm, "Сессия СБП истекла. Создайте новый QR-код.");
      }
    }
  }

  async function startSbpSession(amount) {
    const qrContainer = document.getElementById("paymentQr");
    const sbpLink = document.getElementById("paymentSbpLink");
    const response = await apiJson("/api/sbp-payments/start/", {
      method: "POST",
      body: { amount },
    });

    pendingSbpToken = response.token;
    pendingSbpConfirmUrl = response.confirm_url;
    sbpFinalizing = false;

    if (qrContainer) {
      qrContainer.innerHTML = `<img src="${response.qr_image}" alt="QR-код для оплаты через СБП" loading="eager" decoding="async">`;
    }
    if (sbpLink) {
      sbpLink.hidden = false;
      sbpLink.href = pendingSbpConfirmUrl;
    }

    clearSbpWatchers();
    window._sbpPollInterval = setInterval(() => {
      pollSbpStatus();
    }, 2000);
  }

  // Format card number with spaces
  document.getElementById("cardNumber")?.addEventListener("input", (event) => {
    const v = event.target.value.replace(/\D/g, "").slice(0, 16);
    event.target.value = v.replace(/(.{4})/g, "$1 ").trim();
  });

  document.getElementById("cardExpiry")?.addEventListener("input", (event) => {
    let v = event.target.value.replace(/\D/g, "").slice(0, 4);
    if (v.length >= 3) v = v.slice(0, 2) + "/" + v.slice(2);
    event.target.value = v;
  });

  let pendingOrderPayload = null;

  async function finishOrder(orderResult) {
    const orderNumber = orderResult?.number || orderResult?.id || "";
    const accountCreated = Boolean(orderResult?.account_created);
    const customerEmail = pendingOrderPayload?.email || "";

    items = [];
    P.saveCartItems(items);
    renderItems();
    checkoutForm.reset();
    // Clear server cart — use post-order auth state (account_created) OR the
    // cached flag from page load. When create_account was used, the session
    // cookie now identifies the newly-registered user.
    const authedNow = isAuthenticated || accountCreated;
    if (authedNow && serverCart) {
      for (const row of serverCart.items || []) {
        await apiFetch(`/api/cart-items/${row.id}/`, { method: "DELETE" }).catch(() => {});
      }
      serverCart = { ...serverCart, items: [] };
    }

    const orderNumberEl = document.getElementById("paymentOrderNumber");
    if (orderNumberEl) orderNumberEl.textContent = `Заказ №${orderNumber}`;

    const accountBlock = document.getElementById("paymentAccountCreated");
    const accountEmail = document.getElementById("paymentAccountEmail");
    const doneLabel = document.getElementById("paymentDoneLabel");
    if (accountCreated) {
      if (accountBlock) accountBlock.hidden = false;
      if (accountEmail) accountEmail.textContent = customerEmail;
      if (doneLabel) doneLabel.textContent = "В личный кабинет";
      // Reflect new auth state in the DOM so any code that reads the body
      // attribute (and our header update below) behaves correctly.
      document.body.setAttribute("data-is-authenticated", "true");
      isAuthenticated = true;
      // Swap login chip → profile link without a full reload so the change is
      // visible the moment the user closes the modal.
      const loginChip = document.querySelector(".site-chip--auth");
      if (loginChip) loginChip.remove();
    } else {
      if (accountBlock) accountBlock.hidden = true;
      if (doneLabel) doneLabel.textContent = "Вернуться в каталог";
    }
    // Remember redirect target for the "Готово" button.
    pendingDoneRedirect = accountCreated ? "/profile/" : "/catalog/";

    showModal(stepSuccess);
  }

  async function processPayment(btn, delayMs) {
    btn.disabled = true;
    showModal(stepProcessing);
    await new Promise((resolve) => setTimeout(resolve, delayMs));
    try {
      const result = await submitOrder(pendingOrderPayload);
      await finishOrder(result);
    } catch (error) {
      closeModal();
      btn.disabled = false;
      showError(checkoutForm, error.message);
    }
  }

  document.getElementById("cardPayBtn")?.addEventListener("click", () => {
    const btn = document.getElementById("cardPayBtn");
    const num = document.getElementById("cardNumber").value.replace(/\s/g, "");
    const exp = document.getElementById("cardExpiry").value;
    const cvv = document.getElementById("cardCvv").value;
    if (num.length < 16 || exp.length < 4 || cvv.length < 3) {
      alert("Заполните все поля карты корректно");
      return;
    }
    processPayment(btn, 1800);
  });

  document.getElementById("sbpSimulateBtn")?.addEventListener("click", () => {
    const btn = document.getElementById("sbpSimulateBtn");
    sbpFinalizing = true;
    clearSbpWatchers();
    processPayment(btn, 1200);
  });

  document.getElementById("cashConfirmBtn")?.addEventListener("click", () => {
    const btn = document.getElementById("cashConfirmBtn");
    processPayment(btn, 1000);
  });

  document.getElementById("paymentDoneBtn")?.addEventListener("click", () => {
    closeModal();
    window.location.href = pendingDoneRedirect || "/catalog/";
  });

  checkoutForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    checkoutForm.querySelectorAll(".form-error").forEach((node) => node.remove());

    if (items.length === 0) {
      showError(checkoutForm, "Корзина пуста. Добавьте товары перед оформлением.");
      return;
    }

    if (!checkoutForm.checkValidity()) {
      showError(checkoutForm, "Пожалуйста, заполните обязательные поля корректно.");
      return;
    }

    const orderItems = items
      .filter((item) => /^\d+$/.test(String(item.id)))
      .map((item) => ({
        product: Number(item.id),
        quantity: item.qty,
        unit_price: item.price,
      }));

    if (orderItems.length === 0) {
      showError(checkoutForm, "Не удалось определить товары. Попробуйте добавить их заново.");
      return;
    }

    const paymentType = document.getElementById("paymentType")?.value;
    let deliveryPrice = getDeliveryPrice();
    if (appliedPromo?.free_shipping) deliveryPrice = 0;
    let total = totalAmount() + deliveryPrice;
    if (appliedPromo && !appliedPromo.free_shipping) total = Math.max(0, total - (appliedPromo.discount || 0));

    const createAccountCheckbox = document.getElementById("createAccount");
    const accountPasswordInput = document.getElementById("accountPassword");
    const wantAccount = Boolean(createAccountCheckbox?.checked);
    const accountPassword = accountPasswordInput?.value || "";

    if (wantAccount) {
      if (accountPassword.length < 8) {
        showError(checkoutForm, "Для создания аккаунта укажите пароль (минимум 8 символов).");
        accountPasswordInput?.focus();
        return;
      }
    }

    const deliveryType = selectedDeliveryType();
    const pickupPointId = pickupPointSelect?.value ? Number(pickupPointSelect.value) : null;

    if (deliveryType === "pickup" && !pickupPointId) {
      showError(checkoutForm, "Выберите пункт самовывоза из списка.");
      pickupPointSelect?.focus();
      return;
    }

    // Pickup orders use the selected point's address; courier orders use the form fields.
    let orderCity = document.getElementById("city")?.value || "";
    let orderAddress = document.getElementById("address")?.value || "";
    if (deliveryType === "pickup" && pickupPointId) {
      const point = pickupPoints.find((p) => p.id === pickupPointId);
      if (point) {
        orderCity = point.city || orderCity || "Курск";
        orderAddress = `${point.name}, ${point.address}`;
      }
    }

    pendingOrderPayload = {
      full_name: document.getElementById("fullName")?.value,
      phone: document.getElementById("phone")?.value,
      email: document.getElementById("email")?.value,
      city: orderCity,
      address: orderAddress,
      delivery_type: deliveryType,
      payment_type: paymentType,
      comment: deliveryType === "courier" ? (document.getElementById("comment")?.value || "") : "",
      items: orderItems,
      delivery_price: deliveryPrice,
      pickup_point: deliveryType === "pickup" ? pickupPointId : null,
      create_account: wantAccount,
      account_password: wantAccount ? accountPassword : "",
      promo_code_input: appliedPromo?.code || "",
    };

    const amountText = formatMoney(total);

    if (paymentType === "card") {
      document.getElementById("paymentCardAmount").textContent = amountText;
      document.getElementById("cardNumber").value = "";
      document.getElementById("cardExpiry").value = "";
      document.getElementById("cardCvv").value = "";
      showModal(stepCard);
    } else if (paymentType === "sbp") {
      document.getElementById("paymentSbpAmount").textContent = amountText;
      try {
        await startSbpSession(total);
        showModal(stepSbp);
        startSbpTimer(() => {
          closeModal();
          showError(checkoutForm, "Время ожидания оплаты истекло. Попробуйте ещё раз.");
        });
      } catch (error) {
        closeModal();
        showError(checkoutForm, "Не удалось создать QR-код для СБП. Попробуйте ещё раз.");
      }
    } else {
      document.getElementById("paymentCashAmount").textContent = amountText;
      showModal(stepCash);
    }
  });

  searchForm?.addEventListener("submit", (event) => {
    event.preventDefault();
    const query = searchForm.querySelector("input")?.value.trim();
    if (query) window.location.href = `/catalog/?q=${encodeURIComponent(query)}`;
  });

  // ---------- Init ----------
  (async () => {
    bindPhoneMask();
    await Promise.all([loadDeliveryTariffs(), loadPickupPoints()]);
    applyDeliveryTypeVisibility();
    renderItems();
    await hydrateFromServer();
    renderItems();
    await refreshLimits();
  })();
});
