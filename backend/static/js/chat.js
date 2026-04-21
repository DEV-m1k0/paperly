/*
 * Paperly AI support chat — floating widget backed by Claude Opus 4.7.
 * Exposed on window.paperly.chat so templates can trigger it programmatically.
 */
(function () {
  "use strict";

  const STORAGE_KEY = "paperly_chat_history_v1";
  const STATE_KEY = "paperly_chat_open";
  const MAX_HISTORY = 16;

  const paperly = window.paperly || {};
  const apiFetch = paperly.apiFetch || fetch.bind(window);
  const escapeHtml = paperly.escapeHtml || ((v) => String(v == null ? "" : v));
  const formatMoney = paperly.formatMoney || ((v) => `${v} ₽`);

  const WELCOME_SUGGESTIONS = [
    "Подскажите ручки для офиса",
    "Какие есть блокноты до 500 ₽?",
    "Что по доставке в Курск?",
    "Нужен подарочный набор",
  ];

  const state = {
    history: [],
    open: false,
    busy: false,
    mounted: false,
    els: {},
  };

  // ── Persistence ──
  function loadHistory() {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (!raw) return [];
      const parsed = JSON.parse(raw);
      if (!Array.isArray(parsed)) return [];
      return parsed.slice(-MAX_HISTORY);
    } catch {
      return [];
    }
  }

  function saveHistory() {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(state.history.slice(-MAX_HISTORY)));
    } catch {
      /* quota or private mode — non-fatal */
    }
  }

  function clearHistory() {
    state.history = [];
    saveHistory();
    renderMessages();
  }

  // ── Markup ──
  function markup() {
    return `
      <button class="chat-launcher" type="button" aria-haspopup="dialog" aria-expanded="false" aria-controls="chatPanel" data-chat-toggle>
        <span class="chat-launcher__icon" aria-hidden="true"><span class="spark">✨</span></span>
        <span class="chat-launcher__label">AI-помощник</span>
        <span class="chat-launcher__badge" hidden data-chat-badge>1</span>
      </button>
      <div class="chat-panel" id="chatPanel" role="dialog" aria-label="AI-помощник Paperly" hidden>
        <header class="chat-header">
          <span class="chat-header__avatar" aria-hidden="true">🤖</span>
          <div class="chat-header__body">
            <p class="chat-header__name">Paperly AI</p>
            <span class="chat-header__status">локально · Llama 3.2</span>
          </div>
          <div class="chat-header__actions">
            <button class="chat-icon-btn" type="button" aria-label="Очистить историю" data-chat-clear title="Очистить историю">
              <i class="bi bi-arrow-counterclockwise" aria-hidden="true"></i>
            </button>
            <button class="chat-icon-btn" type="button" aria-label="Свернуть" data-chat-toggle title="Свернуть">
              <i class="bi bi-x-lg" aria-hidden="true"></i>
            </button>
          </div>
        </header>
        <div class="chat-messages" data-chat-messages role="log" aria-live="polite"></div>
        <form class="chat-composer" data-chat-form>
          <textarea
            class="chat-composer__input"
            data-chat-input
            rows="1"
            maxlength="1500"
            placeholder="Спросите о товарах, доставке, бренде..."
            aria-label="Сообщение AI-помощнику"
          ></textarea>
          <button class="chat-composer__send" type="submit" aria-label="Отправить" data-chat-send>
            <i class="bi bi-arrow-up" aria-hidden="true"></i>
          </button>
        </form>
        <p class="chat-footer-hint">Работает на <span>Ollama</span> локально · ответы могут содержать неточности</p>
      </div>
    `;
  }

  // ── Rendering ──
  function renderWelcome() {
    const suggestions = WELCOME_SUGGESTIONS.map((text) => (
      `<button type="button" class="chat-suggestion" data-chat-suggest="${escapeHtml(text)}">${escapeHtml(text)}</button>`
    )).join("");
    return `
      <div class="chat-welcome">
        <h3 class="chat-welcome__title">Привет! Я AI-консультант Paperly 👋</h3>
        <p class="chat-welcome__text">Помогу подобрать товары, расскажу про доставку и оплату, отвечу на вопросы о магазине.</p>
        <div class="chat-suggestions">${suggestions}</div>
      </div>
    `;
  }

  function renderProductCard(product) {
    const title = escapeHtml(product.title || "");
    const brand = escapeHtml(product.brand || "");
    const priceBlock = `
      <div class="chat-product-card__price">
        ${formatMoney(product.price || 0)}
        ${product.old_price ? `<span class="chat-product-card__price-old">${formatMoney(product.old_price)}</span>` : ""}
      </div>
    `;
    const img = product.image
      ? `<img class="chat-product-card__image" src="${escapeHtml(product.image)}" alt="${title}" loading="lazy">`
      : `<div class="chat-product-card__image chat-product-card__image--placeholder"><i class="bi bi-image" aria-hidden="true"></i></div>`;
    const stock = product.in_stock
      ? `<span class="chat-product-card__stock">В наличии</span>`
      : `<span class="chat-product-card__stock chat-product-card__stock--out">Под заказ</span>`;

    return `
      <a class="chat-product-card" href="${escapeHtml(product.url || "#")}" target="_blank" rel="noopener">
        ${img}
        <div class="chat-product-card__body">
          <span class="chat-product-card__title">${title}</span>
          <span class="chat-product-card__meta">${brand} · ${stock}</span>
        </div>
        ${priceBlock}
      </a>
    `;
  }

  function renderMessages() {
    const { messages } = state.els;
    if (!messages) return;

    if (!state.history.length) {
      messages.innerHTML = renderWelcome();
      return;
    }

    const html = state.history.map((msg) => {
      if (msg.role === "user") {
        return `<div class="chat-msg chat-msg--user">${escapeHtml(msg.content)}</div>`;
      }
      if (msg.role === "assistant") {
        const products = Array.isArray(msg.products) && msg.products.length
          ? `<div class="chat-products">${msg.products.map(renderProductCard).join("")}</div>`
          : "";
        const text = msg.content ? `<div class="chat-msg chat-msg--assistant">${escapeHtml(msg.content)}</div>` : "";
        return text + products;
      }
      if (msg.role === "error") {
        return `<div class="chat-msg chat-msg--error">${escapeHtml(msg.content)}</div>`;
      }
      return "";
    }).join("");

    messages.innerHTML = html;
    scrollToBottom();
  }

  function scrollToBottom() {
    const { messages } = state.els;
    if (messages) {
      requestAnimationFrame(() => {
        messages.scrollTop = messages.scrollHeight;
      });
    }
  }

  function showTyping() {
    const { messages } = state.els;
    if (!messages) return;
    const existing = messages.querySelector(".chat-typing");
    if (existing) return;
    const node = document.createElement("div");
    node.className = "chat-typing";
    node.setAttribute("aria-label", "Ассистент печатает...");
    node.innerHTML = "<span></span><span></span><span></span>";
    messages.appendChild(node);
    scrollToBottom();
  }

  function hideTyping() {
    const { messages } = state.els;
    if (!messages) return;
    const existing = messages.querySelector(".chat-typing");
    if (existing) existing.remove();
  }

  // ── Panel state ──
  function setOpen(open) {
    state.open = !!open;
    const { panel, launcher, input, badge } = state.els;
    if (!panel || !launcher) return;
    panel.hidden = !state.open;
    launcher.setAttribute("aria-expanded", state.open ? "true" : "false");
    try {
      localStorage.setItem(STATE_KEY, state.open ? "1" : "0");
    } catch { /* ignore */ }
    if (state.open) {
      if (badge) badge.hidden = true;
      setTimeout(() => input && input.focus(), 60);
      scrollToBottom();
    }
  }

  function toggle() {
    setOpen(!state.open);
  }

  // ── Send flow ──
  async function sendMessage(text) {
    const value = (text || "").trim();
    if (!value || state.busy) return;

    state.history.push({ role: "user", content: value });
    saveHistory();
    renderMessages();

    state.busy = true;
    const { sendBtn, input } = state.els;
    if (sendBtn) sendBtn.disabled = true;
    if (input) {
      input.value = "";
      autosize(input);
    }
    showTyping();

    // Only send user/assistant text turns to the server (skip error markers)
    const payload = {
      messages: state.history
        .filter((m) => m.role === "user" || m.role === "assistant")
        .map((m) => ({ role: m.role, content: m.content || "" })),
    };

    try {
      const response = await apiFetch("/api/chat/", {
        method: "POST",
        body: payload,
      });
      const data = await response.json().catch(() => ({}));
      hideTyping();

      if (!response.ok) {
        const reason = data?.reply || data?.error || "Не удалось связаться с ассистентом. Попробуйте ещё раз.";
        state.history.push({ role: "error", content: reason });
      } else {
        state.history.push({
          role: "assistant",
          content: data.reply || "",
          products: Array.isArray(data.products) ? data.products : [],
        });
      }
    } catch (err) {
      hideTyping();
      state.history.push({
        role: "error",
        content: "Сетевая ошибка. Проверьте подключение к интернету.",
      });
    } finally {
      state.busy = false;
      if (sendBtn) sendBtn.disabled = false;
      saveHistory();
      renderMessages();
      if (input) input.focus();
    }
  }

  function autosize(input) {
    input.style.height = "auto";
    input.style.height = Math.min(input.scrollHeight, 120) + "px";
  }

  // ── Wiring ──
  function bindEvents() {
    const { root, launcher, panel, input, form, sendBtn, messages } = state.els;

    root.addEventListener("click", (event) => {
      const toggleBtn = event.target.closest("[data-chat-toggle]");
      if (toggleBtn) {
        event.preventDefault();
        toggle();
        return;
      }
      const clearBtn = event.target.closest("[data-chat-clear]");
      if (clearBtn) {
        event.preventDefault();
        if (confirm("Очистить историю чата?")) clearHistory();
        return;
      }
      const suggestBtn = event.target.closest("[data-chat-suggest]");
      if (suggestBtn) {
        event.preventDefault();
        sendMessage(suggestBtn.dataset.chatSuggest || suggestBtn.textContent);
      }
    });

    form.addEventListener("submit", (event) => {
      event.preventDefault();
      sendMessage(input.value);
    });

    input.addEventListener("input", () => autosize(input));
    input.addEventListener("keydown", (event) => {
      if (event.key === "Enter" && !event.shiftKey) {
        event.preventDefault();
        sendMessage(input.value);
      }
    });

    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape" && state.open) {
        setOpen(false);
      }
    });
  }

  function mount() {
    if (state.mounted) return;
    const root = document.createElement("div");
    root.className = "chat-widget";
    root.setAttribute("data-chat-root", "");
    root.innerHTML = markup();
    document.body.appendChild(root);

    state.els = {
      root,
      launcher: root.querySelector(".chat-launcher"),
      panel: root.querySelector(".chat-panel"),
      messages: root.querySelector("[data-chat-messages]"),
      form: root.querySelector("[data-chat-form]"),
      input: root.querySelector("[data-chat-input]"),
      sendBtn: root.querySelector("[data-chat-send]"),
      badge: root.querySelector("[data-chat-badge]"),
    };

    state.history = loadHistory();
    state.mounted = true;
    bindEvents();
    renderMessages();

    // Restore open state (but not on mobile — avoid obscuring initial view)
    try {
      if (localStorage.getItem(STATE_KEY) === "1" && window.matchMedia("(min-width: 601px)").matches) {
        setOpen(true);
      }
    } catch { /* ignore */ }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", mount);
  } else {
    mount();
  }

  // Public API
  window.paperly = Object.assign(window.paperly || {}, {
    chat: {
      open: () => setOpen(true),
      close: () => setOpen(false),
      toggle,
      ask: (text) => { setOpen(true); sendMessage(text); },
      clear: clearHistory,
    },
  });
})();
