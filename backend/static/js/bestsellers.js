document.addEventListener("DOMContentLoaded", () => {
  window.paperly.renderCartCount();
  window.paperly.renderProductGrid({
    container: document.getElementById("bestsellersProducts"),
    endpoint: "/api/products/?bestseller_days=3&ordering=-sold_recent",
    mode: "hit",
    loadingText: "Загрузка хитов продаж...",
    emptyText: "За последние 3 дня продаж не было.",
    errorText: "Ошибка загрузки хитов.",
  });
});
