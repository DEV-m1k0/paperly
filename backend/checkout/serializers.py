from decimal import Decimal

from django.db import transaction
from django.db.models import F
from rest_framework import serializers

from shop.models import Cart, CartItem, Order, OrderItem, Product


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
            'unit_price': {'required': False},
        }

    def create(self, validated_data):
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
        read_only_fields = ('user', 'number', 'subtotal', 'total')

    def validate_items(self, items_data):
        if not items_data:
            raise serializers.ValidationError("Заказ должен содержать хотя бы одну позицию.")
        for item in items_data:
            product = item.get('product')
            quantity = item.get('quantity', 1)
            if not product:
                raise serializers.ValidationError("Каждая позиция должна содержать товар.")
            if product.status != Product.ProductStatus.ACTIVE:
                raise serializers.ValidationError(f'Товар "{product.title}" недоступен для заказа.')
            if product.stock < quantity:
                raise serializers.ValidationError(
                    f'Недостаточно товара "{product.title}" на складе '
                    f'(доступно: {product.stock}, запрошено: {quantity}).'
                )
        return items_data

    def validate(self, attrs):
        delivery_type = attrs.get('delivery_type')
        pickup_point = attrs.get('pickup_point')
        if delivery_type == Order.DeliveryType.PICKUP and not pickup_point:
            raise serializers.ValidationError(
                {"pickup_point": "Укажите пункт самовывоза для типа доставки «Самовывоз»."}
            )
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        items_data = validated_data.pop('items')

        last_order = Order.objects.order_by('-id').values_list('id', flat=True).first()
        next_num = (last_order or 0) + 1
        validated_data['number'] = f"ORD-{next_num:06d}"

        subtotal = Decimal('0')
        for item in items_data:
            product = item['product']
            quantity = item.get('quantity', 1)
            unit_price = product.price
            item['unit_price'] = unit_price
            subtotal += unit_price * quantity

        validated_data['subtotal'] = subtotal
        delivery_price = validated_data.get('delivery_price', Decimal('0'))
        discount_amount = validated_data.get('discount_amount', Decimal('0'))
        validated_data['total'] = subtotal + delivery_price - discount_amount

        order = Order.objects.create(**validated_data)

        for item_data in items_data:
            product = item_data['product']
            quantity = item_data.get('quantity', 1)
            if not item_data.get('title_snapshot'):
                item_data['title_snapshot'] = product.title
            if not item_data.get('sku_snapshot'):
                item_data['sku_snapshot'] = product.sku
            OrderItem.objects.create(order=order, **item_data)
            Product.objects.filter(pk=product.pk).update(stock=F('stock') - quantity)

        return order
