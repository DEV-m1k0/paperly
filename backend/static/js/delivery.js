// Delivery page: free-delivery calculator + tariff highlighting.
document.addEventListener("DOMContentLoaded", () => {
  const input = document.getElementById("deliveryCalcInput");
  const output = document.getElementById("deliveryCalcOutput");
  const tariffGrid = document.getElementById("tariffGrid");
  if (!input || !output) return;

  // Parse numbers that may come localized ("2 500,00") as well as "2500" / "2500.00".
  const parseNum = (s) => {
    if (s == null) return 0;
    const cleaned = String(s).replace(/\s/g, "").replace(",", ".");
    const n = parseFloat(cleaned);
    return Number.isFinite(n) ? n : 0;
  };

  const tariffs = Array.from(tariffGrid?.querySelectorAll(".tariff-card") || []).map((node) => ({
    node,
    type: node.dataset.tariffType || "",
    price: parseNum(node.dataset.tariffPrice),
    freeFrom: parseNum(node.dataset.tariffFreeFrom),
    title: node.querySelector("h3")?.textContent?.trim() || "Тариф",
  }));

  const fmt = (n) => `${Math.round(n).toLocaleString("ru-RU")} ₽`;

  function render(amount) {
    tariffs.forEach((t) => t.node.classList.remove("is-free-active"));

    if (!amount || amount <= 0) {
      output.className = "delivery-calc__output";
      output.innerHTML = "Введите сумму заказа — покажем доступные варианты.";
      return;
    }

    // Tariffs that became free (amount >= their free_from threshold)
    const winners = tariffs.filter((t) => t.freeFrom > 0 && amount >= t.freeFrom);
    winners.forEach((t) => t.node.classList.add("is-free-active"));

    // Always-free tariffs (pickup)
    const alwaysFree = tariffs.filter((t) => t.price === 0 && !t.freeFrom);

    // Closest threshold still unmet
    const nearest = tariffs
      .filter((t) => t.freeFrom > 0 && amount < t.freeFrom)
      .sort((a, b) => a.freeFrom - b.freeFrom)[0];

    // ── Case 1: at least one paid tariff became free ──
    if (winners.length > 0) {
      const lines = winners.map((t) =>
        `<li><i class="bi bi-check-circle-fill"></i> <span><b>${t.title}</b> — стала бесплатной (экономия ${fmt(t.price)})</span></li>`
      );
      if (nearest) {
        const need = nearest.freeFrom - amount;
        lines.push(
          `<li><i class="bi bi-plus-circle"></i> <span>Добавьте ещё <b>${fmt(need)}</b> — и «${nearest.title}» тоже станет бесплатной</span></li>`
        );
      }
      output.className = "delivery-calc__output is-win";
      output.innerHTML = `Отлично! При сумме <b>${fmt(amount)}</b> вы получаете:<ul>${lines.join("")}</ul>`;
      return;
    }

    // ── Case 2: no winners — show the closest threshold + alternatives ──
    const lines = [];
    if (nearest) {
      const need = nearest.freeFrom - amount;
      lines.push(
        `<li><i class="bi bi-arrow-up-circle-fill"></i> <span>До бесплатной «<b>${nearest.title}</b>» не хватает <b>${fmt(need)}</b> (экономия ${fmt(nearest.price)})</span></li>`
      );
    }
    alwaysFree.forEach((t) => {
      lines.push(
        `<li><i class="bi bi-check-circle"></i> <span>Или <b>${t.title}</b> — всегда бесплатно</span></li>`
      );
    });

    if (lines.length === 0) {
      output.className = "delivery-calc__output";
      output.innerHTML = `При сумме <b>${fmt(amount)}</b> подойдёт стандартная платная доставка.`;
      return;
    }

    output.className = "delivery-calc__output";
    output.innerHTML = `При сумме <b>${fmt(amount)}</b>:<ul>${lines.join("")}</ul>`;
  }

  let timer;
  input.addEventListener("input", () => {
    clearTimeout(timer);
    timer = setTimeout(() => render(Number(input.value)), 120);
  });

  // Render once on load if there's a prefilled value.
  render(Number(input.value));
});
