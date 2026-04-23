/*
 * Paperly support chat — template-based conversational widget.
 *
 * Без нейросетей и без серверного эндпоинта. Весь контент — статическое
 * дерево вопросов/ответов ниже (константа NODES). Пользователь кликает
 * кнопки, диалог разворачивается как обычный чат поддержки.
 *
 * Единственный сетевой вызов — GET /api/products/ для подборок товаров
 * (при нажатии «Подобрать товар» → категория → покажем 5 карточек).
 *
 * Публичный API:
 *   window.paperly.chat.open()
 *   window.paperly.chat.close()
 *   window.paperly.chat.toggle()
 *   window.paperly.chat.goto(nodeId)     // открыть сразу конкретный раздел
 *   window.paperly.chat.reset()          // вернуть в начало + свернуть
 */
(function () {
  "use strict";

  // ── Небольшие утилиты (ждём, что paperly.* доступен из utils.js) ──
  const paperly = window.paperly || {};
  const escapeHtml = paperly.escapeHtml || ((v) => String(v == null ? "" : v));
  const formatMoney = paperly.formatMoney || ((v) => `${v} ₽`);
  const apiJson = paperly.apiJson || (async (url) => {
    const r = await fetch(url, { credentials: "same-origin" });
    if (!r.ok) throw new Error("HTTP " + r.status);
    return r.json();
  });

  const STORAGE_KEY = "paperly_chat_state_v2";
  const OPEN_KEY = "paperly_chat_open_v2";
  const ROOT = "root";
  const TYPING_DELAY_MS = 320;      // имитация «печатает…» перед ответом
  const PRODUCTS_PAGE_SIZE = 5;     // сколько товаров показываем в одной подборке

  // Контактные данные для узлов с `contacts: true`. Если понадобится —
  // выкатываются из окна site_settings в шаблон и вшиваются сюда через
  // data-атрибут body.
  const CONTACTS = {
    phone: "+7 (4712) 39-10-10",
    phoneHref: "tel:+74712391010",
    email: "info@paperly.ru",
    emailHref: "mailto:info@paperly.ru",
    hours: "Пн–Пт, 9:00–19:00 (МСК)",
  };

  // ──────────────────────────────────────────────────────────────────────
  // Дерево сценариев. Каждый узел:
  //   message: string | string[]         — что говорит бот (bubble(s))
  //   options: [{icon, label, hint?, next?, action?, params?, href?}]
  //   body:    string[]                  — блок текста (для инфо-страниц)
  //   links:   [{label, href, icon?}]    — ссылки под текстом
  //   contacts: true                     — добавить блок с телефоном/email
  //   headline: string                   — опциональный подзаголовок ввода
  //
  // Опция срабатывает так:
  //   next   → перейти к другому узлу
  //   action: "filter" + params → подгрузить товары с /api/products/
  //   href   → открыть URL (в этой же вкладке)
  //   (ничего нет) → показать только label как выбор (редко нужно)
  // ──────────────────────────────────────────────────────────────────────
  const NODES = {
    root: {
      message: [
        "Здравствуйте! 👋 Я помогу разобраться.",
        "Выберите, с чем помочь — ниже кнопки.",
      ],
      options: [
        { icon: "🛒", label: "Подобрать товар",    hint: "категории, хиты, новинки, скидки", next: "pick" },
        { icon: "📦", label: "Помощь с заказом",   hint: "оформление, отслеживание, отмена",  next: "order-help" },
        { icon: "🚚", label: "Доставка и оплата",  hint: "сроки, способы, стоимость",         next: "delivery" },
        { icon: "↩️", label: "Возврат и обмен",    hint: "условия и сроки возврата",          next: "returns" },
        { icon: "🏢", label: "Для бизнеса (B2B)",  hint: "опт, счёт, безнал",                 next: "b2b" },
        { icon: "❓", label: "Частые вопросы",     hint: "режим работы, контакты, скидки",    next: "faq" },
      ],
    },

    // ─── Подбор товара ───────────────────────────────────────────────
    pick: {
      message: "С чем помочь — выбрать товар по категории или по сценарию?",
      options: [
        { icon: "🗂️", label: "По категориям",         next: "pick-category" },
        { icon: "🎯", label: "По назначению",          next: "pick-purpose" },
        { icon: "🔥", label: "Хиты продаж",           action: "filter",
          params: { is_hit: "true" }, listTitle: "Хиты продаж",
          catalogHref: "/bestsellers/" },
        { icon: "🆕", label: "Новинки",               action: "filter",
          params: { is_new: "true" }, listTitle: "Новинки каталога",
          catalogHref: "/new-arrivals/" },
        { icon: "🏷️", label: "Товары со скидкой",    action: "filter",
          params: { sale: "true" }, listTitle: "Товары со скидкой",
          catalogHref: "/promotions/" },
      ],
    },

    "pick-category": {
      message: "Какая категория вам интересна?",
      options: [
        { icon: "📒", label: "Тетради и блокноты",    action: "filter",
          params: { category: "paper" }, listTitle: "Тетради и блокноты" },
        { icon: "✏️", label: "Ручки и карандаши",    action: "filter",
          params: { category: "writing" }, listTitle: "Ручки и карандаши" },
        { icon: "🎨", label: "Товары для творчества", action: "filter",
          params: { category: "art" }, listTitle: "Товары для творчества" },
        { icon: "🖇️", label: "Товары для офиса",     action: "filter",
          params: { category: "office" }, listTitle: "Товары для офиса" },
        { icon: "🎒", label: "Школа и канцелярия",   action: "filter",
          params: { category: "kids" }, listTitle: "Для школы и учёбы" },
      ],
    },

    "pick-purpose": {
      message: "Для чего подбираем? Покажу подборку под ваш сценарий.",
      options: [
        { icon: "🏫", label: "Для школы",       action: "filter",
          params: { purpose: "school" }, listTitle: "Для школы" },
        { icon: "🏢", label: "Для офиса",       action: "filter",
          params: { purpose: "office" }, listTitle: "Для офиса" },
        { icon: "🖌️", label: "Для творчества",  action: "filter",
          params: { purpose: "creative" }, listTitle: "Для творчества" },
        { icon: "✨", label: "Универсальное",    action: "filter",
          params: { purpose: "universal" }, listTitle: "Универсальные товары" },
      ],
    },

    // ─── Помощь с заказом ────────────────────────────────────────────
    "order-help": {
      message: "Чем помочь с заказом?",
      options: [
        { icon: "📝", label: "Как оформить заказ",  next: "order-how-to" },
        { icon: "📍", label: "Где мой заказ?",      next: "order-track" },
        { icon: "🔁", label: "Изменить заказ",      next: "order-change" },
        { icon: "🚫", label: "Отменить заказ",      next: "order-cancel" },
      ],
    },

    "order-how-to": {
      message: "Заказ оформляется за пару минут — вот как.",
      body: [
        "1. Добавьте товары в корзину кнопкой «В корзину» на странице товара.",
        "2. Перейдите в корзину → «Оформить заказ».",
        "3. Укажите ФИО, телефон, email и адрес доставки.",
        "4. Выберите способ доставки (курьер или самовывоз) и оплаты.",
        "5. Подтвердите заказ — номер придёт на почту.",
        "",
        "Регистрация не обязательна: можно заказывать как гость и создать аккаунт на этапе оформления.",
      ],
      links: [
        { icon: "🛒", label: "Перейти в корзину", href: "/cart/" },
        { icon: "🗂️", label: "Открыть каталог",   href: "/catalog/" },
      ],
    },

    "order-track": {
      message: "Отследить заказ можно в личном кабинете.",
      body: [
        "1. Войдите на сайт (если ещё нет — раздел «Войти» в шапке).",
        "2. Перейдите в раздел «Мои заказы».",
        "3. Там номер заказа, текущий статус и история переходов.",
        "",
        "Если оформляли заказ как гость — обновления статуса приходят на указанный email автоматически.",
      ],
      links: [
        { icon: "🔐", label: "Войти в аккаунт", href: "/auth/" },
        { icon: "📋", label: "Мои заказы",      href: "/order-history/" },
      ],
    },

    "order-change": {
      message: "Изменить состав или адрес можно, пока заказ в статусе «Новый» или «Подтверждён».",
      body: [
        "Позвоните или напишите нам — укажите номер заказа и что нужно изменить. Ответим в течение рабочего дня.",
        "Если заказ уже в «Оплачен» или «Отгружен» — скорее всего, проще оформить новый и оформить возврат по старому.",
      ],
      contacts: true,
    },

    "order-cancel": {
      message: "Отменить заказ можно бесплатно, пока он не отгружен.",
      body: [
        "Свободная отмена: статусы «Новый», «Подтверждён», «Оплачен».",
        "После «Отгружен» — можно отказаться при получении. Оплаченная сумма возвращается в течение 3–10 рабочих дней.",
        "Чтобы отменить — свяжитесь с нами и назовите номер заказа.",
      ],
      contacts: true,
    },

    // ─── Доставка ────────────────────────────────────────────────────
    delivery: {
      message: "Что вас интересует по доставке?",
      options: [
        { icon: "🏠", label: "Курьерская доставка", next: "delivery-courier" },
        { icon: "📦", label: "Самовывоз",            next: "delivery-pickup" },
        { icon: "💳", label: "Способы оплаты",      next: "delivery-payment" },
        { icon: "⏱️", label: "Сроки доставки",       next: "delivery-eta" },
      ],
    },

    "delivery-courier": {
      message: "Курьером — быстро и без встреч в ПВЗ.",
      body: [
        "📍 По Курску",
        "• Стоимость: 350 ₽",
        "• Бесплатно от 2 500 ₽ в чеке",
        "• Срок: 1–2 рабочих дня",
        "",
        "🇷🇺 По России (СДЭК)",
        "• Стоимость: от 490 ₽ (зависит от города и веса)",
        "• Бесплатно от 5 000 ₽",
        "• Срок: 3–7 рабочих дней",
      ],
      links: [
        { icon: "🛒", label: "Оформить заказ", href: "/cart/" },
        { icon: "📜", label: "Условия на странице доставки", href: "/delivery/" },
      ],
    },

    "delivery-pickup": {
      message: "Самовывоз — бесплатно, 7 пунктов по Курску.",
      body: [
        "Работают ежедневно с 10:00 до 21:00.",
        "На карте можно выбрать ближайший пункт — отметим на Яндекс.Карте.",
        "Заказ хранится 5 дней, потом возвращается на склад.",
      ],
      links: [
        { icon: "🗺️", label: "Пункты выдачи на карте", href: "/pickup/" },
      ],
    },

    "delivery-payment": {
      message: "Принимаем 4 способа оплаты.",
      body: [
        "💳 Картой онлайн — Visa, Mastercard, МИР",
        "📱 СБП — быстро и без комиссии",
        "💵 Наличными или картой при получении (курьер / ПВЗ)",
        "🧾 По счёту — для юрлиц (после подтверждения менеджером)",
      ],
      links: [
        { icon: "📖", label: "Подробнее о способах оплаты", href: "/delivery/" },
      ],
    },

    "delivery-eta": {
      message: "Сроки с момента подтверждения заказа:",
      body: [
        "• Курьер по Курску — 1–2 дня",
        "• Экспресс по Курску — до 1 дня (+240 ₽)",
        "• Самовывоз — обычно в день заказа, если оформили до 18:00",
        "• По России (СДЭК) — 3–7 дней",
      ],
    },

    // ─── Возврат ─────────────────────────────────────────────────────
    returns: {
      message: "Какой у вас вопрос по возврату?",
      options: [
        { icon: "⏳", label: "Сроки возврата",         next: "returns-periods" },
        { icon: "📃", label: "Как оформить возврат",   next: "returns-how" },
        { icon: "🚫", label: "Что нельзя вернуть",    next: "returns-not-allowed" },
      ],
    },

    "returns-periods": {
      message: "Сроки зависят от причины возврата.",
      body: [
        "Товар надлежащего качества — 14 дней с даты получения, если товар не был в использовании и сохранил товарный вид.",
        "Брак или неисправность — в течение гарантийного срока (обычно 12 месяцев).",
        "Деньги возвращаются тем же способом, что была оплата — в течение 3–10 рабочих дней.",
      ],
      links: [
        { icon: "📋", label: "Мои заказы", href: "/order-history/" },
        { icon: "📖", label: "Полные условия", href: "/guarantee/" },
      ],
    },

    "returns-how": {
      message: "Как оформить возврат:",
      body: [
        "1. Войдите в личный кабинет → «Мои заказы».",
        "2. Найдите нужный заказ → «Оформить возврат».",
        "3. Выберите позиции, укажите причину и опишите проблему.",
        "4. Менеджер свяжется в течение рабочего дня и согласует способ.",
        "",
        "Если заказ был гостевым — свяжитесь с нами напрямую, мы оформим возврат вручную.",
      ],
      links: [
        { icon: "📋", label: "Мои заказы", href: "/order-history/" },
      ],
      contacts: true,
    },

    "returns-not-allowed": {
      message: "По закону не подлежат возврату:",
      body: [
        "• Товары личной гигиены",
        "• Парфюмерия и косметика после вскрытия",
        "• Товары с нарушенной упаковкой, если она входит в потребительские свойства",
        "",
        "Почти все канцтовары Paperly — возвращаемые. Если сомневаетесь — спросите у нас до покупки.",
      ],
      contacts: true,
    },

    // ─── B2B ─────────────────────────────────────────────────────────
    b2b: {
      message: "Для юрлиц, школ и учреждений — отдельные условия.",
      body: [
        "• Скидки от 10% на оптовые заказы",
        "• Оплата по счёту (безнал, с НДС)",
        "• Отсрочка платежа для постоянных клиентов",
        "• Персональный менеджер и доставка прямо в офис/школу",
        "",
        "Оставьте заявку — менеджер свяжется в течение рабочего дня.",
      ],
      links: [
        { icon: "📄", label: "Подать оптовую заявку", href: "/wholesale/" },
      ],
      contacts: true,
    },

    // ─── FAQ ─────────────────────────────────────────────────────────
    faq: {
      message: "Часто спрашивают:",
      options: [
        { icon: "🕒", label: "Режим работы",                  next: "faq-hours" },
        { icon: "📞", label: "Как связаться с менеджером",    next: "faq-contact" },
        { icon: "🎁", label: "Программа лояльности",          next: "faq-loyalty" },
        { icon: "🏫", label: "Скидки для школ",               next: "faq-schools" },
        { icon: "🧾", label: "Документы для юрлиц",           next: "faq-docs" },
      ],
    },

    "faq-hours": {
      message: "Работаем так:",
      body: [
        "🌐 Интернет-магазин — круглосуточно, заказы принимаются в любое время.",
        "🏪 Пункты самовывоза — ежедневно, 10:00–21:00.",
        `📞 Служба поддержки — ${CONTACTS.hours}.`,
      ],
    },

    "faq-contact": {
      message: "Написать или позвонить можно в любое время — отвечаем в рабочие часы.",
      contacts: true,
    },

    "faq-loyalty": {
      message: "Программы с накопительными баллами пока нет.",
      body: [
        "Мы делаем акции со скидками до 30% на категории товаров и выпускаем промокоды — их можно увидеть в разделе «Акции» или получить в рассылке.",
      ],
      links: [
        { icon: "🏷️", label: "Текущие акции", href: "/promotions/" },
      ],
    },

    "faq-schools": {
      message: "Для школ, гимназий и колледжей:",
      body: [
        "• Скидки до 20% на оптовые заказы",
        "• Рассрочка без процентов",
        "• Доставка прямо в школу (в пределах Курска — бесплатно)",
        "",
        "Оставьте заявку на странице для юрлиц — в поле «Тип организации» выберите «Школа».",
      ],
      links: [
        { icon: "📄", label: "Заявка для школ", href: "/wholesale/" },
      ],
    },

    "faq-docs": {
      message: "Для юрлиц предоставляем полный пакет документов.",
      body: [
        "• Договор",
        "• Счёт на оплату",
        "• УПД / СФ",
        "• Товарную накладную",
        "",
        "Оставьте заявку — менеджер согласует документооборот и оформит отгрузку.",
      ],
      links: [
        { icon: "📄", label: "Подать заявку", href: "/wholesale/" },
      ],
    },
  };

  // ──────────────────────────────────────────────────────────────────────
  // Состояние
  //
  // steps — лента того, что уже показано пользователю. Каждый элемент:
  //   { nodeId, pickedLabel? }          — узел из NODES. Когда картридж
  //                                       выбран, его label мигрирует
  //                                       в pickedLabel.
  //   { kind: "result", listTitle, params, catalogHref?, products?, error? }
  //                                     — синтетическая карточка «вот что
  //                                       нашлось» после filter-action.
  //                                       При первом показе products=null
  //                                       и крутится индикатор.
  // ──────────────────────────────────────────────────────────────────────
  const state = {
    mounted: false,
    open: false,
    loading: false,
    steps: [{ nodeId: ROOT }],
    els: {},
  };

  // ── Persistence ──
  function loadState() {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (!raw) return null;
      const parsed = JSON.parse(raw);
      if (!parsed || !Array.isArray(parsed.steps) || !parsed.steps.length) return null;
      // Валидируем, что nodeId всё ещё существует в NODES, иначе всё дерево
      // могло сдвинуться и ссылка протухла — в таком случае сбрасываем.
      for (const step of parsed.steps) {
        if (step.kind === "result") continue;
        if (!step.nodeId || !NODES[step.nodeId]) return null;
      }
      return parsed;
    } catch {
      return null;
    }
  }

  function saveState() {
    try {
      // В persistence не кладём products — их всегда перезапросим при
      // следующем открытии. Храним только метаданные фильтра.
      const slim = state.steps.map((s) => {
        if (s.kind === "result") {
          return { kind: "result", listTitle: s.listTitle, params: s.params, catalogHref: s.catalogHref };
        }
        return { nodeId: s.nodeId, pickedLabel: s.pickedLabel };
      });
      localStorage.setItem(STORAGE_KEY, JSON.stringify({ steps: slim }));
    } catch { /* quota / private mode — не критично */ }
  }

  function saveOpenState(open) {
    try { localStorage.setItem(OPEN_KEY, open ? "1" : "0"); }
    catch { /* ignore */ }
  }

  // ── Навигация ──
  function currentStep() {
    return state.steps[state.steps.length - 1];
  }

  function isInteractive() {
    // Можно ли сейчас жать опции? Когда идёт загрузка товаров — нельзя,
    // чтобы не плодить дубли.
    return !state.loading;
  }

  function navigate(nodeId, pickedLabel) {
    if (!NODES[nodeId]) return;
    const step = currentStep();
    if (step && !step.kind && pickedLabel) {
      step.pickedLabel = pickedLabel;
    }
    state.steps.push({ nodeId });
    saveState();
    renderTranscript({ scroll: true, typing: true });
  }

  async function runFilter(option) {
    const step = currentStep();
    if (step && !step.kind) {
      step.pickedLabel = option.label;
    }
    const resultStep = {
      kind: "result",
      listTitle: option.listTitle || option.label,
      params: option.params || {},
      catalogHref: option.catalogHref || buildCatalogHref(option.params || {}),
      products: null,
      error: null,
    };
    state.steps.push(resultStep);
    saveState();
    renderTranscript({ scroll: true, typing: false });

    state.loading = true;
    updateInteractive();
    try {
      const url = buildApiUrl(option.params || {});
      const data = await apiJson(url);
      const rows = Array.isArray(data) ? data : (data?.results || []);
      resultStep.products = rows.slice(0, PRODUCTS_PAGE_SIZE);
    } catch (err) {
      resultStep.error = "Не удалось загрузить товары. Попробуйте ещё раз.";
      // Не пишем err.message в интерфейс — для простого пользователя
      // это шум. В консоли пусть будет.
      console.warn("[chat] product filter failed", err);
    } finally {
      state.loading = false;
      saveState();
      renderTranscript({ scroll: true, typing: false });
      updateInteractive();
    }
  }

  function buildApiUrl(params) {
    const qs = new URLSearchParams();
    qs.set("page_size", String(PRODUCTS_PAGE_SIZE));
    qs.set("in_stock", "true");
    qs.set("ordering", "-sold_recent");
    Object.entries(params || {}).forEach(([k, v]) => {
      if (v !== undefined && v !== null && v !== "") qs.set(k, v);
    });
    return "/api/products/?" + qs.toString();
  }

  function buildCatalogHref(params) {
    // «Показать все» ведёт в каталог с теми же фильтрами, чтобы юзер
    // мог уточнить параметры через полный UI.
    const qs = new URLSearchParams();
    Object.entries(params || {}).forEach(([k, v]) => {
      if (v !== undefined && v !== null && v !== "") qs.set(k, v);
    });
    const suffix = qs.toString();
    return "/catalog/" + (suffix ? "?" + suffix : "");
  }

  function back() {
    if (state.steps.length <= 1) return;
    state.steps.pop();
    const step = currentStep();
    if (step && !step.kind) delete step.pickedLabel;
    saveState();
    renderTranscript({ scroll: true, typing: false });
  }

  function restart() {
    state.steps = [{ nodeId: ROOT }];
    saveState();
    renderTranscript({ scroll: false, typing: false });
  }

  // ── DOM: markup ──
  function chromeMarkup() {
    return `
      <button class="chat-launcher" type="button" aria-haspopup="dialog" aria-expanded="false" aria-controls="chatPanel" data-chat-toggle>
        <span class="chat-launcher__icon" aria-hidden="true">💬</span>
        <span class="chat-launcher__label">Помощь</span>
      </button>
      <div class="chat-panel" id="chatPanel" role="dialog" aria-modal="false" aria-label="Помощь Paperly" hidden>
        <header class="chat-header">
          <span class="chat-header__avatar" aria-hidden="true">💬</span>
          <div class="chat-header__body">
            <p class="chat-header__name">Помощь Paperly</p>
            <span class="chat-header__status">онлайн</span>
          </div>
          <div class="chat-header__actions">
            <button class="chat-icon-btn" type="button" aria-label="Начать заново" data-chat-reset title="Начать заново">
              <i class="bi bi-arrow-counterclockwise" aria-hidden="true"></i>
            </button>
            <button class="chat-icon-btn" type="button" aria-label="Свернуть" data-chat-toggle title="Свернуть">
              <i class="bi bi-x-lg" aria-hidden="true"></i>
            </button>
          </div>
        </header>
        <div class="chat-messages" data-chat-messages role="log" aria-live="polite" aria-atomic="false"></div>
        <footer class="chat-footer" data-chat-footer></footer>
      </div>
    `;
  }

  function renderMessage(content) {
    const paragraphs = Array.isArray(content) ? content : [content];
    return paragraphs
      .filter((p) => p !== undefined && p !== null)
      .map((p) => `<div class="chat-msg chat-msg--assistant">${escapeHtml(p)}</div>`)
      .join("");
  }

  function renderPick(label) {
    return `<div class="chat-msg chat-msg--user">${escapeHtml(label)}</div>`;
  }

  function renderBody(body) {
    if (!Array.isArray(body) || !body.length) return "";
    const inner = body.map((line) => {
      if (line === "") return `<span class="chat-info__br"></span>`;
      return `<p>${escapeHtml(line)}</p>`;
    }).join("");
    return `<div class="chat-info">${inner}</div>`;
  }

  function renderLinks(links) {
    if (!Array.isArray(links) || !links.length) return "";
    const items = links.map((l) => (
      `<a class="chat-link" href="${escapeHtml(l.href)}">
        <span class="chat-link__icon" aria-hidden="true">${escapeHtml(l.icon || "→")}</span>
        <span class="chat-link__label">${escapeHtml(l.label)}</span>
        <i class="bi bi-chevron-right chat-link__arrow" aria-hidden="true"></i>
      </a>`
    )).join("");
    return `<div class="chat-links">${items}</div>`;
  }

  function renderContacts() {
    return `
      <div class="chat-contacts">
        <a class="chat-link" href="${CONTACTS.phoneHref}">
          <span class="chat-link__icon" aria-hidden="true">📞</span>
          <span class="chat-link__label">Позвонить ${escapeHtml(CONTACTS.phone)}</span>
          <i class="bi bi-chevron-right chat-link__arrow" aria-hidden="true"></i>
        </a>
        <a class="chat-link" href="${CONTACTS.emailHref}">
          <span class="chat-link__icon" aria-hidden="true">✉️</span>
          <span class="chat-link__label">Написать ${escapeHtml(CONTACTS.email)}</span>
          <i class="bi bi-chevron-right chat-link__arrow" aria-hidden="true"></i>
        </a>
        <p class="chat-contacts__hint">${escapeHtml(CONTACTS.hours)}</p>
      </div>
    `;
  }

  function renderProductCard(product) {
    if (!product) return "";
    const title = escapeHtml(product.title || "");
    const imageUrl = product.images?.[0]?.image_url || "/static/img/placeholder-product.svg";
    const brandName = product.brand_name || product.brand_slug || "";
    const price = Number(product.price || 0);
    const oldPrice = product.old_price ? Number(product.old_price) : 0;
    const hasDiscount = oldPrice > price && oldPrice > 0;
    const stockText = Number(product.stock || 0) > 0 ? "В наличии" : "Под заказ";
    const stockClass = Number(product.stock || 0) > 0 ? "" : " chat-product-card__stock--out";
    const href = `/product/?id=${encodeURIComponent(product.id)}`;

    return `
      <a class="chat-product-card" href="${href}">
        <img class="chat-product-card__image" src="${escapeHtml(imageUrl)}" alt="${title}" loading="lazy">
        <div class="chat-product-card__body">
          <span class="chat-product-card__title">${title}</span>
          <span class="chat-product-card__meta">
            ${brandName ? `<span>${escapeHtml(brandName)}</span>` : ""}
            <span class="chat-product-card__stock${stockClass}">${stockText}</span>
          </span>
        </div>
        <div class="chat-product-card__price">
          ${formatMoney(price)}
          ${hasDiscount ? `<span class="chat-product-card__price-old">${formatMoney(oldPrice)}</span>` : ""}
        </div>
      </a>
    `;
  }

  function renderResultStep(step) {
    const heading = `<div class="chat-msg chat-msg--assistant">${escapeHtml(step.listTitle || "Подборка")} — вот что нашлось:</div>`;
    if (step.products === null && !step.error) {
      return heading + `<div class="chat-loading" aria-label="Загружаем">
        <span></span><span></span><span></span>
      </div>`;
    }
    if (step.error) {
      return heading + `<div class="chat-msg chat-msg--error">${escapeHtml(step.error)}</div>`;
    }
    if (!step.products || !step.products.length) {
      return heading + `<div class="chat-msg chat-msg--assistant">Подходящих товаров не нашлось. Попробуйте другую категорию.</div>`;
    }
    const cards = step.products.map(renderProductCard).join("");
    const catalog = step.catalogHref
      ? `<a class="chat-more" href="${escapeHtml(step.catalogHref)}">
          Показать все в каталоге
          <i class="bi bi-arrow-right" aria-hidden="true"></i>
        </a>`
      : "";
    return heading + `<div class="chat-products">${cards}</div>${catalog}`;
  }

  function renderNodeStep(step, { isCurrent, showOptions }) {
    const node = NODES[step.nodeId];
    if (!node) return "";

    let out = renderMessage(node.message);
    if (node.body) out += renderBody(node.body);
    if (node.links) out += renderLinks(node.links);
    if (node.contacts) out += renderContacts();

    // Если это — самый свежий шаг и ждёт ответа юзера, покажем его
    // опции ниже (в body сообщения, а не в футере: так они визуально
    // ближе к вопросу бота).
    if (showOptions && node.options && node.options.length && !step.pickedLabel) {
      out += renderOptionsGrid(node.options);
    }

    if (step.pickedLabel) {
      out += renderPick(step.pickedLabel);
    }

    return out;
  }

  function renderOptionsGrid(options) {
    const buttons = options.map((option, idx) => {
      const icon = option.icon ? `<span class="chat-option__icon" aria-hidden="true">${escapeHtml(option.icon)}</span>` : "";
      const hint = option.hint ? `<span class="chat-option__hint">${escapeHtml(option.hint)}</span>` : "";
      return `
        <button type="button" class="chat-option" data-chat-option="${idx}">
          ${icon}
          <span class="chat-option__body">
            <span class="chat-option__label">${escapeHtml(option.label)}</span>
            ${hint}
          </span>
          <i class="bi bi-chevron-right chat-option__arrow" aria-hidden="true"></i>
        </button>
      `;
    }).join("");
    return `<div class="chat-options" role="group" aria-label="Варианты ответа">${buttons}</div>`;
  }

  // ── Ленивый «печатает…» ──
  // Показываем 3 точки на 300мс перед следующим bot-message, чтобы
  // диалог не казался «скакающим».
  let typingTimer = null;

  function injectTyping(container) {
    if (typingTimer) clearTimeout(typingTimer);
    const el = document.createElement("div");
    el.className = "chat-typing";
    el.setAttribute("aria-label", "Помощник печатает");
    el.innerHTML = "<span></span><span></span><span></span>";
    container.appendChild(el);
    scrollToBottom(container);
    typingTimer = setTimeout(() => {
      el.remove();
      typingTimer = null;
      renderTranscript({ scroll: true, typing: false, _skipTyping: true });
    }, TYPING_DELAY_MS);
  }

  function scrollToBottom(container) {
    const el = container || state.els.messages;
    if (!el) return;
    requestAnimationFrame(() => { el.scrollTop = el.scrollHeight; });
  }

  // ── Рендер всей ленты ──
  // typing=true — перед последним bot-шагом вставим «…», через
  // TYPING_DELAY_MS перерисуем без него. _skipTyping — флаг из таймера,
  // чтобы не зациклиться.
  function renderTranscript(opts) {
    const { messages } = state.els;
    if (!messages) return;
    const { scroll = true, typing = false, _skipTyping = false } = opts || {};

    const lastIdx = state.steps.length - 1;

    if (typing && !_skipTyping && state.steps.length > 1) {
      // Нарисуем всё, кроме последнего шага, и добавим «печатает…»
      const upTo = state.steps.slice(0, lastIdx);
      messages.innerHTML = buildHtml(upTo, -1);
      injectTyping(messages);
      return;
    }

    messages.innerHTML = buildHtml(state.steps, lastIdx);
    renderFooter();
    if (scroll) scrollToBottom(messages);
    // Фокус на первую опцию — помогает клавиатурной навигации, но
    // осторожно: первый mount срабатывает до открытия, фокус в закрытой
    // панели нежелателен. Фокусим только когда панель открыта.
    if (state.open) focusFirstOption();
  }

  function buildHtml(steps, currentIdx) {
    return steps.map((step, idx) => {
      const isCurrent = idx === currentIdx;
      if (step.kind === "result") {
        return `<section class="chat-step chat-step--result">${renderResultStep(step)}</section>`;
      }
      return `<section class="chat-step">${renderNodeStep(step, { isCurrent, showOptions: isCurrent })}</section>`;
    }).join("");
  }

  function renderFooter() {
    const { footer } = state.els;
    if (!footer) return;

    const canBack = state.steps.length > 1;
    const notAtRoot = state.steps.length > 1 ||
      (currentStep()?.nodeId && currentStep().nodeId !== ROOT);

    footer.innerHTML = `
      <button type="button" class="chat-nav-btn"
        data-chat-back ${canBack ? "" : "disabled"}>
        <i class="bi bi-arrow-left" aria-hidden="true"></i>
        <span>Назад</span>
      </button>
      <button type="button" class="chat-nav-btn chat-nav-btn--ghost"
        data-chat-restart ${notAtRoot ? "" : "disabled"}>
        <i class="bi bi-house" aria-hidden="true"></i>
        <span>В начало</span>
      </button>
    `;
  }

  function focusFirstOption() {
    const { messages } = state.els;
    if (!messages) return;
    const btn = messages.querySelector(".chat-step:last-of-type .chat-option");
    if (btn) {
      // Аккуратно: не зовём focus() сразу при открытии, а только если
      // перед этим был явный keyboard-exchange. Проще всего — не
      // фокусировать автоматически, пусть юзер сам ведёт Tab.
      // Оставляем метод как заготовку — можно включить по флагу.
    }
  }

  function updateInteractive() {
    const { panel } = state.els;
    if (!panel) return;
    panel.classList.toggle("is-loading", state.loading);
  }

  // ── Open / close ──
  function setOpen(open) {
    state.open = !!open;
    const { panel, launcher } = state.els;
    if (!panel || !launcher) return;
    panel.hidden = !state.open;
    launcher.setAttribute("aria-expanded", state.open ? "true" : "false");
    saveOpenState(state.open);
    if (state.open) {
      scrollToBottom();
    }
  }

  function toggle() { setOpen(!state.open); }

  // ── Обработка кликов ──
  function onRootClick(event) {
    if (event.target.closest("[data-chat-toggle]")) {
      event.preventDefault();
      toggle();
      return;
    }
    if (event.target.closest("[data-chat-reset]")) {
      event.preventDefault();
      if (confirm("Вернуться в начало диалога?")) restart();
      return;
    }
    const optBtn = event.target.closest("[data-chat-option]");
    if (optBtn) {
      event.preventDefault();
      if (!isInteractive()) return;
      const step = currentStep();
      if (!step || step.kind === "result") return;
      const node = NODES[step.nodeId];
      if (!node || !Array.isArray(node.options)) return;
      const idx = Number(optBtn.dataset.chatOption);
      const option = node.options[idx];
      if (!option) return;
      if (option.next) { navigate(option.next, option.label); return; }
      if (option.action === "filter") { runFilter(option); return; }
      if (option.href) { window.location.href = option.href; return; }
      return;
    }
    const backBtn = event.target.closest("[data-chat-back]");
    if (backBtn && !backBtn.disabled) {
      event.preventDefault();
      if (!isInteractive()) return;
      back();
      return;
    }
    const restartBtn = event.target.closest("[data-chat-restart]");
    if (restartBtn && !restartBtn.disabled) {
      event.preventDefault();
      if (!isInteractive()) return;
      restart();
      return;
    }
  }

  function onKeyDown(event) {
    if (event.key === "Escape" && state.open) {
      setOpen(false);
    }
  }

  // ── Mount ──
  function mount() {
    if (state.mounted) return;

    // Восстанавливаем сохранённое дерево шагов (если есть и не протухло).
    const restored = loadState();
    if (restored && restored.steps && restored.steps.length) {
      state.steps = restored.steps;
      // Перетаскиваем products-кэш в null — перезапросим при отображении.
      // Но чтобы показать пользователю ленту сразу, оставим заглушки
      // (products=null → индикатор). Триггер перезагрузки — запустим
      // ниже после монтажа.
    }

    const root = document.createElement("div");
    root.className = "chat-widget";
    root.setAttribute("data-chat-root", "");
    root.innerHTML = chromeMarkup();
    document.body.appendChild(root);

    state.els = {
      root,
      launcher: root.querySelector(".chat-launcher"),
      panel: root.querySelector(".chat-panel"),
      messages: root.querySelector("[data-chat-messages]"),
      footer: root.querySelector("[data-chat-footer]"),
    };

    root.addEventListener("click", onRootClick);
    document.addEventListener("keydown", onKeyDown);

    state.mounted = true;
    renderTranscript({ scroll: false, typing: false });

    // Если при восстановлении попались шаги с filter-результатами без
    // products — перезапросим свежие данные (цены/наличие могли изменитсья).
    state.steps.forEach((step, idx) => {
      if (step.kind === "result" && (!step.products || !step.products.length) && !step.error) {
        refetchResult(step, idx);
      }
    });

    // Автоматически НЕ открываем — слишком навязчиво. Но если пользователь
    // в прошлый раз оставил панель открытой и с десктопа — восстановим.
    try {
      if (localStorage.getItem(OPEN_KEY) === "1" &&
          window.matchMedia("(min-width: 601px)").matches) {
        setOpen(true);
      }
    } catch { /* ignore */ }
  }

  async function refetchResult(step, stepIdx) {
    state.loading = true;
    updateInteractive();
    try {
      const url = buildApiUrl(step.params || {});
      const data = await apiJson(url);
      const rows = Array.isArray(data) ? data : (data?.results || []);
      step.products = rows.slice(0, PRODUCTS_PAGE_SIZE);
      step.error = null;
    } catch (err) {
      step.error = "Не удалось загрузить товары. Попробуйте ещё раз.";
      console.warn("[chat] refetch failed", err);
    } finally {
      state.loading = false;
      renderTranscript({ scroll: false, typing: false });
      updateInteractive();
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", mount);
  } else {
    mount();
  }

  // ── Публичный API ──
  window.paperly = Object.assign(window.paperly || {}, {
    chat: {
      open: () => setOpen(true),
      close: () => setOpen(false),
      toggle,
      goto: (nodeId) => {
        if (!NODES[nodeId]) return;
        state.steps = [{ nodeId: ROOT }];
        if (nodeId !== ROOT) state.steps.push({ nodeId });
        saveState();
        renderTranscript({ scroll: true, typing: false });
        setOpen(true);
      },
      reset: () => { restart(); setOpen(false); },
    },
  });
})();
