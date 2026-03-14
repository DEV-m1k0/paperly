from rest_framework.routers import DefaultRouter

from .api_views import CartItemViewSet, CartViewSet, OrderViewSet

router = DefaultRouter()
router.register("carts", CartViewSet, basename="api-carts")
router.register("cart-items", CartItemViewSet, basename="api-cart-items")
router.register("orders", OrderViewSet, basename="api-orders")

urlpatterns = router.urls
