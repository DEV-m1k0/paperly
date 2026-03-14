from rest_framework import permissions, viewsets
from rest_framework.filters import OrderingFilter, SearchFilter

from .models import (
    BlogPost,
    Brand,
    Cart,
    CartItem,
    Category,
    DeliveryTariff,
    Favorite,
    GiftCertificate,
    Order,
    PickupPoint,
    Product,
    ProductReview,
    Promotion,
    SitePage,
    WholesalePriceList,
    WholesaleRequest,
)
from .serializers import (
    BlogPostSerializer,
    BrandSerializer,
    CartItemSerializer,
    CartSerializer,
    CategorySerializer,
    DeliveryTariffSerializer,
    FavoriteSerializer,
    GiftCertificateSerializer,
    OrderSerializer,
    PickupPointSerializer,
    ProductReviewSerializer,
    ProductSerializer,
    PromotionSerializer,
    SitePageSerializer,
    WholesalePriceListSerializer,
    WholesaleRequestSerializer,
)


class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Category.objects.filter(is_active=True)
    serializer_class = CategorySerializer


class BrandViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Brand.objects.filter(is_active=True)
    serializer_class = BrandSerializer


class ProductViewSet(viewsets.ModelViewSet):
    serializer_class = ProductSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ["title", "sku", "description", "short_description"]
    ordering_fields = ["price", "title", "created_at"]
    ordering = ["title"]

    def get_queryset(self):
        queryset = Product.objects.prefetch_related("images", "specifications", "reviews", "categories").all()

        category_slug = self.request.query_params.get("category")
        if category_slug:
            queryset = queryset.filter(categories__slug=category_slug)

        brand_slug = self.request.query_params.get("brand")
        if brand_slug:
            queryset = queryset.filter(brand__slug=brand_slug)

        min_price = self.request.query_params.get("min_price")
        max_price = self.request.query_params.get("max_price")
        if min_price:
            queryset = queryset.filter(price__gte=min_price)
        if max_price:
            queryset = queryset.filter(price__lte=max_price)

        for flag in ("is_new", "is_hit", "is_featured"):
            value = self.request.query_params.get(flag)
            if value in ("true", "1"):
                queryset = queryset.filter(**{flag: True})

        status = self.request.query_params.get("status")
        if status:
            queryset = queryset.filter(status=status)

        return queryset.distinct()


class ProductReviewViewSet(viewsets.ModelViewSet):
    queryset = ProductReview.objects.select_related("product", "user").all()
    serializer_class = ProductReviewSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        queryset = super().get_queryset()
        product_id = self.request.query_params.get("product")
        if product_id:
            queryset = queryset.filter(product_id=product_id)
        return queryset

    def perform_create(self, serializer):
        if self.request.user.is_authenticated:
            serializer.save(user=self.request.user)
            return
        serializer.save()


class PromotionViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Promotion.objects.filter(is_active=True)
    serializer_class = PromotionSerializer


class GiftCertificateViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = GiftCertificate.objects.filter(is_active=True)
    serializer_class = GiftCertificateSerializer


class BlogPostViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = BlogPost.objects.all()
    serializer_class = BlogPostSerializer


class PickupPointViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = PickupPoint.objects.filter(is_active=True)
    serializer_class = PickupPointSerializer


class DeliveryTariffViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = DeliveryTariff.objects.filter(is_active=True)
    serializer_class = DeliveryTariffSerializer


class FavoriteViewSet(viewsets.ModelViewSet):
    serializer_class = FavoriteSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Favorite.objects.filter(user=self.request.user).select_related("product")

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class CartViewSet(viewsets.ModelViewSet):
    serializer_class = CartSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        if self.request.user.is_authenticated:
            return Cart.objects.filter(user=self.request.user).prefetch_related("items")
        return Cart.objects.none()

    def perform_create(self, serializer):
        if self.request.user.is_authenticated:
            serializer.save(user=self.request.user)
            return
        serializer.save()


class CartItemViewSet(viewsets.ModelViewSet):
    serializer_class = CartItemSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        if self.request.user.is_authenticated:
            return CartItem.objects.filter(cart__user=self.request.user).select_related("product", "cart")
        return CartItem.objects.none()


class OrderViewSet(viewsets.ModelViewSet):
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        if self.request.user.is_authenticated:
            return Order.objects.filter(user=self.request.user).prefetch_related("items")
        return Order.objects.none()

    def perform_create(self, serializer):
        if self.request.user.is_authenticated:
            serializer.save(user=self.request.user)
            return
        serializer.save()


class WholesalePriceListViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = WholesalePriceList.objects.filter(is_active=True)
    serializer_class = WholesalePriceListSerializer


class WholesaleRequestViewSet(viewsets.ModelViewSet):
    queryset = WholesaleRequest.objects.all()
    serializer_class = WholesaleRequestSerializer
    permission_classes = [permissions.AllowAny]


class SitePageViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = SitePage.objects.filter(is_published=True)
    serializer_class = SitePageSerializer
