from django.db import models
from rest_framework import permissions, viewsets

from shop.models import Address, CustomerProfile, Favorite, NotificationSetting

from .serializers import AddressSerializer, CustomerProfileSerializer, FavoriteSerializer, NotificationSettingSerializer


class CustomerProfileViewSet(viewsets.ModelViewSet):
    serializer_class = CustomerProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return CustomerProfile.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class AddressViewSet(viewsets.ModelViewSet):
    serializer_class = AddressSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Address.objects.filter(profile__user=self.request.user)

    def perform_create(self, serializer):
        profile, _ = CustomerProfile.objects.get_or_create(user=self.request.user)
        serializer.save(profile=profile)


class NotificationSettingViewSet(viewsets.ModelViewSet):
    serializer_class = NotificationSettingSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return NotificationSetting.objects.filter(profile__user=self.request.user)

    def perform_create(self, serializer):
        profile, _ = CustomerProfile.objects.get_or_create(user=self.request.user)
        serializer.save(profile=profile)


class FavoriteViewSet(viewsets.ModelViewSet):
    serializer_class = FavoriteSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return (
            Favorite.objects.filter(user=self.request.user)
            .select_related("product", "product__brand")
            .prefetch_related("product__images", "product__categories", "product__reviews")
            .annotate(
                product_avg_rating=models.Avg("product__reviews__rating"),
                product_reviews_count=models.Count("product__reviews", distinct=True),
            )
        )

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

