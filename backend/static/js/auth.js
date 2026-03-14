document.addEventListener("DOMContentLoaded", () => {
  const cartCount = document.getElementById("cartCount");
  const searchForm = document.getElementById("searchForm");
  const tabs = document.querySelectorAll(".tab");
  const panels = document.querySelectorAll(".panel");

  const count = Number(localStorage.getItem("paperly_cart_count") || 0);
  cartCount.textContent = String(count);

  const params = new URLSearchParams(window.location.search);
  const mode = params.get("mode");
  if (mode && ["login", "register", "restore"].includes(mode)) {
    activateTab(mode);
  }

  tabs.forEach((tab) => {
    tab.addEventListener("click", () => {
      const tabId = tab.dataset.tab;
      activateTab(tabId);
      const url = new URL(window.location.href);
      if (tabId) {
        url.searchParams.set("mode", tabId);
      } else {
        url.searchParams.delete("mode");
      }
      window.history.replaceState({}, "", url.toString());
    });
  });

  function activateTab(id) {
    tabs.forEach((tab) => tab.classList.toggle("is-active", tab.dataset.tab === id));
    panels.forEach((panel) => panel.classList.toggle("is-active", panel.id === id));
  }

  searchForm?.addEventListener("submit", (event) => {
    event.preventDefault();
    const query = searchForm.querySelector("input")?.value.trim();
    if (query) {
      window.location.href = `/catalog/?q=${encodeURIComponent(query)}`;
    }
  });

});
