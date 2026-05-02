document.addEventListener("DOMContentLoaded", () => {
  const P = window.paperly;
  const { escapeHtml, formatPurpose, apiJson, unwrapList, renderStars } = P;

  // --- DOM refs ---
  const openFilters = document.getElementById("openFilters");
  const closeFilters = document.getElementById("closeFilters");
  const filtersPanel = document.getElementById("filtersPanel");
  const sortSelect = document.getElementById("sortSelect");
  const applyFilters = document.getElementById("applyFilters");
  const applyCountText = document.getElementById("applyCountText");
  const resetFilters = document.getElementById("resetFilters");
  const productsGrid = document.getElementById("productsGrid");
  const dynamicFilters = document.getElementById("dynamicFilters");
  const resultsCount = document.getElementById("resultsCount");
  const filtersSummary = document.getElementById("filtersSummary");
  const activeChipsEl = document.getElementById("activeChips");
  const searchForm = document.getElementById("searchForm");

  // --- State ---
  let schema = [];               // filter schema from API
  let products = [];
  let previewCount = 0;          // count for "Показать (N)"
  const LABEL_MAP = new Map();   // `${queryParam}:${value}` -> label
  let applyTimer = null;
  const CATALOG_PAGE_SIZE = 100;

  P.renderCartCount();

  function updateFiltersOffset() {
    const header = document.querySelector(".site-header");
    if (!header) return;
    const height = Math.ceil(header.getBoundingClientRect().height);
    document.documentElement.style.setProperty("--filters-offset", `${Math.max(80, height + 12)}px`);
  }
  window.paperlyUpdateFiltersOffset = updateFiltersOffset;

  const SORT_MAP = {
    popular: "-sold_recent",
    "price-asc": "price",
    "price-desc": "-price",
    name: "title",
  };

  // --- URL & param helpers ---
  function currentUrlParams() {
    return new URLSearchParams(window.location.search);
  }

  function getQueryValues(key) {
    const raw = currentUrlParams().get(key) || "";
    return raw.split(",").map((v) => v.trim()).filter(Boolean);
  }

  function setQueryValues(key, values) {
    const params = currentUrlParams();
    if (!values || !values.length) params.delete(key);
    else params.set(key, values.join(","));
    const next = params.toString();
    window.history.replaceState(null, "", next ? `?${next}` : window.location.pathname);
  }

  function removeQueryKey(key) {
    const params = currentUrlParams();
    params.delete(key);
    const next = params.toString();
    window.history.replaceState(null, "", next ? `?${next}` : window.location.pathname);
  }

  // --- Read current filter state from URL (not DOM) ---
  function readActiveFilters() {
    const result = [];
    for (const group of schema) {
      if (group.type === "range") {
        const minKey = group.min_query_param;
        const maxKey = group.max_query_param;
        const min = currentUrlParams().get(minKey);
        const max = currentUrlParams().get(maxKey);
        if (min || max) {
          const label = [
            min ? `от ${Number(min).toLocaleString("ru-RU")} ₽` : "",
            max ? `до ${Number(max).toLocaleString("ru-RU")} ₽` : "",
          ].filter(Boolean).join(" ");
          result.push({
            key: `${minKey}+${maxKey}`,
            label: `${group.title}: ${label}`,
            remove: () => { removeQueryKey(minKey); removeQueryKey(maxKey); },
          });
        }
      } else if (group.type === "toggle-group") {
        for (const opt of group.options || []) {
          const values = getQueryValues(opt.query_param);
          if (values.includes(String(opt.value))) {
            result.push({
              key: `${opt.query_param}=${opt.value}`,
              label: opt.label,
              remove: () => {
                const next = values.filter((v) => v !== String(opt.value));
                setQueryValues(opt.query_param, next);
              },
            });
          }
        }
      } else {
        const values = getQueryValues(group.query_param);
        for (const v of values) {
          const label = LABEL_MAP.get(`${group.query_param}:${v}`) || v;
          result.push({
            key: `${group.query_param}=${v}`,
            label: `${group.title}: ${label}`,
            remove: () => {
              const next = getQueryValues(group.query_param).filter((x) => x !== v);
              setQueryValues(group.query_param, next);
            },
          });
        }
      }
    }
    return result;
  }

  function countActiveFor(group) {
    if (group.type === "range") {
      const min = currentUrlParams().get(group.min_query_param);
      const max = currentUrlParams().get(group.max_query_param);
      return (min ? 1 : 0) + (max ? 1 : 0);
    }
    if (group.type === "toggle-group") {
      return (group.options || []).filter((opt) =>
        getQueryValues(opt.query_param).includes(String(opt.value))
      ).length;
    }
    return getQueryValues(group.query_param).length;
  }

  // --- Render filter panel ---
  function renderCheckboxGroup(group) {
    const selected = new Set(getQueryValues(group.query_param));
    const isSearchable = group.searchable || (group.options || []).length > 10;
    const searchMarkup = isSearchable
      ? `<input type="search" class="filter-search" placeholder="Поиск..." data-filter-search>`
      : "";
    const optionsMarkup = (group.options || [])
      .map((opt) => {
        const checked = selected.has(String(opt.value)) ? "checked" : "";
        return `
          <label class="filter-option">
            <input type="checkbox" data-query-param="${escapeHtml(group.query_param)}" value="${escapeHtml(opt.value)}" ${checked}>
            <span class="filter-option__label">${escapeHtml(opt.label)}</span>
          </label>
        `;
      })
      .join("");
    return `<div class="filter-options">${searchMarkup}<div class="filter-options__list">${optionsMarkup || '<p class="filter-empty">Нет вариантов</p>'}</div></div>`;
  }

  function renderToggleGroup(group) {
    const items = (group.options || [])
      .map((opt) => {
        const checked = getQueryValues(opt.query_param).includes(String(opt.value)) ? "checked" : "";
        const icon = opt.icon ? `<i class="bi bi-${escapeHtml(opt.icon)}" aria-hidden="true"></i>` : "";
        return `
          <label class="filter-toggle">
            <input type="checkbox" data-query-param="${escapeHtml(opt.query_param)}" value="${escapeHtml(opt.value)}" ${checked}>
            <span class="filter-toggle__body">${icon}<span>${escapeHtml(opt.label)}</span></span>
          </label>
        `;
      })
      .join("");
    return `<div class="filter-toggles">${items}</div>`;
  }

  function renderRangeGroup(group) {
    const min = currentUrlParams().get(group.min_query_param) || "";
    const max = currentUrlParams().get(group.max_query_param) || "";
    return `
      <div class="filter-range">
        <div class="filter-range__hint">от ${Number(group.min || 0).toLocaleString("ru-RU")} до ${Number(group.max || 0).toLocaleString("ru-RU")} ₽</div>
        <div class="filter-range__inputs">
          <label>
            <span class="visually-hidden">Цена от</span>
            <input type="number" inputmode="numeric" placeholder="От" min="${group.min || 0}" max="${group.max || 0}" step="${group.step || 10}"
              data-range-param="${escapeHtml(group.min_query_param)}" value="${escapeHtml(min)}">
          </label>
          <span class="filter-range__dash" aria-hidden="true">—</span>
          <label>
            <span class="visually-hidden">Цена до</span>
            <input type="number" inputmode="numeric" placeholder="До" min="${group.min || 0}" max="${group.max || 0}" step="${group.step || 10}"
              data-range-param="${escapeHtml(group.max_query_param)}" value="${escapeHtml(max)}">
          </label>
        </div>
      </div>
    `;
  }

  function renderGroup(group, index) {
    const activeCount = countActiveFor(group);
    const countBadge = activeCount ? `<span class="filter-count">${activeCount}</span>` : "";
    const icon = group.icon ? `<i class="bi bi-${escapeHtml(group.icon)}" aria-hidden="true"></i>` : "";
    let body = "";
    if (group.type === "range") body = renderRangeGroup(group);
    else if (group.type === "toggle-group") body = renderToggleGroup(group);
    else body = renderCheckboxGroup(group);

    const open = activeCount > 0 || index < 3 ? "open" : "";
    return `
      <details class="filter-group" data-group-key="${escapeHtml(group.key)}" ${open}>
        <summary>
          <span class="filter-group__title">${icon}<span>${escapeHtml(group.title)}</span></span>
          <span class="filter-group__aside">${countBadge}<i class="bi bi-chevron-down filter-group__caret" aria-hidden="true"></i></span>
        </summary>
        ${body}
      </details>
    `;
  }

  // --- Build LABEL_MAP for chip display ---
  function rebuildLabelMap() {
    LABEL_MAP.clear();
    for (const group of schema) {
      if (group.type === "checkbox" && group.query_param) {
        for (const opt of group.options || []) {
          LABEL_MAP.set(`${group.query_param}:${opt.value}`, opt.label);
        }
      } else if (group.type === "toggle-group") {
        for (const opt of group.options || []) {
          LABEL_MAP.set(`${opt.query_param}:${opt.value}`, opt.label);
        }
      }
    }
  }

  // --- Active chips bar ---
  function renderActiveChips() {
    const filters = readActiveFilters();
    if (!filters.length) {
      activeChipsEl.hidden = true;
      activeChipsEl.innerHTML = "";
      return;
    }
    activeChipsEl.hidden = false;
    activeChipsEl.innerHTML = filters
      .map((f, i) => `
        <button type="button" class="active-chip" data-chip-index="${i}">
          <span>${escapeHtml(f.label)}</span>
          <i class="bi bi-x-lg" aria-hidden="true"></i>
        </button>
      `)
      .join("") + `<button type="button" class="active-chip active-chip--clear" id="clearAllChips">
        <i class="bi bi-eraser" aria-hidden="true"></i> <span>Сбросить всё</span>
      </button>`;

    activeChipsEl.querySelectorAll(".active-chip[data-chip-index]").forEach((btn) => {
      btn.addEventListener("click", () => {
        const idx = Number(btn.dataset.chipIndex);
        const current = readActiveFilters();
        current[idx]?.remove();
        renderAll();
        scheduleApply(0);
      });
    });
    document.getElementById("clearAllChips")?.addEventListener("click", () => {
      resetAllFilters();
    });
  }

  // --- Summary text in panel head ---
  function renderSummary() {
    const count = readActiveFilters().length;
    const toggleCount = document.getElementById("filtersToggleCount");
    if (!count) {
      filtersSummary.hidden = true;
      resetFilters.hidden = true;
      if (toggleCount) toggleCount.hidden = true;
      return;
    }
    const plural = count === 1 ? "фильтр" : count < 5 ? "фильтра" : "фильтров";
    filtersSummary.textContent = `${count} ${plural} активно`;
    filtersSummary.hidden = false;
    resetFilters.hidden = false;
    if (toggleCount) {
      toggleCount.textContent = String(count);
      toggleCount.hidden = false;
    }
  }

  // --- Build API URL from current URL params + sort ---
  function buildApiUrl() {
    const url = new URL("/api/products/", window.location.origin);
    const params = currentUrlParams();
    url.searchParams.set("page_size", String(CATALOG_PAGE_SIZE));

    const q = params.get("q");
    if (q) url.searchParams.set("search", q);

    const selectedSort = sortSelect?.value || params.get("ordering") || "popular";
    const ordering = SORT_MAP[selectedSort] || selectedSort;
    if (ordering) url.searchParams.set("ordering", ordering);

    // Forward all params except meta ones (q, ordering, page).
    const skipKeys = new Set(["q", "ordering", "page"]);
    for (const [key, value] of params.entries()) {
      if (skipKeys.has(key)) continue;
      if (!value) continue;
      url.searchParams.set(key, value);
    }
    return url;
  }

  // --- Apply with debounce, preview count while typing price ---
  function scheduleApply(delay = 350) {
    clearTimeout(applyTimer);
    applyTimer = setTimeout(loadProducts, delay);
  }

  // --- Filter inputs wired once on each render (panel rebuilt on state change) ---
  function bindFilterControls() {
    // Checkbox & toggle inputs (use data-query-param)
    dynamicFilters.querySelectorAll("input[type='checkbox'][data-query-param]").forEach((input) => {
      input.addEventListener("change", () => {
        const key = input.dataset.queryParam;
        const value = input.value;
        const current = getQueryValues(key);
        const next = input.checked
          ? (current.includes(value) ? current : [...current, value])
          : current.filter((v) => v !== value);
        setQueryValues(key, next);
        renderSummary();
        renderActiveChips();
        updateSectionCounts();
        scheduleApply();
      });
    });

    // Range inputs
    dynamicFilters.querySelectorAll("input[data-range-param]").forEach((input) => {
      input.addEventListener("input", () => {
        const key = input.dataset.rangeParam;
        const value = input.value.trim();
        setQueryValues(key, value ? [value] : []);
        renderSummary();
        renderActiveChips();
        updateSectionCounts();
        scheduleApply(600);
      });
    });

    // Brand search-within-filter
    dynamicFilters.querySelectorAll("input[data-filter-search]").forEach((input) => {
      input.addEventListener("input", () => {
        const q = input.value.trim().toLowerCase();
        const list = input.nextElementSibling;
        list?.querySelectorAll(".filter-option").forEach((label) => {
          const text = label.textContent.toLowerCase();
          label.style.display = !q || text.includes(q) ? "" : "none";
        });
      });
    });
  }

  function updateSectionCounts() {
    // Update per-group count badges without re-rendering the whole panel
    dynamicFilters.querySelectorAll("details[data-group-key]").forEach((details) => {
      const group = schema.find((g) => g.key === details.dataset.groupKey);
      if (!group) return;
      const activeCount = countActiveFor(group);
      const aside = details.querySelector(".filter-group__aside");
      if (!aside) return;
      const existing = aside.querySelector(".filter-count");
      if (activeCount) {
        if (existing) existing.textContent = String(activeCount);
        else aside.insertAdjacentHTML("afterbegin", `<span class="filter-count">${activeCount}</span>`);
      } else if (existing) {
        existing.remove();
      }
    });
  }

  function renderAll() {
    dynamicFilters.innerHTML = schema.map(renderGroup).join("");
    bindFilterControls();
    renderSummary();
    renderActiveChips();
  }

  function resetAllFilters() {
    // Drop all keys except q/ordering
    const params = currentUrlParams();
    const preserved = ["q"];
    const next = new URLSearchParams();
    for (const key of preserved) {
      const v = params.get(key);
      if (v) next.set(key, v);
    }
    const str = next.toString();
    window.history.replaceState(null, "", str ? `?${str}` : window.location.pathname);
    if (sortSelect) sortSelect.value = "popular";
    renderAll();
    loadProducts();
  }

  // --- Products load ---
  function renderEmptyState({ title, message, reset }) {
    productsGrid.innerHTML = `
      <div class="state-empty catalog-empty">
        <div class="state-empty__visual" aria-hidden="true">
          <span class="state-empty__orb state-empty__orb--a"></span>
          <span class="state-empty__orb state-empty__orb--b"></span>
          <div class="state-empty__icon"><i class="bi bi-funnel"></i></div>
        </div>
        <h2>${escapeHtml(title)}</h2>
        <p>${escapeHtml(message)}</p>
        <div class="state-empty__actions">
          ${reset ? `<button type="button" class="btn btn--primary" id="catalogEmptyReset">
            <i class="bi bi-arrow-counterclockwise" aria-hidden="true"></i>
            <span>Сбросить фильтры</span>
          </button>` : ""}
          <a class="btn btn--ghost" href="/">
            <i class="bi bi-house" aria-hidden="true"></i>
            <span>На главную</span>
          </a>
        </div>
      </div>
    `;
    if (reset) {
      document.getElementById("catalogEmptyReset")?.addEventListener("click", resetAllFilters);
    }
  }

  async function loadProducts() {
    try {
      const url = buildApiUrl();
      const payload = await apiJson(url.toString()).catch((err) => {
        console.error("Products API error", err);
        return null;
      });
      if (!payload) {
        renderEmptyState({
          title: "Не удалось загрузить каталог",
          message: "Проверьте соединение или попробуйте обновить страницу.",
          reset: false,
        });
        resultsCount.textContent = "Найдено: 0 товаров";
        previewCount = 0;
        updateApplyBtn();
        return;
      }
      const rows = unwrapList(payload);
      previewCount = payload.count ?? rows.length;
      updateApplyBtn();

      if (!rows.length) {
        const hasFilters = readActiveFilters().length > 0;
        renderEmptyState({
          title: hasFilters ? "По вашему запросу ничего не найдено" : "Пока нет доступных товаров",
          message: hasFilters
            ? "Попробуйте ослабить фильтры или сбросить их полностью."
            : "Мы уже работаем над наполнением каталога.",
          reset: hasFilters,
        });
        resultsCount.textContent = "Найдено: 0 товаров";
        products = [];
        return;
      }

      productsGrid.innerHTML = rows.map(buildProductCard).join("");
      products = Array.from(productsGrid.querySelectorAll(".product"));
      bindProductCardActions();
      syncFavoritesOnCards();
      resultsCount.textContent = `Найдено: ${formatNoun(previewCount, "товар", "товара", "товаров")}`;
    } catch (error) {
      console.error("Catalog load error", error);
      renderEmptyState({
        title: "Ошибка загрузки каталога",
        message: "Попробуйте обновить страницу.",
        reset: false,
      });
    }
  }

  function formatNoun(n, one, few, many) {
    const mod10 = n % 10;
    const mod100 = n % 100;
    let form = many;
    if (mod100 < 10 || mod100 >= 20) {
      if (mod10 === 1) form = one;
      else if (mod10 >= 2 && mod10 <= 4) form = few;
    }
    return `${n} ${form}`;
  }

  function updateApplyBtn() {
    if (!applyCountText) return;
    applyCountText.textContent = previewCount ? `(${previewCount})` : "";
  }

  // --- Product card rendering (reuse product-grid helpers) ---
  function buildProductCard(product) {
    if (P.buildProductCard) return P.buildProductCard(product, { mode: "hit", moneySuffix: "Руб." });

    // Fallback minimal
    const image = product.images?.[0]?.image_url || "";
    return `<article class="product" data-product-id="${product.id}">
      <a class="product__image" href="/product/?id=${product.id}"><img src="${image}" alt=""></a>
      <h3><a href="/product/?id=${product.id}">${escapeHtml(product.title)}</a></h3>
      <div class="product__bottom">
        <strong>${Number(product.price).toLocaleString("ru-RU")} Руб.</strong>
        <button class="add"><i class="bi bi-bag-plus"></i><span>В корзину</span></button>
      </div>
    </article>`;
  }

  function bindProductCardActions() {
    if (P.bindProductGridActions) P.bindProductGridActions(productsGrid);
  }
  function syncFavoritesOnCards() {
    if (P.syncFavoritesOnCards) P.syncFavoritesOnCards(productsGrid);
  }

  // --- Load schema, then render & fetch products ---
  async function init() {
    try {
      const payload = await apiJson("/api/catalog-filters/");
      schema = unwrapList(payload);
    } catch (error) {
      console.error("Filters schema error", error);
      dynamicFilters.innerHTML = `<p class="filter-empty">Не удалось загрузить фильтры</p>`;
      schema = [];
    }
    rebuildLabelMap();
    renderAll();
    await loadProducts();
  }

  // --- Wiring top-level controls ---
  openFilters?.addEventListener("click", () => {
    filtersPanel.classList.add("is-open");
    document.body.classList.add("filters-locked");
  });

  function closeFilterPanel() {
    filtersPanel.classList.remove("is-open");
    document.body.classList.remove("filters-locked");
  }

  closeFilters?.addEventListener("click", closeFilterPanel);
  document.addEventListener("click", (event) => {
    if (event.target.closest("#closeFilters")) closeFilterPanel();
    if (document.body.classList.contains("filters-locked") && !event.target.closest("#filtersPanel") && !event.target.closest("#openFilters")) {
      closeFilterPanel();
    }
  });
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && document.body.classList.contains("filters-locked")) closeFilterPanel();
  });

  applyFilters?.addEventListener("click", () => {
    clearTimeout(applyTimer);
    loadProducts();
    if (window.innerWidth <= 1040) {
      closeFilterPanel();
    }
  });

  resetFilters?.addEventListener("click", resetAllFilters);

  sortSelect?.addEventListener("change", () => {
    setQueryValues("ordering", sortSelect.value ? [sortSelect.value] : []);
    loadProducts();
  });

  searchForm?.addEventListener("submit", (event) => {
    event.preventDefault();
    const query = searchForm.querySelector("input")?.value.trim();
    if (query) window.location.href = `/catalog/?q=${encodeURIComponent(query)}`;
  });

  // Restore sort from URL
  const sortFromUrl = currentUrlParams().get("ordering");
  if (sortFromUrl && sortSelect) {
    const matched = Object.entries(SORT_MAP).find(([k, v]) => v === sortFromUrl)?.[0];
    if (matched) sortSelect.value = matched;
  }

  updateFiltersOffset();
  window.addEventListener("resize", updateFiltersOffset);
  init();
});
