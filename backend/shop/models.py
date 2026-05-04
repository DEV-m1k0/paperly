import secrets

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils.text import slugify


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField("Создано", auto_now_add=True)
    updated_at = models.DateTimeField("Обновлено", auto_now=True)

    class Meta:
        abstract = True


# ──────────────────────────────────────────────
# Глобальные настройки сайта (singleton)
# ──────────────────────────────────────────────
class SiteSetting(models.Model):
    site_name = models.CharField("Название сайта", max_length=255, default="Paperly")
    tagline = models.CharField("Слоган", max_length=500, blank=True)

    # ── Контакты ──
    phone = models.CharField("Телефон (основной)", max_length=32, blank=True)
    secondary_phone = models.CharField(
        "Телефон (дополнительный)", max_length=32, blank=True,
        help_text="Например, для оптовых клиентов или другого региона.",
    )
    email = models.EmailField("Email (основной)", blank=True)
    sales_email = models.EmailField(
        "Email отдела продаж", blank=True,
        help_text="Если оставить пустым — везде показывается основной email.",
    )
    wholesale_email = models.EmailField(
        "Email для оптовых клиентов", blank=True,
        help_text="Используется на странице «Оптовым клиентам». Пусто — основной email.",
    )

    # ── Локация / часы ──
    city = models.CharField("Город", max_length=120, blank=True)
    address = models.CharField("Адрес офиса", max_length=255, blank=True)
    work_hours = models.CharField(
        "Часы работы (полные)", max_length=255, blank=True,
        help_text="Например: «Пн–Пт 09:00–21:00, Сб–Вс 10:00–18:00».",
    )
    work_hours_short = models.CharField(
        "Часы работы (короткая запись)", max_length=120, blank=True,
        help_text="Для шапки/футера: «09:00–21:00 ежедневно».",
    )
    latitude = models.DecimalField(
        "Широта офиса", max_digits=9, decimal_places=6, null=True, blank=True,
        help_text="Координата для карты на странице «Контакты».",
    )
    longitude = models.DecimalField(
        "Долгота офиса", max_digits=9, decimal_places=6, null=True, blank=True,
    )

    # ── Маркетинговые плашки ──
    free_shipping_from = models.DecimalField(
        "Бесплатная доставка от суммы, ₽", max_digits=10, decimal_places=2,
        null=True, blank=True,
        help_text="Если задано — на сайте показывается плашка «Бесплатная доставка от X ₽».",
    )
    free_shipping_text = models.CharField(
        "Текст плашки бесплатной доставки", max_length=200, blank=True,
        help_text="Если оставить пустым, текст соберётся автоматически.",
    )
    cookies_banner_text = models.TextField(
        "Текст cookie-баннера", blank=True,
        help_text="Если пусто — используется стандартный текст.",
    )

    copyright_text = models.CharField("Текст копирайта", max_length=255, blank=True)

    class Meta:
        verbose_name = "Настройки сайта"
        verbose_name_plural = "Настройки сайта"

    def __str__(self):
        return self.site_name

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


# ──────────────────────────────────────────────
# Каталог
# ──────────────────────────────────────────────
class Category(TimeStampedModel):
    name = models.CharField("Название", max_length=255)
    slug = models.SlugField("Слаг", max_length=255, unique=True)
    parent = models.ForeignKey(
        "self", verbose_name="Родительская категория",
        on_delete=models.CASCADE, related_name="children", null=True, blank=True,
    )
    description = models.TextField("Описание", blank=True)
    image_url = models.URLField("URL изображения", blank=True)
    image = models.ImageField("Изображение", upload_to="categories/", blank=True)
    sort_order = models.PositiveIntegerField("Порядок сортировки", default=0)
    is_active = models.BooleanField("Активна", default=True)

    class Meta:
        ordering = ["sort_order", "name"]
        constraints = [models.UniqueConstraint(fields=["parent", "name"], name="uniq_category_name_in_parent")]
        indexes = [
            # Menu-builder queries always pair "active" with parent traversal.
            models.Index(fields=["parent", "is_active"]),
        ]
        verbose_name = "Категория"
        verbose_name_plural = "Категории"

    @property
    def display_image_url(self):
        if self.image:
            return self.image.url
        return self.image_url

    def __str__(self) -> str:
        return self.name


class Brand(TimeStampedModel):
    name = models.CharField("Название", max_length=255, unique=True)
    slug = models.SlugField("Слаг", max_length=255, unique=True)
    description = models.TextField("Описание", blank=True)
    logo_url = models.URLField("URL логотипа", blank=True)
    logo = models.ImageField("Логотип", upload_to="brands/", blank=True)
    website = models.URLField("Сайт", blank=True)
    is_active = models.BooleanField("Активен", default=True, db_index=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Бренд"
        verbose_name_plural = "Бренды"

    def __str__(self) -> str:
        return self.name


class CatalogFilterGroup(TimeStampedModel):
    title = models.CharField("Заголовок", max_length=255)
    slug = models.SlugField("Слаг", max_length=255, unique=True)
    sort_order = models.PositiveIntegerField("Порядок сортировки", default=0)
    is_active = models.BooleanField("Активна", default=True)

    class Meta:
        ordering = ["sort_order", "title"]
        verbose_name = "Группа фильтров каталога"
        verbose_name_plural = "Группы фильтров каталога"

    def __str__(self) -> str:
        return self.title


class CatalogFilterOption(TimeStampedModel):
    group = models.ForeignKey(
        CatalogFilterGroup, verbose_name="Группа",
        on_delete=models.CASCADE, related_name="options",
    )
    label = models.CharField("Метка", max_length=255)
    query_param = models.CharField(
        "Параметр запроса", max_length=64,
        help_text=(
            "Параметр запроса для API. Допустимые значения: brand, category, "
            "purpose, product_format, sheets_count, in_stock, is_new, is_hit, "
            "is_featured, has_discount, has_promotion, sale."
        ),
    )
    value = models.CharField("Значение", max_length=64)
    sort_order = models.PositiveIntegerField("Порядок сортировки", default=0)
    is_active = models.BooleanField("Активна", default=True)

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

    title = models.CharField("Название", max_length=255)
    slug = models.SlugField("Слаг", max_length=255, unique=True)
    sku = models.CharField("Артикул", max_length=64, unique=True)
    brand = models.ForeignKey(Brand, verbose_name="Бренд", on_delete=models.PROTECT, related_name="products")
    categories = models.ManyToManyField(Category, verbose_name="Категории", related_name="products")

    short_description = models.CharField("Краткое описание", max_length=300, blank=True)
    description = models.TextField("Описание", blank=True)

    price = models.DecimalField("Цена", max_digits=10, decimal_places=2)
    old_price = models.DecimalField("Старая цена", max_digits=10, decimal_places=2, null=True, blank=True)
    stock = models.PositiveIntegerField("Остаток на складе", default=0)
    max_order_quantity = models.PositiveIntegerField(
        "Макс. кол-во в заказе", default=0,
        help_text="0 = без ограничения",
    )
    format = models.CharField("Формат", max_length=16, choices=ProductFormat.choices, default=ProductFormat.A4)
    sheets_count = models.PositiveSmallIntegerField("Кол-во листов", null=True, blank=True)
    purpose = models.CharField("Назначение", max_length=16, choices=ProductPurpose.choices, default=ProductPurpose.UNIVERSAL)

    status = models.CharField("Статус", max_length=16, choices=ProductStatus.choices, default=ProductStatus.ACTIVE)
    is_new = models.BooleanField("Новинка", default=False)
    is_hit = models.BooleanField("Хит продаж", default=False)
    is_featured = models.BooleanField("Рекомендуемый", default=False)

    weight_grams = models.PositiveIntegerField("Вес (г)", default=0)
    length_mm = models.PositiveIntegerField("Длина (мм)", default=0)
    width_mm = models.PositiveIntegerField("Ширина (мм)", default=0)
    height_mm = models.PositiveIntegerField("Высота (мм)", default=0)

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
            ),
            # DB-level guard against negative stock. PositiveIntegerField at
            # the Python level only validates via forms/serializers, but raw
            # F('stock') - quantity updates bypass that. This constraint makes
            # the DB reject the update transactionally.
            models.CheckConstraint(
                check=models.Q(stock__gte=0),
                name="product_stock_non_negative",
            ),
        ]
        verbose_name = "Товар"
        verbose_name_plural = "Товары"

    def __str__(self) -> str:
        return f"{self.title} ({self.sku})"


class ProductImage(TimeStampedModel):
    product = models.ForeignKey(Product, verbose_name="Товар", on_delete=models.CASCADE, related_name="images")
    image_url = models.URLField("URL изображения", blank=True)
    image = models.ImageField("Файл изображения", upload_to="products/", blank=True)
    alt_text = models.CharField("Альтернативный текст", max_length=255, blank=True)
    is_primary = models.BooleanField("Основное", default=False)
    sort_order = models.PositiveIntegerField("Порядок сортировки", default=0)

    @property
    def url(self):
        if self.image:
            return self.image.url
        return self.image_url

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
    product = models.ForeignKey(Product, verbose_name="Товар", on_delete=models.CASCADE, related_name="specifications")
    name = models.CharField("Название", max_length=120)
    value = models.CharField("Значение", max_length=255)
    sort_order = models.PositiveIntegerField("Порядок сортировки", default=0)

    class Meta:
        ordering = ["sort_order", "id"]
        constraints = [models.UniqueConstraint(fields=["product", "name"], name="uniq_spec_name_per_product")]
        verbose_name = "Характеристика товара"
        verbose_name_plural = "Характеристики товаров"

    def __str__(self) -> str:
        return f"{self.product.title}: {self.name}"


class ProductReview(TimeStampedModel):
    product = models.ForeignKey(Product, verbose_name="Товар", on_delete=models.CASCADE, related_name="reviews")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="Пользователь",
        on_delete=models.SET_NULL, null=True, blank=True,
    )
    author_name = models.CharField("Имя автора", max_length=120)
    rating = models.PositiveSmallIntegerField("Оценка", validators=[MinValueValidator(1), MaxValueValidator(5)])
    text = models.TextField("Текст отзыва")
    is_published = models.BooleanField("Опубликован", default=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Отзыв на товар"
        verbose_name_plural = "Отзывы на товары"

    def __str__(self) -> str:
        return f"{self.product.title} [{self.rating}/5]"


# ──────────────────────────────────────────────
# Маркетинг
# ──────────────────────────────────────────────
class Promotion(TimeStampedModel):
    class PromotionType(models.TextChoices):
        DISCOUNT = "discount", "Скидка"
        BUNDLE = "bundle", "Набор"
        GIFT = "gift", "Подарок"

    title = models.CharField("Название", max_length=255)
    slug = models.SlugField("Слаг", max_length=255, unique=True)
    description = models.TextField("Описание", blank=True)
    promo_type = models.CharField("Тип акции", max_length=16, choices=PromotionType.choices, default=PromotionType.DISCOUNT)
    discount_percent = models.PositiveSmallIntegerField(
        "Процент скидки", null=True, blank=True, validators=[MinValueValidator(1), MaxValueValidator(99)]
    )
    start_at = models.DateTimeField("Начало")
    end_at = models.DateTimeField("Окончание")
    is_active = models.BooleanField("Активна", default=True)
    products = models.ManyToManyField(Product, verbose_name="Товары", related_name="promotions", blank=True)

    class Meta:
        ordering = ["-start_at"]
        indexes = [
            # apply_product_filters and the catalog page query promotions by
            # is_active + start/end window — this triple-column index makes
            # it an index-only scan.
            models.Index(fields=["is_active", "start_at", "end_at"]),
        ]
        verbose_name = "Акция"
        verbose_name_plural = "Акции"

    def __str__(self) -> str:
        return self.title


class GiftCertificate(TimeStampedModel):
    title = models.CharField("Название", max_length=120)
    slug = models.SlugField("Слаг", max_length=120, unique=True)
    nominal = models.DecimalField("Номинал", max_digits=10, decimal_places=2)
    description = models.TextField("Описание", blank=True)
    is_active = models.BooleanField("Активен", default=True)

    class Meta:
        ordering = ["nominal"]
        verbose_name = "Подарочный сертификат"
        verbose_name_plural = "Подарочные сертификаты"

    def __str__(self) -> str:
        return f"{self.title} ({self.nominal})"


# ──────────────────────────────────────────────
# Блог
# ──────────────────────────────────────────────
class BlogCategory(TimeStampedModel):
    title = models.CharField("Заголовок", max_length=120, unique=True)
    slug = models.SlugField("Слаг", max_length=120, unique=True)

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

    title = models.CharField("Заголовок", max_length=255)
    slug = models.SlugField("Слаг", max_length=255, unique=True)
    category = models.ForeignKey(BlogCategory, verbose_name="Категория", on_delete=models.SET_NULL, null=True, blank=True)
    excerpt = models.CharField("Анонс", max_length=350, blank=True)
    content = models.TextField("Содержание")
    cover_url = models.URLField("URL обложки", blank=True)
    cover = models.ImageField("Обложка", upload_to="blog/", blank=True)
    status = models.CharField("Статус", max_length=16, choices=PostStatus.choices, default=PostStatus.DRAFT, db_index=True)

    @property
    def display_cover_url(self):
        if self.cover:
            return self.cover.url
        return self.cover_url

    @property
    def content_html(self):
        """Markdown → безопасный HTML.

        Импорт внутри метода — markdown_utils тащит markdown/bleach/pygments,
        не хочется грузить их при импорте моделей в worker'ах celery
        и management-командах, где блог не нужен.
        """
        from .markdown_utils import render_markdown
        return render_markdown(self.content or "")

    published_at = models.DateTimeField("Дата публикации", null=True, blank=True)

    class Meta:
        ordering = ["-published_at", "-created_at"]
        verbose_name = "Пост блога"
        verbose_name_plural = "Посты блога"

    def __str__(self) -> str:
        return self.title


# ──────────────────────────────────────────────
# Логистика
# ──────────────────────────────────────────────
class PickupPoint(TimeStampedModel):
    name = models.CharField("Название", max_length=255)
    slug = models.SlugField("Слаг", max_length=255, unique=True)
    city = models.CharField("Город", max_length=120)
    address = models.CharField("Адрес", max_length=255)
    metro = models.CharField("Метро / ориентир", max_length=120, blank=True)
    latitude = models.DecimalField("Широта", max_digits=9, decimal_places=6)
    longitude = models.DecimalField("Долгота", max_digits=9, decimal_places=6)
    opening_hours = models.CharField("Часы работы", max_length=255)
    is_active = models.BooleanField("Активен", default=True)

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

    title = models.CharField("Название", max_length=120)
    city = models.CharField("Город", max_length=120, blank=True)
    delivery_type = models.CharField("Тип доставки", max_length=16, choices=DeliveryType.choices)
    price = models.DecimalField("Цена", max_digits=10, decimal_places=2)
    free_from_amount = models.DecimalField("Бесплатно от суммы", max_digits=10, decimal_places=2, null=True, blank=True)
    eta_min_days = models.PositiveSmallIntegerField("Мин. дней доставки", default=1)
    eta_max_days = models.PositiveSmallIntegerField("Макс. дней доставки", default=1)
    is_active = models.BooleanField("Активен", default=True)

    class Meta:
        ordering = ["delivery_type", "city", "title"]
        verbose_name = "Тариф доставки"
        verbose_name_plural = "Тарифы доставки"

    def __str__(self) -> str:
        return f"{self.title} ({self.delivery_type})"


# ──────────────────────────────────────────────
# Клиенты
# ──────────────────────────────────────────────
class CustomerProfile(TimeStampedModel):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, verbose_name="Пользователь", on_delete=models.CASCADE, related_name="profile")
    first_name = models.CharField("Имя", max_length=120, blank=True)
    last_name = models.CharField("Фамилия", max_length=120, blank=True)
    phone = models.CharField("Телефон", max_length=32, blank=True)
    birth_date = models.DateField("Дата рождения", null=True, blank=True)

    class Meta:
        verbose_name = "Профиль клиента"
        verbose_name_plural = "Профили клиентов"

    def __str__(self) -> str:
        return f"Профиль: {self.user}"


class Address(TimeStampedModel):
    class AddressType(models.TextChoices):
        SHIPPING = "shipping", "Адрес доставки"
        BILLING = "billing", "Платежный адрес"

    profile = models.ForeignKey(CustomerProfile, verbose_name="Профиль", on_delete=models.CASCADE, related_name="addresses")
    address_type = models.CharField("Тип адреса", max_length=16, choices=AddressType.choices, default=AddressType.SHIPPING)
    city = models.CharField("Город", max_length=120)
    street = models.CharField("Улица", max_length=255)
    entrance = models.CharField("Подъезд", max_length=50, blank=True)
    flat_or_office = models.CharField("Кв./Офис", max_length=50, blank=True)
    postal_code = models.CharField("Почтовый индекс", max_length=20, blank=True)
    comment = models.TextField("Комментарий", blank=True)
    is_default = models.BooleanField("По умолчанию", default=False)

    class Meta:
        verbose_name = "Адрес"
        verbose_name_plural = "Адреса"
        constraints = [
            # At most one default address per (profile, address_type). The
            # _checkout_prefill code always picks the first default — having
            # multiple flagged led to non-deterministic prefills.
            models.UniqueConstraint(
                fields=["profile", "address_type"],
                condition=models.Q(is_default=True),
                name="uniq_default_address_per_profile_type",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.city}, {self.street}"


class NotificationSetting(TimeStampedModel):
    profile = models.OneToOneField(
        CustomerProfile, verbose_name="Профиль",
        on_delete=models.CASCADE, related_name="notification_settings",
    )
    order_status = models.BooleanField("Статус заказа", default=True)
    promotions = models.BooleanField("Акции", default=False)
    restock = models.BooleanField("Поступления", default=True)

    class Meta:
        verbose_name = "Настройки уведомлений"
        verbose_name_plural = "Настройки уведомлений"

    def __str__(self) -> str:
        return f"Уведомления: {self.profile.user}"


class Favorite(TimeStampedModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name="Пользователь", on_delete=models.CASCADE, related_name="favorites")
    product = models.ForeignKey(Product, verbose_name="Товар", on_delete=models.CASCADE, related_name="favorite_by")

    class Meta:
        constraints = [models.UniqueConstraint(fields=["user", "product"], name="uniq_user_favorite")]
        verbose_name = "Избранное"
        verbose_name_plural = "Избранное"

    def __str__(self) -> str:
        return f"{self.user} -> {self.product}"


# ──────────────────────────────────────────────
# Корзина
# ──────────────────────────────────────────────
class Cart(TimeStampedModel):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, verbose_name="Пользователь",
        on_delete=models.CASCADE, related_name="cart", null=True, blank=True,
    )
    session_key = models.CharField("Ключ сессии", max_length=64, blank=True, db_index=True)
    is_active = models.BooleanField("Активна", default=True)

    class Meta:
        verbose_name = "Корзина"
        verbose_name_plural = "Корзины"

    def __str__(self) -> str:
        return f"Корзина #{self.pk}"


class CartItem(TimeStampedModel):
    cart = models.ForeignKey(Cart, verbose_name="Корзина", on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, verbose_name="Товар", on_delete=models.CASCADE, related_name="in_carts")
    quantity = models.PositiveIntegerField("Количество", default=1)
    price_snapshot = models.DecimalField("Цена на момент добавления", max_digits=10, decimal_places=2)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["cart", "product"], name="uniq_cart_product")]
        verbose_name = "Позиция корзины"
        verbose_name_plural = "Позиции корзины"

    def __str__(self) -> str:
        return f"{self.cart} — {self.product} x{self.quantity}"


# ──────────────────────────────────────────────
# Заказы
# ──────────────────────────────────────────────
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

    user = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name="Покупатель", on_delete=models.SET_NULL, null=True, blank=True)
    number = models.CharField("Номер заказа", max_length=32, unique=True)
    status = models.CharField("Статус", max_length=16, choices=OrderStatus.choices, default=OrderStatus.NEW, db_index=True)

    full_name = models.CharField("ФИО", max_length=255)
    phone = models.CharField("Телефон", max_length=32)
    email = models.EmailField("Email")
    city = models.CharField("Город", max_length=120)
    address = models.CharField("Адрес", max_length=255)
    comment = models.TextField("Комментарий", blank=True)

    delivery_type = models.CharField("Тип доставки", max_length=16, choices=DeliveryType.choices)
    payment_type = models.CharField("Тип оплаты", max_length=16, choices=PaymentType.choices)
    pickup_point = models.ForeignKey(PickupPoint, verbose_name="Пункт самовывоза", on_delete=models.SET_NULL, null=True, blank=True)

    subtotal = models.DecimalField("Подытог", max_digits=12, decimal_places=2)
    delivery_price = models.DecimalField("Стоимость доставки", max_digits=12, decimal_places=2, default=0)
    discount_amount = models.DecimalField("Сумма скидки", max_digits=12, decimal_places=2, default=0)
    total = models.DecimalField("Итого", max_digits=12, decimal_places=2)
    promo_code = models.ForeignKey(
        "PromoCode", verbose_name="Промокод", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="orders",
    )

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            # Guest-order tracking by email; admin search ("моё имя"); promo
            # quota lookup by email.
            models.Index(fields=["email"]),
            # Admin date_hierarchy + status filters use this together a lot.
            models.Index(fields=["status", "created_at"]),
        ]
        verbose_name = "Заказ"
        verbose_name_plural = "Заказы"

    def __str__(self) -> str:
        return self.number


class OrderItem(TimeStampedModel):
    order = models.ForeignKey(Order, verbose_name="Заказ", on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, verbose_name="Товар", on_delete=models.SET_NULL, null=True, blank=True)
    title_snapshot = models.CharField("Название товара", max_length=255)
    sku_snapshot = models.CharField("Артикул", max_length=64, blank=True)
    quantity = models.PositiveIntegerField("Количество", default=1)
    unit_price = models.DecimalField("Цена за единицу", max_digits=10, decimal_places=2)

    class Meta:
        verbose_name = "Позиция заказа"
        verbose_name_plural = "Позиции заказа"

    def __str__(self) -> str:
        return f"{self.order.number} — {self.title_snapshot}"


class OrderStatusHistory(TimeStampedModel):
    order = models.ForeignKey(Order, verbose_name="Заказ", on_delete=models.CASCADE, related_name="status_history")
    status = models.CharField("Статус", max_length=16, choices=Order.OrderStatus.choices)
    comment = models.CharField("Комментарий", max_length=255, blank=True)

    class Meta:
        ordering = ["created_at"]
        verbose_name = "История статуса заказа"
        verbose_name_plural = "История статусов заказов"

    def __str__(self) -> str:
        return f"{self.order.number}: {self.status}"


# ──────────────────────────────────────────────
# Опт
# ──────────────────────────────────────────────
class WholesalePriceList(TimeStampedModel):
    class Segment(models.TextChoices):
        BUSINESS = "business", "Юрлица"
        SCHOOL = "school", "Школы"
        UNIVERSITY = "university", "Университеты"

    title = models.CharField("Название", max_length=255)
    slug = models.SlugField("Слаг", max_length=255, unique=True)
    segment = models.CharField("Сегмент", max_length=16, choices=Segment.choices)
    file_url = models.URLField("URL файла", blank=True)
    is_active = models.BooleanField("Активен", default=True)

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

    organization_name = models.CharField("Название организации", max_length=255)
    organization_type = models.CharField("Тип организации", max_length=16, choices=OrganizationType.choices)
    contact_person = models.CharField("Контактное лицо", max_length=120)
    phone = models.CharField("Телефон", max_length=32)
    email = models.EmailField("Email")
    comment = models.TextField("Комментарий", blank=True)
    status = models.CharField("Статус", max_length=16, choices=RequestStatus.choices, default=RequestStatus.NEW)

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

    order = models.ForeignKey(Order, verbose_name="Заказ", on_delete=models.CASCADE, related_name="return_requests")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name="Пользователь", on_delete=models.SET_NULL, null=True, blank=True)
    return_type = models.CharField("Тип возврата", max_length=16, choices=ReturnType.choices)
    reason = models.TextField("Причина")
    status = models.CharField("Статус", max_length=16, choices=ReturnStatus.choices, default=ReturnStatus.NEW)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Заявка на возврат"
        verbose_name_plural = "Заявки на возврат"

    def __str__(self) -> str:
        return f"Возврат #{self.pk} ({self.order.number})"


class ReturnRequestItem(TimeStampedModel):
    return_request = models.ForeignKey(ReturnRequest, verbose_name="Заявка на возврат", on_delete=models.CASCADE, related_name="items")
    order_item = models.ForeignKey(OrderItem, verbose_name="Позиция заказа", on_delete=models.SET_NULL, null=True, blank=True)
    quantity = models.PositiveIntegerField("Количество", default=1)
    comment = models.CharField("Комментарий", max_length=255, blank=True)

    class Meta:
        verbose_name = "Позиция возврата"
        verbose_name_plural = "Позиции возврата"

    def __str__(self) -> str:
        return f"Позиция возврата #{self.pk}"


# ──────────────────────────────────────────────
# Контент сайта (инфо-страницы)
# ──────────────────────────────────────────────
class SitePage(TimeStampedModel):
    class PageType(models.TextChoices):
        INDEX = "index", "Главная"
        ABOUT = "about", "О магазине"
        DELIVERY = "delivery", "Доставка и оплата"
        GUARANTEE = "guarantee", "Гарантия и возврат"
        WHOLESALE = "wholesale", "Оптовым клиентам"
        PICKUP = "pickup", "Пункты самовывоза"
        PRIVACY = "privacy", "Политика конфиденциальности"
        TERMS = "terms", "Пользовательское соглашение"
        OFFER = "offer", "Договор оферты"
        COOKIES = "cookies", "Политика cookie"

    title = models.CharField("Заголовок", max_length=255)
    slug = models.SlugField("Слаг", max_length=255, unique=True)
    page_type = models.CharField("Тип страницы", max_length=24, choices=PageType.choices)
    content = models.TextField("Содержание (HTML)", blank=True, help_text="HTML-контент страницы. Отображается в основном блоке.")
    is_published = models.BooleanField("Опубликована", default=True)

    # ── SEO meta (опциональные; при пустом значении используются дефолты сайта) ──
    meta_title = models.CharField(
        "SEO заголовок (title)", max_length=200, blank=True,
        help_text="То, что видно во вкладке браузера и в выдаче поисковиков. "
                  "Если пусто — берётся обычный заголовок страницы.",
    )
    meta_description = models.CharField(
        "SEO описание (description)", max_length=300, blank=True,
        help_text="2–3 предложения для сниппета в поисковой выдаче (≤160 симв. идеально).",
    )
    og_image = models.ImageField(
        "Картинка для соцсетей (OG image)", upload_to="seo/", blank=True,
        help_text="Превью при репосте ссылки в Telegram/VK/Facebook. Рекомендуем 1200×630.",
    )
    og_image_url = models.URLField(
        "URL картинки для соцсетей", blank=True,
        help_text="Если файл не загружен, можно указать прямую ссылку.",
    )

    class Meta:
        verbose_name = "Инфо-страница"
        verbose_name_plural = "Инфо-страницы"

    def __str__(self) -> str:
        return self.title

    @property
    def og_image_display_url(self) -> str:
        """Resolve the OG image: uploaded file first, fallback to URL."""
        if self.og_image:
            try:
                return self.og_image.url
            except Exception:
                pass
        return self.og_image_url or ""


# ──────────────────────────────────────────────
# Рассылка (newsletter)
# ──────────────────────────────────────────────
class SocialLink(TimeStampedModel):
    """Icon link in the site footer — Telegram, VK, YouTube, Instagram, etc.

    Admin can upload a custom icon image, or fall back to a Bootstrap Icons
    class (e.g. ``bi-telegram``). The footer picks the upload if present.
    """

    label = models.CharField(
        "Название", max_length=60,
        help_text="Видно в aria-label. Например: «Telegram», «ВКонтакте».",
    )
    url = models.URLField("Ссылка", max_length=300)
    icon_class = models.CharField(
        "Bootstrap-иконка", max_length=60, blank=True,
        help_text="Класс иконки из Bootstrap Icons, например: bi-telegram, bi-youtube. "
                  "Используется, если не загружена картинка.",
    )
    icon_image = models.ImageField(
        "Иконка (картинка)", upload_to="social-icons/", blank=True, null=True,
        help_text="PNG/SVG ≈ 48×48. Если загружено — используется вместо bi-класса.",
    )
    sort_order = models.PositiveIntegerField("Порядок", default=0)
    is_active = models.BooleanField("Показывать в футере", default=True)

    class Meta:
        verbose_name = "Ссылка на соцсеть"
        verbose_name_plural = "Ссылки на соцсети"
        ordering = ["sort_order", "label"]

    def __str__(self) -> str:
        return self.label

    @property
    def icon_url(self) -> str:
        try:
            return self.icon_image.url if self.icon_image else ""
        except Exception:
            return ""


class PromoCode(TimeStampedModel):
    """Coupon code a customer can redeem at checkout for a discount."""

    class DiscountType(models.TextChoices):
        PERCENT = "percent", "Процент от суммы"
        FIXED = "fixed", "Фиксированная сумма"
        FREE_SHIPPING = "free_shipping", "Бесплатная доставка"

    class Audience(models.TextChoices):
        ALL = "all", "Все покупатели"
        NEW_ONLY = "new_only", "Только для новых клиентов"
        REGISTERED = "registered", "Только для зарегистрированных"

    code = models.CharField(
        "Код", max_length=32, unique=True, db_index=True,
        help_text="Заглавные латиница/цифры. Например: PAPERLY10, SUMMER20.",
    )
    description = models.CharField("Описание (для админа)", max_length=200, blank=True)

    discount_type = models.CharField(
        "Тип скидки", max_length=16, choices=DiscountType.choices, default=DiscountType.PERCENT,
    )
    discount_value = models.DecimalField(
        "Размер", max_digits=10, decimal_places=2, default=0,
        help_text="Для процента — 1..100. Для фикс. суммы — рубли. Для free_shipping можно 0.",
    )
    max_discount_amount = models.DecimalField(
        "Максимум скидки, ₽", max_digits=10, decimal_places=2, null=True, blank=True,
        help_text="Необязательный потолок для процентных скидок. Оставьте пустым — без ограничения.",
    )
    min_order_amount = models.DecimalField(
        "Мин. сумма заказа, ₽", max_digits=10, decimal_places=2, default=0,
        help_text="Заказ ниже этой суммы не принимает промокод.",
    )

    valid_from = models.DateTimeField("Действует с", null=True, blank=True)
    valid_until = models.DateTimeField("Действует до", null=True, blank=True)

    usage_limit = models.PositiveIntegerField(
        "Лимит использований всего", default=0,
        help_text="0 = без ограничения. После достижения лимита код отключается.",
    )
    usage_limit_per_user = models.PositiveIntegerField(
        "Лимит на пользователя", default=1,
        help_text="Сколько раз один email может использовать код. 0 = без ограничения.",
    )
    used_count = models.PositiveIntegerField("Использовано раз", default=0, editable=False)

    audience = models.CharField(
        "Для кого", max_length=16, choices=Audience.choices, default=Audience.ALL,
    )

    applicable_products = models.ManyToManyField(
        Product, blank=True, related_name="promo_codes",
        help_text="Код действует только на выбранные товары. Пусто — весь каталог.",
    )
    applicable_categories = models.ManyToManyField(
        "Category", blank=True, related_name="promo_codes",
        help_text="Код действует только на товары из выбранных категорий.",
    )

    is_active = models.BooleanField("Активен", default=True)
    is_public = models.BooleanField(
        "Публиковать на сайте", default=False,
        help_text="Показывать на странице /promotions/. Включайте только для «широких» "
                  "кампаний (сезонные распродажи, баннерные акции). Точечные коды "
                  "(для рассылок, cart-abandonment, VIP) оставляйте выключенными — "
                  "они раздаются адресно.",
    )

    class Meta:
        verbose_name = "Промокод"
        verbose_name_plural = "Промокоды"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.code

    def save(self, *args, **kwargs):
        if self.code:
            self.code = self.code.strip().upper()
        super().save(*args, **kwargs)

    # Validation helpers ─────────────────────────────────────────────
    def is_time_valid(self, now=None) -> bool:
        from django.utils import timezone
        now = now or timezone.now()
        if self.valid_from and now < self.valid_from:
            return False
        if self.valid_until and now > self.valid_until:
            return False
        return True

    def quota_available(self) -> bool:
        if self.usage_limit == 0:
            return True
        return self.used_count < self.usage_limit

    def user_quota_available(self, *, user=None, email: str = "") -> bool:
        if self.usage_limit_per_user == 0:
            return True
        filters = models.Q()
        if user and user.is_authenticated:
            filters |= models.Q(user=user)
        if email:
            filters |= models.Q(email__iexact=email.strip())
        if not filters:
            return True  # anonymous guest with no email — nothing to check
        count = self.redemptions.filter(filters).count()
        return count < self.usage_limit_per_user


class PromoCodeRedemption(TimeStampedModel):
    """Log of every successful promo-code use — powers per-user limits + analytics."""

    promo = models.ForeignKey(PromoCode, verbose_name="Промокод", on_delete=models.CASCADE, related_name="redemptions")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="Пользователь",
        on_delete=models.SET_NULL, null=True, blank=True, related_name="promo_redemptions",
    )
    email = models.EmailField("Email", blank=True)
    order = models.ForeignKey("Order", verbose_name="Заказ", on_delete=models.CASCADE, related_name="promo_redemptions")
    amount_discounted = models.DecimalField("Сумма скидки", max_digits=12, decimal_places=2)

    class Meta:
        verbose_name = "Использование промокода"
        verbose_name_plural = "Использования промокодов"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["promo", "user"]),
            models.Index(fields=["promo", "email"]),
        ]

    def __str__(self) -> str:
        return f"{self.promo.code} → {self.email or (self.user and self.user.email) or '—'}"


class NewsletterSubscriber(TimeStampedModel):
    """Stores an opted-in email address for marketing emails."""

    email = models.EmailField("Email", unique=True)
    is_active = models.BooleanField("Активна", default=True, help_text="Снимается при отписке.")
    source = models.CharField(
        "Источник", max_length=64, default="footer", blank=True,
        help_text="Где оставили email: footer, checkout, manual...",
    )
    unsubscribe_token = models.CharField(
        max_length=64, unique=True, editable=False,
        help_text="Секретный токен для ссылки отписки.",
    )
    unsubscribed_at = models.DateTimeField("Отписался", null=True, blank=True)

    class Meta:
        verbose_name = "Подписчик рассылки"
        verbose_name_plural = "Подписчики рассылки"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.email

    def save(self, *args, **kwargs):
        if not self.unsubscribe_token:
            self.unsubscribe_token = secrets.token_urlsafe(32)
        super().save(*args, **kwargs)


class NewsletterCampaign(TimeStampedModel):
    """Admin-created campaign that gets emailed to all active subscribers."""

    class Status(models.TextChoices):
        DRAFT = "draft", "Черновик"
        SENDING = "sending", "Отправляется"
        SENT = "sent", "Отправлено"

    subject = models.CharField("Тема письма", max_length=200)
    preview = models.CharField(
        "Превью-строка", max_length=200, blank=True,
        help_text="Короткая строка, которую показывают почтовые клиенты рядом с темой.",
    )
    heading = models.CharField("Заголовок в письме", max_length=200)
    intro_html = models.TextField(
        "Вступление (HTML)", blank=True,
        help_text="Основной текст перед карточками товаров. Разрешён базовый HTML.",
    )
    cta_label = models.CharField("Текст кнопки", max_length=60, default="Перейти в каталог")
    cta_url = models.CharField(
        "Ссылка кнопки", max_length=300, default="/catalog/",
        help_text="Абсолютная ссылка или относительная (будет преобразована).",
    )
    featured_products = models.ManyToManyField(
        Product, blank=True, related_name="campaigns",
        help_text="До 6 товаров, которые покажутся в письме карточками.",
    )
    status = models.CharField("Статус", max_length=16, choices=Status.choices, default=Status.DRAFT)
    sent_at = models.DateTimeField("Отправлено", null=True, blank=True)
    sent_count = models.PositiveIntegerField("Доставлено писем", default=0)

    class Meta:
        verbose_name = "Рассылка (кампания)"
        verbose_name_plural = "Рассылки (кампании)"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.subject


# ──────────────────────────────────────────────
# Контент главной страницы (singleton + блоки)
# ──────────────────────────────────────────────
class HomePage(TimeStampedModel):
    """Singleton-модель с настраиваемым контентом главной.

    Все поля опциональны: если не заполнены, шаблон index.html использует
    встроенные дефолтные значения (как было до внедрения админки). Это
    позволяет включать кастомизацию инкрементально.
    """

    # ── Hero ──
    hero_eyebrow = models.CharField(
        "Hero · подпись над заголовком", max_length=120, blank=True,
        help_text='Маленькая строка над h1. Пример: «Paperly — канцтовары».',
    )
    hero_title = models.CharField(
        "Hero · основной заголовок", max_length=255, blank=True,
        help_text='Главный заголовок страницы. Пример: «Соберите идеальный набор».',
    )
    hero_title_accent = models.CharField(
        "Hero · акцентный фрагмент", max_length=200, blank=True,
        help_text="Часть заголовка, которая выделится цветом. Пример: «учёбы, офиса и творчества».",
    )
    hero_subtitle = models.TextField(
        "Hero · подзаголовок (lead)", blank=True,
        help_text="2–3 предложения под заголовком. Можно писать обычным текстом.",
    )
    hero_cta_primary_label = models.CharField("Hero · CTA #1 · текст", max_length=60, blank=True)
    hero_cta_primary_url = models.CharField(
        "Hero · CTA #1 · ссылка", max_length=300, blank=True,
        help_text="Абсолютная или относительная ссылка. Пример: «/catalog/», «https://…».",
    )
    hero_cta_primary_icon = models.CharField(
        "Hero · CTA #1 · иконка", max_length=60, blank=True,
        help_text="Bootstrap-icons класс, например: bi-grid, bi-arrow-right.",
    )
    hero_cta_secondary_label = models.CharField("Hero · CTA #2 · текст", max_length=60, blank=True)
    hero_cta_secondary_url = models.CharField("Hero · CTA #2 · ссылка", max_length=300, blank=True)
    hero_cta_secondary_icon = models.CharField("Hero · CTA #2 · иконка", max_length=60, blank=True)

    # ── Управление видимостью секций ──
    show_stats = models.BooleanField(
        "Показывать блок «цифры о магазине»", default=True,
        help_text="Плашка с автоматическими цифрами (товары/бренды/пункты).",
    )
    show_categories = models.BooleanField("Показывать «Популярные категории»", default=True)
    show_promotions = models.BooleanField("Показывать «Акции и скидки»", default=True)
    show_new_arrivals = models.BooleanField("Показывать «Новинки»", default=True)
    show_bestsellers = models.BooleanField("Показывать «Хиты продаж»", default=True)
    show_brands = models.BooleanField("Показывать «Популярные бренды»", default=True)
    show_services = models.BooleanField("Показывать карточки сервисов (доставка/пункты/опт)", default=True)
    show_features = models.BooleanField("Показывать блок «Почему покупают»", default=True)

    # ── Заголовки секций (опциональные оверрайды) ──
    features_title = models.CharField(
        "Заголовок блока «Почему мы»", max_length=200, blank=True,
        help_text='Если пусто — «Почему покупают в {название_сайта}».',
    )
    features_eyebrow = models.CharField(
        "Подпись над «Почему мы»", max_length=120, blank=True,
        help_text='По умолчанию — «Почему мы».',
    )

    # ── Подборки ──
    featured_categories = models.ManyToManyField(
        "Category", verbose_name="Витринные категории", blank=True, related_name="featured_on_homepage",
        help_text="Если выбраны — заменяют дефолтные карточки в блоке «Популярные категории». "
                  "Иконка/цвет берётся из «Карточек категорий на главной» (см. ниже) при совпадении.",
    )
    featured_products = models.ManyToManyField(
        "Product", verbose_name="Витринные товары (опц.)", blank=True, related_name="featured_on_homepage",
        help_text="Если задано — рендерятся под hero как «Рекомендуем». До 8 шт по sort_order.",
    )

    class Meta:
        verbose_name = "Главная страница"
        verbose_name_plural = "Главная страница"

    def __str__(self) -> str:
        return "Главная страница"

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def load(cls):
        """Singleton accessor — always returns the row, creating if missing."""
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    @property
    def hero_image_url(self) -> str:
        """Currently no hero image field — reserved for future expansion."""
        return ""


class HomeHeroCard(TimeStampedModel):
    """Карточка справа от hero-блока (сейчас их 3: «Снова в школу», «Офис», «Творческая зона»)."""

    class ColorVariant(models.TextChoices):
        SCHOOL = "school", "Школа (бирюза)"
        OFFICE = "office", "Офис (нейтральный)"
        ART = "art", "Творчество (амбер)"
        DEFAULT = "default", "Базовый"

    home = models.ForeignKey(HomePage, verbose_name="Главная", on_delete=models.CASCADE, related_name="hero_cards")
    badge = models.CharField(
        "Бейдж (необязательно)", max_length=60, blank=True,
        help_text='Маленькая плашка над заголовком, например «Снова в школу».',
    )
    title = models.CharField("Заголовок карточки", max_length=120)
    description = models.CharField("Описание", max_length=200, blank=True)
    icon_class = models.CharField(
        "Иконка", max_length=60, blank=True,
        help_text="Bootstrap-icons класс, например: bi-backpack, bi-briefcase, bi-palette.",
    )
    url = models.CharField(
        "Ссылка", max_length=300,
        help_text="Куда ведёт карточка. Пример: «/catalog/?category=kids».",
    )
    color_variant = models.CharField(
        "Цветовая схема", max_length=16, choices=ColorVariant.choices, default=ColorVariant.DEFAULT,
    )
    sort_order = models.PositiveIntegerField("Порядок", default=0)
    is_active = models.BooleanField("Показывать", default=True)

    class Meta:
        ordering = ["sort_order", "id"]
        verbose_name = "Hero · карточка"
        verbose_name_plural = "Hero · карточки"

    def __str__(self) -> str:
        return self.title


class HomeCategoryCard(TimeStampedModel):
    """Карточки в блоке «Популярные категории».

    Когда заданы — полностью заменяют дефолтные 6 захардкоженных карточек.
    Пусто — рендерится дефолт из шаблона.
    """

    home = models.ForeignKey(HomePage, verbose_name="Главная", on_delete=models.CASCADE, related_name="category_cards")
    title = models.CharField("Заголовок", max_length=120)
    subtitle = models.CharField("Подпись (мелкая)", max_length=200, blank=True)
    icon_class = models.CharField(
        "Иконка", max_length=60, blank=True,
        help_text="Bootstrap-icons класс. Примеры: bi-journal-bookmark, bi-pencil, bi-palette.",
    )
    url = models.CharField(
        "Ссылка", max_length=300,
        help_text="Например: «/catalog/?category=paper» или «/brands/».",
    )
    color_modifier = models.CharField(
        "CSS-модификатор", max_length=24, blank=True,
        help_text="Хвост к классу .category-card—. Допустимые: paper, writing, art, office, kids, brands. "
                  "Пусто — без подсветки.",
    )
    sort_order = models.PositiveIntegerField("Порядок", default=0)
    is_active = models.BooleanField("Показывать", default=True)

    class Meta:
        ordering = ["sort_order", "id"]
        verbose_name = "Карточка категории"
        verbose_name_plural = "Карточки категорий"

    def __str__(self) -> str:
        return self.title


class HomeFeature(TimeStampedModel):
    """Блок «Почему покупают в Paperly» — 4 преимущества."""

    class ColorVariant(models.TextChoices):
        TEAL = "teal", "Бирюзовый"
        AMBER = "amber", "Янтарный"
        ROSE = "rose", "Розовый"
        INDIGO = "indigo", "Индиго"

    home = models.ForeignKey(HomePage, verbose_name="Главная", on_delete=models.CASCADE, related_name="features")
    icon_class = models.CharField(
        "Иконка", max_length=60,
        help_text="Bootstrap-icons. Примеры: bi-box-seam, bi-lightning-charge, bi-arrow-counterclockwise, bi-percent.",
    )
    color_variant = models.CharField(
        "Цвет иконки", max_length=16, choices=ColorVariant.choices, default=ColorVariant.TEAL,
    )
    title = models.CharField("Заголовок", max_length=120)
    description = models.CharField("Описание", max_length=300)
    sort_order = models.PositiveIntegerField("Порядок", default=0)
    is_active = models.BooleanField("Показывать", default=True)

    class Meta:
        ordering = ["sort_order", "id"]
        verbose_name = "Преимущество"
        verbose_name_plural = "Преимущества"

    def __str__(self) -> str:
        return self.title


# ──────────────────────────────────────────────
# Контент страниц About / Delivery / Wholesale (singleton-ы)
# ──────────────────────────────────────────────
# Все три модели следуют единому паттерну:
#   * singleton (одна запись на проект, pk=1)
#   * Hero-блок (eyebrow / title / accent / subtitle / 2 CTA)
#   * Видимость секций (булевые флаги show_*)
#   * Inline-блоки (features / steps / faq / bullets)
#   * Шаблон делает fallback на захардкоженный дизайн, если запись пустая
#     или не создана — это гарантирует совместимость с существующим сайтом.


class AboutPage(TimeStampedModel):
    """Singleton для контента страницы /about/."""

    # ── Hero ──
    hero_eyebrow = models.CharField("Hero · подпись", max_length=120, blank=True)
    hero_title = models.CharField("Hero · заголовок", max_length=255, blank=True)
    hero_title_accent = models.CharField("Hero · акцент в заголовке", max_length=200, blank=True)
    hero_subtitle = models.TextField("Hero · подзаголовок", blank=True)
    hero_cta_primary_label = models.CharField("Hero · CTA #1 · текст", max_length=60, blank=True)
    hero_cta_primary_url = models.CharField("Hero · CTA #1 · ссылка", max_length=300, blank=True)
    hero_cta_primary_icon = models.CharField("Hero · CTA #1 · иконка", max_length=60, blank=True)
    hero_cta_secondary_label = models.CharField("Hero · CTA #2 · текст", max_length=60, blank=True)
    hero_cta_secondary_url = models.CharField("Hero · CTA #2 · ссылка", max_length=300, blank=True)
    hero_cta_secondary_icon = models.CharField("Hero · CTA #2 · иконка", max_length=60, blank=True)

    # ── Mission card (правый блок hero) ──
    mission_eyebrow = models.CharField("Mission · заголовок", max_length=120, blank=True)
    mission_title = models.CharField("Mission · подпись", max_length=200, blank=True)
    mission_text = models.TextField("Mission · описание", blank=True)
    mission_icon = models.CharField(
        "Mission · иконка", max_length=60, blank=True,
        help_text="Bootstrap-icons класс (bi-compass и т.п.). Пусто — дефолт.",
    )

    # ── Section visibility ──
    show_stats = models.BooleanField("Показывать «цифры о магазине»", default=True)
    show_features = models.BooleanField("Показывать «Преимущества»", default=True)
    show_steps = models.BooleanField("Показывать «Как мы работаем»", default=True)
    show_b2b_cta = models.BooleanField("Показывать B2B CTA", default=True)
    show_contacts = models.BooleanField("Показывать «Контакты»", default=True)

    # ── Section titles (опциональные оверрайды) ──
    features_eyebrow = models.CharField("Features · подпись", max_length=120, blank=True)
    features_title = models.CharField("Features · заголовок", max_length=200, blank=True)
    steps_eyebrow = models.CharField("Steps · подпись", max_length=120, blank=True)
    steps_title = models.CharField("Steps · заголовок", max_length=200, blank=True)
    contacts_eyebrow = models.CharField("Contacts · подпись", max_length=120, blank=True)
    contacts_title = models.CharField("Contacts · заголовок", max_length=200, blank=True)

    # ── B2B CTA section ──
    b2b_eyebrow = models.CharField("B2B · подпись", max_length=120, blank=True)
    b2b_title = models.CharField("B2B · заголовок", max_length=200, blank=True)
    b2b_text = models.TextField("B2B · описание", blank=True)
    b2b_button_label = models.CharField("B2B · текст кнопки", max_length=60, blank=True)
    b2b_button_url = models.CharField("B2B · ссылка кнопки", max_length=300, blank=True)

    class Meta:
        verbose_name = "Страница «О магазине»"
        verbose_name_plural = "Страница «О магазине»"

    def __str__(self) -> str:
        return "Страница «О магазине»"

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class AboutFeature(TimeStampedModel):
    """Карточки в блоке «Преимущества» страницы /about/."""

    class ColorVariant(models.TextChoices):
        TEAL = "teal", "Бирюзовый"
        AMBER = "amber", "Янтарный"
        ROSE = "rose", "Розовый"
        INDIGO = "indigo", "Индиго"

    page = models.ForeignKey(AboutPage, on_delete=models.CASCADE, related_name="features", verbose_name="Страница")
    icon_class = models.CharField("Иконка", max_length=60, help_text="Bootstrap-icons. Пример: bi-box-seam.")
    color_variant = models.CharField("Цвет иконки", max_length=16, choices=ColorVariant.choices, default=ColorVariant.TEAL)
    title = models.CharField("Заголовок", max_length=120)
    description = models.CharField("Описание", max_length=300)
    meta_label = models.CharField(
        "Доп. подпись", max_length=120, blank=True,
        help_text='Например, "12 категорий". Опционально.',
    )
    sort_order = models.PositiveIntegerField("Порядок", default=0)
    is_active = models.BooleanField("Показывать", default=True)

    class Meta:
        ordering = ["sort_order", "id"]
        verbose_name = "About · преимущество"
        verbose_name_plural = "About · преимущества"

    def __str__(self) -> str:
        return self.title


class AboutStep(TimeStampedModel):
    """Шаги «Как мы работаем» на странице /about/."""

    page = models.ForeignKey(AboutPage, on_delete=models.CASCADE, related_name="steps", verbose_name="Страница")
    title = models.CharField("Заголовок", max_length=120)
    description = models.CharField("Описание", max_length=300)
    sort_order = models.PositiveIntegerField("Порядок (номер шага)", default=0)
    is_active = models.BooleanField("Показывать", default=True)

    class Meta:
        ordering = ["sort_order", "id"]
        verbose_name = "About · шаг"
        verbose_name_plural = "About · шаги"

    def __str__(self) -> str:
        return f"{self.sort_order}. {self.title}"


class AboutMissionBullet(TimeStampedModel):
    """Список buzz-points в правой карточке «Наша миссия» страницы /about/."""

    page = models.ForeignKey(AboutPage, on_delete=models.CASCADE, related_name="mission_bullets", verbose_name="Страница")
    icon_class = models.CharField("Иконка", max_length=60, help_text="Например: bi-patch-check-fill.")
    label = models.CharField("Текст", max_length=200)
    sort_order = models.PositiveIntegerField("Порядок", default=0)
    is_active = models.BooleanField("Показывать", default=True)

    class Meta:
        ordering = ["sort_order", "id"]
        verbose_name = "About · пункт миссии"
        verbose_name_plural = "About · пункты миссии"

    def __str__(self) -> str:
        return self.label


class AboutB2BBullet(TimeStampedModel):
    """Список преимуществ внутри B2B CTA-блока на странице /about/."""

    page = models.ForeignKey(AboutPage, on_delete=models.CASCADE, related_name="b2b_bullets", verbose_name="Страница")
    icon_class = models.CharField(
        "Иконка", max_length=60, blank=True,
        help_text="Опционально. По умолчанию используется bi-check2-circle.",
    )
    label = models.CharField("Текст", max_length=200)
    sort_order = models.PositiveIntegerField("Порядок", default=0)
    is_active = models.BooleanField("Показывать", default=True)

    class Meta:
        ordering = ["sort_order", "id"]
        verbose_name = "About · B2B пункт"
        verbose_name_plural = "About · B2B пункты"

    def __str__(self) -> str:
        return self.label


# ─────────── Delivery ────────────────────────────────────────────────


class DeliveryPage(TimeStampedModel):
    """Singleton для контента страницы /delivery/."""

    # ── Hero ──
    hero_eyebrow = models.CharField("Hero · подпись", max_length=120, blank=True)
    hero_title = models.CharField("Hero · заголовок", max_length=255, blank=True)
    hero_title_accent = models.CharField("Hero · акцент", max_length=200, blank=True)
    hero_subtitle = models.TextField("Hero · подзаголовок", blank=True)
    hero_cta_primary_label = models.CharField("Hero · CTA #1 · текст", max_length=60, blank=True)
    hero_cta_primary_url = models.CharField("Hero · CTA #1 · ссылка", max_length=300, blank=True)
    hero_cta_primary_icon = models.CharField("Hero · CTA #1 · иконка", max_length=60, blank=True)
    hero_cta_secondary_label = models.CharField("Hero · CTA #2 · текст", max_length=60, blank=True)
    hero_cta_secondary_url = models.CharField("Hero · CTA #2 · ссылка", max_length=300, blank=True)
    hero_cta_secondary_icon = models.CharField("Hero · CTA #2 · иконка", max_length=60, blank=True)

    # ── Free-delivery card (правый блок hero) ──
    free_card_ribbon = models.CharField("Карточка · ribbon", max_length=40, blank=True)
    free_card_kicker = models.CharField("Карточка · kicker", max_length=40, blank=True)
    free_card_title = models.CharField(
        "Карточка · заголовок", max_length=120, blank=True,
        help_text="Можно использовать <br> для переноса строки.",
    )
    free_card_subtitle = models.CharField(
        "Карточка · подпись", max_length=200, blank=True,
        help_text="Например: «при заказе от <b>2 500 ₽</b>». HTML разрешён (только b/strong/em).",
    )

    # ── Section visibility ──
    show_calc = models.BooleanField("Показывать «Калькулятор бесплатной доставки»", default=True)
    show_steps = models.BooleanField("Показывать «От оформления до получения»", default=True)
    show_pay_methods = models.BooleanField("Показывать «Способы оплаты»", default=True)
    show_faq = models.BooleanField("Показывать FAQ", default=True)
    show_final_cta = models.BooleanField("Показывать финальный CTA «Готовы оформить заказ?»", default=True)

    # ── Section titles ──
    tariffs_eyebrow = models.CharField("Tariffs · подпись", max_length=120, blank=True)
    tariffs_title = models.CharField("Tariffs · заголовок", max_length=200, blank=True)
    tariffs_subtitle = models.CharField("Tariffs · подпись под заголовком", max_length=300, blank=True)
    steps_eyebrow = models.CharField("Steps · подпись", max_length=120, blank=True)
    steps_title = models.CharField("Steps · заголовок", max_length=200, blank=True)
    pay_eyebrow = models.CharField("Pay · подпись", max_length=120, blank=True)
    pay_title = models.CharField("Pay · заголовок", max_length=200, blank=True)
    faq_eyebrow = models.CharField("FAQ · подпись", max_length=120, blank=True)
    faq_title = models.CharField("FAQ · заголовок", max_length=200, blank=True)

    # ── Final CTA ──
    final_cta_title = models.CharField("Final CTA · заголовок", max_length=200, blank=True)
    final_cta_text = models.CharField("Final CTA · текст", max_length=300, blank=True)

    class Meta:
        verbose_name = "Страница «Доставка»"
        verbose_name_plural = "Страница «Доставка»"

    def __str__(self) -> str:
        return "Страница «Доставка»"

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class DeliveryFreeCardItem(TimeStampedModel):
    """Пункты внутри free-delivery карточки (правый блок hero)."""

    page = models.ForeignKey(DeliveryPage, on_delete=models.CASCADE, related_name="free_card_items", verbose_name="Страница")
    label = models.CharField("Что", max_length=120, help_text='Например, «По городу Курск».')
    value = models.CharField("Срок / условие", max_length=120, help_text='Например, «1–2 дня».')
    sort_order = models.PositiveIntegerField("Порядок", default=0)
    is_active = models.BooleanField("Показывать", default=True)

    class Meta:
        ordering = ["sort_order", "id"]
        verbose_name = "Delivery · пункт карточки"
        verbose_name_plural = "Delivery · пункты карточки"

    def __str__(self) -> str:
        return f"{self.label} — {self.value}"


class DeliveryStep(TimeStampedModel):
    """Шаги «От оформления до получения»."""

    page = models.ForeignKey(DeliveryPage, on_delete=models.CASCADE, related_name="steps", verbose_name="Страница")
    icon_class = models.CharField("Иконка", max_length=60, help_text="Например: bi-bag-check, bi-box-seam, bi-truck.")
    title = models.CharField("Заголовок", max_length=120)
    description = models.CharField("Описание", max_length=300)
    sort_order = models.PositiveIntegerField("Порядок (номер шага)", default=0)
    is_active = models.BooleanField("Показывать", default=True)

    class Meta:
        ordering = ["sort_order", "id"]
        verbose_name = "Delivery · шаг"
        verbose_name_plural = "Delivery · шаги"

    def __str__(self) -> str:
        return f"{self.sort_order}. {self.title}"


class DeliveryPayMethod(TimeStampedModel):
    """Карточки «Способы оплаты»."""

    class ColorVariant(models.TextChoices):
        TEAL = "teal", "Бирюзовый"
        AMBER = "amber", "Янтарный"
        ROSE = "rose", "Розовый"
        INDIGO = "indigo", "Индиго"

    page = models.ForeignKey(DeliveryPage, on_delete=models.CASCADE, related_name="pay_methods", verbose_name="Страница")
    icon_class = models.CharField("Иконка", max_length=60)
    color_variant = models.CharField("Цвет", max_length=16, choices=ColorVariant.choices, default=ColorVariant.TEAL)
    title = models.CharField("Заголовок", max_length=120)
    description = models.CharField("Описание", max_length=300)
    badges_text = models.CharField(
        "Бейджи (через запятую)", max_length=200, blank=True,
        help_text='Краткие пометки внизу карточки. Пример: «VISA, MasterCard, МИР».',
    )
    sort_order = models.PositiveIntegerField("Порядок", default=0)
    is_active = models.BooleanField("Показывать", default=True)

    class Meta:
        ordering = ["sort_order", "id"]
        verbose_name = "Delivery · способ оплаты"
        verbose_name_plural = "Delivery · способы оплаты"

    def __str__(self) -> str:
        return self.title


class DeliveryFAQ(TimeStampedModel):
    """Вопросы и ответы блока FAQ."""

    page = models.ForeignKey(DeliveryPage, on_delete=models.CASCADE, related_name="faqs", verbose_name="Страница")
    question = models.CharField("Вопрос", max_length=255)
    answer = models.TextField("Ответ", help_text="Можно использовать HTML (ссылки и т.п.).")
    sort_order = models.PositiveIntegerField("Порядок", default=0)
    is_active = models.BooleanField("Показывать", default=True)

    class Meta:
        ordering = ["sort_order", "id"]
        verbose_name = "Delivery · FAQ"
        verbose_name_plural = "Delivery · FAQ"

    def __str__(self) -> str:
        return self.question


# ─────────── Wholesale ───────────────────────────────────────────────


class WholesalePage(TimeStampedModel):
    """Singleton для контента страницы /wholesale/."""

    # ── Hero ──
    hero_eyebrow = models.CharField("Hero · подпись", max_length=120, blank=True)
    hero_title = models.CharField("Hero · заголовок", max_length=255, blank=True)
    hero_title_accent = models.CharField("Hero · акцент", max_length=200, blank=True)
    hero_subtitle = models.TextField("Hero · подзаголовок", blank=True)
    hero_cta_primary_label = models.CharField("Hero · CTA #1 · текст", max_length=60, blank=True)
    hero_cta_primary_url = models.CharField(
        "Hero · CTA #1 · ссылка", max_length=300, blank=True,
        help_text='По умолчанию ведёт на форму заявки в этой же странице («#request»).',
    )
    hero_cta_primary_icon = models.CharField("Hero · CTA #1 · иконка", max_length=60, blank=True)

    # ── Side card (правый блок hero) ──
    side_eyebrow = models.CharField("Side · подпись", max_length=120, blank=True)
    side_title = models.CharField("Side · заголовок", max_length=200, blank=True)
    side_text = models.TextField("Side · описание", blank=True)
    side_icon = models.CharField("Side · иконка", max_length=60, blank=True)

    # ── Section visibility ──
    show_features = models.BooleanField("Показывать «Условия»", default=True)
    show_steps = models.BooleanField("Показывать «Как начать работу»", default=True)
    show_form = models.BooleanField("Показывать форму заявки", default=True)

    # ── Section titles ──
    features_eyebrow = models.CharField("Features · подпись", max_length=120, blank=True)
    features_title = models.CharField("Features · заголовок", max_length=200, blank=True)
    steps_eyebrow = models.CharField("Steps · подпись", max_length=120, blank=True)
    steps_title = models.CharField("Steps · заголовок", max_length=200, blank=True)
    form_eyebrow = models.CharField("Form · подпись", max_length=120, blank=True)
    form_title = models.CharField("Form · заголовок", max_length=200, blank=True)
    form_intro_title = models.CharField("Form · заголовок интро-блока", max_length=200, blank=True)
    form_intro_text = models.CharField("Form · текст интро-блока", max_length=300, blank=True)

    class Meta:
        verbose_name = "Страница «Опт»"
        verbose_name_plural = "Страница «Опт»"

    def __str__(self) -> str:
        return "Страница «Опт»"

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class WholesaleFeature(TimeStampedModel):
    """Преимущества опт-сотрудничества."""

    class ColorVariant(models.TextChoices):
        TEAL = "teal", "Бирюзовый"
        AMBER = "amber", "Янтарный"
        ROSE = "rose", "Розовый"
        INDIGO = "indigo", "Индиго"

    page = models.ForeignKey(WholesalePage, on_delete=models.CASCADE, related_name="features", verbose_name="Страница")
    icon_class = models.CharField("Иконка", max_length=60)
    color_variant = models.CharField("Цвет иконки", max_length=16, choices=ColorVariant.choices, default=ColorVariant.TEAL)
    title = models.CharField("Заголовок", max_length=120)
    description = models.CharField("Описание", max_length=300)
    sort_order = models.PositiveIntegerField("Порядок", default=0)
    is_active = models.BooleanField("Показывать", default=True)

    class Meta:
        ordering = ["sort_order", "id"]
        verbose_name = "Wholesale · преимущество"
        verbose_name_plural = "Wholesale · преимущества"

    def __str__(self) -> str:
        return self.title


class WholesaleStep(TimeStampedModel):
    """Шаги «Как начать работу»."""

    page = models.ForeignKey(WholesalePage, on_delete=models.CASCADE, related_name="steps", verbose_name="Страница")
    title = models.CharField("Заголовок", max_length=120)
    description = models.CharField("Описание", max_length=300)
    sort_order = models.PositiveIntegerField("Порядок (номер шага)", default=0)
    is_active = models.BooleanField("Показывать", default=True)

    class Meta:
        ordering = ["sort_order", "id"]
        verbose_name = "Wholesale · шаг"
        verbose_name_plural = "Wholesale · шаги"

    def __str__(self) -> str:
        return f"{self.sort_order}. {self.title}"


class WholesaleSideBullet(TimeStampedModel):
    """Список преимуществ в правой side-карточке hero-блока."""

    page = models.ForeignKey(WholesalePage, on_delete=models.CASCADE, related_name="side_bullets", verbose_name="Страница")
    icon_class = models.CharField(
        "Иконка", max_length=60, blank=True,
        help_text="Опционально. По умолчанию bi-check2-circle.",
    )
    label = models.CharField("Текст", max_length=200)
    sort_order = models.PositiveIntegerField("Порядок", default=0)
    is_active = models.BooleanField("Показывать", default=True)

    class Meta:
        ordering = ["sort_order", "id"]
        verbose_name = "Wholesale · пункт side-карточки"
        verbose_name_plural = "Wholesale · пункты side-карточки"

    def __str__(self) -> str:
        return self.label


# ──────────────────────────────────────────────
# Автогенерация slug — с защитой от коллизий
# ──────────────────────────────────────────────
def _build_unique_slug(model_cls, base_slug: str, *, exclude_pk=None) -> str:
    """Append -2, -3, ... if `base_slug` already taken in this model."""
    if not base_slug:
        return base_slug
    qs = model_cls.objects.filter(slug=base_slug)
    if exclude_pk is not None:
        qs = qs.exclude(pk=exclude_pk)
    if not qs.exists():
        return base_slug
    counter = 2
    while True:
        candidate = f"{base_slug}-{counter}"
        if not model_cls.objects.filter(slug=candidate).exclude(pk=exclude_pk or 0).exists():
            return candidate
        counter += 1


def set_slugs(sender, instance, **kwargs):
    """Pre-save signal: derive slug from title/name and ensure uniqueness.

    Two products named "Тетрадь" used to crash on `.save()` because the
    raw slugified value collided with the unique constraint. We now suffix
    with -2, -3, ... up to a unique value.
    """
    if not hasattr(instance, "slug"):
        return
    if instance.slug:
        return  # admin already set one explicitly

    source = ""
    if hasattr(instance, "title") and instance.title:
        source = instance.title
    elif hasattr(instance, "name") and instance.name:
        source = instance.name
    if not source:
        return

    base = slugify(source, allow_unicode=True)
    instance.slug = _build_unique_slug(sender, base, exclude_pk=instance.pk)


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
