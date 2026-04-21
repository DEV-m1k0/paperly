from django.urls import path

from .chat_views import ChatAPIView
from .views import (
    auth_password_reset_confirm_view,
    auth_view,
    legacy_html_redirect,
    legal_view,
    logout_view,
    page_view,
)

urlpatterns = [
    path("api/chat/", ChatAPIView.as_view(), name="chat_api"),
    path("", page_view, {"page_name": "home"}, name="home"),
    path("catalog/", page_view, {"page_name": "catalog"}, name="catalog"),
    path("category/", page_view, {"page_name": "category"}, name="category"),
    path("product/", page_view, {"page_name": "product"}, name="product"),
    path("about/", page_view, {"page_name": "about"}, name="about"),
    path("delivery/", page_view, {"page_name": "delivery"}, name="delivery"),
    path("pickup/", page_view, {"page_name": "pickup"}, name="pickup"),
    path("guarantee/", page_view, {"page_name": "guarantee"}, name="guarantee"),
    path("wholesale/", page_view, {"page_name": "wholesale"}, name="wholesale"),
    path("auth/", auth_view, name="auth"),
    path(
        "auth/reset/<uidb64>/<token>/",
        auth_password_reset_confirm_view,
        name="auth_password_reset_confirm",
    ),
    path("logout/", logout_view, name="logout"),
    path("profile/", page_view, {"page_name": "profile"}, name="profile"),
    path("order-history/", page_view, {"page_name": "order_history"}, name="order_history"),
    path("favorites/", page_view, {"page_name": "favorites"}, name="favorites"),
    path("cart/", page_view, {"page_name": "cart"}, name="cart"),
    path("promotions/", page_view, {"page_name": "promotions"}, name="promotions"),
    path("new-arrivals/", page_view, {"page_name": "new_arrivals"}, name="new_arrivals"),
    path("bestsellers/", page_view, {"page_name": "bestsellers"}, name="bestsellers"),
    path("brands/", page_view, {"page_name": "brands"}, name="brands"),
    path("blog/", page_view, {"page_name": "blog"}, name="blog"),
    path("legal/privacy/", legal_view, {"kind": "privacy"}, name="legal_privacy"),
    path("legal/terms/", legal_view, {"kind": "offer"}, name="legal_offer"),
    path("legal/cookies/", legal_view, {"kind": "cookies"}, name="legal_cookies"),
    path("<slug:page>.html", legacy_html_redirect, name="legacy_html_redirect"),
]
