from rest_framework import mixins, permissions, viewsets

from shop.models import BlogPost, Promotion, SitePage, WholesalePriceList, WholesaleRequest

from .serializers import (
    BlogPostSerializer,
    PromotionSerializer,
    SitePageSerializer,
    WholesalePriceListSerializer,
    WholesaleRequestSerializer,
)


class PromotionViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Promotion.objects.filter(is_active=True)
    serializer_class = PromotionSerializer
    permission_classes = [permissions.AllowAny]


class BlogPostViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = BlogPostSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        queryset = BlogPost.objects.filter(status=BlogPost.PostStatus.PUBLISHED)
        slug = self.request.query_params.get("slug")
        if slug:
            queryset = queryset.filter(slug=slug)
        return queryset


class WholesalePriceListViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = WholesalePriceList.objects.filter(is_active=True)
    serializer_class = WholesalePriceListSerializer
    permission_classes = [permissions.AllowAny]


class WholesaleRequestViewSet(mixins.CreateModelMixin, viewsets.GenericViewSet):
    queryset = WholesaleRequest.objects.none()
    serializer_class = WholesaleRequestSerializer
    permission_classes = [permissions.AllowAny]


class SitePageViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = SitePage.objects.filter(is_published=True)
    serializer_class = SitePageSerializer
    permission_classes = [permissions.AllowAny]

