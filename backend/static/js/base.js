document.addEventListener("DOMContentLoaded", () => {
  const P = window.paperly;
  const isAuthenticated = document.body?.dataset.isAuthenticated === "true";
  const authUrl = document.body?.dataset.authUrl || "/auth/";
  const userId = document.body?.dataset.userId || "";
  const flashes = document.querySelectorAll(".auth-flash .flash");
  const nav = document.getElementById("nav");
  const burger = document.getElementById("burger");

  // --- Счётчик избранного ---
  P.updateFavoritesCount();

  // --- Сброс корзины при смене пользователя ---
  if (isAuthenticated && userId) {
    const storedUser = localStorage.getItem("paperly_user_id");
    if (storedUser && storedUser !== userId) {
      P.clearCart();
    }
    localStorage.setItem("paperly_user_id", userId);
  }

  // --- Счётчик корзины ---
  P.renderCartCount();

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

  // Guests могут добавлять товары в корзину и избранное без аккаунта —
  // создание аккаунта предлагается на шаге оформления заказа.
  // Если был localStorage-избранного гостя, мёрджим его на сервер после логина.
  if (isAuthenticated) {
    P.mergeLocalFavoritesToServer?.();
  }

  // --- Извлечение данных товара из карточки ---
  function parsePrice(text) {
    const digits = String(text || "").replace(/[^0-9]/g, "");
    return digits ? Number(digits) : 0;
  }

  function productFromTrigger(trigger) {
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
    // Лимит максимального кол-ва в заказе. На product-page кладём на кнопку
    // сами, в гриде берём с карточки (data-product-max-qty). 0 = без лимита.
    const maxQtyRaw = trigger.dataset.maxQty ?? card.dataset?.productMaxQty ?? "0";
    const maxQty = Math.max(0, Number(maxQtyRaw) || 0);
    return {
      id: productId || title,
      title,
      desc,
      price,
      img: image,
      maxQty,
    };
  }

  function addItemFromTrigger(trigger, quantity = 1) {
    const product = productFromTrigger(trigger);
    return P.addCartItem(product, quantity);
  }
  window.paperlyAddToCart = addItemFromTrigger;

  // --- Fallback для кнопок корзины ---
  document.addEventListener(
    "click",
    (event) => {
      const trigger = event.target.closest("button.add, button.add-to-cart, button.add-btn, #addToCart, .add");
      if (!trigger || trigger.dataset.cartBound === "true" || event.defaultPrevented) return;

      // Keep the click from bubbling to the surrounding card (which would
      // navigate to the product page) or to any wrapping anchor.
      event.preventDefault();
      event.stopPropagation();

      let quantity = 1;
      if (trigger.id === "addToCart") {
        const qtyInput = document.getElementById("qtyInput");
        if (qtyInput) quantity = Math.max(1, Number(qtyInput.value) || 1);
      }

      addItemFromTrigger(trigger, quantity);

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

  // --- Footer newsletter subscription ---
  const subscribeForm = document.getElementById("footerSubscribeForm");
  const subscribeStatus = document.getElementById("footerSubscribeStatus");
  if (subscribeForm) {
    subscribeForm.addEventListener("submit", async (event) => {
      event.preventDefault();
      const input = subscribeForm.querySelector('input[type="email"]');
      const submitBtn = subscribeForm.querySelector("button[type='submit']");
      const email = (input?.value || "").trim();
      if (!email) return;

      if (subscribeStatus) {
        subscribeStatus.hidden = false;
        subscribeStatus.className = "site-footer__status is-pending";
        subscribeStatus.textContent = "Отправляем...";
      }
      if (submitBtn) submitBtn.disabled = true;

      try {
        const response = await P.apiFetch("/api/newsletter/subscribe/", {
          method: "POST",
          body: { email, source: "footer" },
        });
        const data = await response.json().catch(() => ({}));
        if (response.ok) {
          if (subscribeStatus) {
            subscribeStatus.className = "site-footer__status is-success";
            subscribeStatus.textContent = data.message || "Готово — проверьте почту!";
          }
          subscribeForm.reset();
        } else {
          const fieldError = Array.isArray(data.email) ? data.email[0] : null;
          const msg = fieldError || data.detail || data.message || "Не удалось подписаться. Попробуйте позже.";
          if (subscribeStatus) {
            subscribeStatus.className = "site-footer__status is-error";
            subscribeStatus.textContent = msg;
          }
        }
      } catch (err) {
        if (subscribeStatus) {
          subscribeStatus.className = "site-footer__status is-error";
          subscribeStatus.textContent = "Сетевая ошибка. Проверьте подключение.";
        }
      } finally {
        if (submitBtn) submitBtn.disabled = false;
      }
    });
  }

  // --- Animations on scroll ---
  if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;

  const candidates = Array.from(
    document.querySelectorAll("main > *, main section, main article, .site-footer")
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

  // --- Flatpickr ---
  if (typeof flatpickr !== "undefined") {
    document.querySelectorAll('input[type="date"]').forEach((input) => {
      flatpickr(input, {
        locale: typeof flatpickr.l10ns?.ru !== "undefined" ? "ru" : "default",
        dateFormat: "Y-m-d",
        altInput: true,
        altFormat: "j F Y",
        allowInput: true,
        disableMobile: true,
        monthSelectorType: "dropdown",
        prevArrow: '<svg width="14" height="14" viewBox="0 0 16 16"><path d="M11.354 1.646a.5.5 0 0 1 0 .708L5.707 8l5.647 5.646a.5.5 0 0 1-.708.708l-6-6a.5.5 0 0 1 0-.708l6-6a.5.5 0 0 1 .708 0z" fill="currentColor"/></svg>',
        nextArrow: '<svg width="14" height="14" viewBox="0 0 16 16"><path d="M4.646 1.646a.5.5 0 0 1 .708 0l6 6a.5.5 0 0 1 0 .708l-6 6a.5.5 0 0 1-.708-.708L10.293 8 4.646 2.354a.5.5 0 0 1 0-.708z" fill="currentColor"/></svg>',
      });
    });
  }

  // --- Choices.js ---
  if (typeof Choices !== "undefined") {
    document.querySelectorAll("select:not(.no-choices)").forEach((select) => {
      new Choices(select, {
        searchEnabled: select.options.length > 6,
        searchPlaceholderValue: "Поиск...",
        itemSelectText: "",
        noResultsText: "Ничего не найдено",
        noChoicesText: "Нет вариантов",
        shouldSort: false,
        allowHTML: false,
      });
    });
  }
});

// Global helper for back-compat
window.updateFavoritesCount = () => window.paperly?.updateFavoritesCount?.();
