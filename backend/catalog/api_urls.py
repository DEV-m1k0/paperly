from django.urls import path
from rest_framework.routers import DefaultRouter

from .api_views import (
    BrandViewSet,
    CatalogFilterGroupViewSet,
    CatalogMetaAPIView,
    CategoryViewSet,
    ProductReviewViewSet,
    ProductViewSet,
)

router = DefaultRouter()
router.register("categories", CategoryViewSet, basename="api-categories")
router.register("brands", BrandViewSet, basename="api-brands")
router.register("catalog-filters", CatalogFilterGroupViewSet, basename="api-catalog-filters")
router.register("products", ProductViewSet, basename="api-products")
router.register("reviews", ProductReviewViewSet, basename="api-reviews")

urlpatterns = router.urls + [
    path("catalog-meta/", CatalogMetaAPIView.as_view(), name="api-catalog-meta"),
]
