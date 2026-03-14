from rest_framework import serializers

from .models import (
    Address,
    BlogCategory,
    BlogPost,
    Brand,
    Cart,
    CartItem,
    Category,
    CustomerProfile,
    DeliveryTariff,
    Favorite,
    GiftCertificate,
    NotificationSetting,
    Order,
    OrderItem,
    PickupPoint,
    Product,
    ProductImage,
    ProductReview,
    ProductSpecification,
    Promotion,
    SitePage,
    WholesalePriceList,
    WholesaleRequest,
)


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = "__all__"


class BrandSerializer(serializers.ModelSerializer):
    class Meta:
        model = Brand
        fields = "__all__"


class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = "__all__"


class ProductSpecificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductSpecification
        fields = "__all__"


class ProductReviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductReview
        fields = "__all__"
        read_only_fields = ("user",)


class ProductSerializer(serializers.ModelSerializer):
    images = ProductImageSerializer(many=True, read_only=True)
    specifications = ProductSpecificationSerializer(many=True, read_only=True)
    reviews = ProductReviewSerializer(many=True, read_only=True)

    class Meta:
        model = Product
        fields = "__all__"


class PromotionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Promotion
        fields = "__all__"


class GiftCertificateSerializer(serializers.ModelSerializer):
    class Meta:
        model = GiftCertificate
        fields = "__all__"


class BlogCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = BlogCategory
        fields = "__all__"


class BlogPostSerializer(serializers.ModelSerializer):
    class Meta:
        model = BlogPost
        fields = "__all__"


class PickupPointSerializer(serializers.ModelSerializer):
    class Meta:
        model = PickupPoint
        fields = "__all__"


class DeliveryTariffSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeliveryTariff
        fields = "__all__"


class CustomerProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomerProfile
        fields = "__all__"
        read_only_fields = ("user",)


class AddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = Address
        fields = "__all__"


class NotificationSettingSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationSetting
        fields = "__all__"


class FavoriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Favorite
        fields = "__all__"
        read_only_fields = ("user",)


class CartItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = CartItem
        fields = "__all__"


class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)

    class Meta:
        model = Cart
        fields = "__all__"
        read_only_fields = ("user",)


class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = "__all__"
        extra_kwargs = {
            'title_snapshot': {'required': False, 'allow_blank': True},
            'sku_snapshot': {'required': False, 'allow_blank': True},
        }

    def create(self, validated_data):
        # Автоматически заполняем название и артикул, если они не переданы
        if not validated_data.get('title_snapshot') and validated_data.get('product'):
            validated_data['title_snapshot'] = validated_data['product'].title
        if not validated_data.get('sku_snapshot') and validated_data.get('product'):
            validated_data['sku_snapshot'] = validated_data['product'].sku
        return super().create(validated_data)


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True)

    class Meta:
        model = Order
        fields = "__all__"
        read_only_fields = ("user", "number")

    def create(self, validated_data):
        items_data = validated_data.pop('items')
        # Генерируем номер заказа, например, из первых 8 символов UUID
        import uuid
        validated_data['number'] = str(uuid.uuid4())[:8].upper()
        order = Order.objects.create(**validated_data)
        for item_data in items_data:
            OrderItem.objects.create(order=order, **item_data)
        return order

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
