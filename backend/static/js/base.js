document.addEventListener("DOMContentLoaded", () => {
  const isAuthenticated = document.body?.dataset.isAuthenticated === "true";
  const authUrl = document.body?.dataset.authUrl || "/auth/";
  const userId = document.body?.dataset.userId || "";
  const wishlistCount = document.getElementById("wishlistCount");
  const cartCount = document.getElementById("cartCount");
  const flashes = document.querySelectorAll(".auth-flash .flash");
  const nav = document.getElementById("nav");
  const burger = document.getElementById("burger");

  // --- Функция обновления счётчика избранного с сервера ---
  async function updateFavoritesCount() {
    const favCountSpan = document.getElementById('wishlistCount');
    if (!favCountSpan) return;

    if (!isAuthenticated) {
      favCountSpan.textContent = '0';
      return;
    }

    try {
      const response = await fetch('/api/favorites/', { credentials: 'same-origin' });
      if (!response.ok) {
        favCountSpan.textContent = '0';
        return;
      }
      const data = await response.json();
      const favorites = Array.isArray(data) ? data : data.results || [];
      favCountSpan.textContent = favorites.length;
    } catch (error) {
      console.error('Failed to fetch favorites count', error);
      favCountSpan.textContent = '0';
    }
  }

  // Вызываем при загрузке
  updateFavoritesCount();
  window.updateFavoritesCount = updateFavoritesCount; // делаем глобальной

  // --- Синхронизация пользователя (сброс корзины при смене аккаунта) ---
  if (isAuthenticated && userId) {
    const storedUser = localStorage.getItem("paperly_user_id");
    if (storedUser !== userId) {
      localStorage.setItem("paperly_cart_count", "0");
      localStorage.setItem("paperly_cart_items", "[]");
    }
    localStorage.setItem("paperly_user_id", userId);
  }

  // Инициализация счётчика корзины из localStorage
  if (cartCount) {
    const savedCount = localStorage.getItem("paperly_cart_count");
    cartCount.textContent = savedCount || "0";
  }

  if (flashes.length) {
    flashes.forEach((flash) => {
      setTimeout(() => {
        flash.classList.add("is-hide");
        setTimeout(() => flash.remove(), 220);
      }, 5000);
    });
  }

  burger?.addEventListener("click", () => {
    nav?.classList.toggle("is-open");
    if (typeof window.paperlyUpdateFiltersOffset === "function") {
      setTimeout(() => window.paperlyUpdateFiltersOffset(), 0);
    }
  });

  nav?.querySelectorAll("a").forEach((link) => {
    link.addEventListener("click", () => {
      if (window.innerWidth <= 760) {
        nav.classList.remove("is-open");
      }
    });
  });

  // --- Защита: неавторизованные пользователи не могут добавлять в корзину ---
  document.addEventListener(
    "click",
    (event) => {
      const trigger = event.target.closest("button.add, button.add-to-cart, button.add-btn, #addToCart, .add");
      if (!trigger || isAuthenticated) return;

      event.preventDefault();
      event.stopImmediatePropagation();

      const next = encodeURIComponent(
        `${window.location.pathname}${window.location.search}${window.location.hash}`
      );
      window.location.href = `${authUrl}?next=${next}`;
    },
    true
  );

  // --- Работа с корзиной (localStorage) ---
  function readCartItems() {
    try {
      return JSON.parse(localStorage.getItem("paperly_cart_items") || "[]");
    } catch {
      return [];
    }
  }

  function saveCartItems(items) {
    localStorage.setItem("paperly_cart_items", JSON.stringify(items));
  }

  function updateCartCountDisplay() {
    const items = readCartItems();
    const count = items.reduce((sum, item) => sum + (item.qty || 0), 0);
    localStorage.setItem("paperly_cart_count", String(count));
    if (cartCount) cartCount.textContent = String(count);
    return count;
  }

  function parsePrice(text) {
    const raw = String(text || "");
    const digits = raw.replace(/[^0-9]/g, "");
    return digits ? Number(digits) : 0;
  }

  function addItemFromTrigger(trigger, quantity = 1) {
    const card = trigger.closest(".product, .fav-card") || trigger.closest("article") || document;
    const link = card.querySelector("h3 a, h2 a, a.product__image, a.fav-image");
    const title = trigger.dataset.title || link?.textContent?.trim() || card.querySelector("h3, h2")?.textContent?.trim() || "Товар";
    const priceText = trigger.dataset.price || card.querySelector(".price-stack strong")?.textContent || card.querySelector(".fav-bottom strong")?.textContent || "0";
    const price = Number(trigger.dataset.price) || parsePrice(priceText);
    const desc = trigger.dataset.desc || card.querySelector("p")?.textContent?.trim() || "";
    const image = trigger.dataset.image || card.querySelector("img")?.getAttribute("src") || "";
    let productId = trigger.dataset.productId;
    if (!productId && link?.href) {
      try {
        const url = new URL(link.href, window.location.origin);
        productId = url.searchParams.get("id") || url.searchParams.get("product") || "";
      } catch {
        productId = "";
      }
    }
    const id = productId || title;
    const items = readCartItems();
    const existing = items.find((item) => item.id === id);
    if (existing) {
      existing.qty += quantity;
    } else {
      items.push({ id, title, desc, price, qty: quantity, img: image });
    }
    saveCartItems(items);
    return updateCartCountDisplay();
  }
  window.paperlyAddToCart = addItemFromTrigger;

  // --- Fallback для кнопок корзины, не обработанных в конкретных скриптах ---
  document.addEventListener(
    "click",
    (event) => {
      const trigger = event.target.closest("button.add, button.add-to-cart, button.add-btn, #addToCart, .add");
      if (!trigger || trigger.dataset.cartBound === "true" || event.defaultPrevented) return;
      if (!isAuthenticated) return;

      // Проверяем, есть ли data-атрибут quantity (для страницы товара)
      let quantity = 1;
      if (trigger.id === 'addToCart') {
        const qtyInput = document.getElementById('qtyInput');
        if (qtyInput) quantity = Math.max(1, Number(qtyInput.value) || 1);
      }

      const qty = addItemFromTrigger(trigger, quantity);
      
      const initial = trigger.dataset.cartInitial || trigger.innerHTML;
      trigger.dataset.cartInitial = initial;
      trigger.innerHTML = '<i class="bi bi-check2"></i><span>Добавлено</span>';
      trigger.disabled = true;
      setTimeout(() => {
        trigger.innerHTML = initial;
        trigger.disabled = false;
      }, 900);
    },
    true
  );

  // --- Анимации (AOS) ---
  if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;

  const candidates = Array.from(
    document.querySelectorAll(
      "main > *, main section, main article, .site-footer"
    )
  );

  if (!candidates.length) return;

  const unique = Array.from(new Set(candidates));
  unique.forEach((node) => node.classList.add("aos-item"));
  unique.forEach((node, index) => {
    node.style.transitionDelay = `${Math.min(index * 0.02, 0.16)}s`;
  });

  if (!("IntersectionObserver" in window)) {
    unique.forEach((node) => node.classList.add("is-in-view"));
    return;
  }

  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (!entry.isIntersecting) return;
        entry.target.classList.add("is-in-view");
        observer.unobserve(entry.target);
      });
    },
    { threshold: 0.14, rootMargin: "0px 0px -6% 0px" }
  );

  unique.forEach((node) => observer.observe(node));

  setTimeout(() => {
    unique.forEach((node) => node.classList.add("is-in-view"));
  }, 1200);
});
