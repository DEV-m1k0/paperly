from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from .models import Order, OrderStatusHistory


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
