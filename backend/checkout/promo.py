"""
Promo-code validation + discount calculation.

Used by the /api/promo-codes/validate/ endpoint (preview) and by the order
serializer (apply-on-checkout). Validation and calc share the same code path
to guarantee the preview exactly matches the final discount.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Iterable

from django.utils import timezone

from shop.models import Order, PromoCode, PromoCodeRedemption


ZERO = Decimal("0")


class PromoError(Exception):
    """Raised with a user-facing message when a promo code can't be applied."""


@dataclass
class PromoApplication:
    promo: PromoCode
    discount: Decimal
    free_shipping: bool

    def as_dict(self) -> dict:
        return {
            "code": self.promo.code,
            "description": self.promo.description,
            "discount_type": self.promo.discount_type,
            "discount": float(self.discount),
            "free_shipping": self.free_shipping,
        }


def _eligible_subtotal(promo: PromoCode, order_items: Iterable) -> Decimal:
    """Sum of line totals for products the code actually applies to.

    ``order_items`` is an iterable of dicts with keys ``product`` (Product
    instance or id) and ``quantity`` + ``unit_price``.
    """
    product_ids = {p.id for p in promo.applicable_products.all()}
    category_ids = {c.id for c in promo.applicable_categories.all()}

    # No restriction → whole basket is eligible.
    if not product_ids and not category_ids:
        total = ZERO
        for item in order_items:
            qty = Decimal(str(item.get("quantity", 1)))
            unit = Decimal(str(item.get("unit_price", 0) or 0))
            total += qty * unit
        return total

    eligible = ZERO
    for item in order_items:
        product = item.get("product")
        if hasattr(product, "id"):
            product_id = product.id
            product_obj = product
        else:
            from shop.models import Product
            product_id = product
            try:
                product_obj = Product.objects.prefetch_related("categories").get(pk=product_id)
            except Product.DoesNotExist:
                continue
        qty = Decimal(str(item.get("quantity", 1)))
        unit = Decimal(str(item.get("unit_price", 0) or 0))
        line = qty * unit

        if product_ids and product_id in product_ids:
            eligible += line
            continue
        if category_ids:
            prod_cat_ids = {c.id for c in product_obj.categories.all()}
            if prod_cat_ids & category_ids:
                eligible += line
    return eligible


def _user_has_orders(user, email: str) -> bool:
    """True if this buyer has any previously placed (non-canceled) order."""
    from django.db.models import Q
    q = Q()
    if user and user.is_authenticated:
        q |= Q(user=user)
    if email:
        q |= Q(email__iexact=email.strip())
    if not q:
        return False
    return Order.objects.filter(q).exclude(status=Order.OrderStatus.CANCELED).exists()


def apply_promo(
    code: str,
    *,
    subtotal: Decimal,
    delivery_price: Decimal,
    items: Iterable,
    user=None,
    email: str = "",
) -> PromoApplication:
    """Validate the promo code against the current cart and compute the discount.

    Raises ``PromoError`` with a user-friendly Russian message on any failure.
    Returns a ``PromoApplication`` on success with the exact discount amount.
    """
    code = (code or "").strip().upper()
    if not code:
        raise PromoError("Введите промокод.")

    try:
        promo = PromoCode.objects.prefetch_related("applicable_products", "applicable_categories").get(code=code)
    except PromoCode.DoesNotExist:
        raise PromoError("Промокод не найден. Проверьте написание.")

    if not promo.is_active:
        raise PromoError("Этот промокод отключён.")
    if not promo.is_time_valid():
        raise PromoError("Срок действия промокода истёк.")
    if not promo.quota_available():
        raise PromoError("Лимит использований промокода исчерпан.")

    if promo.audience == PromoCode.Audience.NEW_ONLY and _user_has_orders(user, email):
        raise PromoError("Этот промокод только для первого заказа.")
    if promo.audience == PromoCode.Audience.REGISTERED and not (user and user.is_authenticated):
        raise PromoError("Промокод доступен только зарегистрированным покупателям — войдите или создайте аккаунт.")

    if not promo.user_quota_available(user=user, email=email):
        raise PromoError("Вы уже использовали этот промокод.")

    subtotal = Decimal(str(subtotal or 0))
    delivery_price = Decimal(str(delivery_price or 0))
    # Compare min_order_amount against the order total (items + delivery) — matches
    # the "Итого" the customer sees in the cart summary.
    order_total = subtotal + delivery_price
    if promo.min_order_amount and order_total < promo.min_order_amount:
        need = promo.min_order_amount - order_total
        raise PromoError(
            f"Минимальная сумма для этого промокода — {int(promo.min_order_amount)} ₽ "
            f"(не хватает {int(need)} ₽)."
        )

    eligible = _eligible_subtotal(promo, items)
    if eligible <= 0:
        raise PromoError("Промокод не применим к выбранным товарам.")

    free_shipping = False
    discount = ZERO

    if promo.discount_type == PromoCode.DiscountType.PERCENT:
        pct = Decimal(str(promo.discount_value or 0))
        raw = (eligible * pct / Decimal("100")).quantize(Decimal("0.01"))
        if promo.max_discount_amount and raw > promo.max_discount_amount:
            raw = Decimal(str(promo.max_discount_amount))
        discount = raw
    elif promo.discount_type == PromoCode.DiscountType.FIXED:
        discount = min(Decimal(str(promo.discount_value or 0)), eligible).quantize(Decimal("0.01"))
    elif promo.discount_type == PromoCode.DiscountType.FREE_SHIPPING:
        free_shipping = True
        discount = Decimal(str(delivery_price or 0)).quantize(Decimal("0.01"))

    if discount < 0:
        discount = ZERO
    return PromoApplication(promo=promo, discount=discount, free_shipping=free_shipping)


def record_redemption(application: PromoApplication, order, user=None, email: str = "") -> PromoCodeRedemption:
    """Log the redemption and bump used_count atomically."""
    from django.db.models import F

    PromoCode.objects.filter(pk=application.promo.pk).update(used_count=F("used_count") + 1)
    return PromoCodeRedemption.objects.create(
        promo=application.promo,
        user=user if (user and user.is_authenticated) else None,
        email=(email or "").strip().lower(),
        order=order,
        amount_discounted=application.discount,
    )
