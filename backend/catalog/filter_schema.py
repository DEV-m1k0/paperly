"""
Builds the catalog filter schema returned by /api/catalog-filters/.

Architecture:
- The frontend renders filters generically based on `type`. It has no hardcoded
  knowledge of which filters exist — everything comes from this endpoint.
- Out of the box we return a sensible default set (price range, category, brand,
  format, purpose, sheets count, toggles). Options are populated from live DB
  data — admins don't need to seed anything.
- Admins can add EXTRA filter groups via the CatalogFilterGroup admin
  (e.g. for custom product specifications). Those merge in after the defaults.
"""

from __future__ import annotations

from decimal import Decimal

from django.db.models import Max, Min

from shop.models import (
    Brand,
    CatalogFilterGroup,
    Category,
    Product,
)


# --------- Defaults -----------------------------------------------------------

DEFAULT_GROUP_KEYS = {
    "price",
    "category",
    "brand",
    "product_format",
    "purpose",
    "sheets_count",
    "flags",
}

DEFAULT_QUERY_PARAMS = {
    "min_price", "max_price",
    "category", "brand", "product_format", "purpose", "sheets_count",
    "in_stock", "has_discount", "has_promotion", "sale",
    "is_new", "is_hit", "is_featured",
}


def _active_products():
    return Product.objects.filter(status=Product.ProductStatus.ACTIVE)


def _price_range():
    agg = _active_products().exclude(price__isnull=True).aggregate(
        min_price=Min("price"),
        max_price=Max("price"),
    )
    min_price = agg["min_price"] or Decimal("0")
    max_price = agg["max_price"] or Decimal("0")
    return {
        "min": int(min_price),
        "max": int(max_price),
    }


def _category_options():
    return [
        {"label": c.name, "value": c.slug}
        for c in Category.objects.filter(is_active=True).order_by("sort_order", "name")
    ]


def _brand_options():
    return [
        {"label": b.name, "value": b.slug}
        for b in Brand.objects.filter(is_active=True).order_by("name")
    ]


def _format_options():
    used_formats = set(
        _active_products()
        .exclude(format="")
        .values_list("format", flat=True)
        .distinct()
    )
    return [
        {"label": label, "value": key}
        for key, label in Product.ProductFormat.choices
        if key in used_formats
    ]


def _purpose_options():
    used_purposes = set(
        _active_products()
        .exclude(purpose="")
        .values_list("purpose", flat=True)
        .distinct()
    )
    return [
        {"label": label, "value": key}
        for key, label in Product.ProductPurpose.choices
        if key in used_purposes
    ]


def _sheets_options():
    values = (
        _active_products()
        .exclude(sheets_count__isnull=True)
        .values_list("sheets_count", flat=True)
        .distinct()
    )
    sorted_values = sorted({int(v) for v in values if v is not None})
    return [{"label": f"{v} л.", "value": str(v)} for v in sorted_values]


TOGGLE_GROUP_OPTIONS = [
    {"label": "В наличии", "value": "true", "query_param": "in_stock", "icon": "box-seam"},
    {"label": "Со скидкой", "value": "true", "query_param": "has_discount", "icon": "tag"},
    {"label": "По акции", "value": "true", "query_param": "has_promotion", "icon": "megaphone"},
    {"label": "Новинки", "value": "true", "query_param": "is_new", "icon": "stars"},
    {"label": "Хиты продаж", "value": "true", "query_param": "is_hit", "icon": "trophy"},
    {"label": "Рекомендуемые", "value": "true", "query_param": "is_featured", "icon": "bookmark-heart"},
]


def build_default_schema():
    groups = []

    price = _price_range()
    if price["max"] > price["min"]:
        groups.append({
            "key": "price",
            "title": "Цена, ₽",
            "type": "range",
            "icon": "cash-coin",
            "min_query_param": "min_price",
            "max_query_param": "max_price",
            "min": price["min"],
            "max": price["max"],
            "step": 10,
        })

    category_opts = _category_options()
    if category_opts:
        groups.append({
            "key": "category",
            "title": "Категория",
            "type": "checkbox",
            "icon": "folder2-open",
            "query_param": "category",
            "options": category_opts,
        })

    brand_opts = _brand_options()
    if brand_opts:
        groups.append({
            "key": "brand",
            "title": "Бренд",
            "type": "checkbox",
            "icon": "patch-check",
            "query_param": "brand",
            "searchable": len(brand_opts) > 6,
            "options": brand_opts,
        })

    format_opts = _format_options()
    if format_opts:
        groups.append({
            "key": "product_format",
            "title": "Формат",
            "type": "checkbox",
            "icon": "aspect-ratio",
            "query_param": "product_format",
            "options": format_opts,
        })

    purpose_opts = _purpose_options()
    if purpose_opts:
        groups.append({
            "key": "purpose",
            "title": "Назначение",
            "type": "checkbox",
            "icon": "bullseye",
            "query_param": "purpose",
            "options": purpose_opts,
        })

    sheets_opts = _sheets_options()
    if sheets_opts:
        groups.append({
            "key": "sheets_count",
            "title": "Количество листов",
            "type": "checkbox",
            "icon": "file-earmark-ruled",
            "query_param": "sheets_count",
            "options": sheets_opts,
        })

    groups.append({
        "key": "flags",
        "title": "Специальные предложения",
        "type": "toggle-group",
        "icon": "stars",
        "options": TOGGLE_GROUP_OPTIONS,
    })

    return groups


# --------- Custom groups from admin -------------------------------------------

def build_custom_groups():
    """Extra groups configured by admin in Django admin (for custom specifications).

    Skips groups whose options overlap with default/well-known query_params —
    those are already handled by build_default_schema().
    """
    custom = []
    for group in CatalogFilterGroup.objects.filter(is_active=True).prefetch_related("options").order_by("sort_order", "title"):
        slug = (group.slug or "").strip().lower()
        if slug in DEFAULT_GROUP_KEYS:
            continue

        manual_options = [
            {
                "label": opt.label,
                "value": opt.value,
                "query_param": opt.query_param,
            }
            for opt in group.options.filter(is_active=True).order_by("sort_order", "label")
        ]
        if not manual_options:
            continue

        query_params = {opt["query_param"] for opt in manual_options}
        # Skip groups that overlap with built-in defaults — they'd duplicate the UI.
        if query_params & DEFAULT_QUERY_PARAMS:
            continue
        if len(query_params) != 1:
            continue

        qp = next(iter(query_params))
        custom.append({
            "key": slug or f"group-{group.id}",
            "title": group.title,
            "type": "checkbox",
            "query_param": qp,
            "options": [{"label": o["label"], "value": o["value"]} for o in manual_options],
        })
    return custom


def build_full_schema():
    return build_default_schema() + build_custom_groups()
