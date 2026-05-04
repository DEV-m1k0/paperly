"""
Markdown-рендер для текстов блога.

Архитектура (важно понимать ДО правок):
1. Кастомный pre-processing на regex'ах:
   - Callout-блоки: `> [!INFO|TIP|WARNING|DANGER|SUCCESS] заголовок`
     + следующие строки `> ...` — превращаются в <div class="callout callout--info">
   - Video-эмбеды: `@[youtube](VIDEO_ID)` / `@[vk](OWNER_ID_VIDEO_ID)`
     — превращаются в <div class="video-embed"><iframe …></iframe></div>
   Делаем это ДО markdown-парсера, чтобы вставленный HTML не ломался.
2. Парсинг через библиотеку `markdown` с расширениями:
   tables, fenced_code, codehilite (Pygments), footnotes, sane_lists,
   smarty, attr_list, toc.
3. Санитайз через `bleach` — whitelist тегов/атрибутов. Все iframe'ы из
   шага 1 сохраняются (мы их добавили в whitelist), остальные — режутся.
   Это блокирует XSS если редактор пропустит сырой HTML от пользователя.

Кэшируем результат по hash(content) в памяти процесса — рендер на каждый
запрос blog detail иначе бьёт по latency. Кэш ограничен 256 записями
(LRU), достаточно для типового объёма постов в блоге.
"""
from __future__ import annotations

import hashlib
import re
from functools import lru_cache

import bleach
import markdown


# ─── Whitelist для bleach ───────────────────────────────────────────────
# Не трогать без понимания: добавление тегов = расширение поверхности XSS.
# iframe разрешён только с фиксированных доменов через allowed_iframe_src().
_ALLOWED_TAGS = [
    # text
    "p", "br", "hr", "span", "div",
    "strong", "em", "b", "i", "u", "s", "del", "mark", "small", "sub", "sup",
    # headings
    "h1", "h2", "h3", "h4", "h5", "h6",
    # lists
    "ul", "ol", "li", "dl", "dt", "dd",
    # blocks
    "blockquote", "pre", "code", "kbd", "samp",
    # tables
    "table", "thead", "tbody", "tfoot", "tr", "th", "td", "caption",
    # links + media
    "a", "img", "figure", "figcaption",
    "iframe",
    # callouts/video используют div с class
]

_ALLOWED_ATTRS = {
    "*": ["class", "id", "title"],
    "a": ["href", "title", "target", "rel"],
    "img": ["src", "alt", "title", "width", "height", "loading"],
    "th": ["colspan", "rowspan", "align"],
    "td": ["colspan", "rowspan", "align"],
    "iframe": [
        "src", "width", "height", "frameborder",
        "allow", "allowfullscreen", "loading", "title",
    ],
    "code": ["class"],   # для language-* классов от codehilite
    "pre": ["class"],
}

_ALLOWED_PROTOCOLS = ["http", "https", "mailto", "tel"]

# Разрешённые домены для iframe (защита от произвольных embed'ов).
_IFRAME_HOSTS_ALLOWED = (
    "https://www.youtube.com/embed/",
    "https://www.youtube-nocookie.com/embed/",
    "https://vk.com/video_ext.php",
)


# ─── Кастомные синтаксисы ───────────────────────────────────────────────

_CALLOUT_TYPES = {
    "INFO":    "info",
    "TIP":     "tip",
    "NOTE":    "note",
    "WARNING": "warning",
    "DANGER":  "danger",
    "SUCCESS": "success",
}

_CALLOUT_RE = re.compile(
    r"""
    ^>[ \t]*\[!(?P<type>INFO|TIP|NOTE|WARNING|DANGER|SUCCESS)\]
    (?:[ \t]+(?P<title>[^\n]+))?\s*\n
    (?P<body>(?:^>[ \t]?.*(?:\n|$))*)
    """,
    re.MULTILINE | re.VERBOSE,
)

# @[youtube](dQw4w9WgXcQ)  /  @[vk](-12345678_456789012)
_VIDEO_RE = re.compile(
    r"@\[(?P<provider>youtube|vk)\]\((?P<vid>[\w\-_]+)\)",
    re.IGNORECASE,
)


def _render_callout(match: re.Match) -> str:
    typ = _CALLOUT_TYPES[match.group("type").upper()]
    title = (match.group("title") or "").strip()
    body_lines = match.group("body").splitlines()
    # Снимаем `> ` префикс с каждой строки
    cleaned = []
    for line in body_lines:
        s = line.lstrip()
        if s.startswith(">"):
            s = s[1:]
            if s.startswith(" "):
                s = s[1:]
        cleaned.append(s)
    inner_md = "\n".join(cleaned).strip()
    # Парсим внутренности callout'а как markdown отдельно, без расширений
    # codehilite/toc (в callout'ах редко нужны блоки кода).
    inner_html = markdown.markdown(
        inner_md,
        extensions=["extra", "sane_lists", "smarty"],
        output_format="html5",
    )
    title_html = (
        f'<div class="callout__title">{bleach.clean(title, tags=[], strip=True)}</div>'
        if title else ""
    )
    return (
        f'<div class="callout callout--{typ}">'
        f'<div class="callout__icon" aria-hidden="true"></div>'
        f'<div class="callout__body">{title_html}{inner_html}</div>'
        f'</div>\n'
    )


def _render_video(match: re.Match) -> str:
    provider = match.group("provider").lower()
    vid = match.group("vid")
    if provider == "youtube":
        # Используем -nocookie домен — меньше трекинга, лучше для приватности.
        src = f"https://www.youtube-nocookie.com/embed/{vid}"
        title = "YouTube video"
    elif provider == "vk":
        # VK ID имеет формат OWNER_VID; нормализуем `-12345_67890` → oid=-12345&id=67890
        if "_" in vid:
            oid, video_id = vid.split("_", 1)
            src = f"https://vk.com/video_ext.php?oid={oid}&id={video_id}&hd=2"
        else:
            return match.group(0)   # не наш формат, оставляем как есть
        title = "VK video"
    else:
        return match.group(0)
    return (
        f'<div class="video-embed">'
        f'<iframe src="{src}" title="{title}" '
        f'frameborder="0" allowfullscreen loading="lazy" '
        f'allow="accelerometer; clipboard-write; encrypted-media; gyroscope; picture-in-picture"></iframe>'
        f'</div>\n'
    )


def _preprocess(text: str) -> str:
    """Заменяем callouts и video-эмбеды на HTML до markdown-парсера.

    Работаем в правильном порядке: callouts сначала (они многострочные),
    потом video (он inline). Bleach потом проверит результат.
    """
    text = _CALLOUT_RE.sub(_render_callout, text)
    text = _VIDEO_RE.sub(_render_video, text)
    return text


def _safe_iframe_filter(tag, name, value):
    """bleach attribute_filter: пропускаем только src с whitelist'а."""
    if name == "src":
        return value.startswith(_IFRAME_HOSTS_ALLOWED)
    return name in _ALLOWED_ATTRS.get("iframe", [])


# ─── Публичный API ──────────────────────────────────────────────────────

@lru_cache(maxsize=256)
def _render_cached(text_hash: str, text: str) -> str:
    """LRU-кэш по hash(text). Аргумент text_hash — ключ, text — значение."""
    pre = _preprocess(text)
    html = markdown.markdown(
        pre,
        extensions=[
            "extra",          # tables, footnotes, abbreviations, attr_list, def_list, fenced_code
            "sane_lists",
            "smarty",
            "codehilite",
            "toc",
        ],
        extension_configs={
            "codehilite": {
                "css_class": "codehilite",
                "guess_lang": False,
                "use_pygments": True,
            },
            "toc": {
                "permalink": False,
                "anchorlink": True,
            },
        },
        output_format="html5",
    )
    # Bleach с кастомным фильтром для iframe
    attrs = dict(_ALLOWED_ATTRS)
    attrs["iframe"] = _safe_iframe_filter
    cleaned = bleach.clean(
        html,
        tags=_ALLOWED_TAGS,
        attributes=attrs,
        protocols=_ALLOWED_PROTOCOLS,
        strip=True,
    )
    return cleaned


def render_markdown(text: str) -> str:
    """Главная точка входа. Возвращает безопасный HTML для блога."""
    if not text:
        return ""
    h = hashlib.md5(text.encode("utf-8")).hexdigest()
    return _render_cached(h, text)
