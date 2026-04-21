document.addEventListener("DOMContentLoaded", () => {
  window.paperly.renderCartCount();
  window.paperly.renderProductGrid({
    container: document.getElementById("newArrivalsProducts"),
    endpoint: "/api/products/?newest_days=3&ordering=-created_at",
    mode: "new",
    loadingText: "Загрузка новинок...",
    emptyText: "За последние 3 дня новинок нет.",
    errorText: "Ошибка загрузки новинок.",
  });
});
