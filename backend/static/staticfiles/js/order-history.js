document.addEventListener("DOMContentLoaded", () => {
  const cartCount = document.getElementById("cartCount");
  const searchForm = document.getElementById("searchForm");
  const ordersList = document.getElementById("ordersList");

  function updateCartCount() {
    const items = JSON.parse(localStorage.getItem("paperly_cart_items") || "[]");
    const count = items.reduce((sum, item) => sum + item.qty, 0);
    localStorage.setItem("paperly_cart_count", String(count));
    if (cartCount) cartCount.textContent = String(count);
  }

  function formatMoney(value) {
    if (value === undefined || value === null) return "—";
    return `${Number(value).toLocaleString("ru-RU")} ₽`;
  }

  function formatDate(dateString) {
    if (!dateString) return "";
    const d = new Date(dateString);
    return d.toLocaleDateString("ru-RU", { day: "numeric", month: "long", year: "numeric" });
  }

  function escapeHtml(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#39;");
  }

  function getStatusText(status) {
    const map = {
      new: "Новый",
      confirmed: "Подтверждён",
      paid: "Оплачен",
      shipped: "Отгружен",
      done: "Завершён",
      canceled: "Отменён",
    };
    return map[status] || status;
  }

  async function loadOrders() {
    try {
      const response = await fetch("/api/orders/", { credentials: "same-origin" });
      if (!response.ok) {
        if (response.status === 401) {
          ordersList.innerHTML = "";
          ordersList.hidden = true;
          return;
        }
        ordersList.innerHTML = "";
        return;
      }
      const payload = await response.json();
      console.log("Orders payload:", payload); // для отладки
      const orders = Array.isArray(payload) ? payload : payload.results || [];
      if (!orders.length) {
        ordersList.innerHTML = "";
        ordersList.hidden = true;
        return;
      }

      ordersList.hidden = false;

      ordersList.innerHTML = orders.map(order => {
        const items = order.items || [];
        const itemsCount = items.reduce((sum, item) => sum + (Number(item.quantity) || 0), 0);
        const itemsHtml = items.length ? items.map(item => {
          // защита от undefined
          const title = escapeHtml(item.title_snapshot || "Товар");
          const quantity = Number(item.quantity) || 0;
          const price = Number(item.unit_price) || 0;
          const sum = price * quantity;
          return `
            <div class="order-item">
              <div class="order-item-main">
                <span class="order-item-title">${title}</span>
                <span class="order-item-meta">x${quantity}</span>
              </div>
              <div class="order-item-sum">${formatMoney(sum)}</div>
            </div>
          `;
        }).join("") : '<div class="order-item order-item--empty">Нет информации о товарах</div>';

        return `
          <article class="order-card">
            <div class="order-head">
              <div>
                <p class="order-number">Заказ №${order.number || order.id}</p>
                <p class="order-meta">от ${formatDate(order.created_at)}${itemsCount ? ` • ${itemsCount} шт.` : ""}</p>
              </div>
              <div class="order-total">
                <span class="order-status status-${order.status}">${getStatusText(order.status)}</span>
                <strong>${formatMoney(order.total)}</strong>
              </div>
            </div>
            <div class="order-body">
              <div class="order-items">
                ${itemsHtml}
              </div>
              <div class="order-summary">
                <div class="order-summary-row"><span>Сумма</span><span>${formatMoney(order.subtotal)}</span></div>
                <div class="order-summary-row"><span>Доставка</span><span>${formatMoney(order.delivery_price)}</span></div>
                <div class="order-summary-row order-summary-total"><span>Итого</span><span>${formatMoney(order.total)}</span></div>
              </div>
            </div>
          </article>
        `;
      }).join("");
    } catch (error) {
      console.error("Error loading orders:", error);
    }
  }

  function addToCartFromOrderItem(item) {
    let items = JSON.parse(localStorage.getItem("paperly_cart_items") || "[]");
    // item.product может быть id, но в order-history мы не храним product id, если не передали.
    // Можно использовать item.product если он есть, иначе генерировать временный id.
    const productId = item.product ? item.product.toString() : `temp-${Date.now()}-${Math.random()}`;
    const existing = items.find(i => i.id === productId);
    if (existing) {
      existing.qty += (item.quantity || 1);
    } else {
      items.push({
        id: productId,
        title: item.title_snapshot || "Товар",
        price: item.unit_price || 0,
        img: "", // из истории картинок нет
        desc: "",
        qty: item.quantity || 1
      });
    }
    localStorage.setItem("paperly_cart_items", JSON.stringify(items));
  }

  searchForm?.addEventListener("submit", (event) => {
    event.preventDefault();
    const query = searchForm.querySelector("input")?.value.trim();
    if (query) {
      window.location.href = `/catalog/?q=${encodeURIComponent(query)}`;
    }
  });

  updateCartCount();
  loadOrders();
});
