document.addEventListener("DOMContentLoaded", () => {
  const cartCount = document.getElementById("cartCount");
  const blogGrid = document.getElementById("blogGrid");
  const blogEmpty = document.getElementById("blogEmpty");
  const blogDetail = document.getElementById("blogDetail");
  const blogDetailTitle = document.getElementById("blogDetailTitle");
  const blogDetailContent = document.getElementById("blogDetailContent");
  const blogDetailMeta = document.getElementById("blogDetailMeta");
  const blogDetailCover = document.getElementById("blogDetailCover");
  const blogBack = document.getElementById("blogBack");

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

  function formatDate(value) {
    if (!value) return "";
    const date = new Date(value);
    return date.toLocaleDateString("ru-RU", {
      day: "numeric",
      month: "long",
      year: "numeric",
    });
  }

  function renderPosts(rows) {
    if (!rows.length) {
      blogGrid.innerHTML = "";
      blogEmpty.hidden = false;
      return;
    }

    blogGrid.innerHTML = rows
      .map((post) => {
        const title = escapeHtml(post.title || "Статья");
        const excerpt = escapeHtml(post.excerpt || post.content || "").slice(0, 180);
        const date = formatDate(post.published_at || post.created_at);
        const badge = date ? `<span class="promo-card__meta">${date}</span>` : "";
        const link = `/blog/?slug=${encodeURIComponent(post.slug)}`;

        return `
          <article class="promo-card">
            ${badge}
            <h2><a href="${link}">${title}</a></h2>
            <p>${excerpt || "Полезные материалы для выбора канцелярии."}</p>
            <a href="${link}">Читать статью</a>
          </article>
        `;
      })
      .join("");

    blogEmpty.hidden = true;
  }

  function renderDetail(post) {
    blogGrid.hidden = true;
    blogEmpty.hidden = true;
    blogDetail.hidden = false;
    blogBack.hidden = false;

    blogDetailTitle.textContent = post.title || "";
    const date = formatDate(post.published_at || post.created_at);
    blogDetailMeta.textContent = date ? `Опубликовано ${date}` : "";

    if (post.cover_url) {
      blogDetailCover.style.backgroundImage = `url('${post.cover_url}')`;
      blogDetailCover.hidden = false;
    } else {
      blogDetailCover.hidden = true;
    }

    const content = escapeHtml(post.content || post.excerpt || "");
    blogDetailContent.innerHTML = content
      .split(/\n\n+/)
      .map((para) => `<p>${para.replace(/\n/g, "<br>")}</p>`)
      .join("");
  }

  async function loadList() {
    try {
      const response = await fetch("/api/blog/");
      if (!response.ok) {
        blogGrid.innerHTML = "";
        blogEmpty.hidden = false;
        return [];
      }

      const payload = await response.json();
      return Array.isArray(payload) ? payload : payload.results || [];
    } catch (error) {
      console.error("Blog API error", error);
      blogGrid.innerHTML = "";
      blogEmpty.hidden = false;
      return [];
    }
  }

  async function loadDetail(slug) {
    try {
      const response = await fetch(`/api/blog/?slug=${encodeURIComponent(slug)}`);
      if (!response.ok) {
        return null;
      }
      const payload = await response.json();
      const rows = Array.isArray(payload) ? payload : payload.results || [];
      return rows[0] || null;
    } catch (error) {
      console.error("Blog detail error", error);
      return null;
    }
  }

  (async () => {
    const params = new URLSearchParams(window.location.search);
    const slug = params.get("slug");

    if (slug) {
      const post = await loadDetail(slug);
      if (post) {
        renderDetail(post);
        return;
      }
      blogGrid.innerHTML = "";
      blogEmpty.hidden = false;
      blogBack.hidden = false;
      blogDetail.hidden = true;
      return;
    }

    blogDetail.hidden = true;
    blogBack.hidden = true;
    const posts = await loadList();
    renderPosts(posts);
  })();
});
