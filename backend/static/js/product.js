document.addEventListener("DOMContentLoaded", () => {
  const cartCount = document.getElementById("cartCount");
  const addToCartBtn = document.getElementById("addToCart");
  const qtyInput = document.getElementById("qtyInput");
  const qtyMinus = document.getElementById("qtyMinus");
  const qtyPlus = document.getElementById("qtyPlus");
  const tabs = document.querySelectorAll(".tab");
  const panels = document.querySelectorAll(".panel");
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

  // ---------- Вспомогательные функции ----------
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

  function formatMoney(value) {
    const num = Number(value || 0);
    return `${num.toLocaleString("ru-RU")} Руб.`;
  }

  function updateDiscountDisplay(price, oldPrice) {
    if (!productOldPrice || !productDiscount) return;
    const numericPrice = Number(price || 0);
    const numericOld = Number(oldPrice || 0);
    const hasDiscount = numericOld > numericPrice && numericOld > 0;

    if (hasDiscount) {
      const percent = Math.round(((numericOld - numericPrice) / numericOld) * 100);
      productOldPrice.textContent = formatMoney(numericOld);
      productOldPrice.style.display = "inline";
      productDiscount.textContent = `-${percent}%`;
      productDiscount.style.display = "inline";
    } else {
      productOldPrice.style.display = "none";
      productDiscount.style.display = "none";
    }
  }

  // ---------- Корзина (localStorage) ----------
  function updateCartCount() {
    const items = JSON.parse(localStorage.getItem("paperly_cart_items") || "[]");
    const count = items.reduce((sum, item) => sum + item.qty, 0);
    localStorage.setItem("paperly_cart_count", String(count));
    cartCount.textContent = String(count);
    return count;
  }

  function addToCart(product, quantity = 1) {
    let items = JSON.parse(localStorage.getItem("paperly_cart_items") || "[]");
    const existing = items.find(item => item.id === product.id);
    if (existing) {
      existing.qty += quantity;
    } else {
      items.push({
        id: product.id,
        title: product.title,
        price: product.price,
        img: product.img,
        desc: product.desc,
        qty: quantity
      });
    }
    localStorage.setItem("paperly_cart_items", JSON.stringify(items));
    updateCartCount();
  }

  // ---------- Избранное (API) ----------
  async function syncFavoriteButton() {
    if (!currentProductId) return;
    try {
      const response = await fetch("/api/favorites/", { credentials: "same-origin" });
      if (!response.ok) return;
      const payload = await response.json();
      const favorites = Array.isArray(payload) ? payload : payload.results || [];
      const isFav = favorites.some(f => String(f.product) === String(currentProductId));

      favoriteButtons.forEach(btn => {
        if (isFav) {
          btn.classList.add("is-active");
          const icon = btn.querySelector("i");
          if (icon) {
            icon.classList.remove("bi-heart");
            icon.classList.add("bi-heart-fill");
          }
        } else {
          btn.classList.remove("is-active");
          const icon = btn.querySelector("i");
          if (icon) {
            icon.classList.remove("bi-heart-fill");
            icon.classList.add("bi-heart");
          }
        }
      });
    } catch (error) {
      console.error("Sync favorite error", error);
    }
  }

  async function toggleFavorite() {
    if (!currentProductId) return;

    const isActive = favoriteButtons[0]?.classList.contains("is-active");
    const csrfToken = getCookie("csrftoken");

    try {
      if (!isActive) {
        // Добавить
        const response = await fetch("/api/favorites/", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": csrfToken,
          },
          body: JSON.stringify({ product: currentProductId }),
          credentials: "same-origin",
        });
        if (!response.ok) {
          if (response.status === 401) alert("Войдите, чтобы добавить в избранное");
          return;
        }
      } else {
        // Удалить – нужно узнать ID записи
        const listResponse = await fetch("/api/favorites/", { credentials: "same-origin" });
        if (!listResponse.ok) return;
        const payload = await listResponse.json();
        const favorites = Array.isArray(payload) ? payload : payload.results || [];
        const fav = favorites.find(f => String(f.product) === String(currentProductId));
        if (!fav) return;
        await fetch(`/api/favorites/${fav.id}/`, {
          method: "DELETE",
          headers: { "X-CSRFToken": csrfToken },
          credentials: "same-origin",
        });
      }
      // Обновляем кнопки
      await syncFavoriteButton();
    } catch (error) {
      console.error("Toggle favorite error", error);
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
    reviewsList.innerHTML = reviews
      .map((review) => {
        const created = review.created_at ? new Date(review.created_at) : new Date();
        const dateText = created.toLocaleDateString("ru-RU", {
          day: "numeric",
          month: "long",
          year: "numeric",
        });

        return `
          <article class="review-card">
            <div class="review-card__head">
              <strong>${escapeHtml(review.author_name || "Покупатель")}</strong>
              <span>${review.rating}/5</span>
            </div>
            <p>${escapeHtml(review.text || "")}</p>
            <time datetime="${created.toISOString().slice(0, 10)}">${dateText}</time>
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
      };

      document.title = `Paperly — ${product.title}`;
      productTitle.textContent = product.title;
      productBreadcrumb.textContent = product.title;
      productSku.textContent = `Артикул: ${product.sku}`;
      productPrice.textContent = formatMoney(product.price);
      updateDiscountDisplay(product.price, product.old_price);

      renderFacts(product);

      // Заполняем data-атрибуты кнопки корзины
      if (addToCartBtn) {
        addToCartBtn.dataset.productId = currentProductData.id;
        addToCartBtn.dataset.title = currentProductData.title;
        addToCartBtn.dataset.price = String(currentProductData.price);
        addToCartBtn.dataset.image = currentProductData.img;
        addToCartBtn.dataset.desc = currentProductData.desc;
      }

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
  qtyMinus?.addEventListener("click", () => {
    const current = Number(qtyInput.value) || 1;
    qtyInput.value = String(Math.max(1, current - 1));
  });

  qtyPlus?.addEventListener("click", () => {
    const current = Number(qtyInput.value) || 1;
    qtyInput.value = String(current + 1);
  });

  addToCartBtn?.addEventListener("click", () => {
    if (!currentProductData) return;

    const quantity = Math.max(1, Number(qtyInput.value) || 1);
    addToCart(currentProductData, quantity);

    const initialText = addToCartBtn.textContent;
    addToCartBtn.textContent = "Добавлено";
    addToCartBtn.disabled = true;
    setTimeout(() => {
      addToCartBtn.textContent = initialText;
      addToCartBtn.disabled = false;
    }, 900);
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
