document.addEventListener("DOMContentLoaded", () => {
  const P = window.paperly;
  P.renderCartCount?.();

  const productsEl = document.getElementById("bestsellersProducts");
  const emptyEl = document.getElementById("bsEmpty");
  const showAllBtn = document.getElementById("bsShowAll");
  const statCountEl = document.getElementById("bsStatCount");
  const chips = Array.from(document.querySelectorAll(".bs-chip"));

  let currentCategory = "";

  async function loadForCategory(categorySlug) {
    currentCategory = categorySlug;
    chips.forEach((chip) => {
      const isActive = (chip.dataset.category || "") === categorySlug;
      chip.classList.toggle("is-active", isActive);
      chip.setAttribute("aria-selected", isActive ? "true" : "false");
    });

    if (emptyEl) {
      emptyEl.hidden = true;
      emptyEl.classList.remove("is-visible");
    }
    productsEl.innerHTML = `<p class="empty-state">Загружаем хиты продаж...</p>`;

    const params = new URLSearchParams({
      is_hit: "true",
      ordering: "-is_hit,-is_featured,title",
    });
    if (categorySlug) params.set("category", categorySlug);

    const rows = await P.renderProductGrid({
      container: productsEl,
      endpoint: `/api/products/?${params.toString()}`,
      fallbackEndpoint: categorySlug
        ? `/api/products/?category=${encodeURIComponent(categorySlug)}&ordering=-is_hit,title`
        : `/api/products/?ordering=-is_hit,-is_featured,title`,
      mode: "hit",
      loadingText: "Загружаем хиты продаж...",
      emptyText: "",
      errorText: "Ошибка загрузки. Попробуйте обновить страницу.",
    });

    if (statCountEl) statCountEl.textContent = String(rows?.length || 0);

    if (!rows || rows.length === 0) {
      productsEl.innerHTML = "";
      if (emptyEl) {
        emptyEl.hidden = false;
        emptyEl.classList.add("is-visible");
      }
      return;
    }

    decorateTopThree();
  }

  function decorateTopThree() {
    const cards = productsEl.querySelectorAll(".product");
    // Reset previous decoration (when category changes)
    cards.forEach((card) => {
      card.classList.remove("is-top-3");
      card.querySelectorAll(".bs-rank").forEach((n) => n.remove());
    });

    const starSvg = '<svg viewBox="0 0 16 16" fill="currentColor"><path d="M3.612 15.443c-.386.198-.824-.149-.746-.592l.83-4.73L.173 6.765c-.329-.314-.158-.888.283-.95l4.898-.696L7.538.792c.197-.39.73-.39.927 0l2.184 4.327 4.898.696c.441.062.612.636.282.95l-3.522 3.356.83 4.73c.078.443-.36.79-.746.592L8 13.187l-4.389 2.256z"/></svg>';
    const labels = [
      { cls: "bs-rank--1", text: "№1 хит" },
      { cls: "bs-rank--2", text: "№2" },
      { cls: "bs-rank--3", text: "№3" },
    ];
    for (let i = 0; i < Math.min(3, cards.length); i++) {
      const card = cards[i];
      card.classList.add("is-top-3");   // CSS will hide the default .chip
      const badge = document.createElement("span");
      badge.className = `bs-rank ${labels[i].cls}`;
      badge.innerHTML = `${starSvg}${labels[i].text}`;
      card.appendChild(badge);
    }
  }

  chips.forEach((chip) => {
    chip.addEventListener("click", () => {
      const cat = chip.dataset.category || "";
      if (cat !== currentCategory) loadForCategory(cat);
    });
  });

  showAllBtn?.addEventListener("click", () => loadForCategory(""));

  loadForCategory("");
});
