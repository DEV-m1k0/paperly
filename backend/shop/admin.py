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
