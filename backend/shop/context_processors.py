from shop.models import Order, ReturnRequest, WholesaleRequest, ProductReview


def admin_notifications(request):
    """Счётчики для дропдауна уведомлений в navbar админки.

    Выполняет 4 лёгких COUNT-запроса по индексированным полям.
    На не-admin-страницах и для анонимов возвращает пустой dict —
    никакого оверхеда для фронтенда сайта.
    """
    user = getattr(request, "user", None)
    if user is None or not getattr(user, "is_staff", False):
        return {}
    if not request.path.startswith("/admin/"):
        return {}

    new_orders = Order.objects.filter(status=Order.OrderStatus.NEW).count()
    pending_returns = ReturnRequest.objects.filter(
        status__in=[ReturnRequest.ReturnStatus.NEW, ReturnRequest.ReturnStatus.CHECKING],
    ).count()
    new_wholesale = WholesaleRequest.objects.filter(
        status=WholesaleRequest.RequestStatus.NEW,
    ).count()
    unpublished_reviews = ProductReview.objects.filter(is_published=False).count()

    total = new_orders + pending_returns + new_wholesale + unpublished_reviews

    return {
        "pp_notifications": {
            "new_orders": new_orders,
            "pending_returns": pending_returns,
            "new_wholesale": new_wholesale,
            "unpublished_reviews": unpublished_reviews,
            "total": total,
        }
    }
