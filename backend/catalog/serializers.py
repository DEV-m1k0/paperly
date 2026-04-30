from rest_framework import serializers
from django.utils import timezone

from shop.models import (
    Brand,
    CatalogFilterGroup,
    CatalogFilterOption,
    Category,
    Product,
    ProductImage,
    ProductReview,
    ProductSpecification,
)


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = "__all__"


class BrandSerializer(serializers.ModelSerializer):
    product_count = serializers.IntegerField(read_only=True)
    logo_url = serializers.SerializerMethodField()

    class Meta:
        model = Brand
        fields = ["id", "name", "slug", "description", "logo_url", "website", "is_active", "product_count"]

    def get_logo_url(self, obj):
        if obj.logo:
            request = self.context.get("request")
            if request:
                return request.build_absolute_uri(obj.logo.url)
            return obj.logo.url
        return obj.logo_url


class CatalogFilterOptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = CatalogFilterOption
        fields = ("id", "label", "query_param", "value", "sort_order")


class CatalogFilterGroupSerializer(serializers.ModelSerializer):
    options = serializers.SerializerMethodField()

    # Brands list is cached per-context (one shared list per serializer
    # instantiation cycle) so a paginated list of N filter groups doesn't
    # produce N separate `Brand.objects.filter(...)` queries.
    def _get_brands_cached(self):
        cached = self.context.get("_brand_options_cache")
        if cached is not None:
            return cached
        brands = list(Brand.objects.filter(is_active=True).order_by("name"))
        payload = [
            {
                "id": brand.id,
                "label": brand.name,
                "query_param": "brand",
                "value": brand.slug,
                "sort_order": 0,
            }
            for brand in brands
        ]
        self.context["_brand_options_cache"] = payload
        return payload

    def get_options(self, obj):
        slug = (obj.slug or "").strip().lower()
        title = (obj.title or "").strip().lower()
        # Walk in-memory `options` (prefetched) instead of running a fresh
        # SELECT every serialize.
        active_options = [opt for opt in obj.options.all() if opt.is_active]
        has_brand_option = any(opt.query_param == "brand" for opt in active_options)
        is_brand_group = slug in {"brand", "brands"} or "бренд" in title or has_brand_option
        if is_brand_group:
            return self._get_brands_cached()
        return CatalogFilterOptionSerializer(active_options, many=True).data

    class Meta:
        model = CatalogFilterGroup
        fields = ("id", "title", "slug", "sort_order", "options")


class ProductImageSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = ProductImage
        fields = ["id", "product", "image_url", "alt_text", "is_primary", "sort_order"]

    def get_image_url(self, obj):
        if obj.image:
            version = int(obj.updated_at.timestamp()) if obj.updated_at else obj.pk
            request = self.context.get("request")
            if request:
                return request.build_absolute_uri(f"{obj.image.url}?v={version}")
            return f"{obj.image.url}?v={version}"
        return obj.image_url


class ProductSpecificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductSpecification
        fields = "__all__"


class ProductReviewSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = ProductReview
        fields = "__all__"
        read_only_fields = ("user",)


class ProductSerializer(serializers.ModelSerializer):
    images = ProductImageSerializer(many=True, read_only=True)
    specifications = ProductSpecificationSerializer(many=True, read_only=True)
    reviews = ProductReviewSerializer(many=True, read_only=True)
    brand_slug = serializers.CharField(source="brand.slug", read_only=True)
    brand_name = serializers.CharField(source="brand.name", read_only=True)
    category_slugs = serializers.SlugRelatedField(source="categories", many=True, read_only=True, slug_field="slug")
    category_names = serializers.SlugRelatedField(source="categories", many=True, read_only=True, slug_field="name")
    has_active_promotion = serializers.SerializerMethodField()
    active_promotion_title = serializers.SerializerMethodField()
    active_promotion_discount = serializers.SerializerMethodField()
    avg_rating = serializers.FloatField(read_only=True)
    reviews_count = serializers.IntegerField(read_only=True)

    def _get_active_promotion(self, obj):
        cache_attr = "_active_promotion_cache"
        if hasattr(obj, cache_attr):
            return getattr(obj, cache_attr)

        now = timezone.now()
        promotions = list(obj.promotions.all())
        active_promotions = [item for item in promotions if item.is_active and item.start_at <= now <= item.end_at]
        active_promotions.sort(key=lambda item: (item.discount_percent or 0, item.start_at), reverse=True)
        promotion = active_promotions[0] if active_promotions else None
        setattr(obj, cache_attr, promotion)
        return promotion

    def get_has_active_promotion(self, obj):
        return self._get_active_promotion(obj) is not None

    def get_active_promotion_title(self, obj):
        promotion = self._get_active_promotion(obj)
        return promotion.title if promotion else ""

    def get_active_promotion_discount(self, obj):
        promotion = self._get_active_promotion(obj)
        return promotion.discount_percent if promotion and promotion.discount_percent else None

    class Meta:
        model = Product
        fields = "__all__"
