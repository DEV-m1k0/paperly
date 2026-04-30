/*
 * Paperly admin — JS enhancements.
 * Минимум JS: дизайн в CSS. Здесь только UX-полировка и a11y.
 */
(function () {
  "use strict";

  function initAdminEnhancements() {
    localizeSearchPlaceholder();
    enhanceBreadcrumb();
    markPageContext();
    wireStickySubmitRow();
    annotateResponsiveTables();
    hideInlineTemplates();
    polishSidebar();
    wireSidebarAccessibility();
    wireUserDropdown();
    wireMobileDrawer();
    wireFilterPanel();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initAdminEnhancements);
  } else {
    initAdminEnhancements();
  }

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

  function annotateResponsiveTables() {
    annotateTable(document.querySelector("#result_list"));
    document.querySelectorAll(".inline-group .tabular table").forEach(annotateTable);

    document.addEventListener("formset:added", (event) => {
      annotateTable(event.target?.closest?.(".inline-group")?.querySelector(".tabular table"));
      hideInlineTemplates();
    });
  }

  function hideInlineTemplates() {
    document.querySelectorAll(".inline-group .tabular tr.empty-form").forEach((row) => {
      row.hidden = true;
      row.setAttribute("aria-hidden", "true");
    });
  }

  function annotateTable(table) {
    if (!table) return;
    const headers = Array.from(table.querySelectorAll("thead th")).map((cell) => {
      const text = (cell.textContent || "").replace(/\s+/g, " ").trim();
      return text || cell.getAttribute("aria-label") || "";
    });

    table.querySelectorAll("tbody tr").forEach((row) => {
      Array.from(row.children).forEach((cell, index) => {
        if (!(cell instanceof HTMLElement)) return;
        const label = headers[index];
        if (label) {
          cell.setAttribute("data-cell-label", label.replace(/\s*:\s*$/, ""));
        }
      });
    });
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

  function wireUserDropdown() {
    const menu = document.querySelector("#jazzy-usermenu");
    if (!menu) return;

    const dropdown = menu.closest(".dropdown");
    const trigger = dropdown?.querySelector('[data-toggle="dropdown"]');
    if (!dropdown || !trigger) return;

    trigger.setAttribute("aria-haspopup", "true");
    trigger.setAttribute("aria-controls", "jazzy-usermenu");
    menu.setAttribute("role", "menu");

    const setOpen = (open) => {
      dropdown.classList.toggle("show", open);
      trigger.classList.toggle("show", open);
      menu.classList.toggle("show", open);
      trigger.setAttribute("aria-expanded", open ? "true" : "false");

      if (open) {
        menu.style.left = "auto";
        menu.style.right = "0px";
      }
    };

    const isOpen = () => menu.classList.contains("show");

    trigger.addEventListener("click", (event) => {
      event.preventDefault();
      event.stopImmediatePropagation();
      setOpen(!isOpen());
    }, true);

    document.addEventListener("click", (event) => {
      if (!isOpen()) return;
      if (dropdown.contains(event.target)) return;
      setOpen(false);
    }, true);

    document.addEventListener("keydown", (event) => {
      if (event.key !== "Escape") return;
      if (!isOpen()) return;
      setOpen(false);
      trigger.focus();
    });

    menu.addEventListener("click", (event) => {
      const target = event.target.closest("a[href], button[type='submit']");
      if (!target) return;
      setOpen(false);
    });
  }

  // ── Mobile drawer: overlay-div + body-lock + auto-close + focus return ──
  function wireMobileDrawer() {
    const body = document.body;
    const html = document.documentElement;
    const hamburger = document.querySelector('[data-widget="pushmenu"]');
    const sidebar = document.querySelector(".main-sidebar");
    const sidebarScroller = sidebar?.querySelector(".sidebar");
    const mobileMQ = window.matchMedia("(max-width: 991px)");
    let lockedScrollY = 0;
    let sidebarTouchStartY = 0;

    // Создаём кликабельный backdrop (псевдо-элементы не ловят клики).
    // Показывается он CSS-ом при body.sidebar-open — см. admin-custom.css.
    let backdrop = document.querySelector(".sidebar-backdrop");
    if (!backdrop) {
      backdrop = document.createElement("div");
      backdrop.className = "sidebar-backdrop";
      backdrop.setAttribute("aria-hidden", "true");
      body.appendChild(backdrop);
    }

    let closeButton = sidebar?.querySelector("[data-pp-sidebar-close]");
    if (sidebar && !closeButton) {
      closeButton = document.createElement("button");
      closeButton.type = "button";
      closeButton.className = "pp-sidebar-close";
      closeButton.setAttribute("data-pp-sidebar-close", "");
      closeButton.setAttribute("aria-label", "Закрыть боковое меню");
      closeButton.innerHTML = '<span aria-hidden="true">&times;</span>';
      sidebar.appendChild(closeButton);
    }

    function isOpen() {
      return body.classList.contains("sidebar-open");
    }

    function isInteractiveLockActive() {
      return mobileMQ.matches && isOpen();
    }

    function eventInsideSidebar(event) {
      return !!event.target?.closest?.(".main-sidebar");
    }

    function isScrollableElement(element) {
      if (!(element instanceof HTMLElement)) return false;
      const style = window.getComputedStyle(element);
      const overflowY = style.overflowY;
      return (
        (overflowY === "auto" || overflowY === "scroll" || overflowY === "overlay") &&
        element.scrollHeight > element.clientHeight
      );
    }

    function findSidebarScrollContainer(target) {
      if (!sidebar?.contains(target)) return null;
      let current = target instanceof HTMLElement ? target : target?.parentElement;
      while (current && current !== sidebar) {
        if (isScrollableElement(current)) return current;
        current = current.parentElement;
      }
      return isScrollableElement(sidebarScroller) ? sidebarScroller : sidebar;
    }

    function shouldBlockSidebarScroll(container, deltaY) {
      if (!(container instanceof HTMLElement)) return true;
      if (container.scrollHeight <= container.clientHeight) return true;

      const scrollTop = container.scrollTop;
      const maxScrollTop = container.scrollHeight - container.clientHeight;
      const isScrollingUp = deltaY > 0;
      const isScrollingDown = deltaY < 0;

      if (scrollTop <= 0 && isScrollingUp) return true;
      if (scrollTop >= maxScrollTop - 1 && isScrollingDown) return true;
      return false;
    }

    function applySidebarScroll(container, deltaY) {
      if (!(container instanceof HTMLElement)) return;
      const maxScrollTop = Math.max(0, container.scrollHeight - container.clientHeight);
      const nextScrollTop = Math.min(maxScrollTop, Math.max(0, container.scrollTop + deltaY));
      container.scrollTop = nextScrollTop;
    }

    function lockScroll(lock) {
      if (lock) {
        lockedScrollY = window.scrollY || window.pageYOffset || 0;
        const scrollbarWidth = window.innerWidth - document.documentElement.clientWidth;
        body.style.paddingRight = scrollbarWidth > 0 ? `${scrollbarWidth}px` : "";
        body.style.position = "fixed";
        body.style.top = `-${lockedScrollY}px`;
        body.style.left = "0";
        body.style.right = "0";
        body.style.width = "100%";
      } else {
        body.style.paddingRight = "";
        body.style.position = "";
        body.style.top = "";
        body.style.left = "";
        body.style.right = "";
        body.style.width = "";
        window.scrollTo(0, lockedScrollY);
      }
      html.classList.toggle("pp-scroll-locked", !!lock);
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
    backdrop.addEventListener("wheel", (event) => event.preventDefault(), { passive: false });
    backdrop.addEventListener("touchmove", (event) => event.preventDefault(), { passive: false });
    closeButton?.addEventListener("click", () => closeDrawer());

    // Клик по pushmenu-кнопке — после тика актуализируем scroll-lock.
    // Не используем MutationObserver (ловит наш же toggle и уходит в loop).
    if (hamburger) {
      hamburger.addEventListener("click", () => {
        // AdminLTE меняет класс синхронно; оцениваем после microtask.
        queueMicrotask(() => {
          if (!mobileMQ.matches) return;
          lockScroll(isOpen());
          if (isOpen()) {
            closeButton?.focus();
          }
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

    document.addEventListener("touchstart", (event) => {
      if (!isInteractiveLockActive()) return;
      const touch = event.touches?.[0];
      if (!touch) return;
      sidebarTouchStartY = touch.clientY;
    }, { passive: true, capture: true });

    document.addEventListener("touchmove", (event) => {
      if (!isInteractiveLockActive()) return;
      const touch = event.touches?.[0];
      if (!touch) return;
      const deltaY = touch.clientY - sidebarTouchStartY;
      event.preventDefault();
      event.stopPropagation();
      if (eventInsideSidebar(event)) {
        const scrollContainer = findSidebarScrollContainer(event.target);
        if (scrollContainer instanceof HTMLElement && !shouldBlockSidebarScroll(scrollContainer, deltaY)) {
          applySidebarScroll(scrollContainer, -deltaY);
        }
      }
      sidebarTouchStartY = touch.clientY;
    }, { passive: false, capture: true });

    document.addEventListener("wheel", (event) => {
      if (!isInteractiveLockActive()) return;
      event.preventDefault();
      event.stopPropagation();
      if (eventInsideSidebar(event)) {
        const scrollContainer = findSidebarScrollContainer(event.target);
        if (scrollContainer instanceof HTMLElement) {
          applySidebarScroll(scrollContainer, event.deltaY);
        }
      }
    }, { passive: false, capture: true });

    document.addEventListener("focusin", (event) => {
      if (!isInteractiveLockActive()) return;
      if (eventInsideSidebar(event)) return;
      event.stopPropagation();
      closeButton?.focus();
    });

    // Переход в десктоп-брейкпоинт — снимаем scroll-lock, если забыли.
    mobileMQ.addEventListener("change", (e) => { if (!e.matches) lockScroll(false); });
  }

  function wireFilterPanel() {
    const body = document.body;
    const panel = document.querySelector("#pp-filter-panel");
    const toggle = document.querySelector("[data-pp-filter-toggle]");
    const close = document.querySelector("[data-pp-filter-close]");
    const panelBody = panel?.querySelector(".pp-filter-panel__body");
    const mobileMQ = window.matchMedia("(max-width: 991px)");
    let lockedScrollY = 0;
    let panelTouchStartY = 0;

    if (!panel || !toggle) return;

    let backdrop = document.querySelector(".pp-filter-backdrop");
    if (!backdrop) {
      backdrop = document.createElement("div");
      backdrop.className = "pp-filter-backdrop";
      backdrop.setAttribute("aria-hidden", "true");
      body.appendChild(backdrop);
    }

    const isOpen = () => body.classList.contains("pp-filters-open");

    const firstFocusable = () =>
      panel.querySelector("button, [href], input, select, textarea, [tabindex]:not([tabindex='-1'])");

    const isScrollableElement = (element) => {
      if (!(element instanceof HTMLElement)) return false;
      const style = window.getComputedStyle(element);
      const overflowY = style.overflowY;
      return (
        (overflowY === "auto" || overflowY === "scroll" || overflowY === "overlay") &&
        element.scrollHeight > element.clientHeight
      );
    };

    const findPanelScrollContainer = (target) => {
      if (!panel.contains(target)) return null;
      let current = target instanceof HTMLElement ? target : target?.parentElement;
      while (current && current !== panel) {
        if (isScrollableElement(current)) return current;
        current = current.parentElement;
      }
      return isScrollableElement(panelBody) ? panelBody : panel;
    };

    const shouldBlockPanelScroll = (container, deltaY) => {
      if (!(container instanceof HTMLElement)) return true;
      if (container.scrollHeight <= container.clientHeight) return true;

      const scrollTop = container.scrollTop;
      const maxScrollTop = container.scrollHeight - container.clientHeight;
      const isScrollingUp = deltaY > 0;
      const isScrollingDown = deltaY < 0;

      if (scrollTop <= 0 && isScrollingUp) return true;
      if (scrollTop >= maxScrollTop - 1 && isScrollingDown) return true;
      return false;
    };

    const lockScroll = (lock) => {
      if (lock) {
        lockedScrollY = window.scrollY || window.pageYOffset || 0;
        const scrollbarWidth = window.innerWidth - document.documentElement.clientWidth;
        body.style.paddingRight = scrollbarWidth > 0 ? `${scrollbarWidth}px` : "";
        body.style.position = "fixed";
        body.style.top = `-${lockedScrollY}px`;
        body.style.left = "0";
        body.style.right = "0";
        body.style.width = "100%";
      } else {
        body.style.paddingRight = "";
        body.style.position = "";
        body.style.top = "";
        body.style.left = "";
        body.style.right = "";
        body.style.width = "";
        window.scrollTo(0, lockedScrollY);
      }
      document.documentElement.classList.toggle("pp-filters-locked", !!lock);
      body.classList.toggle("pp-filters-locked", !!lock);
    };

    const setState = (open) => {
      body.classList.toggle("pp-filters-open", open);
      toggle.setAttribute("aria-expanded", open ? "true" : "false");
      if (!mobileMQ.matches) return;
      lockScroll(open);
      if (open) {
        firstFocusable()?.focus();
      } else {
        toggle.focus();
      }
    };

    backdrop.addEventListener("click", () => setState(false));
    backdrop.addEventListener("wheel", (event) => event.preventDefault(), { passive: false });
    backdrop.addEventListener("touchmove", (event) => event.preventDefault(), { passive: false });

    toggle.addEventListener("click", () => {
      if (!mobileMQ.matches) return;
      setState(!body.classList.contains("pp-filters-open"));
    });

    close?.addEventListener("click", () => setState(false));

    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape" && body.classList.contains("pp-filters-open")) {
        setState(false);
      }
    });

    mobileMQ.addEventListener("change", (event) => {
      if (!event.matches) {
        setState(false);
      }
    });

    const blockBackgroundInteraction = (event) => {
      if (!mobileMQ.matches || !isOpen()) return;
      if (event.target?.closest?.("#pp-filter-panel")) return;
      event.preventDefault();
    };

    document.addEventListener("wheel", blockBackgroundInteraction, { passive: false });
    document.addEventListener("touchmove", blockBackgroundInteraction, { passive: false });

    panel.addEventListener("touchstart", (event) => {
      if (!mobileMQ.matches || !isOpen()) return;
      const touch = event.touches?.[0];
      if (!touch) return;
      panelTouchStartY = touch.clientY;
    }, { passive: true });

    panel.addEventListener("touchmove", (event) => {
      if (!mobileMQ.matches || !isOpen()) return;
      const touch = event.touches?.[0];
      if (!touch) return;
      const deltaY = touch.clientY - panelTouchStartY;
      const scrollContainer = findPanelScrollContainer(event.target);
      if (shouldBlockPanelScroll(scrollContainer, deltaY)) {
        event.preventDefault();
      }
      panelTouchStartY = touch.clientY;
    }, { passive: false });

    panel.addEventListener("wheel", (event) => {
      if (!mobileMQ.matches || !isOpen()) return;
      const scrollContainer = findPanelScrollContainer(event.target);
      if (shouldBlockPanelScroll(scrollContainer, -event.deltaY)) {
        event.preventDefault();
      }
    }, { passive: false });

    document.addEventListener("focusin", (event) => {
      if (!mobileMQ.matches || !isOpen()) return;
      if (event.target?.closest?.("#pp-filter-panel")) return;
      event.stopPropagation();
      firstFocusable()?.focus();
    });
  }
})();
