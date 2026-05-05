document.addEventListener("DOMContentLoaded", () => {
  const P = window.paperly;
  const searchForm = document.getElementById("searchForm");
  const reveals = document.querySelectorAll(".reveal");

  const homePromotionsProducts = document.getElementById("homePromotionsProducts");
  const homeNewProducts = document.getElementById("homeNewProducts");
  const homeHitProducts = document.getElementById("homeHitProducts");
  const homeBrands = document.getElementById("homeBrands");

  P.renderCartCount();

  function buildBrandCard(brand) {
    const slug = brand.slug || "";
    const name = brand.name || "Бренд";
    const description = brand.description || "Канцелярские товары и аксессуары";
    const logoUrl = brand.logo_url || "";
    const count = Number(brand.product_count || 0);
    const brandLink = `/catalog/?brand=${encodeURIComponent(slug)}`;
    const initial = P.escapeHtml(name.trim().charAt(0).toUpperCase() || "B");
    const plural = count === 1 ? "товар" : (count >= 2 && count <= 4 ? "товара" : "товаров");

    const logoMarkup = logoUrl
      ? `<img src="${logoUrl}" alt="${P.escapeHtml(name)}" loading="lazy">`
      : `<span class="brand-card__initial">${initial}</span>`;

    return `
      <a class="brand-card" href="${brandLink}">
        <div class="brand-card__logo">${logoMarkup}</div>
        <div class="brand-card__body">
          <h3>${P.escapeHtml(name)}</h3>
          <p>${P.escapeHtml(description)}</p>
        </div>
        <div class="brand-card__footer">
          <span class="brand-card__count">${count.toLocaleString("ru-RU")} ${plural}</span>
          <span class="brand-card__arrow" aria-hidden="true"><i class="bi bi-arrow-right"></i></span>
        </div>
      </a>
    `;
  }

  async function loadBrands() {
    if (!homeBrands) return;
    homeBrands.innerHTML = `<p class="empty-state">Загрузка брендов...</p>`;
    try {
      const payload = await P.apiJson("/api/brands/");
      let rows = P.unwrapList(payload).filter((item) => item && item.id);
      if (!rows.length) {
        homeBrands.innerHTML = `<p class="empty-state">Пока нет доступных брендов.</p>`;
        return;
      }
      rows.sort((a, b) => (Number(b.product_count) || 0) - (Number(a.product_count) || 0));
      homeBrands.innerHTML = rows.slice(0, 4).map(buildBrandCard).join("");
    } catch (error) {
      console.error("Home brands API error", error);
      homeBrands.innerHTML = `<p class="empty-state">Ошибка загрузки брендов.</p>`;
    }
  }

  searchForm?.addEventListener("submit", (event) => {
    event.preventDefault();
    const query = searchForm.querySelector("input")?.value.trim();
    if (query) window.location.href = `/catalog/?q=${encodeURIComponent(query)}`;
  });

  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add("is-visible");
          observer.unobserve(entry.target);
        }
      });
    },
    { threshold: 0.2 }
  );
  reveals.forEach((block) => observer.observe(block));

  // --- Sections ---
  const promotionsReady = P.renderProductGrid({
    container: homePromotionsProducts,
    endpoint: "/api/products/?sale=true&ordering=-created_at",
    mode: "promo",
    emptyText: "Сейчас нет активных акций и скидок.",
  });

  P.renderProductGrid({
    container: homeNewProducts,
    endpoint: "/api/products/?newest_days=3&ordering=-created_at",
    fallbackEndpoint: "/api/products/?ordering=-created_at",
    mode: "new",
    limit: 4,
    minItems: 4,
    emptyText: "За последние 3 дня новинок нет.",
  });

  P.renderProductGrid({
    container: homeHitProducts,
    endpoint: "/api/products/?bestseller_days=3&ordering=-sold_recent",
    fallbackEndpoint: "/api/products/?ordering=-sold_recent",
    mode: "hit",
    limit: 4,
    minItems: 4,
    emptyText: "За последние 3 дня хитов продаж нет.",
  });

  loadBrands();

  function initPromoAutoScroll(scrollEl) {
    if (!scrollEl) return;

    const phoneQuery = window.matchMedia?.("(max-width: 520px)");
    const reducedMotion = window.matchMedia?.("(prefers-reduced-motion: reduce)")?.matches;
    let animationFrame = null;
    let lastFrameTime = null;
    let offsetX = 0;
    let loopWidth = 0;
    let trackEl = null;

    function isPhone() {
      return Boolean(phoneQuery?.matches);
    }

    function getOriginalCards() {
      return Array.from(scrollEl.querySelectorAll(".product:not(.is-marquee-clone)"));
    }

    function hasEnoughCards() {
      return getOriginalCards().length > 1;
    }

    function resetCloneBindings(node) {
      node.querySelectorAll("[data-bound], [data-nav-bound]").forEach((element) => {
        delete element.dataset.bound;
        delete element.dataset.navBound;
      });
      delete node.dataset.navBound;
    }

    function teardownTrack() {
      if (!trackEl) {
        loopWidth = 0;
        offsetX = 0;
        return;
      }

      const originals = Array.from(trackEl.querySelectorAll(".product:not(.is-marquee-clone)"));
      scrollEl.innerHTML = "";
      originals.forEach((card) => scrollEl.appendChild(card));
      trackEl = null;
      loopWidth = 0;
      offsetX = 0;
    }

    function setupLoop() {
      teardownTrack();
      if (isPhone() || reducedMotion || !hasEnoughCards()) return;

      const originals = getOriginalCards();
      trackEl = document.createElement("div");
      trackEl.className = "promo-autoscroll__track";
      originals.forEach((card) => {
        trackEl.appendChild(card);
      });

      originals.forEach((card) => {
        const clone = card.cloneNode(true);
        clone.classList.add("is-autoscroll-clone");
        resetCloneBindings(clone);
        trackEl.appendChild(clone);
      });

      scrollEl.innerHTML = "";
      scrollEl.appendChild(trackEl);
      P.bindProductGridActions?.(scrollEl);
      P.syncFavoritesOnCards?.(scrollEl);

      const firstClone = trackEl.querySelector(".is-autoscroll-clone");
      loopWidth = firstClone ? firstClone.offsetLeft : 0;
      offsetX = 0;
      if (trackEl) trackEl.style.transform = "translate3d(0px, 0, 0)";
    }

    function tick(frameTime) {
      if (lastFrameTime === null) lastFrameTime = frameTime;
      const delta = frameTime - lastFrameTime;
      lastFrameTime = frameTime;

      if (!document.hidden && !isPhone() && !reducedMotion && hasEnoughCards()) {
        if (!loopWidth) setupLoop();
        if (loopWidth > 0 && trackEl) {
          offsetX -= delta * 0.045;
          if (Math.abs(offsetX) >= loopWidth) {
            offsetX += loopWidth;
          }
          trackEl.style.transform = `translate3d(${offsetX}px, 0, 0)`;
        }
      }

      animationFrame = window.requestAnimationFrame(tick);
    }

    new ResizeObserver(() => {
      setupLoop();
    }).observe(scrollEl);

    phoneQuery?.addEventListener?.("change", () => {
      lastFrameTime = null;
      setupLoop();
    });

    setupLoop();
    animationFrame = window.requestAnimationFrame(tick);
  }

  promotionsReady.then(() => initPromoAutoScroll(homePromotionsProducts));
});
