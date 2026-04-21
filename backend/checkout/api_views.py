from rest_framework import permissions, viewsets

from shop.models import Cart, CartItem, Order

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

    def get_queryset(self):
        if not self.request.user.is_authenticated:
            return Order.objects.none()
        return (
            Order.objects
            .filter(user=self.request.user)
            .select_related("pickup_point")
            .prefetch_related("items")
        )
