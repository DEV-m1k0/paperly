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
  P.renderProductGrid({
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
    emptyText: "За последние 3 дня новинок нет.",
  });

  P.renderProductGrid({
    container: homeHitProducts,
    endpoint: "/api/products/?bestseller_days=3&ordering=-sold_recent",
    fallbackEndpoint: "/api/products/?ordering=-sold_recent",
    mode: "hit",
    limit: 4,
    emptyText: "За последние 3 дня хитов продаж нет.",
  });

  loadBrands();

  // --- Slider arrows ---
  function initSliderArrows(scrollEl, prevBtn, nextBtn) {
    if (!scrollEl || !prevBtn || !nextBtn) return;

    function updateButtons() {
      const atStart = scrollEl.scrollLeft <= 4;
      const atEnd = scrollEl.scrollLeft + scrollEl.clientWidth >= scrollEl.scrollWidth - 4;
      prevBtn.disabled = atStart;
      nextBtn.disabled = atEnd;
    }

    function getScrollStep() {
      const card = scrollEl.querySelector(".product");
      return card ? card.offsetWidth + 14 : Math.round(scrollEl.clientWidth * 0.8);
    }

    prevBtn.addEventListener("click", () => scrollEl.scrollBy({ left: -getScrollStep(), behavior: "smooth" }));
    nextBtn.addEventListener("click", () => scrollEl.scrollBy({ left: getScrollStep(), behavior: "smooth" }));
    scrollEl.addEventListener("scroll", updateButtons, { passive: true });
    new ResizeObserver(updateButtons).observe(scrollEl);
    updateButtons();
  }

  initSliderArrows(
    homePromotionsProducts,
    document.getElementById("promoScrollPrev"),
    document.getElementById("promoScrollNext")
  );
});
