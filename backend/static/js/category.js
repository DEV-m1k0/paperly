document.addEventListener("DOMContentLoaded", () => {
  const breadcrumbs = document.getElementById("breadcrumbs");
  const treeNav = document.getElementById("treeNav");
  const groupLabel = document.getElementById("groupLabel");
  const subTitle = document.getElementById("subTitle");
  const subLead = document.getElementById("subLead");
  const subCards = document.getElementById("subCards");
  const cartCount = document.getElementById("cartCount");
  const searchForm = document.getElementById("searchForm");

  const catalogTree = [
    {
      key: "paper",
      title: "Бумажная продукция",
      subs: [
        "Тетради (школьные, общие, на спирали, предметные)",
        "Блокноты и ежедневники (датированные, недатированные, с твердой обложкой)",
        "Альбомы для рисования и папки для черчения",
        "Бумага для офисной техники (А4, А3, упаковки)",
        "Цветная бумага и картон",
      ],
    },
    {
      key: "writing",
      title: "Письменные принадлежности",
      subs: [
        "Ручки (шариковые, гелевые, перьевые, подарочные)",
        "Карандаши (простые, чернографитные, цветные, акварельные, механические)",
        "Маркеры, текстовыделители",
        "Фломастеры",
      ],
    },
    {
      key: "art",
      title: "Чертежные и художественные товары",
      subs: [
        "Краски (акварель, гуашь, акрил, масло)",
        "Кисти (разных номеров и типов ворса)",
        "Пастель, уголь, сангина",
        "Доски для лепки, пластилин, глина",
        "Чертежные инструменты (линейки, циркули, лекала, рейсшины)",
      ],
    },
    {
      key: "office",
      title: "Товары для офиса (Бизнес-класс)",
      subs: [
        "Папки и системы архивации (скоросшиватели, регистраторы, конверты на кнопке)",
        "Лотки для бумаг, подставки, органайзеры",
        "Канцелярские мелочи (ножницы, клей, степлеры, дыроколы, скотч, кнопки, скрепки)",
        "Расходные материалы для оргтехники",
      ],
    },
    {
      key: "kids",
      title: "Школа и творчество (Детям)",
      subs: [
        "Товары для первоклассника (готовые наборы)",
        "Пеналы, ранцы, сумки для обуви",
        "Наборы для опытов и творчества (поделки из гипса, квиллинг, скрапбукинг)",
      ],
    },
  ];

  function slugify(text) {
    return text
      .toLowerCase()
      .replace(/[()]/g, "")
      .replace(/[^a-zа-я0-9]+/gi, "-")
      .replace(/^-+|-+$/g, "");
  }

  function unslugifyGroup(key) {
    return catalogTree.find((group) => group.key === key) || catalogTree[0];
  }

  const params = new URLSearchParams(window.location.search);
  const groupParam = params.get("group") || "paper";
  const subParam = params.get("sub") || "";

  const currentGroup = unslugifyGroup(groupParam);
  const currentSub =
    currentGroup.subs.find((item) => slugify(item) === subParam) || currentGroup.subs[0];
  const currentSubSlug = slugify(currentSub);

  groupLabel.textContent = `Раздел каталога: ${currentGroup.title}`;
  subTitle.textContent = currentSub;
  subLead.textContent =
    "Ниже пример наполнения подкатегории. По этой структуре можно масштабировать все разделы магазина.";

  breadcrumbs.innerHTML = `
    <a href="/">Главная</a>
    <span>/</span>
    <a href="/catalog/">Каталог</a>
    <span>/</span>
    <span>${currentGroup.title}</span>
    <span>/</span>
    <span>${currentSub}</span>
  `;

  treeNav.innerHTML = catalogTree
    .map((group) => {
      const subLinks = group.subs
        .map((sub) => {
          const active = group.key === currentGroup.key && sub === currentSub ? "is-active" : "";
          return `<li><a class="${active}" href="/category/?group=${group.key}&sub=${slugify(sub)}">${sub}</a></li>`;
        })
        .join("");

      return `
        <div class="tree-group">
          <h3>${group.title}</h3>
          <ul>${subLinks}</ul>
        </div>
      `;
    })
    .join("");

  const productMap = {
    "тетради-школьные-общие-на-спирали-предметные": [
      { title: "Тетрадь школьная A5, 48 л.", desc: "Клетка, плотная обложка", price: "120 ₽", img: "/static/img/placeholder-product.svg" },
      { title: "Тетрадь на спирали A4, 96 л.", desc: "Для лекций и заметок", price: "290 ₽", img: "/static/img/placeholder-product.svg" },
      { title: "Тетрадь предметная, 48 л.", desc: "Яркие тематические обложки", price: "135 ₽", img: "/static/img/placeholder-product.svg" },
    ],
    "блокноты-и-ежедневники-датированные-недатированные-с-твердой-обложкой": [
      { title: "Ежедневник датированный A5", desc: "176 страниц, экокожа", price: "590 ₽", img: "/static/img/placeholder-product.svg" },
      { title: "Блокнот недатированный A5", desc: "Твердая обложка, 120 л.", price: "360 ₽", img: "/static/img/placeholder-product.svg" },
      { title: "Планер настольный weekly", desc: "Для планирования задач", price: "410 ₽", img: "/static/img/placeholder-product.svg" },
    ],
    "альбомы-для-рисования-и-папки-для-черчения": [
      { title: "Альбом для рисования A4", desc: "40 листов, плотность 120 г/м2", price: "230 ₽", img: "/static/img/placeholder-product.svg" },
      { title: "Папка для черчения A3", desc: "Жесткая, с клапаном", price: "340 ₽", img: "/static/img/placeholder-product.svg" },
      { title: "Скетчбук на спирали A5", desc: "Кремовая бумага 160 г/м2", price: "420 ₽", img: "/static/img/placeholder-product.svg" },
    ],
    "бумага-для-офисной-техники-а4-а3-упаковки": [
      { title: "Бумага офисная A4, 500 л.", desc: "Класс C, яркость 146 CIE", price: "760 ₽", img: "/static/img/placeholder-product.svg" },
      { title: "Бумага A3, 500 л.", desc: "Для печати схем и макетов", price: "1 290 ₽", img: "/static/img/placeholder-product.svg" },
      { title: "Бумага A4, упаковка 5 пачек", desc: "Оптимально для офиса", price: "3 650 ₽", img: "/static/img/placeholder-product.svg" },
    ],
    "цветная-бумага-и-картон": [
      { title: "Цветная бумага A4, 16 цв.", desc: "Для творчества и проектов", price: "180 ₽", img: "/static/img/placeholder-product.svg" },
      { title: "Цветной картон A4, 10 л.", desc: "Плотность 220 г/м2", price: "160 ₽", img: "/static/img/placeholder-product.svg" },
      { title: "Набор для аппликаций", desc: "Бумага + картон, 24 листа", price: "240 ₽", img: "/static/img/placeholder-product.svg" },
    ],
    "ручки-шариковые-гелевые-перьевые-подарочные": [
      { title: "Ручка шариковая синяя", desc: "Толщина линии 0.7 мм", price: "80 ₽", img: "/static/img/placeholder-product.svg" },
      { title: "Набор гелевых ручек, 12 цв.", desc: "Яркие быстросохнущие чернила", price: "420 ₽", img: "/static/img/placeholder-product.svg" },
      { title: "Подарочная перьевая ручка", desc: "Металлический корпус", price: "1 490 ₽", img: "/static/img/placeholder-product.svg" },
    ],
    "карандаши-простые-чернографитные-цветные-акварельные-механические": [
      { title: "Карандаш чернографитный HB", desc: "Классический для школы", price: "35 ₽", img: "/static/img/placeholder-product.svg" },
      { title: "Набор цветных карандашей, 24", desc: "Мягкий грифель", price: "490 ₽", img: "/static/img/placeholder-product.svg" },
      { title: "Карандаш механический 0.5", desc: "С ластиком и клипсой", price: "220 ₽", img: "/static/img/placeholder-product.svg" },
    ],
    "маркеры-текстовыделители": [
      { title: "Текстовыделители пастель, 6 шт", desc: "Скошенный наконечник", price: "260 ₽", img: "/static/img/placeholder-product.svg" },
      { title: "Маркеры художественные, 12 шт", desc: "Двусторонние, спиртовые", price: "370 ₽", img: "/static/img/placeholder-product.svg" },
      { title: "Перманентный маркер 2 мм", desc: "Для разных поверхностей", price: "95 ₽", img: "/static/img/placeholder-product.svg" },
    ],
    "фломастеры": [
      { title: "Фломастеры смываемые, 12 цв.", desc: "Безопасные для детей", price: "290 ₽", img: "/static/img/placeholder-product.svg" },
      { title: "Фломастеры двухсторонние", desc: "Тонкий и толстый наконечник", price: "360 ₽", img: "/static/img/placeholder-product.svg" },
      { title: "Набор фломастеров, 24 цв.", desc: "Яркие насыщенные цвета", price: "450 ₽", img: "/static/img/placeholder-product.svg" },
    ],
  };

  const fallbackProducts = [
    { title: "Базовый товар раздела", desc: "Популярная позиция в выбранной подкатегории", price: "290 ₽", img: "/static/img/placeholder-product.svg" },
    { title: "Премиальный товар раздела", desc: "Решение для продвинутых задач", price: "790 ₽", img: "/static/img/placeholder-product.svg" },
    { title: "Оптовый комплект", desc: "Выгодно для школы и офиса", price: "1 590 ₽", img: "/static/img/placeholder-product.svg" },
  ];

  const groupFallback = {
    art: [
      { title: "Набор акварели, 24 цвета", desc: "Яркие пигменты, удобный кейс", price: "690 ₽", img: "/static/img/placeholder-product.svg" },
      { title: "Кисти синтетика, набор 6 шт", desc: "Разные размеры и типы ворса", price: "360 ₽", img: "/static/img/placeholder-product.svg" },
      { title: "Циркуль металлический", desc: "Для точного черчения", price: "240 ₽", img: "/static/img/placeholder-product.svg" },
    ],
    office: [
      { title: "Папка-регистратор A4", desc: "Архивация документов", price: "210 ₽", img: "/static/img/placeholder-product.svg" },
      { title: "Органайзер настольный", desc: "Для ручек и бумаг", price: "540 ₽", img: "/static/img/placeholder-product.svg" },
      { title: "Степлер + скобы", desc: "Офисный комплект", price: "330 ₽", img: "/static/img/placeholder-product.svg" },
    ],
    kids: [
      { title: "Набор первоклассника", desc: "Полный стартовый комплект", price: "1 990 ₽", img: "/static/img/placeholder-product.svg" },
      { title: "Пенал на молнии", desc: "С отделениями для ручек", price: "420 ₽", img: "/static/img/placeholder-product.svg" },
      { title: "Набор для скрапбукинга", desc: "Творческий комплект для детей", price: "780 ₽", img: "/static/img/placeholder-product.svg" },
    ],
  };

  const products = productMap[currentSubSlug] || groupFallback[currentGroup.key] || fallbackProducts;

  subCards.innerHTML = products
    .map(
      (item) => `
        <article class="item-card">
          <button class="fav-btn" aria-label="Добавить в избранное"><i class="bi bi-heart"></i></button>
          <a class="item-image" href="/catalog/"><img src="${item.img}" alt="${item.title}"></a>
          <h3><a href="/catalog/">${item.title}</a></h3>
          <p>${item.desc}</p>
          <div class="item-bottom">
            <strong>${item.price}</strong>
            <button class="add-btn">В корзину</button>
          </div>
        </article>
      `
    )
    .join("");

  window.paperly.renderCartCount();

  document.querySelectorAll(".add-btn").forEach((button) => {
    button.dataset.cartBound = "true";
    button.addEventListener("click", () => {
      if (typeof window.paperlyAddToCart === "function") {
        window.paperlyAddToCart(button);
      }
      const initialText = button.textContent;
      button.textContent = "Добавлено";
      button.disabled = true;
      setTimeout(() => {
        button.textContent = initialText;
        button.disabled = false;
      }, 900);
    });
  });

  document.querySelectorAll(".fav-btn").forEach((button) => {
    button.addEventListener("click", () => {
      button.classList.toggle("is-active");
      const icon = button.querySelector("i");
      if (icon) {
        icon.classList.toggle("bi-heart");
        icon.classList.toggle("bi-heart-fill");
      }
    });
  });

  searchForm.addEventListener("submit", (event) => {
    event.preventDefault();
    const query = searchForm.querySelector("input")?.value.trim();
    if (query) {
      window.location.href = `/catalog/?q=${encodeURIComponent(query)}`;
    }
  });
});

