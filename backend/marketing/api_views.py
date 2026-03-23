from rest_framework import permissions, viewsets

from shop.models import BlogPost, GiftCertificate, Promotion, SitePage, WholesalePriceList, WholesaleRequest

from .serializers import (
    BlogPostSerializer,
    GiftCertificateSerializer,
    PromotionSerializer,
    SitePageSerializer,
    WholesalePriceListSerializer,
    WholesaleRequestSerializer,
)


class PromotionViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Promotion.objects.filter(is_active=True)
    serializer_class = PromotionSerializer


class GiftCertificateViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = GiftCertificate.objects.filter(is_active=True)
    serializer_class = GiftCertificateSerializer


class BlogPostViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = BlogPostSerializer

    def get_queryset(self):
        queryset = BlogPost.objects.filter(status=BlogPost.PostStatus.PUBLISHED)
        slug = self.request.query_params.get("slug")
        if slug:
            queryset = queryset.filter(slug=slug)
        return queryset



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

