document.addEventListener("DOMContentLoaded", () => {
  const cartCount = document.getElementById("cartCount");
  const searchForm = document.getElementById("searchForm");
  const pickupList = document.getElementById("pickupList");

  const points = [
    { id: "pvz-1", name: "ПВЗ Центр", address: "ул. Тверская, 12", metro: "м. Тверская", hours: "Пн-Вс 09:00-21:00", coords: [55.7649, 37.6069] },
    { id: "pvz-2", name: "ПВЗ Бауманская", address: "ул. Бауманская, 33/2", metro: "м. Бауманская", hours: "Пн-Сб 10:00-20:00", coords: [55.7738, 37.6791] },
    { id: "pvz-3", name: "ПВЗ Сокол", address: "Ленинградский пр-т, 74к6", metro: "м. Сокол", hours: "Пн-Вс 10:00-22:00", coords: [55.8055, 37.5144] },
    { id: "pvz-4", name: "ПВЗ Юго-Запад", address: "пр-т Вернадского, 39", metro: "м. Проспект Вернадского", hours: "Пн-Вс 10:00-21:00", coords: [55.6763, 37.5069] },
    { id: "pvz-5", name: "ПВЗ Марьино", address: "ул. Люблинская, 165", metro: "м. Марьино", hours: "Пн-Сб 09:00-20:00", coords: [55.6508, 37.7448] },
    { id: "pvz-6", name: "ПВЗ Митино", address: "Пятницкое шоссе, 21", metro: "м. Митино", hours: "Пн-Вс 10:00-21:00", coords: [55.844, 37.3614] },
    { id: "pvz-7", name: "ПВЗ Теплый Стан", address: "ул. Профсоюзная, 129А", metro: "м. Теплый Стан", hours: "Пн-Вс 10:00-22:00", coords: [55.6219, 37.5067] },
    { id: "pvz-8", name: "ПВЗ Измайлово", address: "Измайловский б-р, 43", metro: "м. Первомайская", hours: "Пн-Сб 10:00-20:00", coords: [55.7985, 37.811] },
  ];

  let map;
  const placemarks = {};

  const count = Number(localStorage.getItem("paperly_cart_count") || 0);
  cartCount.textContent = String(count);

  searchForm.addEventListener("submit", (event) => {
    event.preventDefault();
    const query = searchForm.querySelector("input")?.value.trim().toLowerCase();
    if (!query) {
      renderList(points);
      return;
    }

    const filtered = points.filter((item) => {
      return (
        item.name.toLowerCase().includes(query) ||
        item.address.toLowerCase().includes(query) ||
        item.metro.toLowerCase().includes(query)
      );
    });

    renderList(filtered);
  });

  function routeUrl(point) {
    return `https://yandex.ru/maps/?rtext=~${point.coords[0]},${point.coords[1]}&rtt=auto`;
  }

  function renderList(list) {
    pickupList.innerHTML = list
      .map((point) => {
        return `
          <article class="pickup-item" data-id="${point.id}">
            <h3>${point.name}</h3>
            <p class="pickup-meta">${point.address}<br>${point.metro}<br>${point.hours}</p>
            <div class="pickup-actions">
              <button class="pickup-btn pickup-btn--main" data-action="show" data-id="${point.id}">Показать на карте</button>
              <a class="pickup-btn" href="${routeUrl(point)}" target="_blank" rel="noopener noreferrer">Маршрут</a>
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

  function focusPoint(id) {
    const point = points.find((item) => item.id === id);
    if (!point || !map) {
      return;
    }

    map.setCenter(point.coords, 14, { duration: 260 });
    const placemark = placemarks[id];
    if (placemark) {
      placemark.balloon.open();
    }
    setActive(id);
  }

  renderList(points);

  pickupList.addEventListener("click", (event) => {
    const target = event.target.closest("[data-action='show']");
    if (!target) {
      return;
    }
    const id = target.dataset.id;
    focusPoint(id);
  });

  if (typeof ymaps !== "undefined") {
    ymaps.ready(() => {
      map = new ymaps.Map("pickupMap", {
        center: [55.751244, 37.618423],
        zoom: 11,
        controls: ["zoomControl", "fullscreenControl"],
      });

      points.forEach((point) => {
        const placemark = new ymaps.Placemark(
          point.coords,
          {
            balloonContentHeader: `<strong>${point.name}</strong>`,
            balloonContentBody: `${point.address}<br>${point.metro}<br>${point.hours}`,
            balloonContentFooter: `<a href="${routeUrl(point)}" target="_blank" rel="noopener noreferrer">Построить маршрут</a>`,
          },
          {
            preset: "islands#darkGreenDotIcon",
          }
        );

        placemark.events.add("click", () => {
          setActive(point.id);
        });

        placemarks[point.id] = placemark;
        map.geoObjects.add(placemark);
      });

      focusPoint(points[0].id);
    });
  } else {
    const mapNode = document.getElementById("pickupMap");
    if (mapNode) {
      mapNode.innerHTML = "<p style='padding:16px;color:#5f747a'>Не удалось загрузить Яндекс.Карту. Проверьте подключение к сети.</p>";
    }
  }
});
