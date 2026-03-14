document.addEventListener("DOMContentLoaded", () => {
  const cartCount = document.getElementById("cartCount");
  let count = Number(localStorage.getItem("paperly_cart_count") || 0);
  if (cartCount) {
    cartCount.textContent = String(count);
  }

  document.querySelectorAll(".add-btn").forEach((button) => {
    button.dataset.cartBound = "true";
    button.addEventListener("click", () => {
      count += 1;
      if (cartCount) {
        cartCount.textContent = String(count);
      }
      localStorage.setItem("paperly_cart_count", String(count));
      const initial = button.textContent;
      button.textContent = "Добавлено";
      button.disabled = true;
      setTimeout(() => {
        button.textContent = initial;
        button.disabled = false;
      }, 900);
    });
  });
});
