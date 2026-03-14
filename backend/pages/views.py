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

from shop.models import Address, BlogPost, CustomerProfile, NotificationSetting

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


PROTECTED_PAGES = {"profile", "order_history", "favorites"}


def _build_initials(first_name, last_name, email):
    initials = ""
    if first_name:
        initials += first_name[:1].upper()
    if last_name:
        initials += last_name[:1].upper()
    if not initials and email:
        initials = email[:2].upper()
    return initials or "PL"


def page_view(request, page_name):
    if page_name in PROTECTED_PAGES and not request.user.is_authenticated:
        query = urlencode({"mode": "login", "next": request.get_full_path()})
        return redirect(f"{reverse('auth')}?{query}")

    template_name = PAGE_TO_TEMPLATE[page_name]
    context = {}

    if page_name == "blog":
        slug = request.GET.get("slug")
        post = BlogPost.objects.filter(slug=slug).first() if slug else None
        posts = BlogPost.objects.all().order_by("-published_at", "-created_at")
        context.update(
            {
                "blog_post": post,
                "blog_posts": posts,
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


@require_POST
def logout_view(request):
    logout(request)
    return redirect("home")













