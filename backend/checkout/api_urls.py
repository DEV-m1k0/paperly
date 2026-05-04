from django.urls import path
from rest_framework.routers import DefaultRouter

from .api_views import (
    CartItemViewSet,
    CartViewSet,
    OrderViewSet,
    PromoCodeValidateView,
    SbpPaymentConfirmView,
    SbpPaymentSessionStatusView,
    SbpPaymentSessionView,
)

router = DefaultRouter()
router.register("carts", CartViewSet, basename="api-carts")
router.register("cart-items", CartItemViewSet, basename="api-cart-items")
router.register("orders", OrderViewSet, basename="api-orders")

urlpatterns = router.urls + [
    path("promo-codes/validate/", PromoCodeValidateView.as_view(), name="api-promo-codes-validate"),
    path("sbp-payments/start/", SbpPaymentSessionView.as_view(), name="api-sbp-payments-start"),
    path("sbp-payments/<str:token>/", SbpPaymentSessionStatusView.as_view(), name="api-sbp-payments-status"),
    path("sbp-payments/<str:token>/confirm/", SbpPaymentConfirmView.as_view(), name="api-sbp-payments-confirm"),
]
