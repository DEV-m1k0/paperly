from rest_framework import serializers

from shop.models import BlogPost, GiftCertificate, Promotion, SitePage, WholesalePriceList, WholesaleRequest


class PromotionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Promotion
        fields = "__all__"


class GiftCertificateSerializer(serializers.ModelSerializer):
    class Meta:
        model = GiftCertificate
        fields = "__all__"


class BlogPostSerializer(serializers.ModelSerializer):
    class Meta:
        model = BlogPost
        fields = "__all__"


class WholesalePriceListSerializer(serializers.ModelSerializer):
    class Meta:
        model = WholesalePriceList
        fields = "__all__"


class WholesaleRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = WholesaleRequest
        fields = "__all__"


class SitePageSerializer(serializers.ModelSerializer):
    class Meta:
        model = SitePage
        fields = "__all__"
