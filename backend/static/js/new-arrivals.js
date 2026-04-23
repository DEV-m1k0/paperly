document.addEventListener("DOMContentLoaded", () => {
  const P = window.paperly;
  P.renderCartCount?.();

  const productsEl = document.getElementById("newArrivalsProducts");
  const emptyEl = document.getElementById("naEmpty");
  const emptyExpandBtn = document.getElementById("naEmptyExpand");
  const statCountEl = document.getElementById("naStatCount");
  const chips = Array.from(document.querySelectorAll(".na-chip"));

  let currentPeriod = 7;

  async function loadForPeriod(days) {
    currentPeriod = days;
    // Sync chips UI
    chips.forEach((chip) => {
      const isActive = Number(chip.dataset.period) === days;
      chip.classList.toggle("is-active", isActive);
      chip.setAttribute("aria-selected", isActive ? "true" : "false");
    });

    if (emptyEl) emptyEl.hidden = true;
    if (emptyEl) emptyEl.classList.remove("is-visible");
    productsEl.innerHTML = `<p class="empty-state">Загружаем новинки за ${periodLabel(days)}...</p>`;

    const rows = await P.renderProductGrid({
      container: productsEl,
      endpoint: `/api/products/?newest_days=${days}&ordering=-created_at`,
      mode: "new",
      loadingText: `Загружаем новинки за ${periodLabel(days)}...`,
      emptyText: "",  // suppress default empty message, we render our own
      errorText: "Ошибка загрузки. Попробуйте обновить страницу.",
    });

    if (statCountEl) statCountEl.textContent = String(rows?.length || 0);

    if (!rows || rows.length === 0) {
      productsEl.innerHTML = "";
      if (emptyEl) {
        emptyEl.hidden = false;
        emptyEl.classList.add("is-visible");
      }
      // Update the expand button to a bigger period if available
      if (emptyExpandBtn) {
        const nextPeriod = days < 30 ? 30 : null;
        if (nextPeriod) {
          emptyExpandBtn.innerHTML = `<i class="bi bi-arrow-clockwise" aria-hidden="true"></i><span>Показать за ${periodLabel(nextPeriod)}</span>`;
          emptyExpandBtn.disabled = false;
          emptyExpandBtn.dataset.nextPeriod = String(nextPeriod);
        } else {
          emptyExpandBtn.innerHTML = `<i class="bi bi-grid" aria-hidden="true"></i><span>В основной каталог</span>`;
          emptyExpandBtn.disabled = false;
          emptyExpandBtn.dataset.nextPeriod = "";
        }
      }
    }
  }

  function periodLabel(days) {
    if (days <= 3) return "3 дня";
    if (days <= 7) return "неделю";
    if (days <= 14) return "2 недели";
    return "месяц";
  }

  // Chip click → switch period
  chips.forEach((chip) => {
    chip.addEventListener("click", () => {
      const days = Number(chip.dataset.period);
      if (days && days !== currentPeriod) loadForPeriod(days);
    });
  });

  // Empty-state button: expand period or go to catalog
  emptyExpandBtn?.addEventListener("click", () => {
    const next = emptyExpandBtn.dataset.nextPeriod;
    if (next) {
      loadForPeriod(Number(next));
    } else {
      window.location.href = "/catalog/";
    }
  });

  // Newsletter form — POST /api/newsletter/subscribe/
  const form = document.getElementById("naSubscribeForm");
  const statusEl = document.getElementById("naSubscribeStatus");
  form?.addEventListener("submit", async (event) => {
    event.preventDefault();
    const input = document.getElementById("naSubscribeInput");
    const email = (input?.value || "").trim();
    if (!email) return;
    if (statusEl) {
      statusEl.hidden = false;
      statusEl.className = "na-notify__status";
      statusEl.textContent = "Отправляем...";
    }
    try {
      const r = await P.apiFetch("/api/newsletter/subscribe/", {
        method: "POST",
        body: { email, source: "new_arrivals" },
      });
      const data = await r.json().catch(() => ({}));
      if (r.ok) {
        if (statusEl) {
          statusEl.className = "na-notify__status is-success";
          statusEl.textContent = data.message || "Готово! Проверьте почту.";
        }
        form.reset();
      } else {
        const msg = (Array.isArray(data.email) ? data.email[0] : null) || data.detail || data.message || "Не удалось подписаться.";
        if (statusEl) {
          statusEl.className = "na-notify__status is-error";
          statusEl.textContent = msg;
        }
      }
    } catch {
      if (statusEl) {
        statusEl.className = "na-notify__status is-error";
        statusEl.textContent = "Сетевая ошибка. Попробуйте ещё раз.";
      }
    }
  });

  // Initial load
  loadForPeriod(7);
});
