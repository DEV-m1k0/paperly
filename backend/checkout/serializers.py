from uuid import uuid4
from rest_framework import serializers
from shop.models import Cart, CartItem, Order, OrderItem


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
        fields = '__all__'
        extra_kwargs = {
            'order': {'required': False},
            'title_snapshot': {'required': False, 'allow_blank': True},
            'sku_snapshot': {'required': False, 'allow_blank': True},
        }

    def create(self, validated_data):
        # Автоматически заполняем название и артикул из продукта, если они не переданы
        if not validated_data.get('title_snapshot') and validated_data.get('product'):
            validated_data['title_snapshot'] = validated_data['product'].title
        if not validated_data.get('sku_snapshot') and validated_data.get('product'):
            validated_data['sku_snapshot'] = validated_data['product'].sku
        return super().create(validated_data)


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True)

    class Meta:
        model = Order
        fields = '__all__'
        read_only_fields = ('user', 'number')

    def create(self, validated_data):
        items_data = validated_data.pop('items')
        import uuid
        validated_data['number'] = str(uuid.uuid4())[:8].upper()
        order = Order.objects.create(**validated_data)

        for item_data in items_data:
            # Явно заполняем title_snapshot и sku_snapshot из продукта, если они отсутствуют
            product = item_data.get('product')
            if product:
                if not item_data.get('title_snapshot'):
                    item_data['title_snapshot'] = product.title
                if not item_data.get('sku_snapshot'):
                    item_data['sku_snapshot'] = product.sku
            OrderItem.objects.create(order=order, **item_data)

        return order