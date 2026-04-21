document.addEventListener("DOMContentLoaded", () => {
  window.paperly.renderCartCount();
  window.paperly.renderProductGrid({
    container: document.getElementById("promotionsProducts"),
    endpoint: "/api/products/?sale=true&ordering=-created_at",
    mode: "promo",
    loadingText: "Загрузка акционных товаров...",
    emptyText: "Сейчас нет активных скидок и акций.",
    errorText: "Ошибка загрузки акций.",
    filter: (item) => {
      const price = Number(item.price || 0);
      const oldPrice = Number(item.old_price || 0);
      const hasOldDiscount = oldPrice > price && oldPrice > 0;
      const promoDiscount = Number(item.active_promotion_discount || 0);
      return hasOldDiscount || promoDiscount > 0;
    },
  });
});
