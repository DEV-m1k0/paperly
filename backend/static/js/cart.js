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
  const deliveryTypeSelect = document.getElementById("deliveryType");
  const pickupPointSelect = document.getElementById("pickupPoint");

  // ---------- State ----------
  let items = P.readCartItems();
  let deliveryTariffs = [];
  let pickupPoints = [];
  let serverCart = null; // { id, items: [{id, product, quantity, price_snapshot}] }

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
    const delivery = getDeliveryPrice();
    const total = amount + delivery;

    summaryNode.innerHTML = `
      <div class="summary-row"><span>Товары (${totalQty()} шт)</span><strong>${formatMoney(amount)}</strong></div>
      <div class="summary-row"><span>Доставка</span><strong>${delivery ? formatMoney(delivery) : "0 ₽"}</strong></div>
      <div class="summary-row"><span>Итого</span><strong>${formatMoney(total)}</strong></div>
    `;
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
                <input type="number" min="1" value="${item.qty}" data-act="input" aria-label="Количество">
                <button data-act="plus" type="button" aria-label="Увеличить"><i class="bi bi-plus"></i></button>
              </div>
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
    items = items.map((item) => (item.id === id ? { ...item, qty: Math.max(1, nextQty) } : item));
    renderItems();
    persistCart();
  }

  function removeItem(id) {
    items = items.filter((item) => item.id !== id);
    renderItems();
    persistCart();
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
    renderSummary();
  });

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
      }));
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
    if (window._sbpTimerInterval) clearInterval(window._sbpTimerInterval);
  }

  document.getElementById("paymentClose")?.addEventListener("click", closeModal);
  overlay?.addEventListener("click", (event) => { if (event.target === overlay) closeModal(); });

  function generateQrSvg(text) {
    const size = 21;
    const cells = [];
    let hash = 0;
    for (let i = 0; i < text.length; i++) hash = ((hash << 5) - hash + text.charCodeAt(i)) | 0;
    const rng = () => { hash = (hash * 16807 + 0) % 2147483647; return hash / 2147483647; };
    for (let y = 0; y < size; y++) {
      for (let x = 0; x < size; x++) {
        const inFinder = (cx, cy) => x >= cx && x < cx + 7 && y >= cy && y < cy + 7;
        const isFinderBlack = (cx, cy) => {
          const rx = x - cx, ry = y - cy;
          if (rx === 0 || rx === 6 || ry === 0 || ry === 6) return true;
          if (rx >= 2 && rx <= 4 && ry >= 2 && ry <= 4) return true;
          return false;
        };
        let black = false;
        if (inFinder(0, 0)) black = isFinderBlack(0, 0);
        else if (inFinder(size - 7, 0)) black = isFinderBlack(size - 7, 0);
        else if (inFinder(0, size - 7)) black = isFinderBlack(0, size - 7);
        else black = rng() > 0.55;
        if (black) {
          const s = 160 / size;
          cells.push(`<rect x="${x * s}" y="${y * s}" width="${s}" height="${s}" rx="1" fill="#0e766e"/>`);
        }
      }
    }
    return `<svg viewBox="0 0 160 160" xmlns="http://www.w3.org/2000/svg">${cells.join("")}</svg>`;
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
        clearInterval(window._sbpTimerInterval);
        onExpire();
      }
    }, 1000);
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
    if (window._sbpTimerInterval) clearInterval(window._sbpTimerInterval);
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

  checkoutForm.addEventListener("submit", (event) => {
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
    const deliveryPrice = getDeliveryPrice();
    const total = totalAmount() + deliveryPrice;

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
      const qrContainer = document.getElementById("paymentQr");
      qrContainer.innerHTML = generateQrSvg(`sbp:paperly:${total}:${Date.now()}`);
      showModal(stepSbp);
      startSbpTimer(() => {
        closeModal();
        showError(checkoutForm, "Время ожидания оплаты истекло. Попробуйте ещё раз.");
      });
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
    await Promise.all([loadDeliveryTariffs(), loadPickupPoints()]);
    applyDeliveryTypeVisibility();
    renderItems();
    await hydrateFromServer();
    renderItems();
  })();
});
