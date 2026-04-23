document.addEventListener("DOMContentLoaded", () => {
  const P = window.paperly;
  const { escapeHtml, apiJson, unwrapList } = P;
  P.renderCartCount?.();

  const gridEl = document.getElementById("brandsGrid");
  const emptyEl = document.getElementById("brandsEmpty");
  const emptyTitle = document.getElementById("brandsEmptyTitle");
  const emptyText = document.getElementById("brandsEmptyText");
  const emptyReset = document.getElementById("brEmptyReset");
  const searchInput = document.getElementById("brSearch");
  const sortButtons = Array.from(document.querySelectorAll(".br-sort__btn"));
  const statBrandsEl = document.getElementById("brStatBrands");
  const statProductsEl = document.getElementById("brStatProducts");

  let allBrands = [];
  let currentSort = "popular";
  let currentQuery = "";

  function renderBrandCard(brand) {
    const title = escapeHtml(brand.name || "Бренд");
    const description = escapeHtml(brand.description || "Товары в каталоге");
    const link = `/catalog/?brand=${encodeURIComponent(brand.slug || "")}`;
    const count = Number(brand.product_count || 0);
    const countText = count > 0
      ? `${count} ${pluralize(count, "товар", "товара", "товаров")}`
      : "В каталоге";
    const logo = brand.logo_url
      ? `<img src="${escapeHtml(brand.logo_url)}" alt="${title}" loading="lazy">`
      : `<span class="br-card__logo--initial">${escapeHtml((brand.name || "?").charAt(0))}</span>`;

    return `
      <a class="br-card" href="${link}" data-brand-name="${title.toLowerCase()}">
        <div class="br-card__logo">${logo}</div>
        <div class="br-card__body">
          <h3 class="br-card__name">${title}</h3>
          <p class="br-card__desc">${description}</p>
        </div>
        <div class="br-card__foot">
          <span class="br-card__count">
            <i class="bi bi-box-seam" aria-hidden="true"></i>
            ${countText}
          </span>
          <span class="br-card__cta">
            <span>К товарам</span>
            <i class="bi bi-arrow-right" aria-hidden="true"></i>
          </span>
        </div>
      </a>
    `;
  }

  function pluralize(n, one, few, many) {
    const mod10 = n % 10;
    const mod100 = n % 100;
    if (mod100 >= 11 && mod100 <= 14) return many;
    if (mod10 === 1) return one;
    if (mod10 >= 2 && mod10 <= 4) return few;
    return many;
  }

  function applySort(list) {
    const copy = [...list];
    if (currentSort === "alpha") {
      return copy.sort((a, b) => (a.name || "").localeCompare(b.name || "", "ru"));
    }
    return copy.sort(
      (a, b) => Number(b.product_count || 0) - Number(a.product_count || 0)
        || (a.name || "").localeCompare(b.name || "", "ru"),
    );
  }

  function render() {
    let list = allBrands;
    if (currentQuery) {
      const q = currentQuery.toLowerCase();
      list = list.filter((b) => (b.name || "").toLowerCase().includes(q));
    }
    list = applySort(list);

    if (!list.length) {
      gridEl.innerHTML = "";
      showEmpty();
      return;
    }

    hideEmpty();
    gridEl.innerHTML = list.map(renderBrandCard).join("");
  }

  function showEmpty() {
    if (!emptyEl) return;
    emptyEl.hidden = false;
    emptyEl.classList.add("is-visible");
    if (currentQuery) {
      emptyTitle.textContent = "Ничего не найдено";
      emptyText.textContent = `По запросу «${currentQuery}» брендов нет. Попробуйте другое название.`;
      if (emptyReset) emptyReset.hidden = false;
    } else {
      emptyTitle.textContent = "Брендов пока нет";
      emptyText.textContent = "Как только добавим новых производителей — они появятся здесь.";
      if (emptyReset) emptyReset.hidden = true;
    }
  }

  function hideEmpty() {
    if (!emptyEl) return;
    emptyEl.hidden = true;
    emptyEl.classList.remove("is-visible");
  }

  // Search (debounced)
  let searchTimer;
  searchInput?.addEventListener("input", (event) => {
    clearTimeout(searchTimer);
    searchTimer = setTimeout(() => {
      currentQuery = (event.target.value || "").trim();
      render();
    }, 120);
  });

  // Sort buttons
  sortButtons.forEach((btn) => {
    btn.addEventListener("click", () => {
      const sort = btn.dataset.sort;
      if (!sort || sort === currentSort) return;
      currentSort = sort;
      sortButtons.forEach((b) => {
        const active = b.dataset.sort === sort;
        b.classList.toggle("is-active", active);
        b.setAttribute("aria-selected", active ? "true" : "false");
      });
      render();
    });
  });

  // "Очистить фильтр" button in empty state
  emptyReset?.addEventListener("click", () => {
    if (searchInput) searchInput.value = "";
    currentQuery = "";
    render();
    searchInput?.focus();
  });

  async function loadBrands() {
    try {
      const payload = await apiJson("/api/brands/");
      allBrands = unwrapList(payload).filter((b) => b && b.id && b.is_active !== false);
    } catch (error) {
      console.error("Brands API error", error);
      allBrands = [];
    }

    // Update hero stats
    if (statBrandsEl) statBrandsEl.textContent = String(allBrands.length);
    if (statProductsEl) {
      const totalProducts = allBrands.reduce((sum, b) => sum + Number(b.product_count || 0), 0);
      statProductsEl.textContent = totalProducts > 0 ? String(totalProducts) : "—";
    }

    render();
  }

  loadBrands();
});
