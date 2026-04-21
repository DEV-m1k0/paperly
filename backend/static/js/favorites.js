document.addEventListener("DOMContentLoaded", () => {
  const P = window.paperly;
  const { escapeHtml, renderStars, formatPurpose, apiJson, apiFetch, unwrapList } = P;

  const favGrid = document.getElementById("favGrid");
  const favSkeleton = document.getElementById("favSkeleton");
  const favToolbar = document.getElementById("favToolbar");
  const favCount = document.getElementById("favCount");
  const favSort = document.getElementById("favSort");
  const favAddAll = document.getElementById("favAddAll");
  const favClearAll = document.getElementById("favClearAll");
  const emptyState = document.getElementById("emptyState");
  const authState = document.getElementById("authState");
  const isAuthenticated = P.isAuthenticated();

  P.renderCartCount();

  let items = [];
  let currentSort = "added-desc";

  // ────────── Helpers ──────────
  function formatNoun(n, one, few, many) {
    const mod10 = n % 10, mod100 = n % 100;
    if (mod100 < 10 || mod100 >= 20) {
      if (mod10 === 1) return `${n} ${one}`;
      if (mod10 >= 2 && mod10 <= 4) return `${n} ${few}`;
    }
    return `${n} ${many}`;
  }

  function sortItems(list, mode) {
    const sorted = [...list];
    switch (mode) {
      case "added-asc":
        return sorted.sort((a, b) => new Date(a.created_at || 0) - new Date(b.created_at || 0));
      case "price-asc":
        return sorted.sort((a, b) => Number(a.product_price || 0) - Number(b.product_price || 0));
      case "price-desc":
        return sorted.sort((a, b) => Number(b.product_price || 0) - Number(a.product_price || 0));
      case "name":
        return sorted.sort((a, b) => (a.product_title || "").localeCompare(b.product_title || "", "ru"));
      case "added-desc":
      default:
        return sorted.sort((a, b) => new Date(b.created_at || 0) - new Date(a.created_at || 0));
    }
  }

  // ────────── Render ──────────
  function renderCard(item) {
    const image = item.product_image || "";
    const title = escapeHtml(item.product_title || "Товар");
    const desc = escapeHtml(item.product_short_description || "");
    const price = Number(item.product_price || 0);
    const oldPrice = item.product_old_price ? Number(item.product_old_price) : null;
    const targetUrl = `/product/?id=${item.product}`;
    const hasDiscount = Number(oldPrice) > Number(price);
    const discountPercent = hasDiscount ? Math.round(((oldPrice - price) / oldPrice) * 100) : 0;
    const chipText = hasDiscount
      ? `-${discountPercent}%`
      : item.product_is_hit ? "Хит" : item.product_is_new ? "Новинка" : "В наличии";
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

    const imageMarkup = image
      ? `<img src="${image}" alt="${title}">`
      : `<div class="product__placeholder"><i class="bi bi-image"></i></div>`;

    return `
      <article class="product"
        data-fav-id="${item.id}"
        data-product-id="${item.product}"
        data-product-title="${title}"
        data-product-price="${price}"
        data-product-img="${image}"
        data-product-desc="${desc}">
        <span class="${chipClass}">${chipText}</span>
        <button class="fav-btn is-active" aria-label="Удалить из избранного" data-fav-id="${item.id}" type="button">
          <i class="bi bi-heart-fill"></i>
        </button>
        <a class="product__image" href="${targetUrl}">
          ${imageMarkup}
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
          <button class="add" type="button"><i class="bi bi-bag-plus"></i><span>В корзину</span></button>
        </div>
      </article>
    `;
  }

  function renderAll() {
    const sorted = sortItems(items, currentSort);
    if (!sorted.length) {
      favGrid.hidden = true;
      favGrid.innerHTML = "";
      favToolbar.hidden = true;
      emptyState.hidden = false;
      return;
    }
    favGrid.hidden = false;
    emptyState.hidden = true;
    favToolbar.hidden = false;
    favCount.textContent = formatNoun(sorted.length, "товар", "товара", "товаров");
    favGrid.innerHTML = sorted.map(renderCard).join("");
  }

  function showSkeleton(visible) {
    if (favSkeleton) favSkeleton.hidden = !visible;
  }

  // ────────── Load ──────────
  async function loadFavorites() {
    showSkeleton(true);
    try {
      if (isAuthenticated) {
        const payload = await apiJson("/api/favorites/");
        items = unwrapList(payload);
      } else {
        items = await loadLocalFavoritesAsItems();
      }
    } catch (error) {
      console.error("Favorites API error", error);
      emptyState.hidden = false;
      showSkeleton(false);
      return;
    }
    showSkeleton(false);
    renderAll();
  }

  async function loadLocalFavoritesAsItems() {
    const localIds = P.readLocalFavorites();
    if (!localIds.length) return [];
    // Fetch all products that match — single API call per ID
    const fetched = await Promise.all(localIds.map((id) =>
      apiJson(`/api/products/${id}/`).catch(() => null)
    ));
    // Clean up stale IDs (product deleted / draft)
    const valid = [];
    const validIds = [];
    fetched.forEach((product, idx) => {
      if (!product) return;
      validIds.push(localIds[idx]);
      valid.push({
        id: `local-${product.id}`,
        product: product.id,
        product_title: product.title,
        product_short_description: product.short_description || "",
        product_image: product.images?.[0]?.image_url || "",
        product_price: product.price,
        product_old_price: product.old_price,
        product_brand_name: product.brand_name || "",
        product_brand_slug: product.brand_slug || "",
        product_stock: product.stock,
        product_is_hit: product.is_hit,
        product_is_new: product.is_new,
        product_is_featured: product.is_featured,
        product_format: product.format,
        product_sheets_count: product.sheets_count,
        product_purpose: product.purpose,
        product_avg_rating: product.avg_rating,
        product_reviews_count: product.reviews_count,
        created_at: new Date().toISOString(),
      });
    });
    // Prune stale entries in localStorage
    if (validIds.length !== localIds.length) P.writeLocalFavorites(validIds);
    return valid;
  }

  // ────────── Actions ──────────
  async function removeFavorite(favId, productId) {
    items = items.filter((x) => String(x.id) !== String(favId));
    renderAll();
    if (!isAuthenticated) {
      P.removeLocalFavorite(productId);
      P.updateFavoritesCount();
      return;
    }
    try {
      await apiFetch(`/api/favorites/${favId}/`, { method: "DELETE" });
      P.updateFavoritesCount();
    } catch (error) {
      console.error("Remove favorite error", error);
    }
  }

  favGrid.addEventListener("click", (event) => {
    const addBtn = event.target.closest(".add");
    if (addBtn) {
      const card = addBtn.closest(".product");
      if (!card) return;
      P.addCartItem({
        id: card.dataset.productId,
        title: card.dataset.productTitle,
        price: parseFloat(card.dataset.productPrice),
        img: card.dataset.productImg,
        desc: card.dataset.productDesc,
      }, 1);
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
      const productId = card?.dataset.productId;
      if (favId) removeFavorite(favId, productId);
    }
  });

  favSort?.addEventListener("change", () => {
    currentSort = favSort.value || "added-desc";
    renderAll();
  });

  favAddAll?.addEventListener("click", () => {
    if (!items.length) return;
    items.forEach((item) => {
      if (Number(item.product_stock || 0) <= 0) return;
      P.addCartItem({
        id: String(item.product),
        title: item.product_title,
        price: Number(item.product_price || 0),
        img: item.product_image || "",
        desc: item.product_short_description || "",
      }, 1);
    });
    const initialHtml = favAddAll.innerHTML;
    favAddAll.innerHTML = `<i class="bi bi-check2"></i><span>Добавлено в корзину</span>`;
    favAddAll.disabled = true;
    setTimeout(() => {
      favAddAll.innerHTML = initialHtml;
      favAddAll.disabled = false;
    }, 1600);
  });

  favClearAll?.addEventListener("click", async () => {
    if (!items.length) return;
    if (!confirm("Удалить все товары из избранного?")) return;
    const previous = [...items];
    items = [];
    renderAll();
    favClearAll.disabled = true;
    if (!isAuthenticated) {
      P.clearLocalFavorites();
      P.updateFavoritesCount();
    } else {
      const results = await Promise.allSettled(
        previous.map((x) => apiFetch(`/api/favorites/${x.id}/`, { method: "DELETE" }))
      );
      const failed = results.filter((r) => r.status === "rejected").length;
      if (failed) console.warn(`Не удалось удалить ${failed} позиций.`);
      P.updateFavoritesCount();
    }
    favClearAll.disabled = false;
  });

  loadFavorites();
});
