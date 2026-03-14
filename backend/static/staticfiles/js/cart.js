document.addEventListener("DOMContentLoaded", () => {
  const cartCount = document.getElementById("cartCount");
  const searchForm = document.getElementById("searchForm");
  const cartItemsNode = document.getElementById("cartItems");
  const cartEmpty = document.getElementById("cartEmpty");
  const checkoutBlock = document.getElementById("checkoutBlock");
  const summaryNode = document.getElementById("summary");
  const checkoutForm = document.getElementById("checkoutForm");

  // ---------- Вспомогательные ----------
  function getCookie(name) {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop().split(";").shift();
    return "";
  }

  function formatMoney(value) {
    return `${value.toLocaleString("ru-RU")} ₽`;
  }

  // ---------- Работа с localStorage ----------
  let items = JSON.parse(localStorage.getItem("paperly_cart_items") || "[]");

  function saveItems() {
    localStorage.setItem("paperly_cart_items", JSON.stringify(items));
  }

  function totalQty() {
    return items.reduce((sum, item) => sum + item.qty, 0);
  }

  function totalAmount() {
    return items.reduce((sum, item) => sum + item.price * item.qty, 0);
  }

  function updateCounter() {
    const qty = totalQty();
    cartCount.textContent = String(qty);
    localStorage.setItem("paperly_cart_count", String(qty));
  }

  function renderSummary() {
    const amount = totalAmount();
    const delivery = items.length ? 350 : 0; // пример тарифа
    const final = amount + delivery;

    summaryNode.innerHTML = `
      <div class="summary-row"><span>Товары (${totalQty()} шт)</span><strong>${formatMoney(amount)}</strong></div>
      <div class="summary-row"><span>Доставка</span><strong>${delivery ? formatMoney(delivery) : "0 ₽"}</strong></div>
      <div class="summary-row"><span>Итого</span><strong>${formatMoney(final)}</strong></div>
    `;
  }

  function renderItems() {
    if (items.length === 0) {
      cartItemsNode.innerHTML = "";
      cartEmpty.hidden = false;
      checkoutBlock.hidden = true;
      updateCounter();
      renderSummary();
      return;
    }

    cartEmpty.hidden = true;
    checkoutBlock.hidden = false;

    cartItemsNode.innerHTML = items
      .map((item) => {
        return `
          <article class="item" data-id="${item.id}">
            <img class="item-img" src="${item.img}" alt="${item.title}">
            <div>
              <h3><a href="/product/?id=${item.id}">${item.title}</a></h3>
              <p>${item.desc || ""}</p>
            </div>
            <div class="item-right">
              <strong class="price">${formatMoney(item.price * item.qty)}</strong>
              <div class="qty">
                <button data-act="minus">-</button>
                <input type="number" min="1" value="${item.qty}" data-act="input">
                <button data-act="plus">+</button>
              </div>
              <button class="item-remove" data-act="remove">Удалить</button>
            </div>
          </article>
        `;
      })
      .join("");

    updateCounter();
    renderSummary();
  }

  function changeQty(id, nextQty) {
    items = items.map((item) => {
      if (item.id !== id) return item;
      return { ...item, qty: Math.max(1, nextQty) };
    });
    saveItems();
    renderItems();
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
    if (act === "remove") {
      items = items.filter((x) => x.id !== id);
      saveItems();
      renderItems();
    }
  });

  cartItemsNode.addEventListener("change", (event) => {
    const input = event.target.closest("input[data-act='input']");
    if (!input) return;
    const itemNode = input.closest(".item");
    const id = itemNode?.dataset.id;
    const next = Number(input.value || 1);
    changeQty(id, next);
  });

  // ---------- Оформление заказа (отправка на сервер) ----------
  function showError(form, text) {
    form.querySelectorAll(".form-error").forEach((node) => node.remove());
    const p = document.createElement("p");
    p.className = "form-error full";
    p.textContent = text;
    form.append(p);
  }

  async function submitOrder(orderData) {
    const csrfToken = getCookie("csrftoken");
    const response = await fetch("/api/orders/", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": csrfToken,
      },
      body: JSON.stringify(orderData),
      credentials: "same-origin",
    });
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.message || "Ошибка при создании заказа");
    }
    return await response.json();
  }

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

    // Собираем данные для заказа
    const formData = new FormData(checkoutForm);
    const orderItems = items.map(item => ({
      product: item.id,
      quantity: item.qty,
      unit_price: item.price,          // внимание: поле называется unit_price
      // Можно не отправлять title_snapshot/sku_snapshot, если бэкенд заполняет их автоматически
    }));

    const orderPayload = {
      full_name: document.getElementById("fullName")?.value,
      phone: document.getElementById("phone")?.value,
      email: document.getElementById("email")?.value,
      city: document.getElementById("city")?.value,
      address: document.getElementById("address")?.value,
      delivery_type: document.getElementById("deliveryType")?.value,
      payment_type: document.getElementById("paymentType")?.value,
      comment: document.getElementById("comment")?.value,
      items: orderItems,
      subtotal: totalAmount(),
      delivery_price: 350,
      total: totalAmount() + 350,
    };

    const button = checkoutForm.querySelector("button[type='submit']");
    const initialText = button.textContent;
    button.textContent = "Оформляем...";
    button.disabled = true;

    try {
      const result = await submitOrder(orderPayload);
      // Очищаем корзину
      items = [];
      saveItems();
      renderItems();
      alert(`Заказ №${result.number || result.id} успешно оформлен!`);
      checkoutForm.reset();
    } catch (error) {
      showError(checkoutForm, error.message);
    } finally {
      button.textContent = initialText;
      button.disabled = false;
    }
  });

  searchForm?.addEventListener("submit", (event) => {
    event.preventDefault();
    const query = searchForm.querySelector("input")?.value.trim();
    if (query) {
      window.location.href = `/catalog/?q=${encodeURIComponent(query)}`;
    }
  });

  // Старт
  renderItems();
});