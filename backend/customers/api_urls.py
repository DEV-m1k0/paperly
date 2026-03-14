from rest_framework.routers import DefaultRouter

from .api_views import AddressViewSet, CustomerProfileViewSet, FavoriteViewSet, NotificationSettingViewSet

router = DefaultRouter()
router.register("profiles", CustomerProfileViewSet, basename="api-profiles")
router.register("addresses", AddressViewSet, basename="api-addresses")
router.register("notification-settings", NotificationSettingViewSet, basename="api-notification-settings")
router.register("favorites", FavoriteViewSet, basename="api-favorites")

urlpatterns = router.urls
