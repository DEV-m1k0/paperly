// Blog article detail — reading progress bar + copy-link
document.addEventListener("DOMContentLoaded", () => {
  // ── Reading progress ─────────────────────────────
  const bar = document.querySelector("#blogProgress .blog-progress__bar");
  const article = document.querySelector(".blog-detail");
  if (bar && article) {
    function updateProgress() {
      const rect = article.getBoundingClientRect();
      const total = rect.height - window.innerHeight;
      const scrolled = Math.min(Math.max(-rect.top, 0), total);
      const pct = total > 0 ? (scrolled / total) * 100 : 0;
      bar.style.width = `${pct.toFixed(1)}%`;
    }
    updateProgress();
    window.addEventListener("scroll", updateProgress, { passive: true });
    window.addEventListener("resize", updateProgress);
  }

  // ── Copy link ────────────────────────────────────
  const copyBtn = document.getElementById("blogShareCopy");
  if (copyBtn) {
    copyBtn.addEventListener("click", async () => {
      const url = copyBtn.dataset.url || window.location.href;
      const label = copyBtn.querySelector("span");
      const originalText = label ? label.textContent : "";
      const icon = copyBtn.querySelector("i");
      const originalIcon = icon ? icon.className : "";

      try {
        if (navigator.clipboard) {
          await navigator.clipboard.writeText(url);
        } else {
          const tmp = document.createElement("textarea");
          tmp.value = url;
          document.body.appendChild(tmp);
          tmp.select();
          document.execCommand("copy");
          document.body.removeChild(tmp);
        }
        if (label) label.textContent = "Скопировано!";
        if (icon) icon.className = "bi bi-check2";
        copyBtn.classList.add("is-success");
      } catch (error) {
        console.error("Copy failed", error);
        if (label) label.textContent = "Не удалось";
      }
      setTimeout(() => {
        if (label) label.textContent = originalText;
        if (icon && originalIcon) icon.className = originalIcon;
        copyBtn.classList.remove("is-success");
      }, 1800);
    });
  }
});
