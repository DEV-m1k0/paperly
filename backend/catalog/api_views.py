from datetime import timedelta

from django.db import models
from django.utils import timezone
from rest_framework import permissions, viewsets
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView

from shop.models import Brand, Category, Order, Product, ProductReview

from .filter_schema import build_full_schema
from .serializers import (
    BrandSerializer,
    CategorySerializer,
    ProductReviewSerializer,
    ProductSerializer,
)


class IsAdminOrReadOnly(permissions.BasePermission):
    """Read for anyone; write only for staff users."""

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return bool(request.user and request.user.is_authenticated and request.user.is_staff)


class IsReviewOwnerOrReadOnly(permissions.BasePermission):
    """Anyone can read reviews; only the author (or staff) can edit/delete theirs."""

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        # Authenticated users can create new reviews; per-object check below
        # restricts updates/deletes to the owner.
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        if request.user.is_staff:
            return True
        return obj.user_id == request.user.id


class ProductPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 200


class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Category.objects.filter(is_active=True)
    serializer_class = CategorySerializer
    permission_classes = [permissions.AllowAny]


class BrandViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = (
        Brand.objects.filter(is_active=True)
        .annotate(
            product_count=models.Count(
                "products",
                filter=models.Q(products__status=Product.ProductStatus.ACTIVE),
                distinct=True,
            )
        )
        .order_by("-product_count", "name")
    )
    serializer_class = BrandSerializer
    permission_classes = [permissions.AllowAny]


class CatalogFiltersSchemaAPIView(APIView):
    """Returns the catalog filter schema (groups + options) for the frontend.

    Options are pulled live from DB for well-known query_params; admin-defined
    CatalogFilterGroup entries with custom query_params merge in after.
    """

    permission_classes = [permissions.AllowAny]

    def get(self, request):
        return Response({"results": build_full_schema()})


class CatalogMetaAPIView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        sheets = (
            Product.objects.exclude(sheets_count__isnull=True)
            .values_list("sheets_count", flat=True)
            .distinct()
        )
        sheets = sorted([value for value in sheets if value is not None])

        categories = list(
            Category.objects.filter(is_active=True)
            .values("name", "slug")
            .order_by("name")
        )

        return Response(
            {
                "formats": [
                    {"value": key, "label": label}
                    for key, label in Product.ProductFormat.choices
                ],
                "purposes": [
                    {"value": key, "label": label}
                    for key, label in Product.ProductPurpose.choices
                ],
                "sheets": sheets,
                "categories": categories,
            }
        )


def _split_multi(value):
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def apply_product_filters(queryset, params, exclude=None, now=None):
    exclude = set(exclude or [])
    known_params = {
        "category",
        "brand",
        "min_price",
        "max_price",
        "product_format",
        "purpose",
        "sheets_count",
        "in_stock",
        "has_discount",
        "has_promotion",
        "sale",
        "newest_days",
        "bestseller_days",
        "is_new",
        "is_hit",
        "is_featured",
        "status",
        "search",
        "ordering",
        "page",
        "page_size",
    }

    def _get(key):
        if key in exclude:
            return None
        return params.get(key)

    now = now or timezone.now()

    category_slug = _get("category")
    if category_slug:
        category_slugs = _split_multi(category_slug)
        if category_slugs:
            queryset = queryset.filter(categories__slug__in=category_slugs)

    brand_slug = _get("brand")
    if brand_slug:
        brand_slugs = _split_multi(brand_slug)
        if brand_slugs:
            queryset = queryset.filter(brand__slug__in=brand_slugs)

    min_price = _get("min_price")
    max_price = _get("max_price")
    if min_price:
        queryset = queryset.filter(price__gte=min_price)
    if max_price:
        queryset = queryset.filter(price__lte=max_price)

    product_format = _get("product_format")
    if product_format:
        formats = _split_multi(product_format)
        if formats:
            queryset = queryset.filter(format__in=formats)

    purpose = _get("purpose")
    if purpose:
        purposes = _split_multi(purpose)
        if purposes:
            queryset = queryset.filter(purpose__in=purposes)

    sheets_count = _get("sheets_count")
    if sheets_count:
        raw_values = _split_multi(sheets_count)
        values = [value for value in raw_values if value.isdigit()]
        if values:
            queryset = queryset.filter(sheets_count__in=values)

    in_stock = _get("in_stock")
    if in_stock in ("true", "1"):
        queryset = queryset.filter(stock__gt=0)
    elif in_stock in ("false", "0"):
        queryset = queryset.filter(stock=0)

    has_discount = _get("has_discount")
    if has_discount in ("true", "1"):
        queryset = queryset.filter(old_price__isnull=False, old_price__gt=models.F("price"))

    has_promotion = _get("has_promotion")
    if has_promotion in ("true", "1"):
        queryset = queryset.filter(
            promotions__is_active=True,
            promotions__start_at__lte=now,
            promotions__end_at__gte=now,
        )

    sale = _get("sale")
    if sale in ("true", "1"):
        queryset = queryset.filter(
            models.Q(old_price__isnull=False, old_price__gt=models.F("price"))
            | models.Q(promotions__is_active=True, promotions__start_at__lte=now, promotions__end_at__gte=now)
        )

    newest_days = _get("newest_days")
    if newest_days:
        try:
            days = max(1, int(newest_days))
            since = now - timedelta(days=days)
            queryset = queryset.filter(created_at__gte=since)
        except (TypeError, ValueError):
            pass

    bestseller_days = _get("bestseller_days")
    if bestseller_days:
        try:
            days = max(1, int(bestseller_days))
            since = now - timedelta(days=days)
            queryset = queryset.annotate(
                sold_recent=models.functions.Coalesce(
                    models.Sum(
                        "orderitem__quantity",
                        filter=(
                            models.Q(orderitem__order__created_at__gte=since)
                            & ~models.Q(orderitem__order__status=Order.OrderStatus.CANCELED)
                        ),
                    ),
                    0,
                    output_field=models.IntegerField(),
                )
            ).filter(sold_recent__gt=0)
        except (TypeError, ValueError):
            pass

    for flag in ("is_new", "is_hit", "is_featured"):
        value = _get(flag)
        if value in ("true", "1"):
            queryset = queryset.filter(**{flag: True})

    status = _get("status")
    if status:
        queryset = queryset.filter(status=status)

    for key in params.keys():
        if key in exclude or key in known_params:
            continue
        values = _split_multi(params.get(key))
        if values:
            queryset = queryset.filter(specifications__name=key, specifications__value__in=values)

    return queryset


class ProductViewSet(viewsets.ModelViewSet):
    serializer_class = ProductSerializer
    pagination_class = ProductPagination
    # Write operations (POST/PUT/PATCH/DELETE) are admin-only. Catalog content
    # is managed via Django admin, never through the public API.
    permission_classes = [IsAdminOrReadOnly]
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ["title", "sku", "description", "short_description"]
    ordering_fields = ["price", "title", "created_at", "sold_recent", "avg_rating", "reviews_count"]
    ordering = ["title"]

    def get_queryset(self):
        queryset = Product.objects.prefetch_related(
            "images",
            "specifications",
            "reviews",
            "categories",
            "promotions",
        ).annotate(
            avg_rating=models.Avg("reviews__rating"),
            reviews_count=models.Count("reviews", distinct=True),
            sold_recent=models.functions.Coalesce(
                models.Sum(
                    "orderitem__quantity",
                    filter=~models.Q(orderitem__order__status=Order.OrderStatus.CANCELED),
                ),
                0,
                output_field=models.IntegerField(),
            ),
        )
        queryset = apply_product_filters(queryset, self.request.query_params)
        return queryset.distinct()


class ProductReviewViewSet(viewsets.ModelViewSet):
    queryset = ProductReview.objects.filter(is_published=True).select_related("product", "user")
    serializer_class = ProductReviewSerializer
    # Anonymous read; auth required for write; only the author (or staff) can
    # update/delete their own review.
    permission_classes = [IsReviewOwnerOrReadOnly]

    def get_queryset(self):
        queryset = super().get_queryset()
        product_id = self.request.query_params.get("product")
        if product_id:
            queryset = queryset.filter(product_id=product_id)
        return queryset

    def perform_create(self, serializer):
        # IsReviewOwnerOrReadOnly already gated this on is_authenticated.
        user = self.request.user
        author_name = user.get_full_name() or user.get_username() or "Покупатель"
        serializer.save(user=user, author_name=author_name)
