from rest_framework import permissions, viewsets

from shop.models import DeliveryTariff, PickupPoint

from .serializers import DeliveryTariffSerializer, PickupPointSerializer


class PickupPointViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = PickupPoint.objects.filter(is_active=True)
    serializer_class = PickupPointSerializer
    permission_classes = [permissions.AllowAny]


class DeliveryTariffViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = DeliveryTariff.objects.filter(is_active=True)
    serializer_class = DeliveryTariffSerializer
    permission_classes = [permissions.AllowAny]
