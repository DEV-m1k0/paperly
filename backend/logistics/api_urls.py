from rest_framework.routers import DefaultRouter

from .api_views import DeliveryTariffViewSet, PickupPointViewSet

router = DefaultRouter()
router.register("pickup-points", PickupPointViewSet, basename="api-pickup-points")
router.register("delivery-tariffs", DeliveryTariffViewSet, basename="api-delivery-tariffs")

urlpatterns = router.urls
