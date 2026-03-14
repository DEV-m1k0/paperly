from rest_framework import serializers

from shop.models import DeliveryTariff, PickupPoint


class PickupPointSerializer(serializers.ModelSerializer):
    class Meta:
        model = PickupPoint
        fields = "__all__"


class DeliveryTariffSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeliveryTariff
        fields = "__all__"
