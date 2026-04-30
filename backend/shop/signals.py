from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver

from .models import (
    Brand,
    CatalogFilterGroup,
    CatalogFilterOption,
    Category,
    Order,
    OrderStatusHistory,
    Product,
)


# ──────────────────────────────────────────────
# Order status history
# ──────────────────────────────────────────────
@receiver(pre_save, sender=Order)
def capture_order_status_change(sender, instance: Order, **kwargs):
    if not instance.pk:
        instance._previous_status = None
        return
    try:
        previous = Order.objects.only("status").get(pk=instance.pk)
    except Order.DoesNotExist:
        instance._previous_status = None
    else:
        instance._previous_status = previous.status


@receiver(post_save, sender=Order)
def record_order_status_history(sender, instance: Order, created: bool, **kwargs):
    previous = getattr(instance, "_previous_status", None)
    if created:
        OrderStatusHistory.objects.create(
            order=instance,
            status=instance.status,
            comment="Заказ создан",
        )
        return
    if previous is None or previous == instance.status:
        return
    OrderStatusHistory.objects.create(
        order=instance,
        status=instance.status,
        comment=f"Статус изменён: {previous} → {instance.status}",
    )


# ──────────────────────────────────────────────
# Catalog filter schema cache invalidation
# ──────────────────────────────────────────────
# These models feed catalog.filter_schema.build_full_schema(). When admins
# add/remove/toggle them in /admin/, the cached schema must be dropped so
# the next API request rebuilds with fresh data.
_SCHEMA_INVALIDATING_MODELS = (
    Product,
    Brand,
    Category,
    CatalogFilterGroup,
    CatalogFilterOption,
)


def _invalidate_filter_schema(*args, **kwargs):
    # Imported lazily so we don't drag the catalog app into shop import time.
    from catalog.filter_schema import invalidate_schema_cache
    invalidate_schema_cache()


for _model in _SCHEMA_INVALIDATING_MODELS:
    post_save.connect(_invalidate_filter_schema, sender=_model, weak=False)
    post_delete.connect(_invalidate_filter_schema, sender=_model, weak=False)
