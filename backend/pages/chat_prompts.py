"""
System prompt + tool definitions for the Paperly AI assistant.
"""

from __future__ import annotations

import re

from django.db.models import Count, Q
from django.db.models.functions import Lower

from shop.models import Brand, Category, DeliveryTariff, PickupPoint, Product, SiteSetting


# Stopwords and crude stemming — SQLite's LIKE is not case-insensitive for
# Cyrillic, and we have no full-text index; so we lowercase everything via
# Lower() and trim common plural/case endings to get decent recall.
_STOP_WORDS = {
    "для", "в", "на", "с", "со", "и", "или", "до", "от", "по", "без", "к",
    "о", "об", "у", "из", "про", "при", "под", "над", "за", "же",
    "а", "но", "как", "чтобы", "это", "эта", "этот", "тот", "та",
    "мне", "мы", "я", "ты", "он", "она", "оно", "они", "вы",
    "есть", "нет", "да", "бы", "ли", "не",
}


def _tokenize(query: str) -> list[str]:
    tokens: list[str] = []
    for match in re.finditer(r"[\w-]+", (query or "").lower(), flags=re.UNICODE):
        word = match.group(0)
        if len(word) < 3 or word in _STOP_WORDS or word.isdigit():
            continue
        # Trim 1–2 trailing chars on long words — crude Russian stem that
        # normalizes ручка/ручки/ручкой, блокнот/блокноты, тетрадь/тетради, etc.
        if len(word) >= 6:
            stem = word[:-2]
        elif len(word) >= 5:
            stem = word[:-1]
        else:
            stem = word
        tokens.append(stem)
    return tokens


PRODUCT_SEARCH_TOOL = {
    "type": "function",
    "function": {
        "name": "search_products",
        "description": (
            "Search the Paperly product catalog. Returns up to 8 matching products with id, title, "
            "price, short description, brand and stock status. Use this tool whenever the user asks "
            "about specific products, needs a recommendation, or wants to compare options. Prefer "
            "this tool over guessing — do NOT invent product IDs or prices."
        ),
        # NOTE: numeric/boolean params are typed as "string" on purpose.
        # Open-weights models (Llama, Qwen, GPT-OSS) routinely emit "300"
        # instead of 300 for numeric fields; strict schemas then blow up
        # with tool_use_failed. We accept strings and coerce in the runner.
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Keywords in Russian: product name, category, brand, purpose, format.",
                },
                "min_price": {"type": "string", "description": "Minimum price in rubles (integer)."},
                "max_price": {"type": "string", "description": "Maximum price in rubles (integer)."},
                "category": {"type": "string", "description": "Category slug or name (optional)."},
                "brand": {"type": "string", "description": "Brand slug or name (optional)."},
                "in_stock_only": {"type": "string", "description": "\"true\" to only return products in stock."},
            },
            "required": ["query"],
        },
    },
}


def run_product_search(query: str, *, min_price=None, max_price=None,
                       category=None, brand=None, in_stock_only=False, limit: int = 8):
    """Executes the `search_products` tool. Called from chat_views."""
    qs = Product.objects.filter(status=Product.ProductStatus.ACTIVE).select_related("brand")

    # SQLite's LIKE isn't case-insensitive for non-ASCII, so compare lowered values.
    qs = qs.annotate(
        _title_l=Lower("title"),
        _short_l=Lower("short_description"),
        _desc_l=Lower("description"),
        _sku_l=Lower("sku"),
        _brand_l=Lower("brand__name"),
    )

    tokens = _tokenize(query) if query else []
    if tokens:
        combined = Q()
        for token in tokens:
            combined |= (
                Q(_title_l__contains=token)
                | Q(_short_l__contains=token)
                | Q(_desc_l__contains=token)
                | Q(_sku_l__contains=token)
                | Q(_brand_l__contains=token)
            )
        qs = qs.filter(combined)

    if min_price is not None:
        qs = qs.filter(price__gte=min_price)
    if max_price is not None:
        qs = qs.filter(price__lte=max_price)
    if category:
        qs = qs.annotate(_cat_name_l=Lower("categories__name")).filter(
            Q(categories__slug__iexact=category) | Q(_cat_name_l__contains=category.lower())
        )
    if brand:
        qs = qs.filter(
            Q(brand__slug__iexact=brand) | Q(_brand_l__contains=brand.lower())
        )
    if in_stock_only:
        qs = qs.filter(stock__gt=0)

    results = []
    for product in qs.distinct().order_by("-is_hit", "-is_featured", "title")[:limit]:
        results.append({
            "id": product.id,
            "title": product.title,
            "price": float(product.price),
            "old_price": float(product.old_price) if product.old_price else None,
            "short_description": product.short_description or "",
            "brand": product.brand.name if product.brand else "",
            "stock": product.stock,
            "in_stock": product.stock > 0,
            "format": product.format or "",
            "category_slugs": list(product.categories.values_list("slug", flat=True)),
            "url": f"/product/?id={product.id}",
        })
    return results


def build_system_prompt() -> str:
    """Assembled once and heavily cached at the API level via prompt caching."""
    site = SiteSetting.load()

    delivery_lines = []
    for tariff in DeliveryTariff.objects.filter(is_active=True).order_by("delivery_type"):
        parts = [tariff.title]
        if tariff.price:
            parts.append(f"{int(tariff.price)}₽")
        else:
            parts.append("бесплатно")
        if tariff.free_from_amount:
            parts.append(f"бесплатно от {int(tariff.free_from_amount)}₽")
        if tariff.eta_min_days or tariff.eta_max_days:
            if tariff.eta_min_days == tariff.eta_max_days:
                parts.append(f"{tariff.eta_min_days} дн.")
            else:
                parts.append(f"{tariff.eta_min_days}–{tariff.eta_max_days} дн.")
        delivery_lines.append("• " + ", ".join(parts))

    top_brands = list(
        Brand.objects.filter(is_active=True)
        .annotate(product_count=Count("products", filter=Q(products__status="active")))
        .order_by("-product_count")
        .values_list("name", flat=True)[:10]
    )

    top_categories = list(
        Category.objects.filter(is_active=True)
        .order_by("sort_order", "name")
        .values_list("name", flat=True)[:12]
    )

    pickup_count = PickupPoint.objects.filter(is_active=True).count()
    products_count = Product.objects.filter(status=Product.ProductStatus.ACTIVE).count()

    return f"""Ты — Paperly, дружелюбный AI-консультант интернет-магазина канцтоваров «{site.site_name or 'Paperly'}». Помогаешь покупателям выбрать товары, отвечаешь на вопросы про доставку, оплату, возврат и подбираешь подходящие позиции из каталога.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ПРАВИЛА ОБЩЕНИЯ
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• Отвечай на том языке, на котором пишет пользователь (по умолчанию — русский).
• Отвечай кратко и по делу: 2-4 предложения в обычном диалоге, списки — только когда уместно.
• Когда тебя спрашивают о товаре, ВСЕГДА вызывай инструмент search_products вместо того, чтобы придумывать данные. Никогда не выдумывай названия, цены и ID — используй только то, что вернул поиск.
• Рекомендуя товар, упоминай его название и примерную цену. В конце реплики укажи ID в формате [product:ID] — они автоматически отрисуются как карточки.
• Если пользователь спрашивает о чём-то вне тематики канцтоваров/магазина — мягко верни к теме.
• Не давай советов по медицинским, юридическим или финансовым вопросам.
• Не обещай скидок, акций и сроков, не подтверждённых контекстом.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
МАГАЗИН
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Название: {site.site_name or 'Paperly'}
Город: {site.city or 'Курск'}
Ассортимент: {products_count} активных товаров
Телефон: {site.phone or '—'}
Email: {site.email or '—'}
Адрес: {site.address or '—'}

Категории:
{chr(10).join('• ' + c for c in top_categories) if top_categories else '• Канцелярские принадлежности'}

Популярные бренды: {', '.join(top_brands) if top_brands else '—'}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ДОСТАВКА И ОПЛАТА
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Тарифы:
{chr(10).join(delivery_lines) if delivery_lines else '• Курьер по городу и самовывоз'}
Пунктов самовывоза: {pickup_count}

Способы оплаты: банковская карта онлайн, СБП, при получении (наличными или картой курьеру/в пункте выдачи), для юрлиц — счёт.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ВОЗВРАТ И ГАРАНТИЯ
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• 14 дней на возврат товара надлежащего качества (ЗоЗПП).
• Производственный брак или повреждения при доставке — обмен/возврат в течение гарантийного срока.
• Деньги возвращаются в течение 10 рабочих дней на ту же карту/счёт.
• Подробности: страница «Гарантия и возврат» на сайте.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ПОЛЕЗНЫЕ ССЫЛКИ
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
/catalog/ — каталог, /delivery/ — доставка и оплата, /guarantee/ — возврат, /pickup/ — пункты выдачи, /wholesale/ — для юрлиц, /cart/ — корзина, /favorites/ — избранное, /blog/ — полезные статьи.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ФОРМАТ РЕКОМЕНДАЦИЙ
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Пример:
«Для офиса подойдут обычные шариковые ручки — Pilot BPS-GP дают мягкий штрих и стоят недорого.
[product:42] [product:57] [product:61]»

Ты НЕ консьерж в гостинице — будь прямым, честным и полезным. Если товара нет в наличии — скажи честно, предложи альтернативу.
"""
