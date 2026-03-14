from rest_framework.routers import DefaultRouter

from .api_views import (
    BlogPostViewSet,
    BrandViewSet,
    CartItemViewSet,
    CartViewSet,
    CategoryViewSet,
    DeliveryTariffViewSet,
    FavoriteViewSet,
    GiftCertificateViewSet,
    OrderViewSet,
    PickupPointViewSet,
    ProductReviewViewSet,
    ProductViewSet,
    PromotionViewSet,
    SitePageViewSet,
    WholesalePriceListViewSet,
    WholesaleRequestViewSet,
)

router = DefaultRouter()
router.register("categories", CategoryViewSet, basename="api-categories")
router.register("brands", BrandViewSet, basename="api-brands")
router.register("products", ProductViewSet, basename="api-products")
router.register("reviews", ProductReviewViewSet, basename="api-reviews")
router.register("promotions", PromotionViewSet, basename="api-promotions")
router.register("gift-certificates", GiftCertificateViewSet, basename="api-gift-certificates")
router.register("blog", BlogPostViewSet, basename="api-blog")
router.register("pickup-points", PickupPointViewSet, basename="api-pickup-points")
router.register("delivery-tariffs", DeliveryTariffViewSet, basename="api-delivery-tariffs")
router.register("favorites", FavoriteViewSet, basename="api-favorites")
router.register("carts", CartViewSet, basename="api-carts")
router.register("cart-items", CartItemViewSet, basename="api-cart-items")
router.register("orders", OrderViewSet, basename="api-orders")
router.register("wholesale-price-lists", WholesalePriceListViewSet, basename="api-wholesale-price-lists")
router.register("wholesale-requests", WholesaleRequestViewSet, basename="api-wholesale-requests")
router.register("pages", SitePageViewSet, basename="api-pages")

urlpatterns = router.urls
