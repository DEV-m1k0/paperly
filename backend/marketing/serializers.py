from rest_framework import serializers

from shop.models import BlogPost, Promotion, SitePage, WholesalePriceList, WholesaleRequest


class NewsletterSubscribeSerializer(serializers.Serializer):
    email = serializers.EmailField(max_length=254)
    source = serializers.CharField(max_length=64, required=False, allow_blank=True)


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
    organization_type = serializers.ChoiceField(
        choices=WholesaleRequest.OrganizationType.choices,
        default=WholesaleRequest.OrganizationType.OTHER,
        required=False,
    )

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
