document.addEventListener("DOMContentLoaded", () => {
  const cartCount = document.getElementById("cartCount");
  const addToCartBtn = document.getElementById("addToCart");
  const qtyInput = document.getElementById("qtyInput");
  const qtyMinus = document.getElementById("qtyMinus");
  const qtyPlus = document.getElementById("qtyPlus");
  const tabs = document.querySelectorAll(".tab");
  const panels = document.querySelectorAll(".tab-panel");
  const productBadge = document.getElementById("productBadge");
  const productBrand = document.getElementById("productBrand");
  const productStock = document.getElementById("productStock");
  const reviewsEmpty = document.getElementById("reviewsEmpty");
  const favoriteButtons = document.querySelectorAll(".fav-btn");
  const searchForm = document.getElementById("searchForm");
  const reviewForm = document.getElementById("reviewForm");
  const reviewsList = document.getElementById("reviewsList");
  const mainImage = document.getElementById("mainImage");
  const thumbsBox = document.querySelector(".gallery__thumbs");
  const productTitle = document.getElementById("productTitle");
  const productSku = document.getElementById("productSku");
  const productPrice = document.getElementById("productPrice");
  const productOldPrice = document.getElementById("productOldPrice");
  const productDiscount = document.getElementById("productDiscount");
  const productBreadcrumb = document.getElementById("productBreadcrumb");
  const specsGrid = document.getElementById("specsGrid");
  const ratingStars = document.getElementById("ratingStars");
  const ratingValue = document.getElementById("ratingValue");
  const ratingCount = document.getElementById("ratingCount");
  const productFacts = document.getElementById("productFacts");

  let currentProductId = null;
  let currentProductData = null; // для хранения данных товара

  // ---------- Shared helpers ----------
  const { getCookie, escapeHtml, apiFetch, apiJson, unwrapList } = window.paperly;
  const formatMoney = (value) => window.paperly.formatMoney(value, "Руб.");

  function updateDiscountDisplay(price, oldPrice) {
    if (!productOldPrice || !productDiscount) return;
    const numericPrice = Number(price || 0);
    const numericOld = Number(oldPrice || 0);
    const hasDiscount = numericOld > numericPrice && numericOld > 0;

    if (hasDiscount) {
      const percent = Math.round(((numericOld - numericPrice) / numericOld) * 100);
      productOldPrice.textContent = formatMoney(numericOld);
      productOldPrice.hidden = false;
      productDiscount.textContent = `−${percent}%`;
      productDiscount.hidden = false;
    } else {
      productOldPrice.hidden = true;
      productDiscount.hidden = true;
    }
  }

  function updateBadge(product) {
    if (!productBadge) return;
    if (product.is_hit) {
      productBadge.textContent = "Хит продаж";
      productBadge.className = "gallery__badge gallery__badge--hit";
      productBadge.hidden = false;
    } else if (product.is_new) {
      productBadge.textContent = "Новинка";
      productBadge.className = "gallery__badge gallery__badge--new";
      productBadge.hidden = false;
    } else if (Number(product.old_price) > Number(product.price)) {
      productBadge.textContent = "Скидка";
      productBadge.className = "gallery__badge gallery__badge--sale";
      productBadge.hidden = false;
    } else {
      productBadge.hidden = true;
    }
  }

  function updateBrand(product) {
    if (!productBrand) return;
    if (product.brand_name) {
      productBrand.innerHTML = `<i class="bi bi-patch-check" aria-hidden="true"></i> ${escapeHtml(product.brand_name)}`;
      productBrand.hidden = false;
    } else {
      productBrand.hidden = true;
    }
  }

  function updateStock(product) {
    if (!productStock) return;
    const stock = Number(product.stock || 0);
    if (stock > 10) {
      productStock.className = "product-stock is-in";
      productStock.innerHTML = `<i class="bi bi-check-circle-fill" aria-hidden="true"></i> В наличии`;
    } else if (stock > 0) {
      productStock.className = "product-stock is-low";
      productStock.innerHTML = `<i class="bi bi-exclamation-circle-fill" aria-hidden="true"></i> Осталось ${stock} шт.`;
    } else {
      productStock.className = "product-stock is-out";
      productStock.innerHTML = `<i class="bi bi-clock-history" aria-hidden="true"></i> Под заказ`;
    }
  }

  // ---------- Корзина ----------
  const updateCartCount = () => window.paperly.renderCartCount();
  const addToCart = (product, quantity = 1) => window.paperly.addCartItem(product, quantity);

  // Рисуем подпись «макс. N шт» под спинбоксом количества.
  // Не создаём элемент, если такой уже есть (идемпотентно при повторном рендере).
  function renderMaxQtyHint() {
    const maxQty = currentProductData?.maxQty || 0;
    if (!qtyInput) return;
    const parent = qtyInput.closest(".qty") || qtyInput.parentElement;
    if (!parent) return;
    let hint = parent.parentElement?.querySelector(".qty-hint");
    if (maxQty <= 0) {
      if (hint) hint.remove();
      return;
    }
    if (!hint) {
      hint = document.createElement("small");
      hint.className = "qty-hint";
      hint.style.cssText = "display:block;margin-top:6px;color:var(--color-muted,#64748b);font-size:12px;";
      parent.insertAdjacentElement("afterend", hint);
    }
    hint.textContent = `Макс. ${maxQty} шт. в одном заказе`;
  }

  // ---------- Избранное (API) ----------
  function setFavButtonState(isFav) {
    favoriteButtons.forEach(btn => {
      btn.classList.toggle("is-active", isFav);
      const icon = btn.querySelector("i");
      if (icon) {
        icon.classList.toggle("bi-heart", !isFav);
        icon.classList.toggle("bi-heart-fill", isFav);
      }
    });
  }

  async function syncFavoriteButton() {
    if (!currentProductId) return;
    if (!window.paperly.isAuthenticated()) {
      setFavButtonState(window.paperly.isLocalFavorite(currentProductId));
      return;
    }
    try {
      const favs = await window.paperly.fetchFavorites();
      setFavButtonState(favs.some(f => String(f.product) === String(currentProductId)));
    } catch (error) {
      console.error("Sync favorite error", error);
    }
  }

  async function toggleFavorite() {
    if (!currentProductId) return;
    const isActive = favoriteButtons[0]?.classList.contains("is-active");
    const nextFav = !isActive;
    setFavButtonState(nextFav);

    if (!window.paperly.isAuthenticated()) {
      if (nextFav) window.paperly.addLocalFavorite(currentProductId);
      else window.paperly.removeLocalFavorite(currentProductId);
      window.paperly.updateFavoritesCount();
      return;
    }

    try {
      if (nextFav) {
        await window.paperly.apiJson("/api/favorites/", {
          method: "POST",
          body: { product: currentProductId },
        });
      } else {
        const favs = await window.paperly.fetchFavorites();
        const fav = favs.find(f => String(f.product) === String(currentProductId));
        if (fav) {
          await window.paperly.apiFetch(`/api/favorites/${fav.id}/`, { method: "DELETE" });
        }
      }
      window.paperly.updateFavoritesCount();
    } catch (error) {
      console.error("Toggle favorite error", error);
      setFavButtonState(isActive); // revert
    }
  }

  // ---------- Рендер звёзд, отзывов и пр. ----------
  function renderStars(container, rating) {
    if (!container) return;
    const full = Math.round(Number(rating));
    container.innerHTML = Array.from({ length: 5 }, (_, index) => {
      return `<i class="bi ${index < full ? "bi-star-fill" : "bi-star"}"></i>`;
    }).join("");
  }

  function updateRating(reviews) {
    if (!ratingValue || !ratingCount || !ratingStars) return;
    if (!reviews.length) {
      ratingValue.textContent = "—";
      ratingCount.textContent = "нет оценок";
      renderStars(ratingStars, 0);
      return;
    }
    const avg = reviews.reduce((sum, item) => sum + Number(item.rating || 0), 0) / reviews.length;
    ratingValue.textContent = avg.toFixed(1);
    ratingCount.textContent = `${reviews.length} оценок`;
    renderStars(ratingStars, avg);
  }

  function renderFacts(product) {
    if (!productFacts) return;
    const items = [];

    if (product.brand_name) {
      items.push(`<span>Бренд: <strong>${escapeHtml(product.brand_name)}</strong></span>`);
    }
    if (Array.isArray(product.category_names) && product.category_names.length) {
      items.push(`<span>Категории: <strong>${escapeHtml(product.category_names.join(", "))}</strong></span>`);
    }
    if (product.format) {
      items.push(`<span>Формат: <strong>${escapeHtml(product.format)}</strong></span>`);
    }
    if (product.purpose) {
      items.push(`<span>Назначение: <strong>${escapeHtml(product.purpose)}</strong></span>`);
    }
    if (product.sheets_count) {
      items.push(`<span>Листов: <strong>${product.sheets_count}</strong></span>`);
    }
    items.push(`<span>Наличие: <strong>${product.stock > 0 ? "В наличии" : "Под заказ"}</strong></span>`);

    if (product.weight_grams) {
      items.push(`<span>Вес: <strong>${product.weight_grams} г</strong></span>`);
    }
    if (product.length_mm || product.width_mm || product.height_mm) {
      const dims = [product.length_mm, product.width_mm, product.height_mm]
        .filter((v) => Number(v) > 0)
        .join(" × ");
      if (dims) {
        items.push(`<span>Размеры: <strong>${dims} мм</strong></span>`);
      }
    }

    if (product.has_active_promotion && product.active_promotion_title) {
      const discount = product.active_promotion_discount ? `-${product.active_promotion_discount}%` : "";
      items.push(`<span>Акция: <strong>${escapeHtml(product.active_promotion_title)} ${discount}</strong></span>`);
    }

    productFacts.innerHTML = items.join("");
  }

  function renderReviews(reviews) {
    if (!reviews.length) {
      reviewsList.innerHTML = `<p class="reviews-empty">Пока нет отзывов — станьте первым.</p>`;
      updateRating([]);
      return;
    }
    reviewsList.innerHTML = reviews
      .map((review) => {
        const created = review.created_at ? new Date(review.created_at) : new Date();
        const dateText = created.toLocaleDateString("ru-RU", {
          day: "numeric",
          month: "long",
          year: "numeric",
        });
        const rating = Math.round(Number(review.rating || 0));
        const authorInitial = (review.author_name || "П").trim().charAt(0).toUpperCase();
        const starsHtml = Array.from({ length: 5 }, (_, i) =>
          `<i class="bi ${i < rating ? "bi-star-fill" : "bi-star"}"></i>`
        ).join("");

        return `
          <article class="review-card">
            <div class="review-card__author">
              <span class="review-card__avatar">${escapeHtml(authorInitial)}</span>
              <div>
                <strong>${escapeHtml(review.author_name || "Покупатель")}</strong>
                <time datetime="${created.toISOString().slice(0, 10)}">${dateText}</time>
              </div>
              <span class="review-card__stars">${starsHtml}</span>
            </div>
            <p>${escapeHtml(review.text || "")}</p>
          </article>
        `;
      })
      .join("");

    updateRating(reviews);
  }

  function bindThumbs() {
    const thumbs = document.querySelectorAll(".thumb");
    thumbs.forEach((thumb) => {
      thumb.addEventListener("click", () => {
        mainImage.src = thumb.dataset.image;
        thumbs.forEach((item) => item.classList.remove("is-active"));
        thumb.classList.add("is-active");
      });
    });
  }

  // ---------- Загрузка товара с API ----------
  async function loadProductFromApi() {
    try {
      const params = new URLSearchParams(window.location.search);
      const requestedId = params.get("id");

      let product = null;

      if (requestedId) {
        const byIdResponse = await fetch(`/api/products/${requestedId}/`);
        if (byIdResponse.ok) {
          product = await byIdResponse.json();
        }
      }

      if (!product) {
        const listResponse = await fetch("/api/products/?ordering=-created_at");
        if (!listResponse.ok) return;
        const listData = await listResponse.json();
        const rows = Array.isArray(listData) ? listData : listData.results || [];
        product = rows[0];
      }

      if (!product) return;

      currentProductId = product.id;
      currentProductData = {
        id: String(product.id),
        title: product.title,
        price: Number(product.price),
        img: product.images?.[0]?.image_url || "",
        desc: product.short_description || "",
        // 0 = без ограничения (парно с Product.max_order_quantity на бекенде)
        maxQty: Math.max(0, Number(product.max_order_quantity) || 0),
      };

      document.title = `Paperly — ${product.title}`;
      productTitle.textContent = product.title;
      productBreadcrumb.textContent = product.title;
      productSku.textContent = product.sku ? `Артикул: ${product.sku}` : "";
      productPrice.textContent = formatMoney(product.price);
      updateDiscountDisplay(product.price, product.old_price);
      updateBadge(product);
      updateBrand(product);
      updateStock(product);

      renderFacts(product);

      // Заполняем data-атрибуты кнопки корзины
      if (addToCartBtn) {
        addToCartBtn.dataset.productId = currentProductData.id;
        addToCartBtn.dataset.title = currentProductData.title;
        addToCartBtn.dataset.price = String(currentProductData.price);
        addToCartBtn.dataset.image = currentProductData.img;
        addToCartBtn.dataset.desc = currentProductData.desc;
        addToCartBtn.dataset.maxQty = String(currentProductData.maxQty);
      }

      // Лимит кол-ва в заказе → ограничиваем спинбокс и показываем подсказку
      if (qtyInput) {
        if (currentProductData.maxQty > 0) {
          qtyInput.max = String(currentProductData.maxQty);
          if (Number(qtyInput.value) > currentProductData.maxQty) {
            qtyInput.value = String(currentProductData.maxQty);
          }
        } else {
          qtyInput.removeAttribute("max");
        }
      }
      renderMaxQtyHint();

      // Характеристики
      if (Array.isArray(product.specifications) && product.specifications.length) {
        specsGrid.innerHTML = product.specifications
          .map((spec) => `<div><span>${escapeHtml(spec.name)}</span><strong>${escapeHtml(spec.value)}</strong></div>`)
          .join("");
      }

      // Изображения
      if (Array.isArray(product.images) && product.images.length) {
        mainImage.src = product.images[0].image_url;
        mainImage.alt = product.title;

        thumbsBox.innerHTML = product.images
          .map(
            (image, index) =>
              `<button class="thumb ${index === 0 ? "is-active" : ""}" data-image="${image.image_url}"><img src="${image.image_url}" alt="${escapeHtml(image.alt_text || product.title)}"></button>`
          )
          .join("");
        bindThumbs();
      }

      // Отзывы
      const reviewsResponse = await fetch(`/api/reviews/?product=${product.id}`);
      if (reviewsResponse.ok) {
        const reviewsPayload = await reviewsResponse.json();
        const reviews = Array.isArray(reviewsPayload) ? reviewsPayload : reviewsPayload.results || [];
        renderReviews(reviews);
      } else {
        updateRating([]);
      }

      // Синхронизация избранного
      await syncFavoriteButton();
    } catch (error) {
      console.error("Product API error", error);
    }
  }

  // ---------- Обработчики событий ----------
  // Верхняя граница: max_order_quantity с товара (0 = нет лимита).
  function clampQty(value) {
    const n = Math.max(1, Number(value) || 1);
    const max = currentProductData?.maxQty || 0;
    return max > 0 ? Math.min(n, max) : n;
  }

  qtyMinus?.addEventListener("click", () => {
    const current = Number(qtyInput.value) || 1;
    qtyInput.value = String(Math.max(1, current - 1));
  });

  qtyPlus?.addEventListener("click", () => {
    const current = Number(qtyInput.value) || 1;
    qtyInput.value = String(clampQty(current + 1));
  });

  qtyInput?.addEventListener("change", () => {
    qtyInput.value = String(clampQty(qtyInput.value));
  });

  addToCartBtn?.addEventListener("click", () => {
    if (!currentProductData) return;

    const quantity = Math.max(1, Number(qtyInput.value) || 1);
    addToCart(currentProductData, quantity);

    const initialHtml = addToCartBtn.innerHTML;
    addToCartBtn.innerHTML = `<i class="bi bi-check2" aria-hidden="true"></i><span>Добавлено</span>`;
    addToCartBtn.disabled = true;
    setTimeout(() => {
      addToCartBtn.innerHTML = initialHtml;
      addToCartBtn.disabled = false;
    }, 1000);
  });

  favoriteButtons.forEach((button) => {
    button.addEventListener("click", (e) => {
      e.preventDefault();
      toggleFavorite();
    });
  });

  bindThumbs();

  tabs.forEach((tab) => {
    tab.addEventListener("click", () => {
      tabs.forEach((item) => item.classList.remove("is-active"));
      panels.forEach((panel) => panel.classList.remove("is-active"));
      tab.classList.add("is-active");
      document.getElementById(tab.dataset.tab)?.classList.add("is-active");
    });
  });

  searchForm?.addEventListener("submit", (event) => {
    event.preventDefault();
    const query = searchForm.querySelector("input")?.value.trim();
    if (query) {
      window.location.href = `/catalog/?q=${encodeURIComponent(query)}`;
    }
  });

  reviewForm?.addEventListener("submit", async (event) => {
    event.preventDefault();

    const rating = Number(document.getElementById("reviewRating")?.value);
    const text = document.getElementById("reviewText")?.value.trim();

    if (!text || !currentProductId) return;

    try {
      const csrfToken = getCookie("csrftoken");
      const response = await fetch("/api/reviews/", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": csrfToken,
        },
        body: JSON.stringify({
          product: currentProductId,
          rating,
          text,
          is_published: true,
        }),
        credentials: "same-origin",
      });

      if (!response.ok) {
        if (response.status === 403) {
          alert("Не удалось отправить отзыв. Проверьте CSRF или авторизацию.");
        }
        return;
      }

      const reviewsResponse = await fetch(`/api/reviews/?product=${currentProductId}`);
      if (reviewsResponse.ok) {
        const reviewsPayload = await reviewsResponse.json();
        const reviews = Array.isArray(reviewsPayload) ? reviewsPayload : reviewsPayload.results || [];
        renderReviews(reviews);
      }

      reviewForm.reset();
    } catch (error) {
      console.error("Review API error", error);
    }
  });

  // Инициализация счётчика корзины
  updateCartCount();
  loadProductFromApi();

});
