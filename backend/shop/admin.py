from django import forms
from django.contrib import admin

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
    list_filter = ("status", "is_new", "is_hit", "is_featured", "brand", "format", "purpose")
    search_fields = ("title", "sku", "slug")
    inlines = (ProductImageInline, ProductSpecificationInline)
    prepopulated_fields = {"slug": ("title",)}
    filter_horizontal = ("categories",)
    list_select_related = ("brand",)


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
        ("Основное", {"fields": ("site_name", "tagline")}),
        ("Контакты", {"fields": ("phone", "email", "city", "address")}),
        ("Прочее", {"fields": ("copyright_text",)}),
    )

    def has_add_permission(self, request):
        return not models.SiteSetting.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


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
