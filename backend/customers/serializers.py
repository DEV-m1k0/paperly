from rest_framework import serializers

from shop.models import Address, CustomerProfile, Favorite, NotificationSetting


class CustomerProfileSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(required=False, write_only=True)
    user_email = serializers.EmailField(source="user.email", read_only=True)
    user_first_name = serializers.CharField(source="user.first_name", read_only=True)
    user_last_name = serializers.CharField(source="user.last_name", read_only=True)

    class Meta:
        model = CustomerProfile
        fields = "__all__"
        read_only_fields = ("user",)

    def _apply_user_email(self, instance, validated_data):
        email = validated_data.get("email")
        if email:
            instance.user.email = email
            instance.user.save(update_fields=["email"])

    def create(self, validated_data):
        email = validated_data.pop("email", None)
        profile = super().create(validated_data)
        if email:
            self._apply_user_email(profile, {"email": email})
        return profile

    def update(self, instance, validated_data):
        email = validated_data.pop("email", None)
        instance = super().update(instance, validated_data)
        if email:
            self._apply_user_email(instance, {"email": email})
        return instance


class AddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = Address
        fields = "__all__"
        read_only_fields = ("profile",)


class NotificationSettingSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationSetting
        fields = "__all__"
        read_only_fields = ("profile",)


class FavoriteSerializer(serializers.ModelSerializer):
    product_title = serializers.CharField(source="product.title", read_only=True)
    product_price = serializers.DecimalField(
        source="product.price", max_digits=10, decimal_places=2, read_only=True
    )
    product_old_price = serializers.DecimalField(
        source="product.old_price", max_digits=10, decimal_places=2, read_only=True
    )
    product_brand_name = serializers.CharField(source="product.brand.name", read_only=True)
    product_brand_slug = serializers.CharField(source="product.brand.slug", read_only=True)
    product_short_description = serializers.CharField(
        source="product.short_description", read_only=True
    )
    product_slug = serializers.CharField(source="product.slug", read_only=True)
    product_category_slugs = serializers.SlugRelatedField(
        source="product.categories", many=True, read_only=True, slug_field="slug"
    )
    product_stock = serializers.IntegerField(source="product.stock", read_only=True)
    product_is_new = serializers.BooleanField(source="product.is_new", read_only=True)
    product_is_hit = serializers.BooleanField(source="product.is_hit", read_only=True)
    product_is_featured = serializers.BooleanField(source="product.is_featured", read_only=True)
    product_format = serializers.CharField(source="product.format", read_only=True)
    product_sheets_count = serializers.IntegerField(source="product.sheets_count", read_only=True)
    product_purpose = serializers.CharField(source="product.purpose", read_only=True)
    product_avg_rating = serializers.FloatField(read_only=True)
    product_reviews_count = serializers.IntegerField(read_only=True)
    product_image = serializers.SerializerMethodField()

    class Meta:
        model = Favorite
        fields = "__all__"
        read_only_fields = ("user",)

    def get_product_image(self, obj):
        if not obj.product:
            return ""
        image = obj.product.images.first()
        if not image:
            return ""
        if image.image:
            request = self.context.get("request")
            if request:
                return request.build_absolute_uri(image.image.url)
            return image.image.url
        return image.image_url or ""
