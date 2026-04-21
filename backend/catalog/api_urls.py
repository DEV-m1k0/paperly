from django.urls import path
from rest_framework.routers import DefaultRouter

from .api_views import (
    BrandViewSet,
    CatalogFiltersSchemaAPIView,
    CatalogMetaAPIView,
    CategoryViewSet,
    ProductReviewViewSet,
    ProductViewSet,
)

router = DefaultRouter()
router.register("categories", CategoryViewSet, basename="api-categories")
router.register("brands", BrandViewSet, basename="api-brands")
router.register("products", ProductViewSet, basename="api-products")
router.register("reviews", ProductReviewViewSet, basename="api-reviews")

urlpatterns = router.urls + [
    path("catalog-filters/", CatalogFiltersSchemaAPIView.as_view(), name="api-catalog-filters"),
    path("catalog-meta/", CatalogMetaAPIView.as_view(), name="api-catalog-meta"),
]
