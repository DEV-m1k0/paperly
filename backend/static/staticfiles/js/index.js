document.addEventListener("DOMContentLoaded", () => {
  const nav = document.getElementById("nav");
  const burger = document.getElementById("burger");
  const cartCount = document.getElementById("cartCount");
  const searchForm = document.getElementById("searchForm");
  const reveals = document.querySelectorAll(".reveal");

  const homePromotionsProducts = document.getElementById("homePromotionsProducts");
  const homeNewProducts = document.getElementById("homeNewProducts");
  const homeHitProducts = document.getElementById("homeHitProducts");
  const homeBrands = document.getElementById("homeBrands");

  const sections = [
    {
      container: homePromotionsProducts,
      url: "/api/products/?sale=true&ordering=-created_at",
      mode: "promo",
      limit: null,
      emptyText: "Сейчас нет активных акций и скидок.",
    },
    {
      container: homeNewProducts,
      url: "/api/products/?newest_days=3&ordering=-created_at",
      mode: "new",
      limit: 4,
      emptyText: "За последние 3 дня новинок нет.",
    },
    {
      container: homeHitProducts,
      url: "/api/products/?bestseller_days=3&ordering=-sold_recent",
      mode: "hit",
      limit: 4,
      emptyText: "За последние 3 дня хитов продаж нет.",
    },
  ];

  let count = Number(localStorage.getItem("paperly_cart_count") || 0);
  if (cartCount) {
    cartCount.textContent = String(count);
  }

  function escapeHtml(value) {
    return String(value || "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#39;");
  }

  function formatMoney(value) {
    const num = Number(value || 0);
    return `${num.toLocaleString("ru-RU")} ₽`;
  }

  function formatCount(value) {
    const num = Number(value || 0);
    return `${num.toLocaleString("ru-RU")} товаров`;
  }

  function parseRows(payload) {
    return Array.isArray(payload) ? payload : payload?.results || [];
  }

  function buildBrandCard(brand) {
    const slug = brand.slug || "";
    const name = brand.name || "Бренд";
    const description = brand.description || "Канцелярские товары и аксессуары";
    const imageUrl =
      brand.logo_url ||
      "https://images.unsplash.com/photo-1452860606245-08befc0ff44b?auto=format&fit=crop&w=900&q=80";
    const count = brand.product_count || 0;
    const brandLink = `/catalog/?brand=${encodeURIComponent(slug)}`;

    return `
      <article class="product-card">
        <a class="product-card__image" href="${brandLink}">
          <span class="tag tag--on-image">BRAND</span>
          <img src="${imageUrl}" alt="${escapeHtml(name)}">
        </a>
        <h3><a href="${brandLink}">${escapeHtml(name)}</a></h3>
        <p>${escapeHtml(description)}</p>
        <div class="product-card__bottom">
          <strong>${formatCount(count)}</strong>
          <a class="brand-link" href="${brandLink}">Смотреть</a>
        </div>
      </article>
    `;
  }

  function mapTypeFromProduct(product) {
    const categorySlug = String(product.category_slugs?.[0] || "").toLowerCase();
    const title = String(product.title || "").toLowerCase();

    if (categorySlug.includes("notebook") || categorySlug.includes("tetrad") || title.includes("тетрад")) return "notebook";
    if (categorySlug.includes("diary") || categorySlug.includes("planner") || title.includes("ежедневник") || title.includes("планер")) return "diary";
    if (categorySlug.includes("paper") || title.includes("бумаг")) return "paper";
    if (categorySlug.includes("pen") || categorySlug.includes("writing") || title.includes("ручк") || title.includes("карандаш")) return "pen";
    if (categorySlug.includes("marker") || categorySlug.includes("art") || title.includes("маркер") || title.includes("текстовыдел")) return "marker";

    return "notebook";
  }

  function renderStars(rating) {
    const full = Math.round(Number(rating));
    return Array.from({ length: 5 }, (_, index) => `<i class="bi ${index < full ? "bi-star-fill" : "bi-star"}"></i>`).join("");
  }

  function getPrimaryImage(product) {
    return product.images?.[0]?.image_url || "https://images.unsplash.com/photo-1503676382389-4809596d5290?auto=format&fit=crop&w=900&q=80";
  }

  function getDiscountPercent(product) {
    const price = Number(product.price || 0);
    const oldPrice = Number(product.old_price || 0);
    if (oldPrice > price && oldPrice > 0) {
      return Math.round(((oldPrice - price) / oldPrice) * 100);
    }

    const promotionDiscount = Number(product.active_promotion_discount || 0);
    if (promotionDiscount > 0) {
      return promotionDiscount;
    }

    return 0;
  }

  function getChip(product, mode, discountPercent) {
    if (mode === "promo") {
      if (discountPercent > 0) {
        return { text: `-${discountPercent}%`, className: "chip chip--discount" };
      }
      return { text: "Акция", className: "chip" };
    }

    if (mode === "new") {
      return { text: "Новинка", className: "chip" };
    }

    return { text: "Хит", className: "chip" };
  }

  function buildCard(product, index, mode) {
    const targetUrl = `/product/?id=${product.id}`;
    const firstImage = getPrimaryImage(product);
    const type = mapTypeFromProduct(product);
    const price = Number(product.price || 0);
    const oldPrice = product.old_price ? Number(product.old_price) : null;
    const hasDiscount = Number(oldPrice) > Number(price);
    const discountPercent = getDiscountPercent(product);
    const chip = getChip(product, mode, discountPercent);
    const rating = (4.6 + ((product.id % 4) * 0.1)).toFixed(1);
    const stockText = Number(product.stock || 0) > 0 ? "Есть на складе" : "Под заказ";
    const oldPriceMarkup = hasDiscount ? `<span class="product__old">${formatMoney(oldPrice)}</span>` : "";
    const discountMarkup = discountPercent > 0 ? `<span class="discount-pill">-${discountPercent}%</span>` : "";

    return `
      <article class="product" data-type="${type}" data-brand="${product.brand_slug || ""}" data-stock="${Number(product.stock || 0) > 0 ? "in_stock" : "out_stock"}" data-flag-new="${product.is_new ? "true" : "false"}" data-flag-hit="${product.is_hit ? "true" : "false"}" data-flag-featured="${product.is_featured ? "true" : "false"}" data-flag-discount="${hasDiscount ? "true" : "false"}" data-format="${product.format || "other"}" data-sheets="${product.sheets_count || ""}" data-purpose="${product.purpose || "universal"}" data-price="${price}">
        <span class="${chip.className}">${chip.text}</span>
        <button class="fav-btn" aria-label="Добавить в избранное"><i class="bi bi-heart"></i></button>
        <a class="product__image" href="${targetUrl}">
          <img src="${firstImage}" alt="${escapeHtml(product.title)}">
        </a>
        <div class="product__meta">
          <span class="rating-stars" aria-label="Рейтинг ${rating} из 5">${renderStars(rating)}</span>
          <span class="meta-score">${rating}</span>
          <span class="meta-stock">${stockText}</span>
        </div>
        <h3><a href="${targetUrl}">${escapeHtml(product.title)}</a></h3>
        <p>${escapeHtml(product.short_description || "Товар из каталога")}</p>
        <div class="product__bottom">
          <div class="price-stack${hasDiscount ? " has-discount" : ""}">
            <strong>${formatMoney(price)}</strong>
            ${oldPriceMarkup}
          </div>
          <button class="add" type="button"><i class="bi bi-bag-plus"></i><span>В корзину</span></button>
        </div>
      </article>
    `;
  }

  function bindActions(container) {
    container.querySelectorAll(".add").forEach((button) => {
      button.dataset.cartBound = "true";
      if (button.dataset.bound === "true") return;
      button.dataset.bound = "true";

      button.addEventListener("click", () => {
      button.addEventListener("click", () => {
        if (typeof window.paperlyAddToCart === "function") {
          count = window.paperlyAddToCart(button);
        } else {
          count += 1;
        }
        if (cartCount) {
          cartCount.textContent = String(count);
        }
        localStorage.setItem("paperly_cart_count", String(count));

        const initialHtml = button.innerHTML;
        button.innerHTML = `<i class="bi bi-check2"></i><span>Добавлено</span>`;
        button.disabled = true;
        setTimeout(() => {
          button.innerHTML = initialHtml;
          button.disabled = false;
        }, 900);
      });
      });
    });

    container.querySelectorAll(".fav-btn").forEach((button) => {
      if (button.dataset.bound === "true") return;
      button.dataset.bound = "true";

      button.addEventListener("click", () => {
        button.classList.toggle("is-active");
        const icon = button.querySelector("i");
        if (icon) {
          icon.classList.toggle("bi-heart");
          icon.classList.toggle("bi-heart-fill");
        }
      });
    });

    container.querySelectorAll(".product").forEach((card) => {
      if (card.dataset.navBound === "true") return;
      card.dataset.navBound = "true";

      card.addEventListener("click", (event) => {
        if (event.target.closest("a, button, input, select, textarea, label")) {
          return;
        }

        const link = card.querySelector("h3 a") || card.querySelector(".product__image");
        if (link?.href) {
          window.location.href = link.href;
        }
      });
    });
  }

  async function loadSection(section) {
    if (!section.container) return;

    section.container.innerHTML = `<p class="empty-state">Загрузка товаров...</p>`;

    try {
      const response = await fetch(section.url);
      if (!response.ok) {
        section.container.innerHTML = `<p class="empty-state">Не удалось загрузить товары.</p>`;
        return;
      }

      let rows = parseRows(await response.json()).filter((item) => item && item.id);
      if (typeof section.limit === "number") {
        rows = rows.slice(0, section.limit);
      }

      if (!rows.length) {
        section.container.innerHTML = `<p class="empty-state">${section.emptyText}</p>`;
        return;
      }

      section.container.innerHTML = rows.map((product, index) => buildCard(product, index, section.mode)).join("");
      bindActions(section.container);
    } catch (error) {
      console.error("Home section API error", error);
      section.container.innerHTML = `<p class="empty-state">Ошибка загрузки товаров.</p>`;
    }
  }

  async function loadBrands() {
    if (!homeBrands) return;

    homeBrands.innerHTML = `<p class="empty-state">Загрузка брендов...</p>`;

    try {
      const response = await fetch("/api/brands/");
      if (!response.ok) {
        homeBrands.innerHTML = `<p class="empty-state">Не удалось загрузить бренды.</p>`;
        return;
      }

      let rows = parseRows(await response.json());
      rows = rows.filter((item) => item && item.id);

      if (!rows.length) {
        homeBrands.innerHTML = `<p class="empty-state">Пока нет доступных брендов.</p>`;
        return;
      }

      rows = rows.sort((a, b) => (Number(b.product_count) || 0) - (Number(a.product_count) || 0));
      homeBrands.innerHTML = rows.slice(0, 4).map(buildBrandCard).join("");
    } catch (error) {
      console.error("Home brands API error", error);
      homeBrands.innerHTML = `<p class="empty-state">Ошибка загрузки брендов.</p>`;
    }
  }

  searchForm?.addEventListener("submit", (event) => {
    event.preventDefault();
    const query = searchForm.querySelector("input")?.value.trim();
    if (query) {
      window.location.href = `/catalog/?q=${encodeURIComponent(query)}`;
    }
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

  sections.forEach((section) => {
    loadSection(section);
  });

  loadBrands();
});



