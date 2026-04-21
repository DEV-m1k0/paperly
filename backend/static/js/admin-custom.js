/*
 * Paperly admin — JS enhancements.
 * Минимум JS: дизайн в CSS. Здесь только мелочи UX.
 */
(function () {
  "use strict";

  document.addEventListener("DOMContentLoaded", () => {
    localizeSearchPlaceholder();
    enhanceBreadcrumb();
    markPageContext();
    wireStickySubmitRow();
    polishSidebar();
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

  function polishSidebar() {
    const activeLink = document.querySelector(".nav-sidebar .nav-link.active");
    if (!activeLink) return;
    let parent = activeLink.closest(".nav-item.has-treeview");
    while (parent) {
      parent.classList.add("menu-open");
      parent = parent.parentElement?.closest(".nav-item.has-treeview");
    }
  }
})();
