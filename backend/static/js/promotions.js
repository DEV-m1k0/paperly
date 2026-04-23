document.addEventListener("DOMContentLoaded", () => {
  const P = window.paperly;
  P.renderCartCount?.();

  // Products grid — только со скидкой
  P.renderProductGrid({
    container: document.getElementById("promotionsProducts"),
    endpoint: "/api/products/?sale=true&ordering=-created_at",
    fallbackEndpoint: "/api/products/?ordering=-is_featured,-created_at",
    mode: "promo",
    loadingText: "Загружаем товары со скидкой...",
    emptyText: "Сейчас нет активных скидок. Вернитесь позже!",
    errorText: "Ошибка загрузки. Попробуйте обновить страницу.",
    filter: (item) => {
      const price = Number(item.price || 0);
      const oldPrice = Number(item.old_price || 0);
      const hasOldDiscount = oldPrice > price && oldPrice > 0;
      const promoDiscount = Number(item.active_promotion_discount || 0);
      return hasOldDiscount || promoDiscount > 0;
    },
  });

  // Copy promo codes
  const toast = document.getElementById("prToast");
  const toastMsg = document.getElementById("prToastMsg");
  let toastTimer;

  function showToast(message = "Промокод скопирован") {
    if (!toast) return;
    if (toastMsg) toastMsg.textContent = message;
    toast.hidden = false;
    requestAnimationFrame(() => toast.classList.add("is-visible"));
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => {
      toast.classList.remove("is-visible");
      setTimeout(() => { toast.hidden = true; }, 280);
    }, 2200);
  }

  async function copyToClipboard(text) {
    try {
      if (navigator.clipboard?.writeText) {
        await navigator.clipboard.writeText(text);
        return true;
      }
    } catch {
      /* fall through to legacy path */
    }
    // Legacy fallback — temp textarea
    try {
      const ta = document.createElement("textarea");
      ta.value = text;
      ta.style.position = "fixed";
      ta.style.opacity = "0";
      document.body.appendChild(ta);
      ta.select();
      const ok = document.execCommand("copy");
      ta.remove();
      return ok;
    } catch {
      return false;
    }
  }

  document.querySelectorAll(".pr-code__copy").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const code = btn.dataset.copy || "";
      if (!code) return;
      const ok = await copyToClipboard(code);
      if (ok) {
        showToast(`Промокод «${code}» скопирован`);
        const label = btn.querySelector(".pr-code__copy-label");
        const originalLabel = label?.textContent || "";
        btn.classList.add("is-copied");
        if (label) label.textContent = "Скопировано";
        setTimeout(() => {
          btn.classList.remove("is-copied");
          if (label) label.textContent = originalLabel;
        }, 1800);
      } else {
        showToast("Не удалось скопировать. Выделите вручную.");
      }
    });
  });

  // Also allow clicking the visible code value to select it
  document.querySelectorAll(".pr-code__value").forEach((valueEl) => {
    valueEl.addEventListener("click", () => {
      const range = document.createRange();
      range.selectNodeContents(valueEl);
      const sel = window.getSelection();
      sel.removeAllRanges();
      sel.addRange(range);
    });
  });

  // "Подписаться" buttons → scroll to footer subscription form + focus
  const scrollToSubscribe = (event) => {
    event.preventDefault();
    const footerInput = document.getElementById("footerSubscribe");
    if (footerInput) {
      footerInput.scrollIntoView({ behavior: "smooth", block: "center" });
      setTimeout(() => footerInput.focus({ preventScroll: true }), 400);
    }
  };
  document.getElementById("prFocusSubscribe")?.addEventListener("click", scrollToSubscribe);
  document.getElementById("prFocusSubscribe2")?.addEventListener("click", scrollToSubscribe);
});
