document.addEventListener("DOMContentLoaded", () => {
  const { escapeHtml, apiJson, unwrapList } = window.paperly;

  const pickupList = document.getElementById("pickupList");
  const pickupSearch = document.getElementById("pickupSearch");
  const pickupCount = document.getElementById("pickupCount");
  const pickupReset = document.getElementById("pickupReset");
  const headerSearchForm = document.getElementById("searchForm");

  let points = [];
  let filteredPoints = [];
  let map;
  const placemarks = {};
  const DEFAULT_CENTER = [51.7304, 36.1926];

  function routeUrl(point) {
    return `https://yandex.ru/maps/?rtext=~${point.latitude},${point.longitude}&rtt=auto`;
  }

  function pointId(point) {
    return `pvz-${point.id}`;
  }

  function formatCount(n) {
    const mod10 = n % 10;
    const mod100 = n % 100;
    if (mod100 >= 11 && mod100 <= 14) return `${n} пунктов`;
    if (mod10 === 1) return `${n} пункт`;
    if (mod10 >= 2 && mod10 <= 4) return `${n} пункта`;
    return `${n} пунктов`;
  }

  // Parse a single "Пн-Вс 09:00-21:00" or "Пн-Пт 09:00-20:00, Сб 10:00-18:00" etc.
  // Returns { isOpen: boolean, label: string } based on current browser time.
  const DAY_MAP = {
    "пн": 1, "вт": 2, "ср": 3, "чт": 4, "пт": 5, "сб": 6, "вс": 0,
  };

  function parseWorkingStatus(hoursText) {
    if (!hoursText) return { isOpen: null, label: "" };
    const now = new Date();
    const currentDay = now.getDay(); // 0..6
    const currentMinutes = now.getHours() * 60 + now.getMinutes();

    // Normalize: each segment separated by , or ;
    const segments = hoursText.split(/[,;]/).map((s) => s.trim()).filter(Boolean);
    for (const seg of segments) {
      // e.g. "Пн-Вс 09:00-21:00" or "Ежедневно 09:00-21:00"
      const m = seg.match(/([а-яА-ЯёЁ-]+)\s+(\d{1,2}):(\d{2})\s*[-–—]\s*(\d{1,2}):(\d{2})/);
      if (!m) continue;
      const [, dayRange, h1, m1, h2, m2] = m;
      const start = parseInt(h1, 10) * 60 + parseInt(m1, 10);
      const end = parseInt(h2, 10) * 60 + parseInt(m2, 10);

      // Determine which days
      let dayMatches = false;
      const lc = dayRange.toLowerCase();
      if (lc.startsWith("ежедневно") || lc === "пн-вс") {
        dayMatches = true;
      } else if (lc.includes("-")) {
        const [d1, d2] = lc.split("-").map((s) => DAY_MAP[s.slice(0, 2)]);
        if (d1 !== undefined && d2 !== undefined) {
          if (d1 <= d2) {
            dayMatches = currentDay >= d1 && currentDay <= d2;
          } else {
            // Wrap around (e.g. Сб-Пн)
            dayMatches = currentDay >= d1 || currentDay <= d2;
          }
        }
      } else {
        const d = DAY_MAP[lc.slice(0, 2)];
        if (d !== undefined) dayMatches = currentDay === d;
      }

      if (dayMatches && currentMinutes >= start && currentMinutes <= end) {
        return { isOpen: true, label: "Сейчас работает" };
      }
    }
    return { isOpen: false, label: "Сейчас закрыто" };
  }

  function renderList(list) {
    filteredPoints = list;
    if (pickupCount) pickupCount.textContent = formatCount(list.length);
    if (pickupReset) pickupReset.hidden = !(pickupSearch && pickupSearch.value.trim());

    if (!list.length) {
      pickupList.innerHTML = `
        <div class="pickup-empty">
          <i class="bi bi-search" aria-hidden="true"></i>
          <h3>Ничего не найдено</h3>
          <p>Попробуйте другой запрос или сбросьте фильтр.</p>
        </div>
      `;
      return;
    }

    pickupList.innerHTML = list
      .map((point) => {
        const id = pointId(point);
        const status = parseWorkingStatus(point.opening_hours || "");
        const statusClass = status.isOpen === true ? "is-open" : status.isOpen === false ? "is-closed" : "";
        const statusMarkup = status.label
          ? `<span class="pickup-item__status ${statusClass}"><i class="bi bi-circle-fill" aria-hidden="true"></i> ${status.label}</span>`
          : "";
        const metro = point.metro ? `<span class="pickup-item__info"><i class="bi bi-geo" aria-hidden="true"></i> ${escapeHtml(point.metro)}</span>` : "";

        return `
          <article class="pickup-item" data-id="${id}">
            <div class="pickup-item__icon"><i class="bi bi-shop" aria-hidden="true"></i></div>
            <div class="pickup-item__body">
              <h3>${escapeHtml(point.name)}</h3>
              <span class="pickup-item__info"><i class="bi bi-geo-alt" aria-hidden="true"></i> ${escapeHtml(point.address)}</span>
              ${metro}
              ${point.opening_hours ? `<span class="pickup-item__info"><i class="bi bi-clock" aria-hidden="true"></i> ${escapeHtml(point.opening_hours)}</span>` : ""}
              ${statusMarkup}
              <div class="pickup-actions">
                <button class="pickup-btn pickup-btn--main" data-action="show" data-id="${id}" type="button">
                  <i class="bi bi-map" aria-hidden="true"></i>
                  <span>На карте</span>
                </button>
                <a class="pickup-btn" href="${routeUrl(point)}" target="_blank" rel="noopener noreferrer">
                  <i class="bi bi-signpost-split" aria-hidden="true"></i>
                  <span>Маршрут</span>
                </a>
                <button class="pickup-btn pickup-btn--icon" data-action="copy" data-text="${escapeHtml(point.address)}" type="button" aria-label="Скопировать адрес" title="Скопировать адрес">
                  <i class="bi bi-clipboard" aria-hidden="true"></i>
                </button>
              </div>
            </div>
          </article>
        `;
      })
      .join("");
  }

  function setActive(id) {
    document.querySelectorAll(".pickup-item").forEach((item) => {
      item.classList.toggle("is-active", item.dataset.id === id);
    });
  }

  function focusPoint(id, { scrollList = true } = {}) {
    const point = points.find((item) => pointId(item) === id);
    if (!point || !map) return;
    const coords = [Number(point.latitude), Number(point.longitude)];
    map.setCenter(coords, 15, { duration: 260 });
    placemarks[id]?.balloon.open();
    setActive(id);
    if (scrollList) {
      document.querySelector(`.pickup-item[data-id="${id}"]`)?.scrollIntoView({ behavior: "smooth", block: "nearest" });
    }
  }

  pickupList.addEventListener("click", async (event) => {
    const showBtn = event.target.closest("[data-action='show']");
    if (showBtn) {
      focusPoint(showBtn.dataset.id, { scrollList: false });
      return;
    }
    const copyBtn = event.target.closest("[data-action='copy']");
    if (copyBtn) {
      const text = copyBtn.dataset.text || "";
      try {
        if (navigator.clipboard) await navigator.clipboard.writeText(text);
        const icon = copyBtn.querySelector("i");
        const orig = icon?.className;
        if (icon) icon.className = "bi bi-check2";
        copyBtn.classList.add("is-copied");
        setTimeout(() => {
          if (icon && orig) icon.className = orig;
          copyBtn.classList.remove("is-copied");
        }, 1500);
      } catch (error) {
        console.error("Copy failed", error);
      }
      return;
    }
    // Click anywhere on the card body (not on a button) focuses the point
    const card = event.target.closest(".pickup-item");
    if (card && !event.target.closest("button, a")) {
      focusPoint(card.dataset.id, { scrollList: false });
    }
  });

  function applySearch(query) {
    const q = (query || "").trim().toLowerCase();
    if (!q) {
      renderList(points);
      return;
    }
    const filtered = points.filter((item) => {
      return (item.name || "").toLowerCase().includes(q)
        || (item.address || "").toLowerCase().includes(q)
        || (item.metro || "").toLowerCase().includes(q)
        || (item.city || "").toLowerCase().includes(q);
    });
    renderList(filtered);
  }

  let searchDebounce;
  pickupSearch?.addEventListener("input", (event) => {
    clearTimeout(searchDebounce);
    searchDebounce = setTimeout(() => applySearch(event.target.value), 180);
  });

  pickupReset?.addEventListener("click", () => {
    if (pickupSearch) pickupSearch.value = "";
    applySearch("");
    pickupSearch?.focus();
  });

  // Keep top-header search form working as before (redirect to catalog)
  headerSearchForm?.addEventListener("submit", (event) => {
    event.preventDefault();
    const q = headerSearchForm.querySelector("input")?.value.trim();
    if (q) window.location.href = `/catalog/?q=${encodeURIComponent(q)}`;
  });

  function initMap() {
    if (typeof ymaps === "undefined") {
      const mapNode = document.getElementById("pickupMap");
      if (mapNode) {
        mapNode.innerHTML = `<p class="pickup-map-error"><i class="bi bi-exclamation-circle"></i> Не удалось загрузить Яндекс.Карту. Проверьте подключение к сети.</p>`;
      }
      return;
    }

    ymaps.ready(() => {
      map = new ymaps.Map("pickupMap", {
        center: DEFAULT_CENTER,
        zoom: 12,
        controls: ["zoomControl", "fullscreenControl", "geolocationControl"],
      });

      points.forEach((point) => {
        const id = pointId(point);
        const coords = [Number(point.latitude), Number(point.longitude)];
        const placemark = new ymaps.Placemark(
          coords,
          {
            balloonContentHeader: `<strong>${escapeHtml(point.name)}</strong>`,
            balloonContentBody: `${escapeHtml(point.address)}<br>${escapeHtml(point.metro || "")}<br>${escapeHtml(point.opening_hours || "")}`,
            balloonContentFooter: `<a href="${routeUrl(point)}" target="_blank" rel="noopener noreferrer">Построить маршрут</a>`,
          },
          { preset: "islands#darkGreenDotIcon" }
        );
        placemark.events.add("click", () => setActive(id));
        placemarks[id] = placemark;
        map.geoObjects.add(placemark);
      });

      if (points.length) focusPoint(pointId(points[0]), { scrollList: false });
    });
  }

  async function loadPoints() {
    try {
      const payload = await apiJson("/api/pickup-points/");
      points = unwrapList(payload);
    } catch (error) {
      console.error("Pickup points API error", error);
      pickupList.innerHTML = `
        <div class="pickup-empty">
          <i class="bi bi-exclamation-triangle" aria-hidden="true"></i>
          <h3>Не удалось загрузить пункты выдачи</h3>
          <p>Попробуйте обновить страницу или зайти позже.</p>
        </div>
      `;
      if (pickupCount) pickupCount.textContent = "—";
      return;
    }
    if (!points.length) {
      pickupList.innerHTML = `
        <div class="pickup-empty">
          <i class="bi bi-geo-alt" aria-hidden="true"></i>
          <h3>Пока нет пунктов выдачи</h3>
          <p>Мы скоро добавим точки в вашем городе.</p>
        </div>
      `;
      if (pickupCount) pickupCount.textContent = "0 пунктов";
      return;
    }
    renderList(points);
    initMap();
  }

  loadPoints();
});
