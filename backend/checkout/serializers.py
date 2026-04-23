from decimal import Decimal

from django.contrib.auth import get_user_model, login
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError, transaction
from django.db.models import F
from rest_framework import serializers

from shop.models import Address, Cart, CartItem, CustomerProfile, Order, OrderItem, Product

from .promo import PromoError, apply_promo, record_redemption

User = get_user_model()


def _sync_profile_from_order(user, order) -> None:
    """Backfill the customer's profile/address from the order — but only for
    fields that are empty. Never overwrite data the user has already saved.

    Runs for authenticated buyers whenever an order lands so the next checkout
    is faster: phone/name/address get captured the first time they enter them.
    """
    if not user or not user.is_authenticated:
        return

    profile, _ = CustomerProfile.objects.get_or_create(user=user)

    # ── Name → profile.first_name/last_name + User.first_name/last_name ──
    parsed_first = parsed_last = ""
    full_name = (order.full_name or "").strip()
    if full_name:
        parsed_first, _, parsed_last = full_name.partition(" ")

    changed_profile: list[str] = []
    if not profile.first_name and parsed_first:
        profile.first_name = parsed_first
        changed_profile.append("first_name")
    if not profile.last_name and parsed_last:
        profile.last_name = parsed_last
        changed_profile.append("last_name")
    if not profile.phone and order.phone:
        profile.phone = order.phone
        changed_profile.append("phone")
    if changed_profile:
        profile.save(update_fields=changed_profile + ["updated_at"])

    changed_user: list[str] = []
    if not user.first_name and parsed_first:
        user.first_name = parsed_first
        changed_user.append("first_name")
    if not user.last_name and parsed_last:
        user.last_name = parsed_last
        changed_user.append("last_name")
    if not user.email and order.email:
        user.email = order.email
        changed_user.append("email")
    if changed_user:
        user.save(update_fields=changed_user)

    # ── Shipping address → create if none exists yet (courier orders only) ──
    # Pickup orders store the PVZ name/address in `order.address`, not the user's home.
    if order.delivery_type == Order.DeliveryType.COURIER and order.city and order.address:
        has_shipping = profile.addresses.filter(address_type=Address.AddressType.SHIPPING).exists()
        if not has_shipping:
            Address.objects.create(
                profile=profile,
                address_type=Address.AddressType.SHIPPING,
                city=order.city,
                street=order.address,
                comment=order.comment or "",
                is_default=True,
            )


class CartItemSerializer(serializers.ModelSerializer):
    product_title = serializers.CharField(source="product.title", read_only=True)
    product_short_description = serializers.CharField(source="product.short_description", read_only=True)
    product_image = serializers.SerializerMethodField()

    class Meta:
        model = CartItem
        fields = [
            "id", "cart", "product", "quantity", "price_snapshot",
            "product_title", "product_short_description", "product_image",
        ]

    def get_product_image(self, obj):
        image = obj.product.images.first() if obj.product_id else None
        if not image:
            return ""
        if image.image:
            return image.image.url
        return image.image_url or ""

    def validate(self, attrs):
        request = self.context.get("request")
        cart = attrs.get("cart") or getattr(self.instance, "cart", None)
        if cart and request and request.user.is_authenticated and cart.user_id != request.user.id:
            raise serializers.ValidationError("Корзина принадлежит другому пользователю.")
        product = attrs.get("product") or getattr(self.instance, "product", None)
        quantity = attrs.get("quantity", getattr(self.instance, "quantity", 1))
        if product and product.max_order_quantity and quantity > product.max_order_quantity:
            raise serializers.ValidationError(
                f'Максимальное количество товара "{product.title}" — {product.max_order_quantity} шт.'
            )
        if not attrs.get("price_snapshot") and product:
            attrs["price_snapshot"] = product.price
        return attrs


class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)

    class Meta:
        model = Cart
        fields = ["id", "user", "session_key", "is_active", "items"]
        read_only_fields = ("user",)


class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = [
            "id", "order", "product", "title_snapshot",
            "sku_snapshot", "quantity", "unit_price",
        ]
        extra_kwargs = {
            'order': {'required': False},
            'title_snapshot': {'required': False, 'allow_blank': True},
            'sku_snapshot': {'required': False, 'allow_blank': True},
            'unit_price': {'required': False},
        }

    def create(self, validated_data):
        product = validated_data.get('product')
        if product:
            if not validated_data.get('title_snapshot'):
                validated_data['title_snapshot'] = product.title
            if not validated_data.get('sku_snapshot'):
                validated_data['sku_snapshot'] = product.sku
            if not validated_data.get('unit_price'):
                validated_data['unit_price'] = product.price
        return super().create(validated_data)


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True)
    create_account = serializers.BooleanField(required=False, default=False, write_only=True)
    account_password = serializers.CharField(required=False, allow_blank=True, write_only=True, trim_whitespace=False)
    account_created = serializers.BooleanField(read_only=True, required=False)
    promo_code_input = serializers.CharField(
        required=False, allow_blank=True, write_only=True, source="_promo_code_input",
        help_text="Code typed by the customer in checkout.",
    )
    promo_code_applied = serializers.CharField(read_only=True, required=False)

    class Meta:
        model = Order
        fields = [
            "id", "user", "number", "status", "full_name", "phone", "email",
            "city", "address", "comment", "delivery_type", "payment_type",
            "pickup_point", "subtotal", "delivery_price", "discount_amount",
            "total", "items", "created_at",
            "create_account", "account_password", "account_created",
            "promo_code_input", "promo_code_applied",
        ]
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
            if product.max_order_quantity > 0 and quantity > product.max_order_quantity:
                raise serializers.ValidationError(
                    f'Максимальное количество товара "{product.title}" в заказе — '
                    f'{product.max_order_quantity} шт.'
                )
        return items_data

    def validate(self, attrs):
        delivery_type = attrs.get('delivery_type')
        pickup_point = attrs.get('pickup_point')
        if delivery_type == Order.DeliveryType.PICKUP and not pickup_point:
            raise serializers.ValidationError(
                {"pickup_point": "Укажите пункт самовывоза для типа доставки «Самовывоз»."}
            )

        request = self.context.get("request")
        is_auth = request and request.user.is_authenticated
        create_account = attrs.get("create_account", False)
        password = attrs.get("account_password", "") or ""
        email = (attrs.get("email") or "").strip().lower()

        if create_account and is_auth:
            # Already logged in — ignore create_account flag silently.
            attrs["create_account"] = False
        elif create_account:
            if not email:
                raise serializers.ValidationError({"email": "Укажите email для создания аккаунта."})
            if len(password) < 8:
                raise serializers.ValidationError(
                    {"account_password": "Пароль должен содержать минимум 8 символов."}
                )
            if User.objects.filter(email__iexact=email).exists():
                raise serializers.ValidationError(
                    {"email": "Пользователь с таким email уже зарегистрирован. Войдите в аккаунт перед оформлением."}
                )
            # Validate password against Django's configured validators (common, numeric, length).
            try:
                validate_password(password)
            except DjangoValidationError as exc:
                raise serializers.ValidationError({"account_password": list(exc.messages)})

        return attrs

    @transaction.atomic
    def create(self, validated_data):
        items_data = validated_data.pop('items')
        create_account = validated_data.pop('create_account', False)
        password = validated_data.pop('account_password', '') or ''
        promo_code_input = (validated_data.pop('_promo_code_input', '') or '').strip()
        request = self.context.get("request")

        # ───── Optional: создаём аккаунт + логиним пользователя в сессию ─────
        account_created = False
        if create_account and request and not request.user.is_authenticated:
            email = validated_data.get('email', '').strip().lower()
            full_name = validated_data.get('full_name', '').strip()
            first_name, _, last_name = full_name.partition(' ')

            base_username = email.split('@')[0] or 'user'
            username = base_username
            suffix = 1
            while User.objects.filter(username__iexact=username).exists():
                suffix += 1
                username = f"{base_username}{suffix}"

            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=first_name or '',
                last_name=last_name or '',
            )
            CustomerProfile.objects.get_or_create(
                user=user,
                defaults={
                    'first_name': first_name or '',
                    'last_name': last_name or '',
                    'phone': validated_data.get('phone', '') or '',
                },
            )
            # Log them in using the session backend so subsequent requests are authenticated.
            user.backend = 'django.contrib.auth.backends.ModelBackend'
            login(request, user)
            validated_data['user'] = user
            account_created = True
        elif request and request.user.is_authenticated:
            validated_data['user'] = request.user

        # Generate unique order number
        last_id = Order.objects.select_for_update().order_by('-id').values_list('id', flat=True).first()
        validated_data['number'] = f"ORD-{(last_id or 0) + 1:06d}"

        # Lock products and re-validate stock inside transaction
        subtotal = Decimal('0')
        for item in items_data:
            product = Product.objects.select_for_update().get(pk=item['product'].pk)
            quantity = item.get('quantity', 1)
            if product.stock < quantity:
                raise serializers.ValidationError(
                    f'Недостаточно товара "{product.title}" на складе '
                    f'(доступно: {product.stock}, запрошено: {quantity}).'
                )
            unit_price = product.price
            item['unit_price'] = unit_price
            item['product'] = product
            subtotal += unit_price * quantity

        validated_data['subtotal'] = subtotal
        delivery_price = validated_data.get('delivery_price', Decimal('0'))

        # ───── Apply promo code (re-validated server-side) ─────
        promo_application = None
        if promo_code_input:
            try:
                promo_application = apply_promo(
                    promo_code_input,
                    subtotal=subtotal,
                    delivery_price=delivery_price,
                    items=items_data,
                    user=validated_data.get('user'),
                    email=(validated_data.get('email') or '').strip(),
                )
            except PromoError as exc:
                raise serializers.ValidationError({"promo_code_input": str(exc)})

        if promo_application:
            if promo_application.free_shipping:
                validated_data['delivery_price'] = Decimal('0')
                delivery_price = Decimal('0')
                validated_data['discount_amount'] = Decimal('0')
                discount_amount = Decimal('0')
            else:
                validated_data['discount_amount'] = promo_application.discount
                discount_amount = promo_application.discount
            validated_data['promo_code'] = promo_application.promo
        else:
            discount_amount = validated_data.get('discount_amount', Decimal('0'))

        validated_data['total'] = max(Decimal('0'), subtotal + delivery_price - discount_amount)

        try:
            order = Order.objects.create(**validated_data)
        except IntegrityError:
            # Order number collision — regenerate
            last_id = Order.objects.order_by('-id').values_list('id', flat=True).first()
            validated_data['number'] = f"ORD-{(last_id or 0) + 1:06d}"
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

        # Record promo redemption (atomic: bumps used_count + creates log row)
        if promo_application:
            record_redemption(
                promo_application,
                order=order,
                user=validated_data.get('user'),
                email=validated_data.get('email', ''),
            )
            order.promo_code_applied = promo_application.promo.code  # type: ignore[attr-defined]

        # Backfill customer profile + address from this order where empty.
        # Covers both freshly-registered and pre-existing authenticated users.
        _sync_profile_from_order(validated_data.get('user'), order)

        # Stash flag on instance so serializer renders `account_created` in response.
        order.account_created = account_created  # type: ignore[attr-defined]
        return order
