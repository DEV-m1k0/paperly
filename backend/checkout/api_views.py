import base64
from decimal import Decimal
from io import BytesIO
from uuid import uuid4

import qrcode
from django.core.cache import cache
from django.http import HttpResponse
from django.urls import reverse
from django.utils import timezone
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


SBP_PAYMENT_TTL = 60 * 5


def _sbp_key(token: str) -> str:
    return f"sbp-payment:{token}"


def _build_sbp_qr_png(url: str) -> bytes:
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=8,
        border=2,
    )
    qr.add_data(url)
    qr.make(fit=True)
    image = qr.make_image(fill_color="#0e766e", back_color="white")
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


class SbpPaymentSessionView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_scope = "anon"

    def post(self, request):
        amount = Decimal(str(request.data.get("amount") or "0"))
        if amount <= 0:
            return Response({"detail": "Некорректная сумма для оплаты."}, status=status.HTTP_400_BAD_REQUEST)

        token = uuid4().hex
        confirm_url = request.build_absolute_uri(reverse("api-sbp-payments-confirm", args=[token]))
        qr_png = _build_sbp_qr_png(confirm_url)
        session_data = {
            "status": "pending",
            "amount": str(amount),
            "created_at": timezone.now().isoformat(),
            "confirmed_at": None,
        }
        cache.set(_sbp_key(token), session_data, timeout=SBP_PAYMENT_TTL)
        return Response({
            "token": token,
            "status": "pending",
            "expires_in": SBP_PAYMENT_TTL,
            "confirm_url": confirm_url,
            "qr_image": f"data:image/png;base64,{base64.b64encode(qr_png).decode('ascii')}",
        })


class SbpPaymentSessionStatusView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_scope = "anon"

    def get(self, request, token: str):
        session_data = cache.get(_sbp_key(token))
        if not session_data:
            return Response({"status": "expired"}, status=status.HTTP_404_NOT_FOUND)
        return Response({
            "token": token,
            "status": session_data["status"],
            "confirmed_at": session_data.get("confirmed_at"),
        })


class SbpPaymentConfirmView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_scope = "anon"

    def get(self, request, token: str):
        session_data = cache.get(_sbp_key(token))
        if not session_data:
            return HttpResponse(
                "<h1>Платёж недоступен</h1><p>Сессия оплаты истекла. Вернитесь в корзину и создайте новый QR-код.</p>",
                status=404,
            )

        if session_data["status"] != "paid":
            session_data["status"] = "paid"
            session_data["confirmed_at"] = timezone.now().isoformat()
            cache.set(_sbp_key(token), session_data, timeout=SBP_PAYMENT_TTL)

        return HttpResponse(
            """
            <!doctype html>
            <html lang="ru">
            <head>
              <meta charset="utf-8">
              <meta name="viewport" content="width=device-width, initial-scale=1">
              <title>Оплата подтверждена</title>
              <style>
                body{margin:0;font-family:Manrope,Arial,sans-serif;background:linear-gradient(135deg,#eefaf8,#fffaf0);color:#17323a;display:grid;place-items:center;min-height:100vh}
                .card{max-width:420px;padding:32px 28px;border-radius:24px;background:#fff;box-shadow:0 24px 60px -26px rgba(14,118,110,.28);text-align:center;border:1px solid rgba(14,118,110,.12)}
                .icon{width:72px;height:72px;margin:0 auto 16px;border-radius:22px;background:linear-gradient(135deg,#0e766e,#14a396);color:#fff;display:grid;place-items:center;font-size:36px}
                h1{margin:0 0 10px;font:700 32px/1.1 Prata,serif}
                p{margin:0;color:#5d7680;line-height:1.55}
              </style>
            </head>
            <body>
              <div class="card">
                <div class="icon">✓</div>
                <h1>Оплата подтверждена</h1>
                <p>Возвращайтесь в корзину Paperly. Заказ завершится автоматически.</p>
              </div>
            </body>
            </html>
            """,
        )
