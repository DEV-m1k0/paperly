from django import forms
from django.contrib import admin
from django.utils.safestring import mark_safe

from . import models


class BaseAdmin(admin.ModelAdmin):
    list_per_page = 30
    save_on_top = True


@admin.register(models.Category)
class CategoryAdmin(BaseAdmin):
    list_display = ("name", "parent", "is_active", "sort_order")
    list_filter = ("is_active",)
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}
    list_editable = ("is_active", "sort_order")


@admin.register(models.Brand)
class BrandAdmin(BaseAdmin):
    list_display = ("name", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}
    list_editable = ("is_active",)


class CatalogFilterOptionInline(admin.TabularInline):
    model = models.CatalogFilterOption
    extra = 0


@admin.register(models.CatalogFilterGroup)
class CatalogFilterGroupAdmin(BaseAdmin):
    list_display = ("title", "slug", "is_active", "sort_order")
    list_filter = ("is_active",)
    search_fields = ("title", "slug")
    prepopulated_fields = {"slug": ("title",)}
    list_editable = ("is_active", "sort_order")
    inlines = (CatalogFilterOptionInline,)


@admin.register(models.CatalogFilterOption)
class CatalogFilterOptionAdmin(BaseAdmin):
    list_display = ("label", "group", "query_param", "value", "is_active", "sort_order")
    list_filter = ("is_active", "query_param", "group")
    search_fields = ("label", "value")
    list_editable = ("is_active", "sort_order")


class ProductImageInline(admin.TabularInline):
    model = models.ProductImage
    extra = 0


class CatalogFilterOptionChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return f"{obj.group.title}: {obj.label}"


class ProductSpecificationInlineForm(forms.ModelForm):
    filter_option = CatalogFilterOptionChoiceField(
        queryset=models.CatalogFilterOption.objects.filter(is_active=True)
        .select_related("group")
        .order_by("group__sort_order", "group__title", "sort_order", "label"),
        required=False,
        label="Фильтр каталога",
        help_text="Выберите, чтобы автоматически заполнить name/value.",
    )

    class Meta:
        model = models.ProductSpecification
        fields = ("filter_option", "name", "value", "sort_order")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["name"].required = False
        self.fields["value"].required = False
        if self.instance and self.instance.pk:
            option = models.CatalogFilterOption.objects.filter(
                query_param=self.instance.name,
                value=self.instance.value,
                is_active=True,
            ).first()
            if option:
                self.initial["filter_option"] = option

    def clean(self):
        cleaned_data = super().clean()
        option = cleaned_data.get("filter_option")
        if option:
            cleaned_data["name"] = option.query_param
            cleaned_data["value"] = option.value
        else:
            name = cleaned_data.get("name")
            value = cleaned_data.get("value")
            if not name or not value:
                raise forms.ValidationError("Выберите фильтр или заполните поля name/value.")
        return cleaned_data


class ProductSpecificationInline(admin.TabularInline):
    model = models.ProductSpecification
    form = ProductSpecificationInlineForm
    fields = ("filter_option", "name", "value", "sort_order")
    extra = 0


@admin.register(models.Product)
class ProductAdmin(BaseAdmin):
    list_display = ("title", "sku", "brand", "format", "purpose", "price", "stock", "max_order_quantity", "status", "is_new", "is_hit")
    list_editable = ("max_order_quantity",)
    list_filter = ("status", "is_new", "is_hit", "is_featured", "brand", "format", "purpose")
    search_fields = ("title", "sku", "slug")
    inlines = (ProductImageInline, ProductSpecificationInline)
    prepopulated_fields = {"slug": ("title",)}
    filter_horizontal = ("categories",)
    list_select_related = ("brand",)
    fieldsets = (
        (None, {"fields": ("title", "slug", "sku", "brand", "categories", "status")}),
        ("Описание", {"fields": ("short_description", "description")}),
        ("Цена и наличие", {"fields": ("price", "old_price", "stock")}),
        ("Ограничения", {
            "fields": ("max_order_quantity",),
            "description": mark_safe(
                "<b>Макс. кол-во в заказе</b> — сколько штук одного товара покупатель "
                "может добавить в корзину и заказать за один раз. "
                "<b>0 = без ограничения</b>. Лимит проверяется и на клиенте (кнопки в "
                "корзине), и на сервере (при создании заказа)."
            ),
        }),
        ("Характеристики", {"fields": ("format", "sheets_count", "purpose")}),
        ("Маркетинг", {"fields": ("is_new", "is_hit", "is_featured")}),
        ("Габариты", {"fields": ("weight_grams", "length_mm", "width_mm", "height_mm")}),
    )


@admin.register(models.ProductReview)
class ProductReviewAdmin(BaseAdmin):
    list_display = ("product", "author_name", "rating", "is_published", "created_at")
    list_filter = ("rating", "is_published")
    search_fields = ("author_name", "text")
    date_hierarchy = "created_at"
    list_select_related = ("product", "user")


@admin.register(models.Promotion)
class PromotionAdmin(BaseAdmin):
    list_display = ("title", "promo_type", "discount_percent", "start_at", "end_at", "is_active")
    list_filter = ("promo_type", "is_active")
    search_fields = ("title", "slug")
    filter_horizontal = ("products",)
    prepopulated_fields = {"slug": ("title",)}
    date_hierarchy = "start_at"



@admin.register(models.BlogCategory)
class BlogCategoryAdmin(BaseAdmin):
    list_display = ("title",)
    search_fields = ("title", "slug")
    prepopulated_fields = {"slug": ("title",)}


@admin.register(models.BlogPost)
class BlogPostAdmin(BaseAdmin):
    list_display = ("title", "category", "status", "published_at")
    list_filter = ("status", "category")
    search_fields = ("title", "slug", "excerpt")
    prepopulated_fields = {"slug": ("title",)}
    date_hierarchy = "published_at"
    list_select_related = ("category",)


@admin.register(models.PickupPoint)
class PickupPointAdmin(BaseAdmin):
    list_display = ("name", "city", "metro", "is_active")
    list_filter = ("city", "is_active")
    search_fields = ("name", "city", "address", "metro")
    prepopulated_fields = {"slug": ("name",)}
    list_editable = ("is_active",)


@admin.register(models.DeliveryTariff)
class DeliveryTariffAdmin(BaseAdmin):
    list_display = ("title", "delivery_type", "city", "price", "free_from_amount", "is_active")
    list_filter = ("delivery_type", "city", "is_active")
    list_editable = ("is_active",)


@admin.register(models.CustomerProfile)
class CustomerProfileAdmin(BaseAdmin):
    list_display = ("user", "first_name", "last_name", "phone")
    search_fields = ("user__username", "user__email", "first_name", "last_name", "phone")
    list_select_related = ("user",)


@admin.register(models.Address)
class AddressAdmin(BaseAdmin):
    list_display = ("profile", "address_type", "city", "street", "is_default")
    list_filter = ("address_type", "city", "is_default")
    list_select_related = ("profile",)


@admin.register(models.NotificationSetting)
class NotificationSettingAdmin(BaseAdmin):
    list_display = ("profile", "order_status", "promotions", "restock")
    list_select_related = ("profile",)


@admin.register(models.Favorite)
class FavoriteAdmin(BaseAdmin):
    list_display = ("user", "product", "created_at")
    search_fields = ("user__username", "user__email", "product__title")
    date_hierarchy = "created_at"
    list_select_related = ("user", "product")


class CartItemInline(admin.TabularInline):
    model = models.CartItem
    extra = 0


@admin.register(models.Cart)
class CartAdmin(BaseAdmin):
    list_display = ("id", "user", "session_key", "is_active", "updated_at")
    list_filter = ("is_active",)
    inlines = (CartItemInline,)
    date_hierarchy = "updated_at"
    list_select_related = ("user",)


class OrderItemInline(admin.TabularInline):
    model = models.OrderItem
    extra = 0


@admin.register(models.Order)
class OrderAdmin(BaseAdmin):
    list_display = ("number", "status", "full_name", "phone", "total", "created_at")
    list_filter = ("status", "delivery_type", "payment_type")
    search_fields = ("number", "full_name", "phone", "email")
    inlines = (OrderItemInline,)
    date_hierarchy = "created_at"
    list_editable = ("status",)


@admin.register(models.OrderStatusHistory)
class OrderStatusHistoryAdmin(BaseAdmin):
    list_display = ("order", "status", "created_at")
    list_filter = ("status",)
    date_hierarchy = "created_at"
    list_select_related = ("order",)


@admin.register(models.WholesalePriceList)
class WholesalePriceListAdmin(BaseAdmin):
    list_display = ("title", "segment", "is_active")
    list_filter = ("segment", "is_active")
    prepopulated_fields = {"slug": ("title",)}
    list_editable = ("is_active",)


@admin.register(models.WholesaleRequest)
class WholesaleRequestAdmin(BaseAdmin):
    list_display = ("organization_name", "organization_type", "contact_person", "status", "created_at")
    list_filter = ("organization_type", "status")
    search_fields = ("organization_name", "contact_person", "phone", "email")
    date_hierarchy = "created_at"
    list_editable = ("status",)


class ReturnRequestItemInline(admin.TabularInline):
    model = models.ReturnRequestItem
    extra = 0


@admin.register(models.ReturnRequest)
class ReturnRequestAdmin(BaseAdmin):
    list_display = ("id", "order", "return_type", "status", "created_at")
    list_filter = ("return_type", "status")
    inlines = (ReturnRequestItemInline,)
    date_hierarchy = "created_at"
    list_editable = ("status",)
    list_select_related = ("order",)


@admin.register(models.SitePage)
class SitePageAdmin(BaseAdmin):
    list_display = ("title", "page_type", "is_published", "updated_at")
    list_filter = ("page_type", "is_published")
    search_fields = ("title", "slug")
    prepopulated_fields = {"slug": ("title",)}
    list_editable = ("is_published",)
    fieldsets = (
        ("Основное", {"fields": ("title", "slug", "page_type", "is_published")}),
        ("Контент", {
            "fields": ("content",),
            "description": mark_safe(
                "<b>HTML-контент страницы.</b> Если на странице есть кастомный шаблон "
                "(например, главная), этот блок может быть проигнорирован — см. описание "
                "конкретного типа страницы в шаблоне."
            ),
        }),
        ("SEO / соцсети", {
            "fields": ("meta_title", "meta_description", "og_image", "og_image_url"),
            "classes": ("collapse",),
            "description": mark_safe(
                "Метаданные для поисковиков и превью при репосте в соцсетях. "
                "Все поля опциональны — при пустом значении используются дефолты сайта."
            ),
        }),
    )


@admin.register(models.SocialLink)
class SocialLinkAdmin(BaseAdmin):
    list_display = ("label", "url", "icon_preview", "sort_order", "is_active")
    list_editable = ("sort_order", "is_active")
    list_filter = ("is_active",)
    search_fields = ("label", "url")
    ordering = ("sort_order", "label")
    fields = ("label", "url", "icon_class", "icon_image", "icon_preview", "sort_order", "is_active")
    readonly_fields = ("icon_preview",)

    @admin.display(description="Иконка")
    def icon_preview(self, obj):
        from django.utils.html import format_html
        if obj.icon_image:
            try:
                return format_html(
                    '<img src="{}" style="width:28px;height:28px;object-fit:contain;border-radius:6px;background:#0e766e;padding:4px;">',
                    obj.icon_image.url,
                )
            except Exception:
                pass
        if obj.icon_class:
            return format_html('<i class="bi {}" style="font-size:22px;color:#0e766e;"></i> {}', obj.icon_class, obj.icon_class)
        return "—"


@admin.register(models.SiteSetting)
class SiteSettingAdmin(admin.ModelAdmin):
    fieldsets = (
        ("Основное", {"fields": ("site_name", "tagline", "copyright_text")}),
        ("Контакты — телефоны и email", {
            "fields": ("phone", "secondary_phone", "email", "sales_email", "wholesale_email"),
            "description": mark_safe(
                "Телефоны и email отображаются в шапке, футере и на странице «Контакты». "
                "Дополнительные поля опциональны — при пустом значении используется основной телефон/email."
            ),
        }),
        ("Адрес и часы работы", {
            "fields": ("city", "address", "work_hours", "work_hours_short", "latitude", "longitude"),
            "description": "Координаты используются для карты на странице контактов.",
        }),
        ("Маркетинговые плашки", {
            "fields": ("free_shipping_from", "free_shipping_text", "cookies_banner_text"),
            "classes": ("collapse",),
        }),
    )

    def has_add_permission(self, request):
        return not models.SiteSetting.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


# ──────────────────────────────────────────────
# Главная страница (singleton + inline-блоки)
# ──────────────────────────────────────────────
class HomeHeroCardInline(admin.TabularInline):
    model = models.HomeHeroCard
    extra = 0
    fields = ("badge", "title", "description", "icon_class", "url", "color_variant", "sort_order", "is_active")


class HomeCategoryCardInline(admin.TabularInline):
    model = models.HomeCategoryCard
    extra = 0
    fields = ("title", "subtitle", "icon_class", "url", "color_modifier", "sort_order", "is_active")


class HomeFeatureInline(admin.TabularInline):
    model = models.HomeFeature
    extra = 0
    fields = ("icon_class", "color_variant", "title", "description", "sort_order", "is_active")


@admin.register(models.HomePage)
class HomePageAdmin(admin.ModelAdmin):
    inlines = (HomeHeroCardInline, HomeCategoryCardInline, HomeFeatureInline)
    save_on_top = True
    filter_horizontal = ("featured_categories", "featured_products")
    fieldsets = (
        ("Hero — главный экран", {
            "fields": (
                "hero_eyebrow", "hero_title", "hero_title_accent", "hero_subtitle",
                ("hero_cta_primary_label", "hero_cta_primary_url", "hero_cta_primary_icon"),
                ("hero_cta_secondary_label", "hero_cta_secondary_url", "hero_cta_secondary_icon"),
            ),
            "description": mark_safe(
                "Все поля опциональны: при пустом значении в hero показывается "
                "встроенный дизайн. Заполняйте только то, что хотите изменить."
            ),
        }),
        ("Видимость секций", {
            "fields": (
                "show_stats", "show_categories", "show_promotions",
                "show_new_arrivals", "show_bestsellers", "show_brands",
                "show_services", "show_features",
            ),
            "description": "Снимите галочку, чтобы спрятать соответствующий блок на главной.",
        }),
        ("Заголовки секций", {
            "fields": ("features_eyebrow", "features_title"),
            "classes": ("collapse",),
        }),
        ("Подборки", {
            "fields": ("featured_categories", "featured_products"),
            "classes": ("collapse",),
            "description": "Если оставить пустыми — блоки берут данные из общих источников.",
        }),
    )

    def has_add_permission(self, request):
        # Singleton — только одна запись
        return not models.HomePage.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False

    def changelist_view(self, request, extra_context=None):
        # Если строки ещё нет — сразу открываем форму редактирования.
        from django.shortcuts import redirect
        from django.urls import reverse
        obj = models.HomePage.objects.first()
        if obj is None:
            obj = models.HomePage.load()
        return redirect(reverse("admin:shop_homepage_change", args=[obj.pk]))


# ──────────────────────────────────────────────
# Singleton-mixin — общая логика для одностраничных моделей
# ──────────────────────────────────────────────
class _SingletonAdminMixin:
    """Mixin для моделей-синглтонов: запрещает добавление >1, удаление,
    и редиректит /changelist/ сразу на форму редактирования."""

    save_on_top = True
    _singleton_model = None  # subclass overrides

    def has_add_permission(self, request):
        return not self._singleton_model.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False

    def changelist_view(self, request, extra_context=None):
        from django.shortcuts import redirect
        from django.urls import reverse
        obj = self._singleton_model.objects.first()
        if obj is None:
            obj = self._singleton_model.load()
        opts = self._singleton_model._meta
        return redirect(reverse(f"admin:{opts.app_label}_{opts.model_name}_change", args=[obj.pk]))


# ──────────────────────────────────────────────
# Страница «О магазине» (singleton + inlines)
# ──────────────────────────────────────────────
class AboutFeatureInline(admin.TabularInline):
    model = models.AboutFeature
    extra = 0
    fields = ("icon_class", "color_variant", "title", "description", "meta_label", "sort_order", "is_active")


class AboutStepInline(admin.TabularInline):
    model = models.AboutStep
    extra = 0
    fields = ("sort_order", "title", "description", "is_active")


class AboutMissionBulletInline(admin.TabularInline):
    model = models.AboutMissionBullet
    extra = 0
    fields = ("icon_class", "label", "sort_order", "is_active")


class AboutB2BBulletInline(admin.TabularInline):
    model = models.AboutB2BBullet
    extra = 0
    fields = ("icon_class", "label", "sort_order", "is_active")


@admin.register(models.AboutPage)
class AboutPageAdmin(_SingletonAdminMixin, admin.ModelAdmin):
    _singleton_model = models.AboutPage
    inlines = (AboutFeatureInline, AboutStepInline, AboutMissionBulletInline, AboutB2BBulletInline)
    fieldsets = (
        ("Hero — главный экран страницы", {
            "fields": (
                "hero_eyebrow", "hero_title", "hero_title_accent", "hero_subtitle",
                ("hero_cta_primary_label", "hero_cta_primary_url", "hero_cta_primary_icon"),
                ("hero_cta_secondary_label", "hero_cta_secondary_url", "hero_cta_secondary_icon"),
            ),
            "description": mark_safe(
                "Все поля опциональны. При пустом значении используются дефолтные тексты "
                "из шаблона."
            ),
        }),
        ("Mission — правая карточка hero", {
            "fields": ("mission_eyebrow", "mission_title", "mission_text", "mission_icon"),
        }),
        ("Видимость секций", {
            "fields": ("show_stats", "show_features", "show_steps", "show_b2b_cta", "show_contacts"),
        }),
        ("Заголовки секций", {
            "fields": (
                ("features_eyebrow", "features_title"),
                ("steps_eyebrow", "steps_title"),
                ("contacts_eyebrow", "contacts_title"),
            ),
            "classes": ("collapse",),
        }),
        ("B2B CTA-блок", {
            "fields": ("b2b_eyebrow", "b2b_title", "b2b_text", "b2b_button_label", "b2b_button_url"),
            "classes": ("collapse",),
        }),
    )


# ──────────────────────────────────────────────
# Страница «Доставка» (singleton + inlines)
# ──────────────────────────────────────────────
class DeliveryFreeCardItemInline(admin.TabularInline):
    model = models.DeliveryFreeCardItem
    extra = 0
    fields = ("label", "value", "sort_order", "is_active")


class DeliveryStepInline(admin.TabularInline):
    model = models.DeliveryStep
    extra = 0
    fields = ("sort_order", "icon_class", "title", "description", "is_active")


class DeliveryPayMethodInline(admin.TabularInline):
    model = models.DeliveryPayMethod
    extra = 0
    fields = ("icon_class", "color_variant", "title", "description", "badges_text", "sort_order", "is_active")


class DeliveryFAQInline(admin.TabularInline):
    model = models.DeliveryFAQ
    extra = 0
    fields = ("sort_order", "question", "answer", "is_active")


@admin.register(models.DeliveryPage)
class DeliveryPageAdmin(_SingletonAdminMixin, admin.ModelAdmin):
    _singleton_model = models.DeliveryPage
    inlines = (DeliveryFreeCardItemInline, DeliveryStepInline, DeliveryPayMethodInline, DeliveryFAQInline)
    fieldsets = (
        ("Hero — главный экран страницы", {
            "fields": (
                "hero_eyebrow", "hero_title", "hero_title_accent", "hero_subtitle",
                ("hero_cta_primary_label", "hero_cta_primary_url", "hero_cta_primary_icon"),
                ("hero_cta_secondary_label", "hero_cta_secondary_url", "hero_cta_secondary_icon"),
            ),
        }),
        ("Карточка «Бесплатная доставка»", {
            "fields": ("free_card_ribbon", "free_card_kicker", "free_card_title", "free_card_subtitle"),
            "description": "Список под карточкой настраивается ниже в инлайн-блоке «Пункты карточки».",
        }),
        ("Видимость секций", {
            "fields": ("show_calc", "show_steps", "show_pay_methods", "show_faq", "show_final_cta"),
        }),
        ("Заголовки секций", {
            "fields": (
                ("tariffs_eyebrow", "tariffs_title", "tariffs_subtitle"),
                ("steps_eyebrow", "steps_title"),
                ("pay_eyebrow", "pay_title"),
                ("faq_eyebrow", "faq_title"),
            ),
            "classes": ("collapse",),
        }),
        ("Финальный CTA «Готовы оформить заказ?»", {
            "fields": ("final_cta_title", "final_cta_text"),
            "classes": ("collapse",),
        }),
    )


# ──────────────────────────────────────────────
# Страница «Опт» (singleton + inlines)
# ──────────────────────────────────────────────
class WholesaleFeatureInline(admin.TabularInline):
    model = models.WholesaleFeature
    extra = 0
    fields = ("icon_class", "color_variant", "title", "description", "sort_order", "is_active")


class WholesaleStepInline(admin.TabularInline):
    model = models.WholesaleStep
    extra = 0
    fields = ("sort_order", "title", "description", "is_active")


class WholesaleSideBulletInline(admin.TabularInline):
    model = models.WholesaleSideBullet
    extra = 0
    fields = ("icon_class", "label", "sort_order", "is_active")


@admin.register(models.WholesalePage)
class WholesalePageAdmin(_SingletonAdminMixin, admin.ModelAdmin):
    _singleton_model = models.WholesalePage
    inlines = (WholesaleFeatureInline, WholesaleStepInline, WholesaleSideBulletInline)
    fieldsets = (
        ("Hero — главный экран", {
            "fields": (
                "hero_eyebrow", "hero_title", "hero_title_accent", "hero_subtitle",
                ("hero_cta_primary_label", "hero_cta_primary_url", "hero_cta_primary_icon"),
            ),
        }),
        ("Side-карточка hero", {
            "fields": ("side_eyebrow", "side_title", "side_text", "side_icon"),
        }),
        ("Видимость секций", {
            "fields": ("show_features", "show_steps", "show_form"),
        }),
        ("Заголовки секций", {
            "fields": (
                ("features_eyebrow", "features_title"),
                ("steps_eyebrow", "steps_title"),
                ("form_eyebrow", "form_title"),
                ("form_intro_title", "form_intro_text"),
            ),
            "classes": ("collapse",),
        }),
    )


# ──────────────────────────────────────────────
# Промокоды
# ──────────────────────────────────────────────
class PromoCodeRedemptionInline(admin.TabularInline):
    model = models.PromoCodeRedemption
    extra = 0
    can_delete = False
    readonly_fields = ("user", "email", "order", "amount_discounted", "created_at")
    fields = readonly_fields

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(models.PromoCode)
class PromoCodeAdmin(BaseAdmin):
    list_display = (
        "code", "discount_type", "discount_value", "used_count", "usage_limit",
        "valid_until", "is_active", "is_public",
    )
    list_filter = ("is_active", "is_public", "discount_type", "audience")
    list_editable = ("is_active", "is_public")
    search_fields = ("code", "description")
    readonly_fields = ("used_count", "created_at", "updated_at")
    filter_horizontal = ("applicable_products", "applicable_categories")
    inlines = [PromoCodeRedemptionInline]
    fieldsets = (
        ("Код и скидка", {
            "fields": ("code", "description", "discount_type", "discount_value", "max_discount_amount"),
        }),
        ("Условия применения", {
            "fields": ("min_order_amount", "audience", "applicable_products", "applicable_categories"),
        }),
        ("Сроки действия", {"fields": ("valid_from", "valid_until", "is_active", "is_public")}),
        ("Лимиты использования", {"fields": ("usage_limit", "usage_limit_per_user", "used_count")}),
        ("Служебное", {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )
    actions = ("action_generate_code", "action_activate", "action_deactivate")

    @admin.action(description="Сгенерировать случайный код и сохранить как черновик")
    def action_generate_code(self, request, queryset):
        import secrets, string
        alphabet = string.ascii_uppercase + string.digits
        code = "PRM" + "".join(secrets.choice(alphabet) for _ in range(8))
        pc = models.PromoCode.objects.create(
            code=code,
            description=f"Сгенерировано администратором {request.user}",
            discount_type=models.PromoCode.DiscountType.PERCENT,
            discount_value=10,
            is_active=False,
        )
        self.message_user(request, f"Создан черновик: {pc.code}. Откройте и заполните условия.")

    @admin.action(description="Активировать")
    def action_activate(self, request, queryset):
        count = queryset.update(is_active=True)
        self.message_user(request, f"Активировано: {count}")

    @admin.action(description="Деактивировать")
    def action_deactivate(self, request, queryset):
        count = queryset.update(is_active=False)
        self.message_user(request, f"Деактивировано: {count}")


@admin.register(models.PromoCodeRedemption)
class PromoCodeRedemptionAdmin(BaseAdmin):
    list_display = ("promo", "email", "user", "order", "amount_discounted", "created_at")
    list_filter = ("promo", "created_at")
    search_fields = ("promo__code", "email", "order__number")
    readonly_fields = ("promo", "user", "email", "order", "amount_discounted", "created_at", "updated_at")

    def has_add_permission(self, request):
        return False


# ──────────────────────────────────────────────
# Рассылка
# ──────────────────────────────────────────────
@admin.register(models.NewsletterSubscriber)
class NewsletterSubscriberAdmin(BaseAdmin):
    list_display = ("email", "is_active", "source", "created_at", "unsubscribed_at")
    list_filter = ("is_active", "source", "created_at")
    search_fields = ("email",)
    list_editable = ("is_active",)
    readonly_fields = ("unsubscribe_token", "created_at", "updated_at", "unsubscribed_at")
    ordering = ("-created_at",)
    actions = ("action_mark_inactive", "action_mark_active")

    @admin.action(description="Деактивировать (отписать)")
    def action_mark_inactive(self, request, queryset):
        from django.utils import timezone
        count = queryset.update(is_active=False, unsubscribed_at=timezone.now())
        self.message_user(request, f"Отписано: {count}")

    @admin.action(description="Активировать")
    def action_mark_active(self, request, queryset):
        count = queryset.update(is_active=True, unsubscribed_at=None)
        self.message_user(request, f"Активировано: {count}")


@admin.register(models.NewsletterCampaign)
class NewsletterCampaignAdmin(BaseAdmin):
    list_display = ("subject", "status", "sent_count", "sent_at", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("subject", "heading")
    filter_horizontal = ("featured_products",)
    readonly_fields = ("status", "sent_at", "sent_count", "created_at", "updated_at")
    actions = ("action_send_now", "action_send_test")
    fieldsets = (
        ("Письмо", {"fields": ("subject", "preview", "heading", "intro_html")}),
        ("Кнопка CTA", {"fields": ("cta_label", "cta_url")}),
        ("Товары в подборке", {"fields": ("featured_products",), "description": "Не более 6 штук — показываются карточками в письме."}),
        ("Служебное", {"fields": ("status", "sent_at", "sent_count", "created_at", "updated_at")}),
    )

    @admin.action(description="Отправить всем активным подписчикам")
    def action_send_now(self, request, queryset):
        from marketing.emails import send_campaign
        total_recipients = 0
        for campaign in queryset:
            if campaign.status == models.NewsletterCampaign.Status.SENT:
                self.message_user(request, f"«{campaign.subject}» уже отправлена — пропускаю.", level="warning")
                continue
            sent = send_campaign(campaign, request=request)
            total_recipients += sent
            self.message_user(request, f"«{campaign.subject}»: доставлено {sent} писем.")
        if total_recipients == 0 and queryset.exists():
            self.message_user(request, "Ни одно письмо не было отправлено — проверьте SMTP.", level="error")

    @admin.action(description="Отправить тест только мне")
    def action_send_test(self, request, queryset):
        from marketing.emails import send_campaign

        class _Dummy:
            def __init__(self, email):
                self.email = email
                import secrets as _s
                self.unsubscribe_token = _s.token_urlsafe(16)

        email = (request.user.email or "").strip()
        if not email:
            self.message_user(request, "У вашего пользователя не заполнен email.", level="error")
            return
        dummy = [_Dummy(email)]
        for campaign in queryset:
            sent = send_campaign(campaign, subscribers=dummy, request=request, is_test=True)
            if sent:
                self.message_user(request, f"Тест «{campaign.subject}» отправлен на {email}.")
            else:
                self.message_user(request, f"Не удалось отправить тест «{campaign.subject}» — проверьте SMTP.", level="error")
