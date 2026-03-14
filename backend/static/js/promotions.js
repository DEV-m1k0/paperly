document.addEventListener("DOMContentLoaded", () => {
  const productsGrid = document.getElementById("promotionsProducts");
  const cartCount = document.getElementById("cartCount");

  let count = Number(localStorage.getItem("paperly_cart_count") || 0);
  if (cartCount) cartCount.textContent = String(count);

  function escapeHtml(value) {
    return String(value || "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#39;");
  }

  function formatMoney(value) {
    const num = Number(value || 0);
    return `${num.toLocaleString("ru-RU")} ₽`;
  }

  function parseRows(payload) {
    return Array.isArray(payload) ? payload : payload?.results || [];
  }

  function mapTypeFromProduct(product) {
    const categorySlug = String(product.category_slugs?.[0] || "").toLowerCase();
    const title = String(product.title || "").toLowerCase();

    if (categorySlug.includes("notebook") || categorySlug.includes("tetrad") || title.includes("тетрад")) return "notebook";
    if (categorySlug.includes("diary") || categorySlug.includes("planner") || title.includes("ежедневник") || title.includes("планер")) return "diary";
    if (categorySlug.includes("paper") || title.includes("бумаг")) return "paper";
    if (categorySlug.includes("pen") || categorySlug.includes("writing") || title.includes("ручк") || title.includes("карандаш")) return "pen";
    if (categorySlug.includes("marker") || categorySlug.includes("art") || title.includes("маркер") || title.includes("текстовыдел")) return "marker";

    return "notebook";
  }

  function renderStars(rating) {
    const full = Math.round(Number(rating));
    return Array.from({ length: 5 }, (_, index) => `<i class="bi ${index < full ? "bi-star-fill" : "bi-star"}"></i>`).join("");
  }

  function getPrimaryImage(product) {
    return product.images?.[0]?.image_url || "https://images.unsplash.com/photo-1503676382389-4809596d5290?auto=format&fit=crop&w=900&q=80";
  }

  function getDiscountPercent(product) {
    const price = Number(product.price || 0);
    const oldPrice = Number(product.old_price || 0);
    if (oldPrice > price && oldPrice > 0) {
      return Math.round(((oldPrice - price) / oldPrice) * 100);
    }

    const promotionDiscount = Number(product.active_promotion_discount || 0);
    return promotionDiscount > 0 ? promotionDiscount : 0;
  }

  function buildCard(product, index) {
    const targetUrl = `/product/?id=${product.id}`;
    const firstImage = getPrimaryImage(product);
    const type = mapTypeFromProduct(product);
    const price = Number(product.price || 0);
    const oldPrice = product.old_price ? Number(product.old_price) : null;
    const hasDiscount = Number(oldPrice) > Number(price);
    const discountPercent = getDiscountPercent(product);
    const chipClass = discountPercent > 0 ? "chip chip--discount" : "chip";
    const chipText = discountPercent > 0 ? `-${discountPercent}%` : "Акция";
    const rating = (4.6 + ((product.id % 4) * 0.1)).toFixed(1);
    const stockText = Number(product.stock || 0) > 0 ? "Есть на складе" : "Под заказ";
    const oldPriceMarkup = hasDiscount ? `<span class="product__old">${formatMoney(oldPrice)}</span>` : "";
    const discountMarkup = discountPercent > 0 ? `<span class="discount-pill">-${discountPercent}%</span>` : "";

    return `
      <article class="product" data-type="${type}" data-brand="${product.brand_slug || ""}" data-stock="${Number(product.stock || 0) > 0 ? "in_stock" : "out_stock"}" data-flag-new="${product.is_new ? "true" : "false"}" data-flag-hit="${product.is_hit ? "true" : "false"}" data-flag-featured="${product.is_featured ? "true" : "false"}" data-flag-discount="${hasDiscount ? "true" : "false"}" data-format="${product.format || "other"}" data-sheets="${product.sheets_count || ""}" data-purpose="${product.purpose || "universal"}" data-price="${price}">
        <span class="${chipClass}">${chipText}</span>
        <button class="fav-btn" aria-label="Добавить в избранное"><i class="bi bi-heart"></i></button>
        <a class="product__image" href="${targetUrl}">
          <img src="${firstImage}" alt="${escapeHtml(product.title)}">
        </a>
        <div class="product__meta">
          <span class="rating-stars" aria-label="Рейтинг ${rating} из 5">${renderStars(rating)}</span>
          <span class="meta-score">${rating}</span>
          <span class="meta-stock">${stockText}</span>
        </div>
        <h3><a href="${targetUrl}">${escapeHtml(product.title)}</a></h3>
        <p>${escapeHtml(product.short_description || "Товар из каталога")}</p>
        <div class="product__bottom">
          <div class="price-stack${hasDiscount ? " has-discount" : ""}">
            <strong>${formatMoney(price)}</strong>
            ${oldPriceMarkup}
          </div>
          <button class="add" type="button"><i class="bi bi-bag-plus"></i><span>В корзину</span></button>
        </div>
      </article>
    `;
  }

  function bindActions() {
    productsGrid.querySelectorAll(".add").forEach((button) => {
      button.dataset.cartBound = "true";
      if (button.dataset.bound === "true") return;
      button.dataset.bound = "true";

      button.addEventListener("click", () => {
        if (typeof window.paperlyAddToCart === "function") {
          count = window.paperlyAddToCart(button);
        } else {
          count += 1;
        }
        if (cartCount) cartCount.textContent = String(count);
        localStorage.setItem("paperly_cart_count", String(count));

        const initialHtml = button.innerHTML;
        button.innerHTML = `<i class="bi bi-check2"></i><span>Добавлено</span>`;
        button.disabled = true;
        setTimeout(() => {
          button.innerHTML = initialHtml;
          button.disabled = false;
        }, 900);
      });
    });

    productsGrid.querySelectorAll(".fav-btn").forEach((button) => {
      if (button.dataset.bound === "true") return;
      button.dataset.bound = "true";

      button.addEventListener("click", () => {
        button.classList.toggle("is-active");
        const icon = button.querySelector("i");
        if (icon) {
          icon.classList.toggle("bi-heart");
          icon.classList.toggle("bi-heart-fill");
        }
      });
    });

    productsGrid.querySelectorAll(".product").forEach((card) => {
      if (card.dataset.navBound === "true") return;
      card.dataset.navBound = "true";

      card.addEventListener("click", (event) => {
        if (event.target.closest("a, button, input, select, textarea, label")) {
          return;
        }

        const link = card.querySelector("h3 a") || card.querySelector(".product__image");
        if (link?.href) {
          window.location.href = link.href;
        }
      });
    });
  }

  async function loadPromotions() {
    if (!productsGrid) return;

    productsGrid.innerHTML = `<p class="empty-state">Загрузка акционных товаров...</p>`;

    try {
      const response = await fetch("/api/products/?sale=true&ordering=-created_at");
      if (!response.ok) {
        productsGrid.innerHTML = `<p class="empty-state">Не удалось загрузить акционные товары.</p>`;
        return;
      }

      const rows = parseRows(await response.json())
        .filter((item) => item && item.id)
        .filter((item) => {
          const price = Number(item.price || 0);
          const oldPrice = Number(item.old_price || 0);
          const hasOldDiscount = oldPrice > price && oldPrice > 0;
          const promoDiscount = Number(item.active_promotion_discount || 0);
          return hasOldDiscount || promoDiscount > 0;
        });
      if (!rows.length) {
        productsGrid.innerHTML = `<p class="empty-state">Сейчас нет активных скидок и акций.</p>`;
        return;
      }

      productsGrid.innerHTML = rows.map((product, index) => buildCard(product, index)).join("");
      bindActions();
    } catch (error) {
      console.error("Promotions API error", error);
      productsGrid.innerHTML = `<p class="empty-state">Ошибка загрузки акций.</p>`;
    }
  }

  loadPromotions();
});



