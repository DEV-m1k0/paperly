from django.shortcuts import redirect, render

PAGE_TO_TEMPLATE = {
    "home": "index.html",
    "catalog": "catalog.html",
    "category": "category.html",
    "product": "product.html",
    "about": "about.html",
    "delivery": "delivery.html",
    "pickup": "pickup.html",
    "guarantee": "guarantee.html",
    "wholesale": "wholesale.html",
    "auth": "auth.html",
    "profile": "profile.html",
    "order_history": "order-history.html",
    "favorites": "favorites.html",
    "cart": "cart.html",
    "promotions": "promotions.html",
    "new_arrivals": "new-arrivals.html",
    "bestsellers": "bestsellers.html",
    "brands": "brands.html",
    "blog": "blog.html",
}

LEGACY_PAGE_TO_NAME = {
    "index": "home",
    "catalog": "catalog",
    "category": "category",
    "product": "product",
    "about": "about",
    "delivery": "delivery",
    "pickup": "pickup",
    "guarantee": "guarantee",
    "wholesale": "wholesale",
    "auth": "auth",
    "profile": "profile",
    "order-history": "order_history",
    "favorites": "favorites",
    "cart": "cart",
    "promotions": "promotions",
    "new-arrivals": "new_arrivals",
    "bestsellers": "bestsellers",
    "brands": "brands",
    "blog": "blog",
}


def page_view(request, page_name):
    template_name = PAGE_TO_TEMPLATE[page_name]
    return render(request, template_name)


def legacy_html_redirect(request, page):
    route_name = LEGACY_PAGE_TO_NAME.get(page)
    if route_name is None:
        return redirect("home", permanent=True)
    return redirect(route_name, permanent=True)
