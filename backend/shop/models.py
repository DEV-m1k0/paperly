from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils.text import slugify


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Category(TimeStampedModel):
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True)
    parent = models.ForeignKey(
        "self", on_delete=models.CASCADE, related_name="children", null=True, blank=True
    )
    description = models.TextField(blank=True)
    image_url = models.URLField(blank=True)
    sort_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["sort_order", "name"]
        constraints = [models.UniqueConstraint(fields=["parent", "name"], name="uniq_category_name_in_parent")]
        verbose_name = "Категория"
        verbose_name_plural = "Категории"

    def __str__(self) -> str:
        return self.name


class Brand(TimeStampedModel):
    name = models.CharField(max_length=255, unique=True)
    slug = models.SlugField(max_length=255, unique=True)
    description = models.TextField(blank=True)
    logo_url = models.URLField(blank=True)
    website = models.URLField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Бренд"
        verbose_name_plural = "Бренды"

    def __str__(self) -> str:
        return self.name


class CatalogFilterGroup(TimeStampedModel):
    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True)
    sort_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["sort_order", "title"]
        verbose_name = "Группа фильтров каталога"
        verbose_name_plural = "Группы фильтров каталога"

    def __str__(self) -> str:
        return self.title


class CatalogFilterOption(TimeStampedModel):
    group = models.ForeignKey(
        CatalogFilterGroup, on_delete=models.CASCADE, related_name="options"
    )
    label = models.CharField(max_length=255)
    query_param = models.CharField(
        max_length=64,
        help_text=(
            "Параметр запроса для API. Допустимые значения: brand, category, "
            "purpose, product_format, sheets_count, in_stock, is_new, is_hit, "
            "is_featured, has_discount, has_promotion, sale."
        ),
    )
    value = models.CharField(max_length=64)
    sort_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["sort_order", "label"]
        verbose_name = "Опция фильтра каталога"
        verbose_name_plural = "Опции фильтров каталога"

    def __str__(self) -> str:
        return f"{self.group.title}: {self.label}"


class Product(TimeStampedModel):
    class ProductStatus(models.TextChoices):
        DRAFT = "draft", "Черновик"
        ACTIVE = "active", "Активный"
        ARCHIVED = "archived", "Архив"

    class ProductFormat(models.TextChoices):
        A3 = "A3", "A3"
        A4 = "A4", "A4"
        A5 = "A5", "A5"
        OTHER = "other", "Другой"

    class ProductPurpose(models.TextChoices):
        SCHOOL = "school", "Школа"
        OFFICE = "office", "Офис"
        CREATIVE = "creative", "Творчество"
        UNIVERSAL = "universal", "Универсальное"

    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True)
    sku = models.CharField(max_length=64, unique=True)
    brand = models.ForeignKey(Brand, on_delete=models.PROTECT, related_name="products")
    categories = models.ManyToManyField(Category, related_name="products")

    short_description = models.CharField(max_length=300, blank=True)
    description = models.TextField(blank=True)

    price = models.DecimalField(max_digits=10, decimal_places=2)
    old_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    stock = models.PositiveIntegerField(default=0)
    format = models.CharField(max_length=16, choices=ProductFormat.choices, default=ProductFormat.A4)
    sheets_count = models.PositiveSmallIntegerField(null=True, blank=True)
    purpose = models.CharField(max_length=16, choices=ProductPurpose.choices, default=ProductPurpose.UNIVERSAL)

    status = models.CharField(max_length=16, choices=ProductStatus.choices, default=ProductStatus.ACTIVE)
    is_new = models.BooleanField(default=False)
    is_hit = models.BooleanField(default=False)
    is_featured = models.BooleanField(default=False)

    weight_grams = models.PositiveIntegerField(default=0)
    length_mm = models.PositiveIntegerField(default=0)
    width_mm = models.PositiveIntegerField(default=0)
    height_mm = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["title"]
        indexes = [
            models.Index(fields=["status", "is_new", "is_hit"]),
            models.Index(fields=["brand", "price"]),
            models.Index(fields=["purpose", "format", "sheets_count"]),
        ]
        constraints = [
            models.CheckConstraint(
                check=models.Q(old_price__isnull=True) | models.Q(old_price__gte=models.F("price")),
                name="old_price_gte_price_or_null",
            )
        ]
        verbose_name = "Товар"
        verbose_name_plural = "Товары"

    def __str__(self) -> str:
        return f"{self.title} ({self.sku})"


class ProductImage(TimeStampedModel):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="images")
    image_url = models.URLField()
    alt_text = models.CharField(max_length=255, blank=True)
    is_primary = models.BooleanField(default=False)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["product"],
                condition=models.Q(is_primary=True),
                name="uniq_primary_image_per_product",
            )
        ]
        verbose_name = "Изображение товара"
        verbose_name_plural = "Изображения товаров"

    def __str__(self) -> str:
        return f"{self.product.title} image #{self.id}"


class ProductSpecification(TimeStampedModel):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="specifications")
    name = models.CharField(max_length=120)
    value = models.CharField(max_length=255)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "id"]
        constraints = [models.UniqueConstraint(fields=["product", "name"], name="uniq_spec_name_per_product")]
        verbose_name = "Характеристика товара"
        verbose_name_plural = "Характеристики товаров"

    def __str__(self) -> str:
        return f"{self.product.title}: {self.name}"


class ProductReview(TimeStampedModel):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="reviews")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    author_name = models.CharField(max_length=120)
    rating = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    text = models.TextField()
    is_published = models.BooleanField(default=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Отзыв на товар"
        verbose_name_plural = "Отзывы на товары"

    def __str__(self) -> str:
        return f"{self.product.title} [{self.rating}/5]"


class Promotion(TimeStampedModel):
    class PromotionType(models.TextChoices):
        DISCOUNT = "discount", "Скидка"
        BUNDLE = "bundle", "Набор"
        GIFT = "gift", "Подарок"

    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True)
    description = models.TextField(blank=True)
    promo_type = models.CharField(max_length=16, choices=PromotionType.choices, default=PromotionType.DISCOUNT)
    discount_percent = models.PositiveSmallIntegerField(
        null=True, blank=True, validators=[MinValueValidator(1), MaxValueValidator(99)]
    )
    start_at = models.DateTimeField()
    end_at = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    products = models.ManyToManyField(Product, related_name="promotions", blank=True)

    class Meta:
        ordering = ["-start_at"]
        verbose_name = "Акция"
        verbose_name_plural = "Акции"

    def __str__(self) -> str:
        return self.title


class GiftCertificate(TimeStampedModel):
    title = models.CharField(max_length=120)
    slug = models.SlugField(max_length=120, unique=True)
    nominal = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["nominal"]
        verbose_name = "Подарочный сертификат"
        verbose_name_plural = "Подарочные сертификаты"

    def __str__(self) -> str:
        return f"{self.title} ({self.nominal})"


class BlogCategory(TimeStampedModel):
    title = models.CharField(max_length=120, unique=True)
    slug = models.SlugField(max_length=120, unique=True)

    class Meta:
        ordering = ["title"]
        verbose_name = "Категория блога"
        verbose_name_plural = "Категории блога"

    def __str__(self) -> str:
        return self.title


class BlogPost(TimeStampedModel):
    class PostStatus(models.TextChoices):
        DRAFT = "draft", "Черновик"
        PUBLISHED = "published", "Опубликовано"

    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True)
    category = models.ForeignKey(BlogCategory, on_delete=models.SET_NULL, null=True, blank=True)
    excerpt = models.CharField(max_length=350, blank=True)
    content = models.TextField()
    cover_url = models.URLField(blank=True)
    status = models.CharField(max_length=16, choices=PostStatus.choices, default=PostStatus.DRAFT)
    published_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-published_at", "-created_at"]
        verbose_name = "Пост блога"
        verbose_name_plural = "Посты блога"

    def __str__(self) -> str:
        return self.title


class PickupPoint(TimeStampedModel):
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True)
    city = models.CharField(max_length=120)
    address = models.CharField(max_length=255)
    metro = models.CharField(max_length=120, blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    opening_hours = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["city", "name"]
        verbose_name = "Пункт самовывоза"
        verbose_name_plural = "Пункты самовывоза"

    def __str__(self) -> str:
        return f"{self.city}: {self.name}"


class DeliveryTariff(TimeStampedModel):
    class DeliveryType(models.TextChoices):
        COURIER = "courier", "Курьер"
        EXPRESS = "express", "Экспресс"
        REGION = "region", "Регионы"
        PICKUP = "pickup", "Самовывоз"

    title = models.CharField(max_length=120)
    city = models.CharField(max_length=120, blank=True)
    delivery_type = models.CharField(max_length=16, choices=DeliveryType.choices)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    free_from_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    eta_min_days = models.PositiveSmallIntegerField(default=1)
    eta_max_days = models.PositiveSmallIntegerField(default=1)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["delivery_type", "city", "title"]
        verbose_name = "Тариф доставки"
        verbose_name_plural = "Тарифы доставки"

    def __str__(self) -> str:
        return f"{self.title} ({self.delivery_type})"


class CustomerProfile(TimeStampedModel):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile")
    first_name = models.CharField(max_length=120, blank=True)
    last_name = models.CharField(max_length=120, blank=True)
    phone = models.CharField(max_length=32, blank=True)
    birth_date = models.DateField(null=True, blank=True)

    class Meta:
        verbose_name = "Профиль клиента"
        verbose_name_plural = "Профили клиентов"

    def __str__(self) -> str:
        return f"Profile: {self.user}"


class Address(TimeStampedModel):
    class AddressType(models.TextChoices):
        SHIPPING = "shipping", "Адрес доставки"
        BILLING = "billing", "Платежный адрес"

    profile = models.ForeignKey(CustomerProfile, on_delete=models.CASCADE, related_name="addresses")
    address_type = models.CharField(max_length=16, choices=AddressType.choices, default=AddressType.SHIPPING)
    city = models.CharField(max_length=120)
    street = models.CharField(max_length=255)
    entrance = models.CharField(max_length=50, blank=True)
    flat_or_office = models.CharField(max_length=50, blank=True)
    postal_code = models.CharField(max_length=20, blank=True)
    comment = models.TextField(blank=True)
    is_default = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Адрес"
        verbose_name_plural = "Адреса"

    def __str__(self) -> str:
        return f"{self.city}, {self.street}"


class NotificationSetting(TimeStampedModel):
    profile = models.OneToOneField(
        CustomerProfile, on_delete=models.CASCADE, related_name="notification_settings"
    )
    order_status = models.BooleanField(default=True)
    promotions = models.BooleanField(default=False)
    restock = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Настройки уведомлений"
        verbose_name_plural = "Настройки уведомлений"

    def __str__(self) -> str:
        return f"Notifications: {self.profile.user}"


class Favorite(TimeStampedModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="favorites")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="favorite_by")

    class Meta:
        constraints = [models.UniqueConstraint(fields=["user", "product"], name="uniq_user_favorite")]
        verbose_name = "Избранное"
        verbose_name_plural = "Избранное"

    def __str__(self) -> str:
        return f"{self.user} -> {self.product}"


class Cart(TimeStampedModel):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="cart", null=True, blank=True
    )
    session_key = models.CharField(max_length=64, blank=True, db_index=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Корзина"
        verbose_name_plural = "Корзины"

    def __str__(self) -> str:
        return f"Cart #{self.pk}"


class CartItem(TimeStampedModel):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="in_carts")
    quantity = models.PositiveIntegerField(default=1)
    price_snapshot = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["cart", "product"], name="uniq_cart_product")]
        verbose_name = "Позиция корзины"
        verbose_name_plural = "Позиции корзины"

    def __str__(self) -> str:
        return f"{self.cart} - {self.product} x{self.quantity}"


class Order(TimeStampedModel):
    class OrderStatus(models.TextChoices):
        NEW = "new", "Новый"
        CONFIRMED = "confirmed", "Подтвержден"
        PAID = "paid", "Оплачен"
        SHIPPED = "shipped", "Отгружен"
        DONE = "done", "Завершен"
        CANCELED = "canceled", "Отменен"

    class DeliveryType(models.TextChoices):
        COURIER = "courier", "Курьер"
        PICKUP = "pickup", "Самовывоз"

    class PaymentType(models.TextChoices):
        CARD = "card", "Карта онлайн"
        SBP = "sbp", "СБП"
        CASH = "cash", "Наличными/картой при получении"
        INVOICE = "invoice", "Счет для юрлица"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    number = models.CharField(max_length=32, unique=True)
    status = models.CharField(max_length=16, choices=OrderStatus.choices, default=OrderStatus.NEW)

    full_name = models.CharField(max_length=255)
    phone = models.CharField(max_length=32)
    email = models.EmailField()
    city = models.CharField(max_length=120)
    address = models.CharField(max_length=255)
    comment = models.TextField(blank=True)

    delivery_type = models.CharField(max_length=16, choices=DeliveryType.choices)
    payment_type = models.CharField(max_length=16, choices=PaymentType.choices)
    pickup_point = models.ForeignKey(PickupPoint, on_delete=models.SET_NULL, null=True, blank=True)

    subtotal = models.DecimalField(max_digits=12, decimal_places=2)
    delivery_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    discount_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Заказ"
        verbose_name_plural = "Заказы"

    def __str__(self) -> str:
        return self.number


class OrderItem(TimeStampedModel):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, blank=True)
    title_snapshot = models.CharField(max_length=255)
    sku_snapshot = models.CharField(max_length=64, blank=True)
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        verbose_name = "Позиция заказа"
        verbose_name_plural = "Позиции заказа"

    def __str__(self) -> str:
        return f"{self.order.number} - {self.title_snapshot}"


class OrderStatusHistory(TimeStampedModel):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="status_history")
    status = models.CharField(max_length=16, choices=Order.OrderStatus.choices)
    comment = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["created_at"]
        verbose_name = "История статуса заказа"
        verbose_name_plural = "История статусов заказов"

    def __str__(self) -> str:
        return f"{self.order.number}: {self.status}"


class WholesalePriceList(TimeStampedModel):
    class Segment(models.TextChoices):
        BUSINESS = "business", "Юрлица"
        SCHOOL = "school", "Школы"
        UNIVERSITY = "university", "Университеты"

    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True)
    segment = models.CharField(max_length=16, choices=Segment.choices)
    file_url = models.URLField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Оптовый прайс-лист"
        verbose_name_plural = "Оптовые прайс-листы"

    def __str__(self) -> str:
        return self.title


class WholesaleRequest(TimeStampedModel):
    class OrganizationType(models.TextChoices):
        LLC = "llc", "Юридическое лицо"
        SCHOOL = "school", "Школа"
        UNIVERSITY = "university", "Университет"
        OTHER = "other", "Другое"

    class RequestStatus(models.TextChoices):
        NEW = "new", "Новая"
        IN_PROGRESS = "in_progress", "В работе"
        DONE = "done", "Обработана"
        DECLINED = "declined", "Отклонена"

    organization_name = models.CharField(max_length=255)
    organization_type = models.CharField(max_length=16, choices=OrganizationType.choices)
    contact_person = models.CharField(max_length=120)
    phone = models.CharField(max_length=32)
    email = models.EmailField()
    comment = models.TextField(blank=True)
    status = models.CharField(max_length=16, choices=RequestStatus.choices, default=RequestStatus.NEW)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Заявка на опт"
        verbose_name_plural = "Заявки на опт"

    def __str__(self) -> str:
        return f"{self.organization_name} ({self.get_organization_type_display()})"


class ReturnRequest(TimeStampedModel):
    class ReturnType(models.TextChoices):
        GOOD_QUALITY = "good_quality", "Надлежащее качество"
        DEFECT = "defect", "Недостаток товара"

    class ReturnStatus(models.TextChoices):
        NEW = "new", "Новая"
        CHECKING = "checking", "Проверка"
        APPROVED = "approved", "Одобрено"
        REJECTED = "rejected", "Отклонено"
        REFUNDED = "refunded", "Возврат выполнен"

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="return_requests")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    return_type = models.CharField(max_length=16, choices=ReturnType.choices)
    reason = models.TextField()
    status = models.CharField(max_length=16, choices=ReturnStatus.choices, default=ReturnStatus.NEW)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Заявка на возврат"
        verbose_name_plural = "Заявки на возврат"

    def __str__(self) -> str:
        return f"Return #{self.pk} ({self.order.number})"


class ReturnRequestItem(TimeStampedModel):
    return_request = models.ForeignKey(ReturnRequest, on_delete=models.CASCADE, related_name="items")
    order_item = models.ForeignKey(OrderItem, on_delete=models.SET_NULL, null=True, blank=True)
    quantity = models.PositiveIntegerField(default=1)
    comment = models.CharField(max_length=255, blank=True)

    class Meta:
        verbose_name = "Позиция возврата"
        verbose_name_plural = "Позиции возврата"

    def __str__(self) -> str:
        return f"Return item #{self.pk}"


class SitePage(TimeStampedModel):
    class PageType(models.TextChoices):
        ABOUT = "about", "О магазине"
        DELIVERY = "delivery", "Доставка и оплата"
        GUARANTEE = "guarantee", "Гарантия и возврат"
        WHOLESALE = "wholesale", "Оптовым клиентам"
        PRIVACY = "privacy", "Политика конфиденциальности"
        TERMS = "terms", "Пользовательское соглашение"
        OFFER = "offer", "Договор оферты"

    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True)
    page_type = models.CharField(max_length=24, choices=PageType.choices)
    content = models.TextField(blank=True)
    is_published = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Инфо-страница"
        verbose_name_plural = "Инфо-страницы"

    def __str__(self) -> str:
        return self.title


def set_slugs(sender, instance, **kwargs):
    if hasattr(instance, "slug") and not instance.slug:
        if hasattr(instance, "title") and instance.title:
            instance.slug = slugify(instance.title)
        elif hasattr(instance, "name") and instance.name:
            instance.slug = slugify(instance.name)


for model in [
    Category,
    Brand,
    Product,
    Promotion,
    GiftCertificate,
    BlogCategory,
    BlogPost,
    PickupPoint,
    WholesalePriceList,
    SitePage,
]:
    models.signals.pre_save.connect(set_slugs, sender=model)
