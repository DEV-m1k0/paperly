document.addEventListener("DOMContentLoaded", () => {
  const cartCount = document.getElementById("cartCount");
  const searchForm = document.getElementById("searchForm");
  const tabs = document.querySelectorAll(".tab");
  const panels = document.querySelectorAll(".tab-panel");
  const faqButtons = document.querySelectorAll(".faq-question");

  const count = Number(localStorage.getItem("paperly_cart_count") || 0);
  cartCount.textContent = String(count);

  searchForm.addEventListener("submit", (event) => {
    event.preventDefault();
    const query = searchForm.querySelector("input")?.value.trim();
    if (query) {
      alert(`Поиск: ${query}`);
    }
  });

  tabs.forEach((tab) => {
    tab.addEventListener("click", () => {
      tabs.forEach((item) => item.classList.remove("is-active"));
      panels.forEach((panel) => panel.classList.remove("is-active"));

      tab.classList.add("is-active");
      document.getElementById(tab.dataset.tab)?.classList.add("is-active");
    });
  });

  faqButtons.forEach((button) => {
    button.addEventListener("click", () => {
      const item = button.closest(".faq-item");
      const isOpen = item.classList.contains("is-open");
      item.classList.toggle("is-open", !isOpen);
      button.setAttribute("aria-expanded", String(!isOpen));
    });
  });
});
