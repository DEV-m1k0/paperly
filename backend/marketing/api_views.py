import logging

from rest_framework import mixins, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from shop.models import BlogPost, NewsletterSubscriber, Promotion, SitePage, WholesalePriceList, WholesaleRequest

from .emails import send_welcome_email
from .serializers import (
    BlogPostSerializer,
    NewsletterSubscribeSerializer,
    PromotionSerializer,
    SitePageSerializer,
    WholesalePriceListSerializer,
    WholesaleRequestSerializer,
)

logger = logging.getLogger(__name__)


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


class NewsletterSubscribeViewSet(viewsets.ViewSet):
    """POST /api/newsletter/subscribe/ — opt-in to the newsletter."""

    permission_classes = [permissions.AllowAny]

    def create(self, request):
        serializer = NewsletterSubscribeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"].lower().strip()
        source = serializer.validated_data.get("source", "footer") or "footer"

        subscriber, created = NewsletterSubscriber.objects.get_or_create(
            email=email, defaults={"source": source},
        )
        already_active = subscriber.is_active and not created
        if not subscriber.is_active:
            subscriber.is_active = True
            subscriber.unsubscribed_at = None
            subscriber.save(update_fields=["is_active", "unsubscribed_at", "updated_at"])

        # Send welcome email on first subscription OR on re-subscribe after unsubscribe.
        sent = False
        if not already_active:
            sent = send_welcome_email(subscriber, request=request)
            if not sent:
                logger.warning("Welcome email could not be sent to %s", email)

        if already_active:
            message = "Вы уже подписаны — спасибо, что с нами!"
        elif sent:
            message = "Готово! Мы отправили письмо с подтверждением — проверьте почту."
        else:
            # SMTP failed but DB was saved; don't hide the fact.
            message = "Вы подписаны! (Письмо-приветствие отправим чуть позже.)"

        return Response(
            {"message": message, "already_subscribed": already_active},
            status=status.HTTP_201_CREATED if not already_active else status.HTTP_200_OK,
        )

