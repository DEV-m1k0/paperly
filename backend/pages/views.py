import re
from urllib.parse import urlencode

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, get_user_model, login, logout
from django.contrib.auth.forms import PasswordResetForm, SetPasswordForm
from django.contrib.auth.tokens import default_token_generator
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.encoding import force_str
from django.utils.http import url_has_allowed_host_and_scheme, urlsafe_base64_decode
from django.views.decorators.http import require_POST

from shop.models import (
    Address,
    BlogCategory,
    BlogPost,
    Brand,
    Category,
    CustomerProfile,
    DeliveryTariff,
    NotificationSetting,
    Order,
    PickupPoint,
    Product,
    SitePage,
    SiteSetting,
)

from .forms import LoginByEmailForm, PasswordRestoreForm, RegistrationForm

User = get_user_model()

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


PAGE_TYPE_MAP = {
    "home": SitePage.PageType.INDEX,
    "about": SitePage.PageType.ABOUT,
    "delivery": SitePage.PageType.DELIVERY,
    "guarantee": SitePage.PageType.GUARANTEE,
    "wholesale": SitePage.PageType.WHOLESALE,
    "pickup": SitePage.PageType.PICKUP,
}

PROTECTED_PAGES = {"profile", "order_history"}


def _build_initials(first_name, last_name, email):
    initials = ""
    if first_name:
        initials += first_name[:1].upper()
    if last_name:
        initials += last_name[:1].upper()
    if not initials and email:
        initials = email[:2].upper()
    return initials or "PL"


def _about_context():
    products_qs = Product.objects.filter(status=Product.ProductStatus.ACTIVE)
    products_count = products_qs.count()
    brands_count = Brand.objects.filter(is_active=True).count()
    categories_count = Category.objects.filter(is_active=True).count()
    pickup_count = PickupPoint.objects.filter(is_active=True).count()
    customers_count = CustomerProfile.objects.count()
    orders_done = Order.objects.filter(status=Order.OrderStatus.DONE).count()

    courier_tariffs = DeliveryTariff.objects.filter(
        is_active=True, delivery_type=DeliveryTariff.DeliveryType.COURIER
    )
    eta_values = [t.eta_min_days for t in courier_tariffs if t.eta_min_days] + [
        t.eta_max_days for t in courier_tariffs if t.eta_max_days
    ]
    delivery_min = min(eta_values) if eta_values else None
    delivery_max = max(eta_values) if eta_values else None
    if delivery_min and delivery_max:
        delivery_eta_text = f"{delivery_min}" if delivery_min == delivery_max else f"{delivery_min}–{delivery_max}"
        delivery_eta_unit = "день" if delivery_max == 1 else ("дня" if delivery_max in (2, 3, 4) else "дней")
    else:
        delivery_eta_text = "1–2"
        delivery_eta_unit = "дня"

    site = SiteSetting.load()

    return {
        "about_stats": [
            {"value": str(products_count) if products_count else "—", "label": "активных товаров"},
            {"value": f"{brands_count}" if brands_count else "—", "label": "брендов в каталоге"},
            {"value": f"{pickup_count}" if pickup_count else "—", "label": f"пунктов выдачи в г. {site.city or 'городе'}" if pickup_count else "пунктов выдачи"},
            {"value": f"{delivery_eta_text} {delivery_eta_unit}", "label": "доставка по городу"},
        ],
        "about_extras": {
            "categories_count": categories_count,
            "customers_count": max(customers_count, orders_done),
            "orders_done": orders_done,
        },
    }


def page_view(request, page_name):
    if page_name in PROTECTED_PAGES and not request.user.is_authenticated:
        query = urlencode({"mode": "login", "next": request.get_full_path()})
        return redirect(f"{reverse('auth')}?{query}")

    template_name = PAGE_TO_TEMPLATE[page_name]
    context = {}

    page_type = PAGE_TYPE_MAP.get(page_name)
    if page_type:
        site_page = SitePage.objects.filter(page_type=page_type, is_published=True).first()
        if site_page:
            context["page_content"] = site_page.content
            context["page_title"] = site_page.title

    if page_name == "about":
        context.update(_about_context())

    if page_name == "home":
        home_ctx = _about_context()
        context["home_stats"] = home_ctx["about_stats"]
        context["home_extras"] = home_ctx["about_extras"]

    if page_name == "delivery":
        context["delivery_tariffs"] = list(
            DeliveryTariff.objects.filter(is_active=True).order_by("delivery_type", "city")
        )
        context["pickup_count"] = PickupPoint.objects.filter(is_active=True).count()

    if page_name == "pickup":
        context["pickup_points"] = list(
            PickupPoint.objects.filter(is_active=True).order_by("city", "name")
        )

    if page_name == "blog":
        slug = request.GET.get("slug")
        published = BlogPost.objects.filter(status=BlogPost.PostStatus.PUBLISHED).select_related("category")
        search_query = (request.GET.get("q") or "").strip()
        active_category = request.GET.get("category", "")

        post = BlogPost.objects.filter(slug=slug).select_related("category").first() if slug else None

        posts_qs = published.order_by("-published_at", "-created_at")
        if active_category:
            posts_qs = posts_qs.filter(category__slug=active_category)
        if search_query:
            from django.db.models import Q
            posts_qs = posts_qs.filter(Q(title__icontains=search_query) | Q(excerpt__icontains=search_query) | Q(content__icontains=search_query))
        posts_list = list(posts_qs)

        # Per-category counts for filter chips
        from django.db.models import Count
        category_counts = dict(
            published.values_list("category__slug").annotate(n=Count("id"))
        )
        categories_with_counts = [
            {"title": cat.title, "slug": cat.slug, "count": category_counts.get(cat.slug, 0)}
            for cat in BlogCategory.objects.all()
        ]

        # Detail-view extras: related (same category, excl. current), prev/next chronologically
        related_posts = []
        prev_post = next_post = None
        reading_minutes = None
        if post:
            if post.category_id:
                related_posts = list(
                    published.filter(category_id=post.category_id)
                    .exclude(id=post.id)
                    .order_by("-published_at", "-created_at")[:3]
                )
            if not related_posts:
                related_posts = list(
                    published.exclude(id=post.id).order_by("-published_at", "-created_at")[:3]
                )
            # Simple chronological prev/next
            ordered = list(published.order_by("-published_at", "-created_at"))
            try:
                idx = next(i for i, p in enumerate(ordered) if p.id == post.id)
                prev_post = ordered[idx + 1] if idx + 1 < len(ordered) else None
                next_post = ordered[idx - 1] if idx > 0 else None
            except StopIteration:
                pass
            # Reading time ≈ 180 words/minute
            word_count = len((post.content or "").split())
            reading_minutes = max(1, round(word_count / 180)) if word_count else 1

        context.update(
            {
                "blog_post": post,
                "blog_posts": posts_list,
                "blog_total_count": published.count(),
                "blog_categories": categories_with_counts,
                "active_category": active_category,
                "blog_search_query": search_query,
                "related_posts": related_posts,
                "prev_post": prev_post,
                "next_post": next_post,
                "reading_minutes": reading_minutes,
            }
        )

    if page_name == "profile" and request.user.is_authenticated:
        profile = CustomerProfile.objects.filter(user=request.user).first()
        address = (
            Address.objects.filter(profile=profile)
            .order_by("-is_default", "-updated_at")
            .first()
            if profile
            else None
        )
        notifications = (
            NotificationSetting.objects.filter(profile=profile).first() if profile else None
        )

        first_name = (profile.first_name if profile else "") or request.user.first_name
        last_name = (profile.last_name if profile else "") or request.user.last_name

        from shop.models import Favorite
        from django.db.models import Sum
        orders_qs = Order.objects.filter(user=request.user)
        orders_count = orders_qs.count()
        orders_done_sum = orders_qs.filter(status=Order.OrderStatus.DONE).aggregate(total=Sum("total"))["total"] or 0
        favorites_count = Favorite.objects.filter(user=request.user).count()

        # Profile completeness %
        completeness_fields = [first_name, last_name, request.user.email, profile.phone if profile else "", profile.birth_date if profile else None, address.city if address else "", address.street if address else ""]
        filled = sum(1 for v in completeness_fields if v)
        completeness_pct = int(round(filled / len(completeness_fields) * 100))

        member_since = request.user.date_joined

        context.update(
            {
                "profile_first_name": first_name or "",
                "profile_last_name": last_name or "",
                "profile_email": request.user.email or "",
                "profile_phone": profile.phone if profile else "",
                "profile_birth_date": profile.birth_date.isoformat() if profile and profile.birth_date else "",
                "address_city": address.city if address else "",
                "address_street": address.street if address else "",
                "address_entrance": address.entrance if address else "",
                "address_flat": address.flat_or_office if address else "",
                "address_comment": address.comment if address else "",
                "notify_order": notifications.order_status if notifications else True,
                "notify_promo": notifications.promotions if notifications else False,
                "notify_restock": notifications.restock if notifications else True,
                "profile_initials": _build_initials(first_name, last_name, request.user.email),
                "profile_orders_count": orders_count,
                "profile_orders_sum": int(orders_done_sum),
                "profile_favorites_count": favorites_count,
                "profile_completeness": completeness_pct,
                "profile_member_since": member_since,
            }
        )

    return render(request, template_name, context)


def _safe_next_url(request, value):
    if not value:
        return ""

    if url_has_allowed_host_and_scheme(
        url=value,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return value
    return ""


def _split_full_name(full_name):
    parts = [chunk for chunk in full_name.strip().split() if chunk]
    if not parts:
        return "", ""
    first_name = parts[0]
    last_name = " ".join(parts[1:]) if len(parts) > 1 else ""
    return first_name, last_name


def _build_unique_username(email):
    base = re.sub(r"[^A-Za-z0-9._+-]", "", email.split("@")[0]).lower() or "user"
    candidate = base
    counter = 1
    while User.objects.filter(username__iexact=candidate).exists():
        counter += 1
        candidate = f"{base}{counter}"
    return candidate


def _resolve_user_by_email(email):
    return User.objects.filter(email__iexact=email).first()


def admin_login_redirect(request):
    admin_next = _safe_next_url(request, request.GET.get("next")) or reverse("admin:index")
    query = urlencode({"mode": "login", "next": admin_next})
    return redirect(f"{reverse('auth')}?{query}")


def auth_view(request):
    requested_mode = request.GET.get("mode", "login")
    active_tab = requested_mode if requested_mode in {"login", "register", "restore"} else "login"
    next_url = _safe_next_url(request, request.GET.get("next") or request.POST.get("next"))

    login_form = LoginByEmailForm()
    register_form = RegistrationForm()
    restore_form = PasswordRestoreForm()

    if request.method == "POST":
        action = request.POST.get("action")
        active_tab = action if action in {"login", "register", "restore"} else active_tab

        if action == "login":
            login_form = LoginByEmailForm(request.POST)
            if login_form.is_valid():
                email = login_form.cleaned_data["email"].strip().lower()
                password = login_form.cleaned_data["password"]
                user_by_email = _resolve_user_by_email(email)
                username = user_by_email.get_username() if user_by_email else email
                user = authenticate(request, username=username, password=password)

                if user is None:
                    login_form.add_error(None, "Неверный email или пароль.")
                elif next_url.startswith("/admin") and not user.is_staff:
                    login_form.add_error(None, "У вас нет доступа к админ-панели.")
                else:
                    login(request, user)
                    messages.success(request, "Вы успешно вошли в аккаунт.")
                    return redirect(next_url or "profile")

        elif action == "register":
            register_form = RegistrationForm(request.POST)
            if register_form.is_valid():
                email = register_form.cleaned_data["email"]
                first_name, last_name = _split_full_name(register_form.cleaned_data["full_name"])
                username = _build_unique_username(email)

                user = User.objects.create_user(
                    username=username,
                    email=email,
                    password=register_form.cleaned_data["password1"],
                    first_name=first_name,
                    last_name=last_name,
                )

                CustomerProfile.objects.update_or_create(
                    user=user,
                    defaults={
                        "first_name": first_name,
                        "last_name": last_name,
                        "phone": register_form.cleaned_data["phone"].strip(),
                    },
                )

                login(request, user)
                messages.success(request, "Аккаунт создан. Добро пожаловать в Paperly.")
                return redirect(next_url or "profile")

        elif action == "restore":
            restore_form = PasswordRestoreForm(request.POST)
            if restore_form.is_valid():
                reset_form = PasswordResetForm({"email": restore_form.cleaned_data["email"]})
                if reset_form.is_valid():
                    reset_form.save(
                        request=request,
                        use_https=request.is_secure(),
                        from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
                        subject_template_name="emails/password_reset_subject.txt",
                        email_template_name="emails/password_reset_email.txt",
                    )
                messages.success(
                    request,
                    "Если аккаунт с таким email существует, письмо для восстановления уже отправлено.",
                )
                return redirect(f"{reverse('auth')}?mode=login")

    context = {
        "active_tab": active_tab,
        "next_url": next_url,
        "login_form": login_form,
        "register_form": register_form,
        "restore_form": restore_form,
    }
    return render(request, "auth.html", context)


def auth_password_reset_confirm_view(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is None or not default_token_generator.check_token(user, token):
        messages.error(request, "Ссылка для восстановления недействительна или устарела.")
        return redirect(f"{reverse('auth')}?mode=restore")

    form = SetPasswordForm(user=user, data=request.POST or None)

    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Пароль успешно обновлен. Теперь можно войти в аккаунт.")
        return redirect(f"{reverse('auth')}?mode=login")

    return render(
        request,
        "auth-reset-confirm.html",
        {
            "form": form,
        },
    )


def legacy_html_redirect(request, page):
    route_name = LEGACY_PAGE_TO_NAME.get(page)
    if route_name is None:
        return redirect("home", permanent=True)
    return redirect(route_name, permanent=True)


LEGAL_META = {
    "privacy": {
        "page_type": SitePage.PageType.PRIVACY,
        "title": "Политика конфиденциальности",
        "eyebrow": "Правовая информация",
        "summary": "Как мы собираем, храним и используем ваши персональные данные.",
        "updated": "15 марта 2026",
    },
    "offer": {
        "page_type": SitePage.PageType.OFFER,
        "title": "Публичная оферта",
        "eyebrow": "Правовая информация",
        "summary": "Условия договора оферты между интернет-магазином и покупателем.",
        "updated": "15 марта 2026",
    },
    "cookies": {
        "page_type": SitePage.PageType.TERMS,
        "title": "Политика использования cookie",
        "eyebrow": "Правовая информация",
        "summary": "Для чего сайт использует cookie-файлы и как управлять настройками.",
        "updated": "15 марта 2026",
    },
}


def legal_view(request, kind):
    meta = LEGAL_META.get(kind)
    if not meta:
        return redirect("home")

    site_page = (
        SitePage.objects.filter(page_type=meta["page_type"], is_published=True).first()
        if kind != "cookies"
        else None
    )

    # Per-kind default HTML content (used when admin hasn't filled SitePage).
    fallback = LEGAL_FALLBACK.get(kind, "")
    content_html = (site_page.content if site_page and site_page.content else fallback)

    return render(
        request,
        "legal.html",
        {
            "legal_kind": kind,
            "legal_title": site_page.title if site_page else meta["title"],
            "legal_eyebrow": meta["eyebrow"],
            "legal_summary": meta["summary"],
            "legal_updated": meta["updated"],
            "legal_content": content_html,
            "is_admin_content": bool(site_page and site_page.content),
        },
    )


LEGAL_FALLBACK = {
    "privacy": """
<p>Настоящая политика конфиденциальности (далее — «Политика») описывает, какие персональные данные собирает интернет-магазин, как они используются, хранятся и защищаются.</p>

<h2>1. Какие данные мы собираем</h2>
<ul>
  <li>Имя и фамилия — для оформления заказа и обращения.</li>
  <li>Email — для уведомлений о статусе заказа и восстановления пароля.</li>
  <li>Телефон — для связи курьера и оператора при доставке.</li>
  <li>Адрес доставки — только для выполнения заказа.</li>
  <li>Технические данные (IP-адрес, cookie, UA браузера) — для работы сайта и аналитики.</li>
</ul>

<h2>2. Как используются данные</h2>
<p>Данные обрабатываются исключительно для:</p>
<ul>
  <li>выполнения и доставки заказов;</li>
  <li>информирования об акциях и новинках (при вашем согласии);</li>
  <li>улучшения работы сайта и сервиса;</li>
  <li>выполнения обязательств по 152-ФЗ «О персональных данных».</li>
</ul>

<h2>3. Передача третьим лицам</h2>
<p>Мы не продаём и не передаём ваши данные третьим лицам, за исключением:</p>
<ul>
  <li>служб доставки — в объёме, необходимом для вручения заказа;</li>
  <li>платёжных систем — при безналичной оплате (по защищённому каналу);</li>
  <li>государственных органов — по обоснованному запросу.</li>
</ul>

<h2>4. Хранение и защита</h2>
<p>Данные хранятся на серверах в РФ. Доступ ограничен сотрудниками, которым он необходим для исполнения служебных обязанностей. Используются TLS-шифрование, контроль доступа и регулярные бэкапы.</p>

<h2>5. Ваши права</h2>
<p>Вы можете в любой момент:</p>
<ul>
  <li>запросить состав своих данных;</li>
  <li>внести изменения или уточнить их;</li>
  <li>отозвать согласие на обработку — написав на email, указанный в контактах.</li>
</ul>

<h2>6. Cookie-файлы</h2>
<p>Подробности — в <a href="/legal/cookies/">Политике cookie</a>.</p>

<h2>7. Изменения политики</h2>
<p>Мы вправе обновлять Политику. Актуальная версия всегда доступна на этой странице.</p>
""",
    "offer": """
<p>Настоящий документ является публичной офертой (далее — «Оферта») — адресованным любому физическому или юридическому лицу предложением заключить договор купли-продажи товаров дистанционным способом.</p>

<h2>1. Общие положения</h2>
<ul>
  <li>Оферта считается принятой с момента оформления заказа покупателем.</li>
  <li>Сайт предоставляет актуальную информацию о товарах, их стоимости и условиях доставки.</li>
  <li>Изображения товаров носят ознакомительный характер и могут отличаться от реального товара.</li>
</ul>

<h2>2. Заказ и оплата</h2>
<p>Заказ оформляется покупателем самостоятельно через сайт. После оформления покупатель получает подтверждение на указанный email.</p>
<p>Оплата производится одним из способов: банковская карта, СБП, при получении (курьеру или в пункте выдачи). Для юрлиц — счёт с безналичной оплатой.</p>

<h2>3. Доставка</h2>
<p>Доставка осуществляется курьерской службой или через сеть пунктов самовывоза. Сроки и стоимость указываются на странице <a href="/delivery/">«Доставка и оплата»</a>.</p>

<h2>4. Возврат и обмен</h2>
<p>Возврат производится в соответствии с Законом РФ «О защите прав потребителей». Подробности — на странице <a href="/guarantee/">«Гарантия и возврат»</a>.</p>

<h2>5. Ответственность</h2>
<p>Продавец не несёт ответственности за задержки, вызванные форс-мажором, действиями служб доставки или неверно указанными покупателем данными.</p>

<h2>6. Контакты</h2>
<p>По всем вопросам — свяжитесь с нами по email или телефону, указанным в футере сайта.</p>
""",
    "cookies": """
<p>Мы используем cookie-файлы, чтобы сайт работал корректно и был удобен для вас.</p>

<h2>1. Что такое cookie</h2>
<p>Cookie — небольшие текстовые файлы, которые сохраняются в вашем браузере при посещении сайта. Они не содержат вредоносного кода и не могут запускать программы.</p>

<h2>2. Какие cookie мы используем</h2>
<ul>
  <li><strong>Технические</strong> — необходимы для работы корзины, авторизации и сохранения выбора товаров. Отключить нельзя.</li>
  <li><strong>Аналитические</strong> — помогают понять, как пользователи работают с сайтом (агрегированно, без идентификации). Используются Яндекс.Метрика и Google Analytics.</li>
  <li><strong>Функциональные</strong> — запоминают ваши предпочтения (например, недавние поисковые запросы).</li>
</ul>

<h2>3. Как управлять</h2>
<p>Вы можете отключить cookie в настройках браузера. Обратите внимание: некоторые функции сайта (корзина, избранное, вход в аккаунт) без cookie могут работать некорректно.</p>

<h2>4. Хранение</h2>
<p>Сессионные cookie удаляются при закрытии браузера. Постоянные — хранятся до 12 месяцев, если не удалены раньше.</p>

<h2>5. Согласие</h2>
<p>Продолжая использовать сайт, вы соглашаетесь с применением cookie. Подробнее — в <a href="/legal/privacy/">Политике конфиденциальности</a>.</p>
""",
}


@require_POST
def logout_view(request):
    logout(request)
    return redirect("home")













