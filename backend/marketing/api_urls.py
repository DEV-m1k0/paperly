from rest_framework.routers import DefaultRouter

from .api_views import (
    BlogPostViewSet,
    GiftCertificateViewSet,
    PromotionViewSet,
    SitePageViewSet,
    WholesalePriceListViewSet,
    WholesaleRequestViewSet,
)

router = DefaultRouter()
router.register("promotions", PromotionViewSet, basename="api-promotions")
router.register("gift-certificates", GiftCertificateViewSet, basename="api-gift-certificates")
router.register("blog", BlogPostViewSet, basename="api-blog")
router.register("wholesale-price-lists", WholesalePriceListViewSet, basename="api-wholesale-price-lists")
router.register("wholesale-requests", WholesaleRequestViewSet, basename="api-wholesale-requests")
router.register("pages", SitePageViewSet, basename="api-pages")

urlpatterns = router.urls
