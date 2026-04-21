from rest_framework import serializers

from shop.models import BlogPost, Promotion, SitePage, WholesalePriceList, WholesaleRequest


class PromotionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Promotion
        fields = [
            "id", "title", "slug", "description", "promo_type",
            "discount_percent", "start_at", "end_at", "is_active",
        ]


class BlogPostSerializer(serializers.ModelSerializer):
    cover_url = serializers.SerializerMethodField()

    class Meta:
        model = BlogPost
        fields = [
            "id", "title", "slug", "category", "excerpt",
            "content", "cover_url", "status", "published_at",
        ]

    def get_cover_url(self, obj):
        if obj.cover:
            request = self.context.get("request")
            if request:
                return request.build_absolute_uri(obj.cover.url)
            return obj.cover.url
        return obj.cover_url


class WholesalePriceListSerializer(serializers.ModelSerializer):
    class Meta:
        model = WholesalePriceList
        fields = ["id", "title", "slug", "segment", "file_url", "is_active"]


class WholesaleRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = WholesaleRequest
        fields = [
            "id", "organization_name", "organization_type",
            "contact_person", "phone", "email", "comment",
        ]
        read_only_fields = ("status",)


class SitePageSerializer(serializers.ModelSerializer):
    class Meta:
        model = SitePage
        fields = ["id", "title", "slug", "page_type", "content", "is_published"]
