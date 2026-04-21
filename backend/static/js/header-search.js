// Header live-search — real-time product lookup with keyboard navigation.
document.addEventListener("DOMContentLoaded", () => {
  const P = window.paperly;
  if (!P) return;

  const input = document.getElementById("siteSearchInput");
  const form = document.getElementById("searchForm");
  const dropdown = document.getElementById("siteSearchDropdown");
  const clearBtn = document.getElementById("siteSearchClear");
  const wrap = document.getElementById("siteSearchWrap");
  if (!input || !dropdown || !wrap) return;

  const MIN_QUERY = 2;
  const DEBOUNCE_MS = 220;
  const MAX_RESULTS = 7;

  const cache = new Map();
  const pendingControllers = new Set();
  let debounceTimer = null;
  let lastQuery = "";
  let activeIndex = -1;
  let currentResults = [];
  let recentQueries = loadRecent();

  function loadRecent() {
    try {
      return JSON.parse(localStorage.getItem("paperly_recent_search") || "[]").slice(0, 5);
    } catch {
      return [];
    }
  }

  function saveRecent(q) {
    if (!q) return;
    const next = [q, ...recentQueries.filter((x) => x.toLowerCase() !== q.toLowerCase())].slice(0, 5);
    recentQueries = next;
    try {
      localStorage.setItem("paperly_recent_search", JSON.stringify(next));
    } catch {}
  }

  function formatPrice(value) {
    return P.formatMoney(value, "Руб.");
  }

  function highlight(text, query) {
    if (!query) return P.escapeHtml(text);
    const escaped = P.escapeHtml(text);
    const re = new RegExp(`(${query.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")})`, "gi");
    return escaped.replace(re, '<mark>$1</mark>');
  }

  function openDropdown() {
    dropdown.hidden = false;
    input.setAttribute("aria-expanded", "true");
    wrap.classList.add("is-open");
  }

  function closeDropdown() {
    dropdown.hidden = true;
    input.setAttribute("aria-expanded", "false");
    wrap.classList.remove("is-open");
    activeIndex = -1;
    input.removeAttribute("aria-activedescendant");
  }

  function setActiveIndex(idx, { scroll = true } = {}) {
    const items = dropdown.querySelectorAll("[data-search-item]");
    if (!items.length) return;
    const maxIdx = items.length - 1;
    if (idx < 0) idx = maxIdx;
    if (idx > maxIdx) idx = 0;
    items.forEach((item, i) => {
      item.classList.toggle("is-active", i === idx);
      if (i === idx) {
        input.setAttribute("aria-activedescendant", item.id);
        if (scroll) item.scrollIntoView({ block: "nearest" });
      }
    });
    activeIndex = idx;
  }

  function renderState(kind, data = {}) {
    const query = data.query || "";
    const catalogHref = query ? `/catalog/?q=${encodeURIComponent(query)}` : "/catalog/";

    if (kind === "loading") {
      dropdown.innerHTML = `
        <div class="site-search-dropdown__state">
          <span class="site-search-spinner" aria-hidden="true"></span>
          <span>Ищем...</span>
        </div>
      `;
      return;
    }

    if (kind === "empty") {
      dropdown.innerHTML = `
        <div class="site-search-dropdown__state site-search-dropdown__state--empty">
          <i class="bi bi-search" aria-hidden="true"></i>
          <div>
            <strong>Ничего не найдено</strong>
            <p>Попробуйте другое слово или посмотрите весь каталог.</p>
          </div>
          <a class="site-search-dropdown__cta" href="${catalogHref}">
            <i class="bi bi-grid" aria-hidden="true"></i>
            <span>Открыть каталог</span>
          </a>
        </div>
      `;
      return;
    }

    if (kind === "recent") {
      if (!recentQueries.length) {
        dropdown.innerHTML = `
          <div class="site-search-dropdown__state site-search-dropdown__state--hint">
            <i class="bi bi-keyboard" aria-hidden="true"></i>
            <div>
              <strong>Начните печатать</strong>
              <p>Введите минимум ${MIN_QUERY} символа для поиска товара.</p>
            </div>
          </div>
        `;
        return;
      }
      const items = recentQueries.map((q, i) => `
        <button type="button" class="site-search-recent" data-search-recent="${P.escapeHtml(q)}" data-search-item id="search-recent-${i}" role="option">
          <i class="bi bi-clock-history" aria-hidden="true"></i>
          <span>${P.escapeHtml(q)}</span>
          <i class="bi bi-arrow-up-left site-search-recent__go" aria-hidden="true"></i>
        </button>
      `).join("");
      dropdown.innerHTML = `
        <div class="site-search-dropdown__section">
          <header class="site-search-dropdown__head">
            <span>Недавние запросы</span>
            <button type="button" class="site-search-dropdown__clear" id="searchClearRecent">Очистить</button>
          </header>
          <div class="site-search-recent-list">${items}</div>
        </div>
      `;
      return;
    }

    if (kind === "results") {
      const { query, results, total } = data;
      const itemsHtml = results.map((p, i) => {
        const imgHtml = p.image
          ? `<img src="${p.image}" alt="${P.escapeHtml(p.title)}" loading="lazy">`
          : `<div class="site-search-item__placeholder"><i class="bi bi-bag"></i></div>`;
        const brand = p.brand ? `<span class="site-search-item__brand">${P.escapeHtml(p.brand)}</span>` : "";
        const oldPrice = p.old_price && Number(p.old_price) > Number(p.price)
          ? `<span class="site-search-item__old">${formatPrice(p.old_price)}</span>`
          : "";
        const stock = Number(p.stock || 0) > 0
          ? `<span class="site-search-item__stock is-in">В наличии</span>`
          : `<span class="site-search-item__stock is-out">Под заказ</span>`;
        return `
          <a class="site-search-item" href="/product/?id=${p.id}" data-search-item id="search-item-${i}" role="option">
            <div class="site-search-item__image">${imgHtml}</div>
            <div class="site-search-item__info">
              ${brand}
              <strong>${highlight(p.title, query)}</strong>
              <div class="site-search-item__meta">
                <span class="site-search-item__price">${formatPrice(p.price)}</span>
                ${oldPrice}
                ${stock}
              </div>
            </div>
            <i class="bi bi-arrow-up-right site-search-item__arrow" aria-hidden="true"></i>
          </a>
        `;
      }).join("");

      const more = total > results.length ? total - results.length : 0;
      const moreLabel = more > 0 ? ` ещё ${more}` : "";

      dropdown.innerHTML = `
        <div class="site-search-dropdown__section">
          <header class="site-search-dropdown__head">
            <span>Товары</span>
            <span class="site-search-dropdown__total">${total} ${pluralNoun(total, "результат", "результата", "результатов")}</span>
          </header>
          <div class="site-search-results">${itemsHtml}</div>
        </div>
        <a class="site-search-dropdown__footer" href="${catalogHref}">
          <span>Показать все${moreLabel} в каталоге</span>
          <i class="bi bi-arrow-right" aria-hidden="true"></i>
        </a>
      `;
    }
  }

  function pluralNoun(n, one, few, many) {
    const mod10 = n % 10, mod100 = n % 100;
    if (mod100 < 10 || mod100 >= 20) {
      if (mod10 === 1) return one;
      if (mod10 >= 2 && mod10 <= 4) return few;
    }
    return many;
  }

  function rankResults(list, query) {
    const q = query.toLowerCase();
    return [...list].sort((a, b) => {
      const aTitle = (a.title || "").toLowerCase();
      const bTitle = (b.title || "").toLowerCase();
      const aStartsWith = aTitle.startsWith(q) ? 0 : aTitle.includes(q) ? 1 : 2;
      const bStartsWith = bTitle.startsWith(q) ? 0 : bTitle.includes(q) ? 1 : 2;
      if (aStartsWith !== bStartsWith) return aStartsWith - bStartsWith;
      const aStock = Number(a.stock || 0) > 0 ? 0 : 1;
      const bStock = Number(b.stock || 0) > 0 ? 0 : 1;
      if (aStock !== bStock) return aStock - bStock;
      return aTitle.localeCompare(bTitle, "ru");
    });
  }

  function extract(product) {
    return {
      id: product.id,
      title: product.title || "",
      brand: product.brand_name || "",
      price: Number(product.price || 0),
      old_price: product.old_price ? Number(product.old_price) : null,
      image: product.images?.[0]?.image_url || "",
      stock: Number(product.stock || 0),
    };
  }

  async function search(query) {
    if (cache.has(query)) {
      const cached = cache.get(query);
      currentResults = cached.results;
      renderState("results", { query, results: cached.results, total: cached.total });
      openDropdown();
      return;
    }

    pendingControllers.forEach((c) => c.abort());
    pendingControllers.clear();
    const controller = new AbortController();
    pendingControllers.add(controller);

    renderState("loading");
    openDropdown();

    try {
      const url = `/api/products/?search=${encodeURIComponent(query)}&status=active&page_size=${MAX_RESULTS}`;
      const response = await fetch(url, { signal: controller.signal, credentials: "same-origin" });
      pendingControllers.delete(controller);
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const payload = await response.json();
      const rows = Array.isArray(payload) ? payload : payload.results || [];
      const total = payload.count ?? rows.length;
      const extracted = rows.slice(0, MAX_RESULTS).map(extract);
      const ranked = rankResults(extracted, query);

      cache.set(query, { results: ranked, total });
      // Limit cache size
      if (cache.size > 40) {
        const oldest = cache.keys().next().value;
        cache.delete(oldest);
      }

      currentResults = ranked;
      if (!ranked.length) {
        renderState("empty", { query });
      } else {
        renderState("results", { query, results: ranked, total });
        setActiveIndex(-1, { scroll: false });
      }
      openDropdown();
    } catch (error) {
      if (error.name === "AbortError") return;
      console.error("Header search error", error);
      renderState("empty", { query });
    }
  }

  // ────────── Event handlers ──────────
  input.addEventListener("input", () => {
    const q = input.value.trim();
    clearBtn.hidden = !q;
    lastQuery = q;
    clearTimeout(debounceTimer);

    if (q.length < MIN_QUERY) {
      if (q.length === 0) {
        renderState("recent");
        openDropdown();
      } else {
        closeDropdown();
      }
      return;
    }

    debounceTimer = setTimeout(() => search(q), DEBOUNCE_MS);
  });

  input.addEventListener("focus", () => {
    const q = input.value.trim();
    if (q.length === 0) {
      renderState("recent");
      openDropdown();
    } else if (q.length >= MIN_QUERY) {
      const cached = cache.get(q);
      if (cached) {
        renderState("results", { query: q, results: cached.results, total: cached.total });
      } else {
        renderState("loading");
      }
      openDropdown();
    }
  });

  input.addEventListener("keydown", (event) => {
    if (event.key === "ArrowDown") {
      event.preventDefault();
      if (dropdown.hidden) {
        if (input.value.trim().length === 0) renderState("recent");
        openDropdown();
      }
      setActiveIndex(activeIndex + 1);
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      if (dropdown.hidden) return;
      setActiveIndex(activeIndex - 1);
    } else if (event.key === "Enter") {
      const items = dropdown.querySelectorAll("[data-search-item]");
      if (!dropdown.hidden && activeIndex >= 0 && items[activeIndex]) {
        event.preventDefault();
        items[activeIndex].click();
        return;
      }
      // Fallback: submit form → /catalog/?q=
      if (input.value.trim()) saveRecent(input.value.trim());
    } else if (event.key === "Escape") {
      if (!dropdown.hidden) {
        event.preventDefault();
        closeDropdown();
        input.blur();
      }
    }
  });

  clearBtn?.addEventListener("click", () => {
    input.value = "";
    clearBtn.hidden = true;
    renderState("recent");
    openDropdown();
    input.focus();
  });

  dropdown.addEventListener("mousemove", (event) => {
    const item = event.target.closest("[data-search-item]");
    if (!item) return;
    const items = [...dropdown.querySelectorAll("[data-search-item]")];
    const idx = items.indexOf(item);
    if (idx >= 0 && idx !== activeIndex) setActiveIndex(idx, { scroll: false });
  });

  dropdown.addEventListener("click", (event) => {
    const recentBtn = event.target.closest("[data-search-recent]");
    if (recentBtn) {
      event.preventDefault();
      input.value = recentBtn.dataset.searchRecent;
      search(input.value.trim());
      clearBtn.hidden = false;
      return;
    }
    const clearRecent = event.target.closest("#searchClearRecent");
    if (clearRecent) {
      event.preventDefault();
      recentQueries = [];
      try { localStorage.removeItem("paperly_recent_search"); } catch {}
      renderState("recent");
      return;
    }
    const searchItem = event.target.closest(".site-search-item");
    if (searchItem) {
      saveRecent(input.value.trim());
    }
  });

  form.addEventListener("submit", (event) => {
    const q = input.value.trim();
    if (!q) {
      event.preventDefault();
      return;
    }
    saveRecent(q);
    // native submit to /catalog/?q= — browser navigates
  });

  document.addEventListener("click", (event) => {
    if (!wrap.contains(event.target)) closeDropdown();
  });

  // Keyboard shortcut: "/" focuses search (unless typing in other input)
  document.addEventListener("keydown", (event) => {
    if (event.key !== "/" || event.ctrlKey || event.metaKey || event.altKey) return;
    const tag = (document.activeElement?.tagName || "").toLowerCase();
    if (tag === "input" || tag === "textarea" || tag === "select") return;
    event.preventDefault();
    input.focus();
    input.select();
  });
});
