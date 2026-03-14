document.addEventListener("DOMContentLoaded", () => {
  const cartCount = document.getElementById("cartCount");
  const searchForm = document.getElementById("searchForm");
  const requestForm = document.getElementById("requestForm");

  const count = Number(localStorage.getItem("paperly_cart_count") || 0);
  cartCount.textContent = String(count);

  searchForm.addEventListener("submit", (event) => {
    event.preventDefault();
    const query = searchForm.querySelector("input")?.value.trim();
    if (query) {
      alert(`Поиск по разделу: ${query}`);
    }
  });

  requestForm.addEventListener("submit", (event) => {
    event.preventDefault();

    const button = requestForm.querySelector("button[type='submit']");
    const initialText = button.textContent;
    button.textContent = "Заявка отправлена";
    button.disabled = true;

    setTimeout(() => {
      button.textContent = initialText;
      button.disabled = false;
      requestForm.reset();
    }, 1400);
  });
});
