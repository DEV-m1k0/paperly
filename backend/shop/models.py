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
    phone = models.CharField("Телефон", max_length=32, blank=True)
    email = models.EmailField("Email", blank=True)
    city = models.CharField("Город", max_length=120, blank=True)
    address = models.CharField("Адрес офиса", max_length=255, blank=True)
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
    is_active = models.BooleanField("Активен", default=True)

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
            )
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

    class Meta:
        verbose_name = "Инфо-страница"
        verbose_name_plural = "Инфо-страницы"

    def __str__(self) -> str:
        return self.title


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
# Автогенерация slug
# ──────────────────────────────────────────────
def set_slugs(sender, instance, **kwargs):
    if hasattr(instance, "slug") and not instance.slug:
        if hasattr(instance, "title") and instance.title:
            instance.slug = slugify(instance.title, allow_unicode=True)
        elif hasattr(instance, "name") and instance.name:
            instance.slug = slugify(instance.name, allow_unicode=True)


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
