document.addEventListener("DOMContentLoaded", () => {
  const nav = document.getElementById("nav");
  const burger = document.getElementById("burger");
  const openFilters = document.getElementById("openFilters");
  const closeFilters = document.getElementById("closeFilters");
  const filtersPanel = document.getElementById("filtersPanel");
  const sortSelect = document.getElementById("sortSelect");
  const applyFilters = document.getElementById("applyFilters");
  const resetFilters = document.getElementById("resetFilters");
  const minPrice = document.getElementById("minPrice");
  const maxPrice = document.getElementById("maxPrice");
  const productsGrid = document.getElementById("productsGrid");
  const dynamicFilters = document.getElementById("dynamicFilters");

  let products = [];
  const cartCount = document.getElementById("cartCount");
  const resultsCount = document.getElementById("resultsCount");
  const searchForm = document.getElementById("searchForm");

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

  function updateFiltersOffset() {
    const header = document.querySelector(".site-header");
    if (!header) return;
    const height = Math.ceil(header.getBoundingClientRect().height);
    const offset = Math.max(80, height + 12);
    document.documentElement.style.setProperty("--filters-offset", `${offset}px`);
  }
  window.paperlyUpdateFiltersOffset = updateFiltersOffset;

  // ---------- Корзина (localStorage) ----------
  function updateCartCount() {
    const items = JSON.parse(localStorage.getItem("paperly_cart_items") || "[]");
    const count = items.reduce((sum, item) => sum + item.qty, 0);
    localStorage.setItem("paperly_cart_count", String(count));
    if (cartCount) cartCount.textContent = String(count);
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

  // ---------- Избранное (API) ----------
  async function syncFavorites() {
    const favButtons = document.querySelectorAll(".fav-btn");
    if (!favButtons.length) return;

    try {
      const response = await fetch("/api/favorites/", { credentials: "same-origin" });
      if (!response.ok) return;
      const payload = await response.json();
      const favorites = Array.isArray(payload) ? payload : payload.results || [];

      const favMap = new Map(favorites.map(f => [String(f.product), f]));

      favButtons.forEach(btn => {
        const card = btn.closest(".product");
        if (!card) return;
        const productId = card.dataset.productId;
        if (favMap.has(productId)) {
          btn.classList.add("is-active");
          btn.dataset.favId = favMap.get(productId).id;
          const icon = btn.querySelector("i");
          if (icon) {
            icon.classList.remove("bi-heart");
            icon.classList.add("bi-heart-fill");
          }
        } else {
          btn.classList.remove("is-active");
          delete btn.dataset.favId;
          const icon = btn.querySelector("i");
          if (icon) {
            icon.classList.remove("bi-heart-fill");
            icon.classList.add("bi-heart");
          }
        }
      });
    } catch (error) {
      console.error("Sync favorites error", error);
    }
  }

  async function getFavoriteIdByProduct(productId) {
    try {
      const response = await fetch("/api/favorites/", { credentials: "same-origin" });
      if (!response.ok) return null;
      const payload = await response.json();
      const favorites = Array.isArray(payload) ? payload : payload.results || [];
      const found = favorites.find(f => String(f.product) === String(productId));
      return found ? found.id : null;
    } catch {
      return null;
    }
  }

  // ---------- Привязка событий к карточкам ----------
  function bindProductActions() {
    // Кнопка «В корзину»
    productsGrid.querySelectorAll(".add").forEach((button) => {
      if (button.dataset.cartBound === "true") return;
      button.dataset.cartBound = "true";

      button.innerHTML = `<i class="bi bi-bag-plus"></i><span>В корзину</span>`;

      button.onclick = (e) => {
        e.stopPropagation();
        const productCard = button.closest(".product");
        if (!productCard) return;

        const productId = productCard.dataset.productId;
        const title = productCard.dataset.productTitle;
        const price = parseFloat(productCard.dataset.productPrice);
        const img = productCard.dataset.productImg;
        const desc = productCard.dataset.productDesc;

        addToCart({ id: productId, title, price, img, desc });

        button.innerHTML = `<i class="bi bi-check2"></i><span>Добавлено</span>`;
        button.disabled = true;
        setTimeout(() => {
          button.innerHTML = `<i class="bi bi-bag-plus"></i><span>В корзину</span>`;
          button.disabled = false;
        }, 900);
      };
    });

    // Кнопка избранного
    productsGrid.querySelectorAll(".fav-btn").forEach((button) => {
      if (button.dataset.favBound === "true") return;
      button.dataset.favBound = "true";

      button.onclick = async (e) => {
        e.stopPropagation();
        const productCard = button.closest(".product");
        if (!productCard) return;
        const productId = productCard.dataset.productId;
        const isActive = button.classList.contains("is-active");
        const favId = button.dataset.favId;
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
              body: JSON.stringify({ product: productId }),
              credentials: "same-origin",
            });
            if (!response.ok) {
              if (response.status === 401) {
                alert("Войдите, чтобы добавить в избранное");
              }
              return;
            }
            const data = await response.json();
            button.dataset.favId = data.id;
            button.classList.add("is-active");
            const icon = button.querySelector("i");
            icon.classList.remove("bi-heart");
            icon.classList.add("bi-heart-fill");
          } else {
            // Удалить
            const id = favId || (await getFavoriteIdByProduct(productId));
            if (!id) return;
            const response = await fetch(`/api/favorites/${id}/`, {
              method: "DELETE",
              headers: { "X-CSRFToken": csrfToken },
              credentials: "same-origin",
            });
            if (response.ok) {
              delete button.dataset.favId;
              button.classList.remove("is-active");
              const icon = button.querySelector("i");
              icon.classList.remove("bi-heart-fill");
              icon.classList.add("bi-heart");
            }
          }
        } catch (error) {
          console.error("Favorite toggle error", error);
        }
      };
    });
  }

  // Навигация по клику на карточку (остаётся без изменений)
  function bindProductCardNavigation() {
    const hasProductId = (href) => {
      try {
        const url = new URL(href, window.location.origin);
        return Boolean(url.searchParams.get("id"));
      } catch {
        return false;
      }
    };

    const resolveProductHref = async (card, fallbackHref) => {
      if (fallbackHref && hasProductId(fallbackHref)) {
        return fallbackHref;
      }

      const title = card.querySelector("h3 a")?.textContent?.trim();
      if (!title) {
        return fallbackHref || "/product/";
      }

      try {
        const response = await fetch(`/api/products/?search=${encodeURIComponent(title)}`);
        if (!response.ok) {
          return fallbackHref || "/product/";
        }

        const payload = await response.json();
        const rows = Array.isArray(payload) ? payload : payload.results || [];
        if (!rows.length) {
          return fallbackHref || "/product/";
        }

        const exact = rows.find((item) => String(item.title || "").trim().toLowerCase() === title.toLowerCase());
        const match = exact || rows[0];
        if (match?.id) {
          return `/product/?id=${match.id}`;
        }
      } catch (error) {
        console.error("Resolve product link error", error);
      }

      return fallbackHref || "/product/";
    };

    productsGrid.querySelectorAll(".product").forEach((card) => {
      if (card.dataset.navBound === "true") return;
      card.dataset.navBound = "true";

      card.addEventListener("click", async (event) => {
        if (event.target.closest("button, input, select, textarea, label")) {
          return;
        }

        const anchor = event.target.closest("a");
        if (anchor) {
          event.preventDefault();
        }

        const link = card.querySelector("h3 a") || card.querySelector(".product__image") || anchor;
        if (link?.href || anchor?.href) {
          const targetHref = await resolveProductHref(card, link?.href || anchor?.href);
          window.location.href = targetHref;
        }
      });
    });
  }

  // ---------- Фильтры и загрузка товаров (оригинальная логика с небольшими правками) ----------
  function setCheckedByValue(name, values) {
    const set = new Set(values);
    document.querySelectorAll(`input[name="${name}"]`).forEach((input) => {
      input.checked = set.has(input.value);
    });
  }

  function hasFilterInputs(name) {
    return Boolean(document.querySelector(`input[name="${name}"]`));
  }

  function hasDynamicParam(param) {
    return Boolean(document.querySelector(`input[data-query-param="${param}"]`));
  }

  function getQueryParamValues(key) {
    const query = new URLSearchParams(window.location.search);
    const raw = query.get(key);
    if (!raw) return [];
    return raw.split(",").map((value) => value.trim()).filter(Boolean);
  }

  function updateResultsCount(count) {
    if (!resultsCount) return;
    resultsCount.textContent = `Найдено: ${count} товаров`;
  }

  function applyDynamicChecksFromQuery() {
    const query = new URLSearchParams(window.location.search);
    const cache = new Map();
    document.querySelectorAll("input[data-query-param]").forEach((input) => {
      const key = input.dataset.queryParam;
      if (!key) return;
      if (!cache.has(key)) {
        const raw = query.get(key) || "";
        const values = raw.split(",").map((value) => value.trim()).filter(Boolean);
        cache.set(key, values);
      }
      const values = cache.get(key) || [];
      input.checked = values.includes(input.value);
    });
  }

  function buildApiUrl() {
    const query = new URLSearchParams(window.location.search);
    const url = new URL("/api/products/", window.location.origin);
    const q = query.get("q");
    if (q) url.searchParams.set("search", q);
    const selectedSort = sortSelect?.value || query.get("ordering");
    if (selectedSort) {
      const sortMap = {
        popular: "-sold_recent",
        "price-asc": "price",
        "price-desc": "-price",
        name: "title",
      };
      const ordering = sortMap[selectedSort] || selectedSort;
      url.searchParams.set("ordering", ordering);
    }

    const selectedBrands = selectedValues("brand");
    if (selectedBrands.length) {
      mergeQueryParam(url, "brand", selectedBrands);
    } else if (!hasFilterInputs("brand") && !hasDynamicParam("brand")) {
      mergeQueryParam(url, "brand", getQueryParamValues("brand"));
    }

    const selectedCategories = selectedValues("category");
    if (selectedCategories.length) {
      mergeQueryParam(url, "category", selectedCategories);
    } else if (!hasFilterInputs("category") && !hasDynamicParam("category")) {
      mergeQueryParam(url, "category", getQueryParamValues("category"));
    }

    const selectedPurposes = selectedValues("purpose");
    if (selectedPurposes.length) {
      mergeQueryParam(url, "purpose", selectedPurposes);
    } else if (!hasFilterInputs("purpose") && !hasDynamicParam("purpose")) {
      mergeQueryParam(url, "purpose", getQueryParamValues("purpose"));
    }

    const selectedFormats = selectedValues("format");
    if (selectedFormats.length) {
      mergeQueryParam(url, "product_format", selectedFormats);
    } else if (!hasFilterInputs("format") && !hasDynamicParam("product_format")) {
      mergeQueryParam(url, "product_format", getQueryParamValues("product_format"));
    }

    const selectedSheets = selectedValues("sheets");
    if (selectedSheets.length) {
      mergeQueryParam(url, "sheets_count", selectedSheets);
    } else if (!hasFilterInputs("sheets") && !hasDynamicParam("sheets_count")) {
      mergeQueryParam(url, "sheets_count", getQueryParamValues("sheets_count"));
    }

    const selectedAvailability = selectedValues("availability");
    if (selectedAvailability.length === 1) {
      url.searchParams.set("in_stock", selectedAvailability[0] === "in_stock" ? "true" : "false");
    } else if (!hasFilterInputs("availability") && !hasDynamicParam("in_stock")) {
      const inStock = query.get("in_stock");
      if (inStock) url.searchParams.set("in_stock", inStock);
    }

    const selectedFlags = selectedValues("flags");
    if (selectedFlags.length) {
      selectedFlags.forEach((flag) => {
        if (flag === "has_discount") url.searchParams.set("has_discount", "true");
        else url.searchParams.set(flag, "true");
      });
    } else if (!hasFilterInputs("flags")
      && !hasDynamicParam("is_new")
      && !hasDynamicParam("is_hit")
      && !hasDynamicParam("is_featured")
      && !hasDynamicParam("has_discount")
      && !hasDynamicParam("has_promotion")
      && !hasDynamicParam("sale")
    ) {
      ["is_new", "is_hit", "is_featured", "has_discount"].forEach((flag) => {
        if (query.get(flag) === "true" || query.get(flag) === "1") {
          url.searchParams.set(flag === "has_discount" ? "has_discount" : flag, "true");
        }
      });
    }

    if (minPrice?.value) url.searchParams.set("min_price", minPrice.value);
    if (maxPrice?.value) url.searchParams.set("max_price", maxPrice.value);

    const dynamicParams = selectedDynamicParams();
    Object.entries(dynamicParams).forEach(([key, values]) => {
      mergeQueryParam(url, key, values);
    });

    return url;
  }

  function selectedValues(name) {
    return Array.from(document.querySelectorAll(`input[name="${name}"]:checked`)).map((item) => item.value);
  }

  function selectedDynamicParams() {
    const params = {};
    document.querySelectorAll("input[data-query-param]:checked").forEach((input) => {
      const key = input.dataset.queryParam;
      if (!key) return;
      if (!params[key]) params[key] = [];
      params[key].push(input.value);
    });
    return params;
  }

  function mergeQueryParam(url, key, values) {
    if (!values?.length) return;
    const existing = url.searchParams.get(key);
    const merged = new Set(
      existing ? existing.split(",").map((value) => value.trim()).filter(Boolean) : []
    );
    values.forEach((value) => merged.add(String(value)));
    url.searchParams.set(key, Array.from(merged).join(","));
  }

  async function loadProductsFromApi() {
    try {
      const query = new URLSearchParams(window.location.search);
      // Устанавливаем чекбоксы из URL (если нужно)
      const brandFromQuery = query.get("brand");
      if (brandFromQuery) setCheckedByValue("brand", brandFromQuery.split(",").map(v => v.trim()).filter(Boolean));
      const categoryFromQuery = query.get("category");
      if (categoryFromQuery) setCheckedByValue("category", categoryFromQuery.split(",").map(v => v.trim()).filter(Boolean));
      const purposeFromQuery = query.get("purpose");
      if (purposeFromQuery) setCheckedByValue("purpose", purposeFromQuery.split(",").map(v => v.trim()).filter(Boolean));
      const formatFromQuery = query.get("product_format");
      if (formatFromQuery) setCheckedByValue("format", formatFromQuery.split(",").map(v => v.trim()).filter(Boolean));
      const sheetsFromQuery = query.get("sheets_count");
      if (sheetsFromQuery) setCheckedByValue("sheets", sheetsFromQuery.split(",").map(v => v.trim()).filter(Boolean));
      const inStock = query.get("in_stock");
      if (inStock === "true" || inStock === "1") setCheckedByValue("availability", ["in_stock"]);
      else if (inStock === "false" || inStock === "0") setCheckedByValue("availability", ["out_stock"]);
      const flags = ["is_new", "is_hit", "is_featured", "has_discount"].filter(f => query.get(f) === "true" || query.get(f) === "1");
      if (flags.length) setCheckedByValue("flags", flags);

      const url = buildApiUrl();
      const response = await fetch(url.toString());
      if (!response.ok) {
        productsGrid.innerHTML = `<p class="empty-state">Не удалось загрузить товары. Попробуйте обновить страницу.</p>`;
        products = [];
        resultsCount.textContent = "Найдено: 0 товаров";
        return;
      }
      const payload = await response.json();
      const rows = Array.isArray(payload) ? payload : payload.results || [];
      if (!rows.length) {
        productsGrid.innerHTML = `<p class="empty-state">По выбранным фильтрам товары не найдены.</p>`;
        products = [];
        resultsCount.textContent = "Найдено: 0 товаров";
        return;
      }

      productsGrid.innerHTML = rows
        .map((product) => {
          const firstImage = product.images?.[0]?.image_url || "https://images.unsplash.com/photo-1503676382389-4809596d5290?auto=format&fit=crop&w=900&q=80";
          const price = Number(product.price || 0);
          const oldPrice = product.old_price ? Number(product.old_price) : null;
          const targetUrl = `/product/?id=${product.id}`;
          const hasDiscount = Number(oldPrice) > Number(price);
          const discountPercent = hasDiscount ? Math.round(((oldPrice - price) / oldPrice) * 100) : 0;
          const chipText = hasDiscount
            ? `-${discountPercent}%`
            : product.is_hit
              ? "Хит"
              : product.is_new
                ? "Новинка"
                : "В наличии";
          const chipClass = hasDiscount ? "chip chip--discount" : "chip";
          const reviewsCount = Number(product.reviews_count || 0);
          const avgRating = Number(product.avg_rating || 0);
          const ratingDisplay = reviewsCount ? avgRating.toFixed(1) : "—";
          const stockText = product.stock > 0 ? "Есть на складе" : "Под заказ";
          const oldPriceMarkup = hasDiscount
            ? `<span class="product__old">${oldPrice.toLocaleString("ru-RU")} Руб.</span>`
            : "";

          const brandName = escapeHtml(product.brand_name || "");
          const formatLabel = escapeHtml(product.format || "");
          const sheets = product.sheets_count ? `${product.sheets_count} л.` : "";
          const purpose = escapeHtml(formatPurpose(product.purpose));
          const details = [
            brandName ? `<span>Бренд: <strong>${brandName}</strong></span>` : "",
            formatLabel ? `<span>Формат: <strong>${formatLabel}</strong></span>` : "",
            sheets ? `<span>Листы: <strong>${sheets}</strong></span>` : "",
            purpose ? `<span>Назначение: <strong>${purpose}</strong></span>` : "",
          ].filter(Boolean).join("");

          const categories = Array.isArray(product.category_slugs)
            ? product.category_slugs.join(",")
            : "";

          return `
            <article class="product" 
              data-product-id="${product.id}"
              data-product-title="${escapeHtml(product.title)}"
              data-product-price="${price}"
              data-product-img="${firstImage}"
              data-product-desc="${escapeHtml(product.short_description || '')}"
              data-brand="${product.brand_slug || ""}" 
              data-categories="${categories}" 
              data-stock="${product.stock > 0 ? "in_stock" : "out_stock"}" 
              data-flag-new="${product.is_new ? "true" : "false"}" 
              data-flag-hit="${product.is_hit ? "true" : "false"}" 
              data-flag-featured="${product.is_featured ? "true" : "false"}" 
              data-flag-discount="${hasDiscount ? "true" : "false"}" 
              data-format="${product.format || "other"}" 
              data-sheets="${product.sheets_count || ""}" 
              data-purpose="${product.purpose || "universal"}" 
              data-price="${price}">
              <span class="${chipClass}">${chipText}</span>
              <button class="fav-btn" aria-label="Добавить в избранное"><i class="bi bi-heart"></i></button>
              <a class="product__image" href="${targetUrl}">
                <img src="${firstImage}" alt="${escapeHtml(product.title)}">
              </a>
              <div class="product__meta">
                <span class="rating-stars" aria-label="Рейтинг ${ratingDisplay} из 5">${renderStars(reviewsCount ? avgRating : 0)}</span>
                <span class="meta-score">${ratingDisplay}</span>
                <span class="meta-stock">${stockText}</span>
              </div>
              <h3><a href="${targetUrl}">${escapeHtml(product.title)}</a></h3>
              <p>${escapeHtml(product.short_description || "Товар из каталога")}</p>
              ${details ? `<div class="product__details">${details}</div>` : ""}
              <div class="product__bottom">
                <div class="price-stack${hasDiscount ? " has-discount" : ""}">
                  <strong>${price.toLocaleString("ru-RU")} Руб.</strong>
                  ${oldPriceMarkup}
                </div>
                <button class="add"><i class="bi bi-bag-plus"></i><span>В корзину</span></button>
              </div>
            </article>
          `;
        })
        .join("");

      products = Array.from(productsGrid.querySelectorAll(".product"));
      updateResultsCount(products.length);
      bindProductActions();
      bindProductCardNavigation();
      await syncFavorites(); // восстановить состояние избранного
      filterProducts(); // если нужно применить фильтры на клиенте
    } catch (error) {
      console.error("Catalog API error", error);
      productsGrid.innerHTML = `<p class="empty-state">Ошибка загрузки каталога. Проверьте API и перезагрузите страницу.</p>`;
      products = [];
      resultsCount.textContent = "Найдено: 0 товаров";
    }
  }

  async function loadDynamicFilters() {
    if (!dynamicFilters) return;
    try {
      const response = await fetch("/api/catalog-filters/");
      if (!response.ok) {
        dynamicFilters.innerHTML = `<p class="filter-empty">Не удалось загрузить фильтры</p>`;
        return;
      }
      const payload = await response.json();
      const rawGroups = Array.isArray(payload) ? payload : payload.results || [];
      const seenGroups = new Set();
      const groups = rawGroups.filter((group) => {
        const key = String(group.slug || group.title || "").trim().toLowerCase();
        if (!key) return true;
        if (seenGroups.has(key)) return false;
        seenGroups.add(key);
        return true;
      });
      if (!groups.length) {
        dynamicFilters.innerHTML = `<p class="filter-empty">Фильтры не найдены</p>`;
        return;
      }

      dynamicFilters.innerHTML = groups
        .map((group) => {
          const title = escapeHtml(group.title || "Фильтр");
          const options = Array.isArray(group.options) ? group.options : [];
          const optionsMarkup = options.length
            ? options
                .map((option) => {
                  const label = escapeHtml(option.label || "");
                  const value = escapeHtml(option.value || "");
                  const queryParam = escapeHtml(option.query_param || "");
                  return `<label><input type="checkbox" data-query-param="${queryParam}" value="${value}"> ${label}</label>`;
                })
                .join("")
            : `<p class="filter-empty">Нет вариантов</p>`;

          return `
            <div class="filter-group">
              <h3>${title}</h3>
              ${optionsMarkup}
            </div>
          `;
        })
        .join("");

      applyDynamicChecksFromQuery();
    } catch (error) {
      console.error("Dynamic filters error", error);
      dynamicFilters.innerHTML = `<p class="filter-empty">Не удалось загрузить фильтры</p>`;
    }
  }
  function filterProducts() {
    updateResultsCount(products.length);
  }
  function sortProducts() {
    loadProductsFromApi();
  }

  // ---------- Инициализация ----------
  openFilters?.addEventListener("click", () => filtersPanel.classList.add("is-open"));
  closeFilters?.addEventListener("click", () => filtersPanel.classList.remove("is-open"));

  searchForm?.addEventListener("submit", (event) => {
    event.preventDefault();
    const query = searchForm.querySelector("input")?.value.trim();
    if (query) window.location.href = `/catalog/?q=${encodeURIComponent(query)}`;
  });

  applyFilters?.addEventListener("click", async () => {
    await loadProductsFromApi();
    if (window.innerWidth <= 1040) filtersPanel.classList.remove("is-open");
  });

  sortSelect?.addEventListener("change", sortProducts);

  resetFilters?.addEventListener("click", () => {
    document.querySelectorAll(".filters input[type='checkbox']").forEach((item) => item.checked = false);
    if (minPrice) minPrice.value = "0";
    if (maxPrice) maxPrice.value = "3000";
    if (sortSelect) sortSelect.value = "popular";
    window.history.replaceState(null, "", window.location.pathname);
    loadProductsFromApi();
  });

  // Старт
  updateFiltersOffset();
  window.addEventListener("resize", updateFiltersOffset);
  updateCartCount();
  loadDynamicFilters();
  loadProductsFromApi();
});
