document.addEventListener("DOMContentLoaded", () => {
  const P = window.paperly;
  const { escapeHtml, formatOrderStatus, apiJson, unwrapList } = P;

  const ordersList = document.getElementById("ordersList");
  const ordersEmpty = document.getElementById("ordersEmpty");
  const ordersFilterEmpty = document.getElementById("ordersFilterEmpty");
  const ordersStats = document.getElementById("ordersStats");
  const ordersFilters = document.getElementById("ordersFilters");
  const ordersFilterReset = document.getElementById("ordersFilterReset");
  const statTotal = document.getElementById("ordersStatTotal");
  const statDone = document.getElementById("ordersStatDone");
  const statSum = document.getElementById("ordersStatSum");

  P.renderCartCount();
  const formatMoney = (v) => v == null ? "—" : P.formatMoney(v);

  const STATUS_ICON = {
    new: "bi-hourglass-split",
    confirmed: "bi-check-circle",
    paid: "bi-cash-coin",
    shipped: "bi-truck",
    done: "bi-patch-check-fill",
    canceled: "bi-x-circle",
  };

  const ACTIVE_STATUSES = new Set(["new", "confirmed", "paid", "shipped"]);

  let allOrders = [];
  let currentFilter = "all";

  function formatDate(dateString) {
    if (!dateString) return "";
    const d = new Date(dateString);
    return d.toLocaleDateString("ru-RU", { day: "numeric", month: "long", year: "numeric" });
  }

  function formatDateShort(dateString) {
    if (!dateString) return "";
    const d = new Date(dateString);
    return d.toLocaleDateString("ru-RU", { day: "numeric", month: "short", year: "numeric" });
  }

  function formatNoun(n, one, few, many) {
    const mod10 = n % 10;
    const mod100 = n % 100;
    if (mod100 < 10 || mod100 >= 20) {
      if (mod10 === 1) return `${n} ${one}`;
      if (mod10 >= 2 && mod10 <= 4) return `${n} ${few}`;
    }
    return `${n} ${many}`;
  }

  function filterOrders(filter) {
    if (filter === "active") return allOrders.filter((o) => ACTIVE_STATUSES.has(o.status));
    if (filter === "done") return allOrders.filter((o) => o.status === "done");
    if (filter === "canceled") return allOrders.filter((o) => o.status === "canceled");
    return allOrders;
  }

  function renderOrder(order) {
    const items = order.items || [];
    const itemsCount = items.reduce((sum, item) => sum + (Number(item.quantity) || 0), 0);
    const icon = STATUS_ICON[order.status] || "bi-box";
    const isDelivery = order.delivery_type === "courier";
    const deliveryLabel = isDelivery ? "Курьер" : "Самовывоз";
    const paymentLabels = {
      card: "Карта онлайн",
      sbp: "СБП",
      cash: "При получении",
      invoice: "По счёту",
    };
    const paymentLabel = paymentLabels[order.payment_type] || order.payment_type || "—";

    const itemsHtml = items.length
      ? items.map((item) => {
          const title = escapeHtml(item.title_snapshot || "Товар");
          const quantity = Number(item.quantity) || 0;
          const price = Number(item.unit_price) || 0;
          const sum = price * quantity;
          const productId = item.product;
          const linkOpen = productId ? `<a href="/product/?id=${productId}">` : "<span>";
          const linkClose = productId ? "</a>" : "</span>";
          return `
            <li class="order-item">
              <div class="order-item__main">
                <span class="order-item__qty">×${quantity}</span>
                <span class="order-item__title">${linkOpen}${title}${linkClose}</span>
              </div>
              <span class="order-item__price">${formatMoney(price)} <small>за шт.</small></span>
              <strong class="order-item__sum">${formatMoney(sum)}</strong>
            </li>
          `;
        }).join("")
      : `<li class="order-item order-item--empty">Нет информации о товарах</li>`;

    const address = [order.city, order.address].filter(Boolean).join(", ");

    return `
      <article class="order-card" data-status="${order.status}">
        <header class="order-card__head">
          <div class="order-card__id">
            <div class="order-card__icon order-card__icon--${order.status}">
              <i class="bi ${icon}" aria-hidden="true"></i>
            </div>
            <div>
              <p class="order-card__number">Заказ №${escapeHtml(String(order.number || order.id))}</p>
              <p class="order-card__meta">
                <span>${formatDateShort(order.created_at)}</span>
                ${itemsCount ? `<span aria-hidden="true">·</span><span>${formatNoun(itemsCount, "товар", "товара", "товаров")}</span>` : ""}
              </p>
            </div>
          </div>
          <div class="order-card__status-wrap">
            <span class="order-status status-${order.status}">${escapeHtml(formatOrderStatus(order.status))}</span>
            <strong class="order-card__total">${formatMoney(order.total)}</strong>
          </div>
        </header>

        <details class="order-card__details">
          <summary class="order-card__toggle">
            <span class="order-card__toggle-show">Показать состав заказа</span>
            <span class="order-card__toggle-hide">Свернуть</span>
            <i class="bi bi-chevron-down" aria-hidden="true"></i>
          </summary>

          <div class="order-card__body">
            <ul class="order-items">${itemsHtml}</ul>

            <div class="order-info">
              <div class="order-info__block">
                <span class="order-info__label"><i class="bi bi-geo-alt" aria-hidden="true"></i> Доставка</span>
                <strong>${escapeHtml(deliveryLabel)}</strong>
                ${address ? `<small>${escapeHtml(address)}</small>` : ""}
              </div>
              <div class="order-info__block">
                <span class="order-info__label"><i class="bi bi-credit-card" aria-hidden="true"></i> Оплата</span>
                <strong>${escapeHtml(paymentLabel)}</strong>
              </div>
            </div>

            <div class="order-summary">
              <div class="order-summary__row"><span>Сумма товаров</span><span>${formatMoney(order.subtotal)}</span></div>
              <div class="order-summary__row"><span>Доставка</span><span>${formatMoney(order.delivery_price)}</span></div>
              ${order.discount_amount && Number(order.discount_amount) > 0 ? `<div class="order-summary__row"><span>Скидка</span><span>−${formatMoney(order.discount_amount)}</span></div>` : ""}
              <div class="order-summary__row order-summary__row--total"><span>Итого</span><span>${formatMoney(order.total)}</span></div>
            </div>
          </div>
        </details>
      </article>
    `;
  }

  function renderOrders(filter = currentFilter) {
    const filtered = filterOrders(filter);
    if (!filtered.length) {
      ordersList.innerHTML = "";
      ordersList.hidden = true;
      if (filter === "all") {
        ordersEmpty.hidden = false;
        ordersFilterEmpty.hidden = true;
      } else {
        ordersEmpty.hidden = true;
        ordersFilterEmpty.hidden = false;
      }
      return;
    }
    ordersEmpty.hidden = true;
    ordersFilterEmpty.hidden = true;
    ordersList.hidden = false;
    ordersList.innerHTML = filtered.map(renderOrder).join("");
  }

  function updateStats() {
    const total = allOrders.length;
    const done = allOrders.filter((o) => o.status === "done");
    const sum = done.reduce((s, o) => s + (Number(o.total) || 0), 0);

    if (!total) {
      ordersStats.hidden = true;
      ordersFilters.hidden = true;
      return;
    }
    ordersStats.hidden = false;
    ordersFilters.hidden = false;
    if (statTotal) statTotal.textContent = String(total);
    if (statDone) statDone.textContent = String(done.length);
    if (statSum) statSum.textContent = formatMoney(sum);

    const counts = {
      all: total,
      active: allOrders.filter((o) => ACTIVE_STATUSES.has(o.status)).length,
      done: done.length,
      canceled: allOrders.filter((o) => o.status === "canceled").length,
    };
    document.querySelectorAll(".orders-filter__count").forEach((el) => {
      const key = el.dataset.countFor;
      el.textContent = String(counts[key] ?? 0);
    });
  }

  function setFilter(filter) {
    currentFilter = filter;
    document.querySelectorAll(".orders-filter").forEach((btn) => {
      btn.classList.toggle("is-active", btn.dataset.filter === filter);
    });
    renderOrders(filter);
  }

  ordersFilters?.addEventListener("click", (event) => {
    const btn = event.target.closest(".orders-filter");
    if (!btn) return;
    setFilter(btn.dataset.filter);
  });

  ordersFilterReset?.addEventListener("click", () => setFilter("all"));

  async function loadOrders() {
    try {
      const payload = await apiJson("/api/orders/").catch((err) => {
        if (err.status === 401 || err.status === 403) {
          return { notAuthorized: true };
        }
        throw err;
      });
      if (payload?.notAuthorized) {
        ordersList.hidden = true;
        ordersList.innerHTML = "";
        return;
      }
      allOrders = unwrapList(payload);
      ordersList.innerHTML = "";
      updateStats();
      renderOrders();
    } catch (error) {
      console.error("Orders load error", error);
      ordersList.hidden = true;
      ordersList.innerHTML = "";
      ordersEmpty.hidden = false;
    }
  }

  loadOrders();
});
