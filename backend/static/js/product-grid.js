// Shared product grid rendering. Used by home, bestsellers, new-arrivals, promotions.
(function () {
  "use strict";
  const P = window.paperly;

  // Локальный SVG-плейсхолдер (брендовый, tiny, работает оффлайн).
  // Используется если у товара вдруг нет ни одной картинки —
  // нормально у засеянных товаров картинка всегда есть (seed_demo_data
  // либо берёт файл из media/, либо генерит Pillow'ом плейсхолдер).
  const FALLBACK_IMAGE = "/static/img/placeholder-product.svg";

  function primaryImage(product) {
    return product.images?.[0]?.image_url || FALLBACK_IMAGE;
  }

  function discountPercent(product) {
    const price = Number(product.price || 0);
    const oldPrice = Number(product.old_price || 0);
    if (oldPrice > price && oldPrice > 0) {
      return Math.round(((oldPrice - price) / oldPrice) * 100);
    }
    const promoDiscount = Number(product.active_promotion_discount || 0);
    return promoDiscount > 0 ? promoDiscount : 0;
  }

  function typeFromProduct(product) {
    const slug = String(product.category_slugs?.[0] || "").toLowerCase();
    const title = String(product.title || "").toLowerCase();
    if (slug.includes("notebook") || slug.includes("tetrad") || title.includes("тетрад")) return "notebook";
    if (slug.includes("diary") || slug.includes("planner") || title.includes("ежедневник") || title.includes("планер")) return "diary";
    if (slug.includes("paper") || title.includes("бумаг")) return "paper";
    if (slug.includes("pen") || slug.includes("writing") || title.includes("ручк") || title.includes("карандаш")) return "pen";
    if (slug.includes("marker") || slug.includes("art") || title.includes("маркер") || title.includes("текстовыдел")) return "marker";
    return "notebook";
  }

  function chipFor(mode, percent) {
    if (percent > 0) return { text: `-${percent}%`, className: "chip chip--discount" };
    if (mode === "promo") return { text: "Акция", className: "chip" };
    if (mode === "new") return { text: "Новинка", className: "chip" };
    if (mode === "hit") return { text: "Хит", className: "chip" };
    return { text: "В наличии", className: "chip" };
  }

  function buildProductCard(product, { mode = "hit", moneySuffix = "₽" } = {}) {
    const targetUrl = `/product/?id=${product.id}`;
    const image = primaryImage(product);
    const type = typeFromProduct(product);
    const price = Number(product.price || 0);
    const oldPrice = product.old_price ? Number(product.old_price) : null;
    const hasDiscount = Number(oldPrice) > Number(price);
    const percent = discountPercent(product);
    const chip = chipFor(mode, percent);
    const rating = (4.6 + ((product.id % 4) * 0.1)).toFixed(1);
    const stockText = Number(product.stock || 0) > 0 ? "Есть на складе" : "Под заказ";
    const oldPriceMarkup = hasDiscount ? `<span class="product__old">${P.formatMoney(oldPrice, moneySuffix)}</span>` : "";
    const title = P.escapeHtml(product.title);
    const desc = P.escapeHtml(product.short_description || "Товар из каталога");

    return `
      <article class="product"
        data-product-id="${product.id}"
        data-product-title="${title}"
        data-product-price="${price}"
        data-product-img="${image}"
        data-product-desc="${desc}"
        data-type="${type}"
        data-brand="${product.brand_slug || ""}"
        data-stock="${Number(product.stock || 0) > 0 ? "in_stock" : "out_stock"}"
        data-flag-new="${product.is_new ? "true" : "false"}"
        data-flag-hit="${product.is_hit ? "true" : "false"}"
        data-flag-featured="${product.is_featured ? "true" : "false"}"
        data-flag-discount="${hasDiscount ? "true" : "false"}"
        data-format="${product.format || "other"}"
        data-sheets="${product.sheets_count || ""}"
        data-purpose="${product.purpose || "universal"}"
        data-price="${price}">
        <span class="${chip.className}">${chip.text}</span>
        <button class="fav-btn" aria-label="Добавить в избранное" type="button"><i class="bi bi-heart"></i></button>
        <a class="product__image" href="${targetUrl}">
          <img src="${image}" alt="${title}">
        </a>
        <div class="product__meta">
          <span class="rating-stars" aria-label="Рейтинг ${rating} из 5">${P.renderStars(rating)}</span>
          <span class="meta-score">${rating}</span>
          <span class="meta-stock">${stockText}</span>
        </div>
        <h3><a href="${targetUrl}">${title}</a></h3>
        <p>${desc}</p>
        <div class="product__bottom">
          <div class="price-stack${hasDiscount ? " has-discount" : ""}">
            <strong>${P.formatMoney(price, moneySuffix)}</strong>
            ${oldPriceMarkup}
          </div>
          <button class="add" type="button"><i class="bi bi-bag-plus"></i><span>В корзину</span></button>
        </div>
      </article>
    `;
  }

  async function toggleFavoriteForCard(card, button) {
    const productId = card.dataset.productId
      || (card.querySelector("h3 a")?.href
        ? new URL(card.querySelector("h3 a").href, location.origin).searchParams.get("id")
        : null);
    if (!productId) return;

    const wantActive = !button.classList.contains("is-active");
    button.classList.toggle("is-active", wantActive);
    const icon = button.querySelector("i");
    if (icon) {
      icon.classList.toggle("bi-heart", !wantActive);
      icon.classList.toggle("bi-heart-fill", wantActive);
    }

    // Guest: хранить избранное в localStorage, без обращения к API
    if (!P.isAuthenticated()) {
      if (wantActive) P.addLocalFavorite(productId);
      else P.removeLocalFavorite(productId);
      P.updateFavoritesCount();
      return;
    }

    try {
      if (wantActive) {
        const data = await P.apiJson("/api/favorites/", {
          method: "POST",
          body: { product: productId },
        });
        if (data?.id) button.dataset.favId = data.id;
      } else {
        let favId = button.dataset.favId;
        if (!favId) {
          const favs = await P.fetchFavorites();
          favId = favs.find((f) => String(f.product) === String(productId))?.id;
        }
        if (favId) {
          await P.apiFetch(`/api/favorites/${favId}/`, { method: "DELETE" });
          delete button.dataset.favId;
        }
      }
    } catch (error) {
      if (error?.status === 401 || error?.status === 403) {
        // Был авторизован, но сессия истекла — откат UI
        button.classList.toggle("is-active", !wantActive);
        if (icon) {
          icon.classList.toggle("bi-heart", wantActive);
          icon.classList.toggle("bi-heart-fill", !wantActive);
        }
      } else {
        console.error("Favorite toggle error", error);
      }
    }
    P.updateFavoritesCount();
  }

  function bindProductGridActions(container) {
    if (!container) return;
    container.querySelectorAll(".add").forEach((button) => {
      button.dataset.cartBound = "true";
      if (button.dataset.bound === "true") return;
      button.dataset.bound = "true";

      button.addEventListener("click", (event) => {
        // Stop the click from bubbling to the card's navigation handler —
        // otherwise a click on "В корзину" also opens the product page.
        event.preventDefault();
        event.stopPropagation();
        if (typeof window.paperlyAddToCart === "function") {
          window.paperlyAddToCart(button);
        }
        const initialHtml = button.innerHTML;
        button.innerHTML = `<i class="bi bi-check2"></i><span>Добавлено</span>`;
        button.disabled = true;
        setTimeout(() => {
          button.innerHTML = initialHtml;
          button.disabled = false;
        }, 900);
      });
    });

    container.querySelectorAll(".fav-btn").forEach((button) => {
      if (button.dataset.bound === "true") return;
      button.dataset.bound = "true";

      button.addEventListener("click", (event) => {
        event.preventDefault();
        event.stopPropagation();
        const card = button.closest(".product");
        if (card) toggleFavoriteForCard(card, button);
      });
    });

    container.querySelectorAll(".product").forEach((card) => {
      if (card.dataset.navBound === "true") return;
      card.dataset.navBound = "true";

      card.addEventListener("click", (event) => {
        if (event.target.closest("a, button, input, select, textarea, label")) return;
        const link = card.querySelector("h3 a") || card.querySelector(".product__image");
        if (link?.href) window.location.href = link.href;
      });
    });
  }

  async function syncFavoritesOnCards(container) {
    if (!container) return;
    const buttons = container.querySelectorAll(".fav-btn");
    if (!buttons.length) return;

    let byProduct;
    if (P.isAuthenticated()) {
      const favs = await P.fetchFavorites();
      byProduct = new Map(favs.map((f) => [String(f.product), f]));
    } else {
      const localIds = P.readLocalFavorites();
      byProduct = new Map(localIds.map((id) => [String(id), { id: null }]));
    }

    buttons.forEach((btn) => {
      const card = btn.closest(".product");
      if (!card) return;
      const productId = card.dataset.productId;
      const fav = byProduct.get(String(productId));
      const icon = btn.querySelector("i");
      if (fav) {
        btn.classList.add("is-active");
        if (fav.id) btn.dataset.favId = fav.id;
        icon?.classList.remove("bi-heart");
        icon?.classList.add("bi-heart-fill");
      } else {
        btn.classList.remove("is-active");
        delete btn.dataset.favId;
        icon?.classList.remove("bi-heart-fill");
        icon?.classList.add("bi-heart");
      }
    });
  }

  async function renderProductGrid({
    container,
    endpoint,
    fallbackEndpoint,
    mode = "hit",
    limit = null,
    emptyText = "Нет товаров",
    loadingText = "Загрузка товаров...",
    errorText = "Ошибка загрузки товаров.",
    filter = null,
    moneySuffix = "₽",
  }) {
    if (!container) return [];
    container.innerHTML = `<p class="empty-state">${loadingText}</p>`;

    async function fetchRows(url) {
      const payload = await P.apiJson(url).catch(() => null);
      if (!payload) return [];
      return P.unwrapList(payload).filter((item) => item && item.id);
    }

    try {
      let rows = await fetchRows(endpoint);
      if (filter) rows = rows.filter(filter);
      if (typeof limit === "number") rows = rows.slice(0, limit);

      if (!rows.length && fallbackEndpoint) {
        rows = await fetchRows(fallbackEndpoint);
        if (filter) rows = rows.filter(filter);
        if (typeof limit === "number") rows = rows.slice(0, limit);
      }

      if (!rows.length) {
        container.innerHTML = `<p class="empty-state">${emptyText}</p>`;
        return [];
      }

      container.innerHTML = rows.map((product) => buildProductCard(product, { mode, moneySuffix })).join("");
      bindProductGridActions(container);
      syncFavoritesOnCards(container);
      return rows;
    } catch (error) {
      console.error("Product grid error", error);
      container.innerHTML = `<p class="empty-state">${errorText}</p>`;
      return [];
    }
  }

  window.paperly = Object.assign(window.paperly || {}, {
    buildProductCard,
    bindProductGridActions,
    syncFavoritesOnCards,
    renderProductGrid,
  });
})();
