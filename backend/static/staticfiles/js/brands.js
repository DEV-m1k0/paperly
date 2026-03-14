document.addEventListener("DOMContentLoaded", () => {
  const cartCount = document.getElementById("cartCount");
  const brandsGrid = document.getElementById("brandsGrid");
  const brandsEmpty = document.getElementById("brandsEmpty");

  let count = Number(localStorage.getItem("paperly_cart_count") || 0);
  cartCount.textContent = String(count);

  function escapeHtml(value) {
    return String(value)
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#39;");
  }

  function renderBrands(rows) {
    if (!rows.length) {
      brandsGrid.innerHTML = "";
      brandsEmpty.hidden = false;
      return;
    }

    brandsGrid.innerHTML = rows
      .map((brand) => {
        const title = escapeHtml(brand.name || "Бренд");
        const description = escapeHtml(brand.description || "Товары бренда в каталоге");
        const image = brand.logo_url || "https://images.unsplash.com/photo-1503676382389-4809596d5290?auto=format&fit=crop&w=900&q=80";
        const link = `/catalog/?brand=${encodeURIComponent(brand.slug)}`;
        const countText = brand.product_count ? `${brand.product_count} товаров` : "Смотреть товары";

        return `
          <article class="product">
            <img src="${image}" alt="${title}">
            <h3><a href="${link}">${title}</a></h3>
            <p>${description}</p>
            <button class="btn" data-link="${link}">${countText}</button>
          </article>
        `;
      })
      .join("");

    brandsEmpty.hidden = true;
  }

  brandsGrid.addEventListener("click", (event) => {
    const button = event.target.closest(".btn");
    if (!button) return;
    const link = button.dataset.link;
    if (link) {
      window.location.href = link;
    }
  });

  async function loadBrands() {
    try {
      const response = await fetch("/api/brands/");
      if (!response.ok) {
        brandsGrid.innerHTML = "";
        brandsEmpty.hidden = false;
        return;
      }

      const payload = await response.json();
      const rows = Array.isArray(payload) ? payload : payload.results || [];
      renderBrands(rows);
    } catch (error) {
      console.error("Brands API error", error);
      brandsGrid.innerHTML = "";
      brandsEmpty.hidden = false;
    }
  }

  loadBrands();
});
