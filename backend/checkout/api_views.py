from decimal import Decimal

from rest_framework import permissions, status, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView

from shop.models import Cart, CartItem, Order, Product

from .promo import PromoError, apply_promo
from .serializers import CartItemSerializer, CartSerializer, OrderSerializer


class CartViewSet(viewsets.ModelViewSet):
    serializer_class = CartSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Cart.objects.filter(user=self.request.user).prefetch_related("items", "items__product__images")

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class CartItemViewSet(viewsets.ModelViewSet):
    serializer_class = CartItemSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return (
            CartItem.objects
            .filter(cart__user=self.request.user)
            .select_related("product", "cart")
            .prefetch_related("product__images")
        )


class OrderPermission(permissions.BasePermission):
    """
    Guest users can POST a new order (guest checkout).
    Listing/retrieving/updating orders still requires authentication.
    """

    def has_permission(self, request, view):
        if view.action == "create":
            return True
        return request.user and request.user.is_authenticated


class OrderViewSet(viewsets.ModelViewSet):
    serializer_class = OrderSerializer
    permission_classes = [OrderPermission]
    # Tighter throttle on the create action — guest checkout is publicly
    # reachable, so a single client cannot flood the orders table. Read
    # actions still use the default user/anon throttle scopes.
    throttle_scope = "checkout"

    def get_queryset(self):
        if not self.request.user.is_authenticated:
            return Order.objects.none()
        return (
            Order.objects
            .filter(user=self.request.user)
            .select_related("pickup_point", "promo_code")
            .prefetch_related("items")
        )


class PromoCodeValidateView(APIView):
    """POST /api/promo-codes/validate/ — check if the code works for this cart.

    body: {
      code: "PAPERLY10",
      items: [{product: <id>, quantity: N, unit_price: X}, ...],
      delivery_price: 350,
      email: "user@example.com"   # optional, helps with per-user quota
    }
    response:
      200 {valid: true, code, discount_type, discount, free_shipping, new_total}
      400 {valid: false, message}
    """

    permission_classes = [permissions.AllowAny]
    throttle_scope = "anon"

    def post(self, request):
        payload = request.data or {}
        code = (payload.get("code") or "").strip()
        items_raw = payload.get("items") or []
        delivery_price = Decimal(str(payload.get("delivery_price") or 0))
        email = (payload.get("email") or "").strip()

        # Resolve product ids into objects + compute subtotal.
        product_ids = [int(i.get("product")) for i in items_raw if i.get("product")]
        products_map = {p.id: p for p in Product.objects.filter(id__in=product_ids).prefetch_related("categories")}
        items = []
        subtotal = Decimal("0")
        for row in items_raw:
            product = products_map.get(int(row.get("product", 0) or 0))
            if not product:
                continue
            qty = Decimal(str(row.get("quantity", 1) or 1))
            unit = Decimal(str(row.get("unit_price") or product.price))
            subtotal += qty * unit
            items.append({"product": product, "quantity": qty, "unit_price": unit})

        if not items:
            return Response(
                {"valid": False, "message": "Добавьте товары в корзину перед применением промокода."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            application = apply_promo(
                code,
                subtotal=subtotal,
                delivery_price=delivery_price,
                items=items,
                user=request.user,
                email=email,
            )
        except PromoError as exc:
            return Response({"valid": False, "message": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        new_delivery = Decimal("0") if application.free_shipping else delivery_price
        new_total = subtotal + new_delivery - (Decimal("0") if application.free_shipping else application.discount)

        return Response({
            "valid": True,
            "code": application.promo.code,
            "description": application.promo.description,
            "discount_type": application.promo.discount_type,
            "discount": float(application.discount),
            "free_shipping": application.free_shipping,
            "subtotal": float(subtotal),
            "delivery_price": float(new_delivery),
            "new_total": float(new_total),
            "message": _human_description(application),
        })


def _human_description(application) -> str:
    promo = application.promo
    if promo.discount_type == promo.DiscountType.PERCENT:
        return f"Скидка {int(promo.discount_value)}% применена: −{int(application.discount)} ₽"
    if promo.discount_type == promo.DiscountType.FIXED:
        return f"Скидка {int(application.discount)} ₽ применена"
    if promo.discount_type == promo.DiscountType.FREE_SHIPPING:
        return "Бесплатная доставка применена"
    return "Промокод применён"
