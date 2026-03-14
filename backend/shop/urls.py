from django.urls import path

from .views import legacy_html_redirect, page_view

urlpatterns = [
    path("", page_view, {"page_name": "home"}, name="home"),
    path("catalog/", page_view, {"page_name": "catalog"}, name="catalog"),
    path("category/", page_view, {"page_name": "category"}, name="category"),
    path("product/", page_view, {"page_name": "product"}, name="product"),
    path("about/", page_view, {"page_name": "about"}, name="about"),
    path("delivery/", page_view, {"page_name": "delivery"}, name="delivery"),
    path("pickup/", page_view, {"page_name": "pickup"}, name="pickup"),
    path("guarantee/", page_view, {"page_name": "guarantee"}, name="guarantee"),
    path("wholesale/", page_view, {"page_name": "wholesale"}, name="wholesale"),
    path("auth/", page_view, {"page_name": "auth"}, name="auth"),
    path("profile/", page_view, {"page_name": "profile"}, name="profile"),
    path("order-history/", page_view, {"page_name": "order_history"}, name="order_history"),
    path("favorites/", page_view, {"page_name": "favorites"}, name="favorites"),
    path("cart/", page_view, {"page_name": "cart"}, name="cart"),
    path("promotions/", page_view, {"page_name": "promotions"}, name="promotions"),
    path("new-arrivals/", page_view, {"page_name": "new_arrivals"}, name="new_arrivals"),
    path("bestsellers/", page_view, {"page_name": "bestsellers"}, name="bestsellers"),
    path("brands/", page_view, {"page_name": "brands"}, name="brands"),
    path("blog/", page_view, {"page_name": "blog"}, name="blog"),
    path("<slug:page>.html", legacy_html_redirect, name="legacy_html_redirect"),
]
