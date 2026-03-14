document.addEventListener("DOMContentLoaded", () => {
  const cartCount = document.getElementById("cartCount");
  const searchForm = document.getElementById("searchForm");
  const favGrid = document.getElementById("favGrid");
  const emptyState = document.getElementById("emptyState");

  // ---------- Вспомогательные ----------
  function getCookie(name) {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop().split(";").shift();
    return "";
  }

  function escapeHtml(value) {
    return String(value)
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#39;");
  }

  function renderStars(rating) {
    const full = Math.round(Number(rating));
    return Array.from({ length: 5 }, (_, index) => {
      return `<i class="bi ${index < full ? "bi-star-fill" : "bi-star"}"></i>`;
    }).join("");
  }

  function formatPurpose(value) {
    const map = {
      school: "Школа",
      office: "Офис",
      creative: "Творчество",
      universal: "Универсально",
    };
    return map[value] || value || "—";
  }

  // ---------- Корзина (localStorage) ----------
  function updateCartCount() {
    const items = JSON.parse(localStorage.getItem("paperly_cart_items") || "[]");
    const count = items.reduce((sum, item) => sum + item.qty, 0);
    localStorage.setItem("paperly_cart_count", String(count));
    cartCount.textContent = String(count);
    return count;
  }

  function addToCart(product) {
    let items = JSON.parse(localStorage.getItem("paperly_cart_items") || "[]");
    const existing = items.find(item => item.id === product.id);
    if (existing) {
      existing.qty += 1;
    } else {
      items.push({
        id: product.id,
        title: product.title,
        price: product.price,
        img: product.img,
        desc: product.desc,
        qty: 1
      });
    }
    localStorage.setItem("paperly_cart_items", JSON.stringify(items));
    updateCartCount();
  }

  // ---------- Отображение избранного ----------
  function updateEmptyState() {
    const cards = favGrid.querySelectorAll(".product");
    const isEmpty = cards.length === 0;
    emptyState.hidden = !isEmpty;
    favGrid.hidden = isEmpty;
  }

  function renderFavorites(rows) {
    favGrid.innerHTML = rows
      .map((item) => {
        const image = item.product_image || "https://images.unsplash.com/photo-1531346878377-a5be20888e57?auto=format&fit=crop&w=900&q=80";
        const title = escapeHtml(item.product_title || "Товар");
        const desc = escapeHtml(item.product_short_description || "");
        const price = Number(item.product_price || 0);
        const oldPrice = item.product_old_price ? Number(item.product_old_price) : null;
        const targetUrl = `/product/?id=${item.product}`;
        const hasDiscount = Number(oldPrice) > Number(price);
        const discountPercent = hasDiscount ? Math.round(((oldPrice - price) / oldPrice) * 100) : 0;
        const chipText = hasDiscount
          ? `-${discountPercent}%`
          : item.product_is_hit
            ? "Хит"
            : item.product_is_new
              ? "Новинка"
              : "В наличии";
        const chipClass = hasDiscount ? "chip chip--discount" : "chip";
        const reviewsCount = Number(item.product_reviews_count || 0);
        const avgRating = Number(item.product_avg_rating || 0);
        const ratingDisplay = reviewsCount ? avgRating.toFixed(1) : "—";
        const stockText = Number(item.product_stock || 0) > 0 ? "Есть на складе" : "Под заказ";

        const brandName = escapeHtml(item.product_brand_name || "");
        const formatLabel = escapeHtml(item.product_format || "");
        const sheets = item.product_sheets_count ? `${item.product_sheets_count} л.` : "";
        const purpose = escapeHtml(formatPurpose(item.product_purpose));
        const details = [
          brandName ? `<span>Бренд: <strong>${brandName}</strong></span>` : "",
          formatLabel ? `<span>Формат: <strong>${formatLabel}</strong></span>` : "",
          sheets ? `<span>Листы: <strong>${sheets}</strong></span>` : "",
          purpose ? `<span>Назначение: <strong>${purpose}</strong></span>` : "",
        ].filter(Boolean).join("");

        const categories = Array.isArray(item.product_category_slugs)
          ? item.product_category_slugs.join(",")
          : "";

        return `
          <article class="product" 
            data-fav-id="${item.id}"
            data-product-id="${item.product}"
            data-product-title="${title}"
            data-product-price="${price}"
            data-product-img="${image}"
            data-product-desc="${desc}"
            data-brand="${item.product_brand_slug || ""}"
            data-categories="${categories}"
            data-stock="${Number(item.product_stock || 0) > 0 ? "in_stock" : "out_stock"}"
            data-flag-new="${item.product_is_new ? "true" : "false"}"
            data-flag-hit="${item.product_is_hit ? "true" : "false"}"
            data-flag-featured="${item.product_is_featured ? "true" : "false"}"
            data-flag-discount="${hasDiscount ? "true" : "false"}"
            data-format="${item.product_format || "other"}"
            data-sheets="${item.product_sheets_count || ""}"
            data-purpose="${item.product_purpose || "universal"}"
            data-price="${price}">
            <span class="${chipClass}">${chipText}</span>
            <button class="fav-btn is-active" aria-label="Удалить из избранного" data-fav-id="${item.id}">
              <i class="bi bi-heart-fill"></i>
            </button>
            <a class="product__image" href="${targetUrl}">
              <img src="${image}" alt="${title}">
            </a>
            <div class="product__meta">
              <span class="rating-stars" aria-label="Рейтинг ${ratingDisplay} из 5">${renderStars(reviewsCount ? avgRating : 0)}</span>
              <span class="meta-score">${ratingDisplay}</span>
              <span class="meta-stock">${stockText}</span>
            </div>
            <h3><a href="${targetUrl}">${title}</a></h3>
            <p>${desc || "Товар из каталога"}</p>
            ${details ? `<div class="product__details">${details}</div>` : ""}
            <div class="product__bottom">
              <div class="price-stack${hasDiscount ? " has-discount" : ""}">
                <strong>${price.toLocaleString("ru-RU")} Руб.</strong>
                ${hasDiscount ? `<span class="product__old">${Number(oldPrice).toLocaleString("ru-RU")} Руб.</span>` : ""}
              </div>
              <button class="add"><i class="bi bi-bag-plus"></i><span>В корзину</span></button>
            </div>
          </article>
        `;
      })
      .join("");

    updateEmptyState();
  }

  async function loadFavorites() {
    try {
      const response = await fetch("/api/favorites/", { credentials: "same-origin" });
      if (!response.ok) {
        if (response.status === 401 || response.status === 403) {
          favGrid.innerHTML = "";
          emptyState.hidden = false;
          emptyState.innerHTML = '<i class="bi bi-heart"></i><h2>Войдите в аккаунт</h2><p>Чтобы увидеть избранное, необходимо авторизоваться.</p><a href="/auth/" class="btn btn--primary">Войти</a>';
          favGrid.hidden = true;
          return;
        }
        updateEmptyState();
        return;
      }

      const payload = await response.json();
      const rows = Array.isArray(payload) ? payload : payload.results || [];
      if (!rows.length) {
        favGrid.innerHTML = "";
        updateEmptyState();
        return;
      }

      renderFavorites(rows);
    } catch (error) {
      console.error("Favorites API error", error);
      updateEmptyState();
    }
  }

  // ---------- Обработчики событий ----------
  favGrid.addEventListener("click", async (event) => {
    const addBtn = event.target.closest(".add");
    if (addBtn) {
      const card = addBtn.closest(".product");
      if (!card) return;

      const product = {
        id: card.dataset.productId,
        title: card.dataset.productTitle,
        price: parseFloat(card.dataset.productPrice),
        img: card.dataset.productImg,
        desc: card.dataset.productDesc,
      };
      addToCart(product);

      const initialHtml = addBtn.innerHTML;
      addBtn.innerHTML = `<i class="bi bi-check2"></i><span>Добавлено</span>`;
      addBtn.disabled = true;
      setTimeout(() => {
        addBtn.innerHTML = initialHtml;
        addBtn.disabled = false;
      }, 900);
      return;
    }

    const removeBtn = event.target.closest(".fav-btn");
    if (removeBtn) {
      const card = removeBtn.closest(".product");
      const favId = removeBtn.dataset.favId || card?.dataset.favId;
      if (!favId) return;

      try {
        await fetch(`/api/favorites/${favId}/`, {
          method: "DELETE",
          credentials: "same-origin",
          headers: { "X-CSRFToken": getCookie("csrftoken") },
        });
      } catch (error) {
        console.error("Remove favorite error", error);
      }
      card.remove();
      updateEmptyState();
    }
  });

  searchForm?.addEventListener("submit", (event) => {
    event.preventDefault();
    const query = searchForm.querySelector("input")?.value.trim();
    if (query) {
      window.location.href = `/catalog/?q=${encodeURIComponent(query)}`;
    }
  });

  // Запуск
  updateCartCount();
  loadFavorites();
});
