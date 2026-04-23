/*
 * Paperly admin — JS enhancements.
 * Минимум JS: дизайн в CSS. Здесь только UX-полировка и a11y.
 */
(function () {
  "use strict";

  document.addEventListener("DOMContentLoaded", () => {
    localizeSearchPlaceholder();
    enhanceBreadcrumb();
    markPageContext();
    wireStickySubmitRow();
    polishSidebar();
    wireSidebarAccessibility();
    wireMobileDrawer();
  });

  function localizeSearchPlaceholder() {
    document.querySelectorAll("#searchbar").forEach((input) => {
      if (!input.placeholder) input.placeholder = "Поиск по списку...";
    });
    const topSearch = document.querySelector(".navbar-search input");
    if (topSearch && !topSearch.placeholder) topSearch.placeholder = "Быстрый поиск...";
  }

  function enhanceBreadcrumb() {
    document.querySelectorAll(".breadcrumb").forEach((crumb) => {
      const items = crumb.querySelectorAll(".breadcrumb-item");
      if (items.length) items[items.length - 1].classList.add("active");
    });
  }

  function markPageContext() {
    const body = document.body;
    const path = location.pathname;
    if (document.querySelector("#result_list")) body.classList.add("pp-changelist");
    if (document.querySelector(".submit-row")) body.classList.add("pp-changeform");
    if (path.endsWith("/add/")) body.classList.add("pp-addform");
    if (body.classList.contains("login") || path.includes("/login/")) body.classList.add("pp-login");
    if (body.classList.contains("dashboard") || path.endsWith("/admin/")) body.classList.add("pp-dashboard");
  }

  function wireStickySubmitRow() {
    const submitRow = document.querySelector(".submit-row");
    if (!submitRow) return;
    const observer = new IntersectionObserver(
      ([entry]) => submitRow.classList.toggle("is-floating", !entry.isIntersecting),
      { rootMargin: "0px 0px -40px 0px", threshold: 1 },
    );
    const sentinel = document.createElement("div");
    sentinel.style.height = "1px";
    submitRow.parentNode?.insertBefore(sentinel, submitRow);
    observer.observe(sentinel);
  }

  // ── Sidebar: подсветка активного предка ──
  function polishSidebar() {
    const activeLink = document.querySelector(".nav-sidebar .nav-link.active");
    if (!activeLink) return;
    activeLink.setAttribute("aria-current", "page");
    let parent = activeLink.closest(".nav-item.has-treeview");
    while (parent) {
      parent.classList.add("menu-open", "has-active-child");
      // Визуальный маркер на «родителе» активного пункта — парный стилю
      // в admin-custom.css: ссылка-родитель получает теньевой underline.
      parent = parent.parentElement?.closest(".nav-item.has-treeview");
    }
  }

  // ── Sidebar: a11y-атрибуты и синхронизация aria-expanded ──
  function wireSidebarAccessibility() {
    // Hamburger-кнопка в navbar — aria-label "Меню навигации"
    const hamburger = document.querySelector('[data-widget="pushmenu"]');
    if (hamburger && !hamburger.getAttribute("aria-label")) {
      hamburger.setAttribute("aria-label", "Переключить боковое меню");
      hamburger.setAttribute("aria-controls", "jazzy-sidebar");
    }

    // aria-expanded на раскрываемых группах синхронизируем при каждом
    // toggle (AdminLTE кидает класс .menu-open на .nav-item).
    const expandables = document.querySelectorAll(".main-sidebar .nav-item.has-treeview > .nav-link");
    const syncAria = () => {
      expandables.forEach((link) => {
        const open = link.parentElement.classList.contains("menu-open");
        link.setAttribute("aria-expanded", open ? "true" : "false");
      });
    };
    syncAria();

    // MutationObserver ловит открытие/закрытие: AdminLTE меняет классы
    // на .nav-item. Одного observer'а достаточно на весь sidebar.
    const sb = document.querySelector(".main-sidebar");
    if (sb) {
      const mo = new MutationObserver(syncAria);
      mo.observe(sb, { attributes: true, attributeFilter: ["class"], subtree: true });
    }
  }

  // ── Mobile drawer: overlay-div + body-lock + auto-close + focus return ──
  function wireMobileDrawer() {
    const body = document.body;
    const hamburger = document.querySelector('[data-widget="pushmenu"]');
    const mobileMQ = window.matchMedia("(max-width: 991px)");

    // Создаём кликабельный backdrop (псевдо-элементы не ловят клики).
    // Показывается он CSS-ом при body.sidebar-open — см. admin-custom.css.
    let backdrop = document.querySelector(".sidebar-backdrop");
    if (!backdrop) {
      backdrop = document.createElement("div");
      backdrop.className = "sidebar-backdrop";
      backdrop.setAttribute("aria-hidden", "true");
      body.appendChild(backdrop);
    }

    function isOpen() {
      return body.classList.contains("sidebar-open");
    }

    function lockScroll(lock) {
      body.classList.toggle("pp-scroll-locked", !!lock);
    }

    function closeDrawer({ restoreFocus = true } = {}) {
      if (!mobileMQ.matches) return;
      if (!isOpen()) return;
      // AdminLTE сам снимает sidebar-open при .click() по pushmenu —
      // используем его как источник истины, чтобы не рассинхрониться.
      if (hamburger) hamburger.click();
      lockScroll(false);
      if (restoreFocus && hamburger) hamburger.focus();
    }

    // Клик по backdrop закрывает drawer
    backdrop.addEventListener("click", () => closeDrawer());

    // Клик по pushmenu-кнопке — после тика актуализируем scroll-lock.
    // Не используем MutationObserver (ловит наш же toggle и уходит в loop).
    if (hamburger) {
      hamburger.addEventListener("click", () => {
        // AdminLTE меняет класс синхронно; оцениваем после microtask.
        queueMicrotask(() => {
          if (mobileMQ.matches) lockScroll(isOpen());
        });
      });
    }

    // Закрывать drawer при переходе по ссылке внутри sidebar'а — UX ожидание на мобиле.
    // Делегирование, чтобы не перебиндить на каждую ссылку (+ отсутствие
    // привязок к ссылкам, добавленным динамически).
    document.addEventListener("click", (event) => {
      if (!mobileMQ.matches) return;
      if (!isOpen()) return;
      const link = event.target.closest(".main-sidebar a[href]");
      if (!link) return;
      const href = link.getAttribute("href");
      if (!href || href === "#" || href.startsWith("javascript:")) return;
      // Не трогаем фокус: пользователь уже ушёл на новую страницу.
      setTimeout(() => closeDrawer({ restoreFocus: false }), 10);
    });

    // Esc — закрыть drawer с возвратом фокуса на hamburger.
    document.addEventListener("keydown", (event) => {
      if (event.key !== "Escape") return;
      if (!mobileMQ.matches) return;
      if (!isOpen()) return;
      event.stopPropagation();
      closeDrawer();
    });

    // Переход в десктоп-брейкпоинт — снимаем scroll-lock, если забыли.
    mobileMQ.addEventListener("change", (e) => { if (!e.matches) lockScroll(false); });
  }
})();
