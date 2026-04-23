import hashlib
import random
import shutil
from datetime import timedelta
from io import BytesIO
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files import File
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify

from shop.models import (
    Address,
    BlogCategory,
    BlogPost,
    Brand,
    Cart,
    CartItem,
    CatalogFilterGroup,
    CatalogFilterOption,
    Category,
    CustomerProfile,
    DeliveryTariff,
    Favorite,
    GiftCertificate,
    NotificationSetting,
    Order,
    OrderItem,
    OrderStatusHistory,
    PickupPoint,
    Product,
    ProductImage,
    ProductReview,
    ProductSpecification,
    Promotion,
    ReturnRequest,
    ReturnRequestItem,
    SitePage,
    SiteSetting,
    WholesalePriceList,
    WholesaleRequest,
)

MEDIA_SRC = Path(settings.BASE_DIR) / "media"

# Each product/blog/category gets its own unique local image.
# Реальные JPG лежат в backend/media/{products,blog,categories,brands}/...
# (они трекаются в git специально — см. .gitignore).
# Если конкретного файла нет — генерим плейсхолдер Pillow'ом на лету,
# так что на Render ничего никогда не ломается.

CATEGORY_IMAGES = {
    "paper": "categories/paper.jpg",
    "writing": "categories/writing.jpg",
    "art": "categories/art.jpg",
    "office": "categories/office.jpg",
    "kids": "categories/kids.jpg",
}

# Цветовая палитра для plaseholder'ов по категории товара (SKU-prefix → цвет).
# Подобрано под брендинг Paperly (teal + янтарный акцент).
PLACEHOLDER_COLORS = {
    "NB": ("#0e766e", "#14a398"),   # тетради — teal
    "PP": ("#0a5f58", "#0e766e"),   # бумага — тёмный teal
    "WR": ("#f59e0b", "#fbbf24"),   # ручки/карандаши — янтарный
    "AR": ("#e85d75", "#f27a8b"),   # художка — розовый
    "OF": ("#475569", "#64748b"),   # офис — графитовый
    "KD": ("#7c3aed", "#a78bfa"),   # школа/дети — фиолетовый
    "_default": ("#0e766e", "#14a398"),
}

BLOG_IMAGES = ["blog/blog_01.jpg", "blog/blog_02.jpg", "blog/blog_03.jpg", "blog/blog_04.jpg", "blog/blog_05.jpg"]

REVIEW_NAMES = [
    "Анна К.", "Дмитрий С.", "Елена В.", "Михаил П.", "Ольга Н.",
    "Сергей Т.", "Ирина Л.", "Алексей М.", "Наталья Б.", "Виктор Г.",
    "Марина Д.", "Павел Ж.", "Татьяна Р.", "Андрей Х.", "Юлия Ф.",
]

REVIEW_TEXTS = [
    "Отличное качество, рекомендую! Буду заказывать ещё.",
    "Товар полностью соответствует описанию. Быстрая доставка.",
    "Хорошее соотношение цены и качества. Ребёнок доволен.",
    "Использую для работы каждый день, очень удобно.",
    "Покупаю не первый раз, всегда стабильное качество.",
    "Приятный дизайн и хорошие материалы.",
    "Для школы — идеальный вариант, всё как нужно.",
    "Немного дороговато, но качество того стоит.",
    "Заказывали для офиса, все остались довольны.",
    "Подарили коллеге — очень понравилось!",
]


def _hex_to_rgb(hex_color):
    hex_color = hex_color.lstrip("#")
    return tuple(int(hex_color[i : i + 2], 16) for i in (0, 2, 4))


def _generate_placeholder_jpg(dest_path: Path, label: str, subtitle: str = "", palette_key: str = "_default"):
    """Draw a 600×600 JPG placeholder: градиент + центрированный текст.

    Запускается только если реального файла нет (когда конкретная картинка
    не была подготовлена вручную, либо её удалили из media/).
    """
    from PIL import Image, ImageDraw, ImageFont

    start_hex, end_hex = PLACEHOLDER_COLORS.get(palette_key, PLACEHOLDER_COLORS["_default"])
    start = _hex_to_rgb(start_hex)
    end = _hex_to_rgb(end_hex)

    size = 600
    img = Image.new("RGB", (size, size), start)
    draw = ImageDraw.Draw(img)

    # Диагональный градиент
    for y in range(size):
        ratio = y / size
        r = int(start[0] * (1 - ratio) + end[0] * ratio)
        g = int(start[1] * (1 - ratio) + end[1] * ratio)
        b = int(start[2] * (1 - ratio) + end[2] * ratio)
        draw.line([(0, y), (size, y)], fill=(r, g, b))

    # Декоративный круг в углу — добавляет визуального интереса
    draw.ellipse([size - 180, -60, size + 120, 240], fill=(255, 255, 255, 40), outline=None)

    # Шрифты — ищем кириллический TTF. Порядок важен: сначала Linux
    # (Render = Ubuntu, DejaVu всегда есть), потом macOS, потом Windows.
    # Дефолтный PIL bitmap-шрифт кириллицу не поддерживает, поэтому если
    # вдруг ничего не нашли — показываем только SKU-подпись латиницей.
    _font_candidates_bold = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf",
        "/Library/Fonts/Arial Bold.ttf",
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "C:/Windows/Fonts/arialbd.ttf",
        "C:/Windows/Fonts/segoeuib.ttf",
        "DejaVuSans-Bold.ttf",                  # в PATH
    ]
    _font_candidates_regular = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/TTF/DejaVuSans.ttf",
        "/Library/Fonts/Arial.ttf",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/segoeui.ttf",
        "DejaVuSans.ttf",
    ]

    def _load_font(paths, size):
        for p in paths:
            try:
                return ImageFont.truetype(p, size)
            except (OSError, IOError):
                continue
        return None

    font_title = _load_font(_font_candidates_bold, 42)
    font_sub = _load_font(_font_candidates_regular, 24)
    cyrillic_ok = font_title is not None
    if font_title is None:
        font_title = ImageFont.load_default()
    if font_sub is None:
        font_sub = ImageFont.load_default()

    # Если кириллического шрифта не нашли — заменяем заголовок на SKU,
    # чтобы не рисовать "квадраты" вместо текста
    if not cyrillic_ok and subtitle:
        label, subtitle = subtitle, ""

    # Вписываем заголовок в 3 строки максимум
    words = label.split()
    lines, line = [], ""
    for w in words:
        test = (line + " " + w).strip()
        if len(test) > 22 and line:
            lines.append(line)
            line = w
        else:
            line = test
    if line:
        lines.append(line)
    lines = lines[:3]

    total_h = len(lines) * 52
    y0 = (size - total_h) // 2 - 20
    for i, ln in enumerate(lines):
        bbox = draw.textbbox((0, 0), ln, font=font_title)
        w = bbox[2] - bbox[0]
        draw.text(((size - w) // 2, y0 + i * 52), ln, fill="white", font=font_title)

    if subtitle:
        bbox = draw.textbbox((0, 0), subtitle, font=font_sub)
        w = bbox[2] - bbox[0]
        draw.text(((size - w) // 2, y0 + total_h + 20), subtitle, fill=(255, 255, 255, 200), font=font_sub)

    dest_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(dest_path, format="JPEG", quality=82, optimize=True)


def _attach_image(instance, field_name, src_path, *, label=None, subtitle=None, palette_key="_default", stdout=None):
    """Set model's ImageField to point at a file in MEDIA_ROOT.

    Если файл уже есть (например, закоммичен в git и доехал на сервер) —
    просто присваиваем относительный путь полю. Если нет — генерим
    plausible-placeholder через Pillow и кладём в MEDIA_ROOT, чтобы
    карточки товаров никогда не были пустыми.
    """
    full_path = MEDIA_SRC / src_path
    if not full_path.exists():
        if label is None:
            # Нет данных для плейсхолдера — нечем заполнить, пропускаем
            if stdout:
                stdout.write(f"  [skip] Нет картинки {src_path}, нет label для fallback")
            return
        if stdout:
            stdout.write(f"  [gen]  Генерим плейсхолдер {src_path} для '{label}'")
        try:
            _generate_placeholder_jpg(full_path, label, subtitle or "", palette_key)
        except Exception as e:
            if stdout:
                stdout.write(f"  [err]  Не удалось сгенерить {src_path}: {e}")
            return

    setattr(instance, field_name, src_path)
    # update_at не у всех моделей — сохраняем без update_fields, чтобы не падать
    try:
        instance.save(update_fields=[field_name, "updated_at"])
    except Exception:
        instance.save()


class Command(BaseCommand):
    help = "Seed database with extended demo data for Paperly"

    def add_arguments(self, parser):
        parser.add_argument("--reset", action="store_true", help="Delete old demo entities before seeding")

    def handle(self, *args, **options):
        # Каждая секция — в своей транзакции + try/except. Так если одна
        # упадёт (например, валидация новой модели), остальные — в т.ч.
        # привязка картинок к товарам/блогу — сохранятся.
        if options["reset"]:
            self.stdout.write("Resetting demo entities...")
            with transaction.atomic():
                self._reset_data()

        categories_map, brands, products = None, None, None

        def _section(label, fn, *args, **kwargs):
            self.stdout.write(f"Seeding {label}...")
            try:
                with transaction.atomic():
                    return fn(*args, **kwargs)
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"  ✗ {label} failed: {e}"))
                return None

        categories_map = _section("categories", self._seed_categories)
        brands = _section("brands", self._seed_brands)
        if categories_map is not None and brands is not None:
            products = _section("products", self._seed_products, categories_map, brands)
        if products is not None:
            _section("marketing", self._seed_marketing, products)
        _section("logistics", self._seed_logistics)
        _section("content", self._seed_content)
        _section("wholesale", self._seed_wholesale)
        if brands is not None:
            _section("filters", self._seed_filters, brands)
        _section("gift certificates", self._seed_gift_certificates)
        if products is not None:
            _section("customer data", self._seed_customer_data, products)
        _section("returns", self._seed_returns)
        _section("site settings", self._seed_site_settings)

        count = len(products) if products else 0
        self.stdout.write(self.style.SUCCESS(f"Done! Created {count} products."))

    def _reset_data(self):
        for model in [
            ReturnRequestItem, ReturnRequest,
            OrderStatusHistory, OrderItem, Order,
            ProductReview, ProductImage, ProductSpecification, Favorite,
            CartItem, Cart,
            CatalogFilterOption, CatalogFilterGroup,
            GiftCertificate, Promotion, Product,
            WholesaleRequest, WholesalePriceList,
            SitePage, BlogPost, BlogCategory,
            DeliveryTariff, PickupPoint,
            NotificationSetting, Address, CustomerProfile,
            Category, Brand,
        ]:
            model.objects.all().delete()

    # ─── Categories ──────────────────────────────
    def _seed_categories(self):
        tree = {
            "paper": {
                "title": "Бумажная продукция",
                "children": [
                    "Тетради", "Блокноты и ежедневники",
                    "Альбомы и папки для черчения",
                    "Бумага для офисной техники",
                    "Цветная бумага и картон",
                    "Бумага для заметок",
                ],
            },
            "writing": {
                "title": "Письменные принадлежности",
                "children": [
                    "Ручки шариковые", "Ручки гелевые",
                    "Карандаши простые", "Карандаши цветные",
                    "Маркеры и текстовыделители", "Фломастеры",
                ],
            },
            "art": {
                "title": "Художественные товары",
                "children": [
                    "Краски", "Кисти",
                    "Пастель и уголь", "Пластилин и лепка",
                    "Чертёжные инструменты", "Скетчбуки",
                ],
            },
            "office": {
                "title": "Товары для офиса",
                "children": [
                    "Папки и архивация", "Органайзеры",
                    "Канцелярские мелочи", "Расходники для оргтехники",
                    "Клей и скотч", "Корректоры",
                ],
            },
            "kids": {
                "title": "Школа и творчество",
                "children": [
                    "Наборы первоклассника", "Пеналы и ранцы",
                    "Наборы для творчества", "Дневники",
                ],
            },
        }

        # Сопоставление ключа категории → префикс SKU для подбора цвета плейсхолдера
        palette_for_group = {"paper": "NB", "writing": "WR", "art": "AR", "office": "OF", "kids": "KD"}

        categories_map = {}
        for idx, (key, payload) in enumerate(tree.items(), start=1):
            parent, _ = Category.objects.get_or_create(
                slug=key,
                defaults={"name": payload["title"], "sort_order": idx},
            )
            img_path = CATEGORY_IMAGES.get(key)
            if img_path and not parent.image:
                _attach_image(
                    parent, "image", img_path,
                    label=payload["title"],
                    subtitle="Paperly",
                    palette_key=palette_for_group.get(key, "_default"),
                    stdout=self.stdout,
                )
            categories_map[key] = [parent]
            for child_idx, child in enumerate(payload["children"], start=1):
                child_obj, _ = Category.objects.get_or_create(
                    slug=f"{parent.slug}-{child_idx}",
                    defaults={"name": child, "parent": parent, "sort_order": child_idx},
                )
                categories_map[key].append(child_obj)
        return categories_map

    # ─── Brands ──────────────────────────────────
    def _seed_brands(self):
        brands_seed = [
            ("erich-krause", "Erich Krause", "Немецкое качество для школы и офиса"),
            ("kores", "Kores", "Канцелярия европейского качества"),
            ("brauberg", "Brauberg", "Надёжные канцтовары для бизнеса"),
            ("maped", "Maped", "Французский бренд для творчества"),
            ("pilot", "Pilot", "Японские ручки и маркеры"),
            ("faber-castell", "Faber-Castell", "Премиальные карандаши с 1761 года"),
            ("hatber", "Hatber", "Тетради и блокноты для школьников"),
            ("bg", "BG", "Бюджетные канцтовары для школы"),
            ("berlingo", "Berlingo", "Качественная канцелярия для офиса"),
            ("pentel", "Pentel", "Японские ручки и фломастеры"),
        ]

        by_slug = {}
        for slug, name, desc in brands_seed:
            brand, _ = Brand.objects.get_or_create(
                slug=slug,
                defaults={"name": name, "description": desc},
            )
            if not brand.logo:
                _attach_image(
                    brand, "logo", f"brands/{slug}.jpg",
                    label=name, subtitle="BRAND",
                    palette_key="_default", stdout=self.stdout,
                )
            by_slug[slug] = brand
        return by_slug

    # ─── Products ────────────────────────────────
    def _seed_products(self, categories_map, brands):
        catalog = [
            # ──── Бумажная продукция ────
            {"title": "Тетрадь школьная A5 12 листов клетка", "sku": "NB-001", "price": 45, "group": "paper", "brand": "bg", "format": "A5", "sheets": 12, "purpose": "school", "desc": "Классическая школьная тетрадь с плотной обложкой. Белая бумага, чёткая линовка."},
            {"title": "Тетрадь A5 48 листов клетка", "sku": "NB-002", "price": 120, "group": "paper", "brand": "hatber", "format": "A5", "sheets": 48, "purpose": "school", "desc": "Общая тетрадь для средней и старшей школы. Скругленные углы."},
            {"title": "Тетрадь A5 96 листов линейка", "sku": "NB-003", "price": 195, "group": "paper", "brand": "hatber", "format": "A5", "sheets": 96, "purpose": "school", "desc": "Толстая тетрадь для конспектов и рефератов. Твердая обложка."},
            {"title": "Тетрадь A4 96 листов на спирали", "sku": "NB-004", "price": 290, "group": "paper", "brand": "brauberg", "format": "A4", "sheets": 96, "purpose": "office", "desc": "Офисная тетрадь на металлической спирали. Микроперфорация для отрыва."},
            {"title": "Блокнот A5 на спирали 80 листов", "sku": "NB-005", "price": 240, "group": "paper", "brand": "berlingo", "format": "A5", "sheets": 80, "purpose": "office", "desc": "Блокнот для заметок. Ламинированная обложка, удобный формат."},
            {"title": "Ежедневник датированный A5", "sku": "NB-006", "price": 590, "group": "paper", "brand": "brauberg", "format": "A5", "sheets": 176, "purpose": "office", "desc": "Ежедневник на текущий год. Обложка из экокожи, ляссе."},
            {"title": "Бумага офисная A4 500 листов", "sku": "PP-001", "price": 760, "group": "paper", "brand": "brauberg", "format": "A4", "sheets": 500, "purpose": "office", "desc": "Бумага для принтеров и копиров. Яркость 146 CIE, плотность 80 г/м²."},
            {"title": "Бумага A3 500 листов", "sku": "PP-002", "price": 1290, "group": "paper", "brand": "brauberg", "format": "A3", "sheets": 500, "purpose": "office", "desc": "Бумага большого формата для чертежей, плакатов и печати."},
            {"title": "Цветной картон A4 10 листов", "sku": "PP-003", "price": 180, "group": "paper", "brand": "kores", "format": "A4", "sheets": 10, "purpose": "creative", "desc": "Набор цветного картона для поделок и аппликаций. 10 ярких цветов."},
            {"title": "Стикеры для заметок 76×76 мм 400 листов", "sku": "PP-004", "price": 210, "group": "paper", "brand": "berlingo", "format": "other", "sheets": 400, "purpose": "office", "desc": "Самоклеящиеся блоки для заметок. 4 неоновых цвета по 100 листов."},
            {"title": "Цветная бумага A4 16 листов", "sku": "PP-005", "price": 130, "group": "paper", "brand": "hatber", "format": "A4", "sheets": 16, "purpose": "creative", "desc": "Двусторонняя цветная бумага для детского творчества."},

            # ──── Письменные принадлежности ────
            {"title": "Ручка шариковая синяя 0.7 мм", "sku": "WR-001", "price": 35, "group": "writing", "brand": "pilot", "format": "other", "sheets": None, "purpose": "school", "desc": "Мягкое письмо, эргономичный корпус. Стержень увеличенной длины."},
            {"title": "Ручка шариковая автоматическая", "sku": "WR-002", "price": 85, "group": "writing", "brand": "pilot", "format": "other", "sheets": None, "purpose": "office", "desc": "Автоматическая ручка с кнопочным механизмом. Резиновый грип."},
            {"title": "Набор гелевых ручек 6 цветов", "sku": "WR-003", "price": 280, "group": "writing", "brand": "pentel", "format": "other", "sheets": None, "purpose": "creative", "desc": "Яркие гелевые ручки с быстросохнущими чернилами. Толщина 0.5 мм."},
            {"title": "Набор гелевых ручек 12 цветов", "sku": "WR-004", "price": 420, "group": "writing", "brand": "pentel", "format": "other", "sheets": None, "purpose": "creative", "desc": "Расширенный набор для рисования и письма. В пластиковом кейсе."},
            {"title": "Карандаш чернографитный HB", "sku": "WR-005", "price": 25, "group": "writing", "brand": "faber-castell", "format": "other", "sheets": None, "purpose": "school", "desc": "Классический карандаш для письма и черчения. Экологичная древесина."},
            {"title": "Набор карандашей HB-2B 6 шт", "sku": "WR-006", "price": 180, "group": "writing", "brand": "faber-castell", "format": "other", "sheets": None, "purpose": "school", "desc": "Набор чернографитных карандашей разной мягкости для черчения."},
            {"title": "Карандаши цветные 12 цветов", "sku": "WR-007", "price": 290, "group": "writing", "brand": "faber-castell", "format": "other", "sheets": None, "purpose": "creative", "desc": "Яркие цветные карандаши с мягким грифелем. Шестигранный корпус."},
            {"title": "Карандаши цветные 24 цвета", "sku": "WR-008", "price": 490, "group": "writing", "brand": "faber-castell", "format": "other", "sheets": None, "purpose": "creative", "desc": "Расширенный набор для рисования. В металлической коробке."},
            {"title": "Текстовыделители пастельные 6 шт", "sku": "WR-009", "price": 260, "group": "writing", "brand": "maped", "format": "other", "sheets": None, "purpose": "office", "desc": "Нежные пастельные тона для выделения текста. Скошенный наконечник."},
            {"title": "Маркеры перманентные 4 шт", "sku": "WR-010", "price": 190, "group": "writing", "brand": "erich-krause", "format": "other", "sheets": None, "purpose": "office", "desc": "Перманентные маркеры: чёрный, синий, красный, зелёный. Толщина 2 мм."},
            {"title": "Фломастеры смываемые 12 шт", "sku": "WR-011", "price": 290, "group": "writing", "brand": "maped", "format": "other", "sheets": None, "purpose": "school", "desc": "Безопасные фломастеры для детей. Смываются с одежды и кожи."},
            {"title": "Фломастеры двусторонние 24 цвета", "sku": "WR-012", "price": 520, "group": "writing", "brand": "maped", "format": "other", "sheets": None, "purpose": "creative", "desc": "Тонкий и толстый наконечник в каждом фломастере."},

            # ──── Художественные товары ────
            {"title": "Краски акварельные 12 цветов", "sku": "AR-001", "price": 350, "group": "art", "brand": "erich-krause", "format": "other", "sheets": None, "purpose": "creative", "desc": "Медовая акварель. Яркие насыщенные цвета, легко смешиваются."},
            {"title": "Краски акварельные 24 цвета", "sku": "AR-002", "price": 690, "group": "art", "brand": "faber-castell", "format": "other", "sheets": None, "purpose": "creative", "desc": "Профессиональная акварель. Высокая пигментация, устойчивость к свету."},
            {"title": "Краски гуашевые 12 цветов", "sku": "AR-003", "price": 420, "group": "art", "brand": "erich-krause", "format": "other", "sheets": None, "purpose": "creative", "desc": "Гуашь для школы и творчества. Плотное покрытие, яркие цвета."},
            {"title": "Кисти синтетика набор 6 шт", "sku": "AR-004", "price": 360, "group": "art", "brand": "maped", "format": "other", "sheets": None, "purpose": "creative", "desc": "Круглые кисти разных размеров. Качественный синтетический ворс."},
            {"title": "Пастель сухая 24 цвета", "sku": "AR-005", "price": 520, "group": "art", "brand": "faber-castell", "format": "other", "sheets": None, "purpose": "creative", "desc": "Мягкая пастель для рисования. Интенсивные цвета, легко растушёвывается."},
            {"title": "Пластилин мягкий 18 цветов", "sku": "AR-006", "price": 310, "group": "art", "brand": "erich-krause", "format": "other", "sheets": None, "purpose": "school", "desc": "Восковой пластилин для лепки. Не липнет к рукам, яркие цвета."},
            {"title": "Циркуль металлический", "sku": "AR-007", "price": 240, "group": "art", "brand": "maped", "format": "other", "sheets": None, "purpose": "school", "desc": "Точный циркуль из нержавеющей стали. С запасными грифелями."},
            {"title": "Скетчбук A5 крафт 80 листов", "sku": "AR-008", "price": 380, "group": "art", "brand": "berlingo", "format": "A5", "sheets": 80, "purpose": "creative", "desc": "Скетчбук с крафтовой бумагой 100 г/м². Для эскизов и зарисовок."},
            {"title": "Набор для скрапбукинга", "sku": "AR-009", "price": 780, "group": "art", "brand": "hatber", "format": "other", "sheets": None, "purpose": "creative", "desc": "Декоративная бумага, наклейки, ленты. 120 элементов в наборе."},
            {"title": "Альбом для рисования A4 40 листов", "sku": "AR-010", "price": 230, "group": "art", "brand": "hatber", "format": "A4", "sheets": 40, "purpose": "school", "desc": "Альбом на скрепке. Плотная бумага 120 г/м² для акварели и карандашей."},

            # ──── Товары для офиса ────
            {"title": "Папка-регистратор A4 70 мм", "sku": "OF-001", "price": 210, "group": "office", "brand": "brauberg", "format": "A4", "sheets": None, "purpose": "office", "desc": "Папка с арочным механизмом. Ламинированный картон, корешок 70 мм."},
            {"title": "Органайзер настольный", "sku": "OF-002", "price": 540, "group": "office", "brand": "berlingo", "format": "other", "sheets": None, "purpose": "office", "desc": "Компактный органайзер для ручек, скрепок и стикеров. 6 отделений."},
            {"title": "Степлер офисный №24/6", "sku": "OF-003", "price": 330, "group": "office", "brand": "kores", "format": "other", "sheets": None, "purpose": "office", "desc": "Сшивает до 25 листов. Эргономичный корпус, надёжный механизм."},
            {"title": "Дырокол на 20 листов", "sku": "OF-004", "price": 290, "group": "office", "brand": "kores", "format": "other", "sheets": None, "purpose": "office", "desc": "Металлический дырокол с линейкой-ограничителем. 2 отверстия."},
            {"title": "Ножницы офисные 21 см", "sku": "OF-005", "price": 180, "group": "office", "brand": "maped", "format": "other", "sheets": None, "purpose": "office", "desc": "Лезвия из нержавеющей стали. Эргономичные кольца с мягкими вставками."},
            {"title": "Клей-карандаш 15 г", "sku": "OF-006", "price": 65, "group": "office", "brand": "erich-krause", "format": "other", "sheets": None, "purpose": "school", "desc": "Быстросохнущий клей-карандаш. Не морщит бумагу, экономичный расход."},
            {"title": "Скотч прозрачный 19 мм × 33 м", "sku": "OF-007", "price": 95, "group": "office", "brand": "berlingo", "format": "other", "sheets": None, "purpose": "office", "desc": "Канцелярский скотч на стандартной втулке. Прочный клеевой слой."},
            {"title": "Корректор-ручка 7 мл", "sku": "OF-008", "price": 75, "group": "office", "brand": "kores", "format": "other", "sheets": None, "purpose": "office", "desc": "Точечная коррекция текста. Тонкий металлический наконечник."},

            # ──── Школа и творчество ────
            {"title": "Набор первоклассника 28 предметов", "sku": "KD-001", "price": 1990, "group": "kids", "brand": "erich-krause", "format": "other", "sheets": None, "purpose": "school", "desc": "Полный стартовый комплект: тетради, ручки, карандаши, линейка, ластик и многое другое."},
            {"title": "Пенал на молнии с отделениями", "sku": "KD-002", "price": 420, "group": "kids", "brand": "maped", "format": "other", "sheets": None, "purpose": "school", "desc": "Вместительный пенал с 3 отделениями. Яркий дизайн для школьников."},
            {"title": "Ранец школьный ортопедический", "sku": "KD-003", "price": 3490, "group": "kids", "brand": "erich-krause", "format": "other", "sheets": None, "purpose": "school", "desc": "Анатомическая спинка, светоотражающие элементы. Объём 15 литров."},
            {"title": "Дневник школьный твёрдая обложка", "sku": "KD-004", "price": 180, "group": "kids", "brand": "hatber", "format": "A5", "sheets": 48, "purpose": "school", "desc": "Дневник для 1-11 класса. Справочная информация, карта России."},
            {"title": "Набор для опытов Юный химик", "sku": "KD-005", "price": 1290, "group": "kids", "brand": "erich-krause", "format": "other", "sheets": None, "purpose": "creative", "desc": "Безопасные химические опыты для детей от 8 лет. 15 экспериментов."},
            {"title": "Набор для квиллинга", "sku": "KD-006", "price": 450, "group": "kids", "brand": "hatber", "format": "other", "sheets": None, "purpose": "creative", "desc": "Полоски бумаги, инструменты и шаблоны для бумагокручения."},
        ]

        products = []
        for idx, item in enumerate(catalog, start=1):
            product, created = Product.objects.get_or_create(
                sku=item["sku"],
                defaults={
                    "title": item["title"],
                    "slug": slugify(item["sku"]),
                    "brand": brands[item["brand"]],
                    "price": item["price"],
                    "old_price": int(item["price"] * 1.15) if idx % 3 != 0 else None,
                    "stock": 10 + idx * 2,
                    "format": item["format"],
                    "sheets_count": item["sheets"],
                    "purpose": item["purpose"],
                    "short_description": item["desc"][:200],
                    "description": item["desc"],
                    "is_new": idx % 4 == 0,
                    "is_hit": idx % 5 == 0,
                    "is_featured": idx % 7 == 0,
                    "weight_grams": 50 + idx * 8,
                    "length_mm": 100 + idx * 3,
                    "width_mm": 50 + idx * 2,
                    "height_mm": 5 + idx,
                },
            )

            # Привязываем уникальную картинку по SKU. Цвет плейсхолдера —
            # по префиксу SKU (NB/PP/WR/AR/OF/KD).
            img_file = f"products/{item['sku']}.jpg"
            sku_prefix = item["sku"].split("-")[0]
            pi1, pi_created1 = ProductImage.objects.get_or_create(
                product=product,
                sort_order=1,
                defaults={"is_primary": True, "alt_text": item["title"]},
            )
            # Идемпотентно: если у записи нет реального файла — всё равно
            # вызываем attach, он либо найдёт существующий файл, либо
            # сгенерит плейсхолдер.
            if not pi1.image:
                _attach_image(
                    pi1, "image", img_file,
                    label=item["title"],
                    subtitle=item["sku"],
                    palette_key=sku_prefix,
                    stdout=self.stdout,
                )

            # Categories
            for cat in categories_map[item["group"]][:2]:
                product.categories.add(cat)

            # Specs
            ProductSpecification.objects.get_or_create(product=product, name="Формат", defaults={"value": item["format"]})
            ProductSpecification.objects.get_or_create(product=product, name="Назначение", defaults={"value": item["purpose"]})
            if item["sheets"]:
                ProductSpecification.objects.get_or_create(product=product, name="Кол-во листов", defaults={"value": str(item["sheets"])})

            products.append(product)

        return products

    # ─── Marketing ───────────────────────────────
    def _seed_marketing(self, products):
        promos = [
            ("back-to-school", "Снова в школу", "Скидки до 30% на школьные наборы", 30, -3, 20),
            ("office-week", "Неделя офиса", "Скидки 15% на офисные товары", 15, -1, 7),
            ("creative-sale", "Творческая распродажа", "Скидки 20% на товары для творчества", 20, 0, 14),
        ]
        for slug, title, desc, pct, start_off, duration in promos:
            promo, _ = Promotion.objects.get_or_create(
                slug=slug,
                defaults={
                    "title": title,
                    "description": desc,
                    "discount_percent": pct,
                    "start_at": timezone.now() + timedelta(days=start_off),
                    "end_at": timezone.now() + timedelta(days=start_off + duration),
                },
            )
            promo.products.set(random.sample(products, min(8, len(products))))

        # Reviews — 2-3 per product
        for product in products:
            num_reviews = random.randint(2, 4)
            for i in range(num_reviews):
                name = random.choice(REVIEW_NAMES)
                ProductReview.objects.get_or_create(
                    product=product,
                    author_name=f"{name}",
                    defaults={
                        "rating": random.choice([4, 4, 5, 5, 5, 3]),
                        "text": random.choice(REVIEW_TEXTS),
                        "is_published": True,
                    },
                )

    # ─── Logistics ───────────────────────────────
    def _seed_logistics(self):
        points = [
            ("kursk-center", "ПВЗ Центр", "Курск", "ул. Ленина, 11", "Центральный рынок", 51.7373, 36.1877),
            ("kursk-north", "ПВЗ Северный", "Курск", "ул. Карла Маркса, 65", "ТЦ Пушкинский", 51.7480, 36.1870),
            ("kursk-klykova", "ПВЗ Клыкова", "Курск", "пр-т Клыкова, 52", "ТЦ Европа", 51.6950, 36.1540),
            ("kursk-magistral", "ПВЗ Магистральный", "Курск", "ул. Магистральная, 21", "ТЦ Магистральный", 51.7130, 36.1460),
            ("kursk-left", "ПВЗ Левобережный", "Курск", "ул. Сумская, 37А", "Левобережный рынок", 51.7220, 36.2130),
            ("kursk-entuz", "ПВЗ Энтузиастов", "Курск", "ул. Энтузиастов, 4", "ТЦ Барабашово", 51.7560, 36.1680),
            ("kursk-kztz", "ПВЗ КЗТЗ", "Курск", "пр-т Кулакова, 12", "р-н КЗТЗ", 51.6870, 36.1260),
        ]
        for slug, name, city, address, metro, lat, lon in points:
            PickupPoint.objects.get_or_create(
                slug=slug,
                defaults={
                    "name": name, "city": city, "address": address,
                    "metro": metro, "latitude": lat, "longitude": lon,
                    "opening_hours": "Пн-Вс 10:00-21:00",
                },
            )

        tariffs = [
            ("Курьер по Курску", "Курск", DeliveryTariff.DeliveryType.COURIER, 350, 2500, 1, 2),
            ("Экспресс-доставка", "Курск", DeliveryTariff.DeliveryType.EXPRESS, 590, None, 0, 1),
            ("Доставка по России", "", DeliveryTariff.DeliveryType.REGION, 490, 5000, 3, 7),
            ("Самовывоз", "", DeliveryTariff.DeliveryType.PICKUP, 0, None, 0, 1),
        ]
        for title, city, dtype, price, free_from, eta_min, eta_max in tariffs:
            DeliveryTariff.objects.get_or_create(
                title=title,
                delivery_type=dtype,
                defaults={
                    "city": city, "price": price,
                    "free_from_amount": free_from,
                    "eta_min_days": eta_min, "eta_max_days": eta_max,
                },
            )

    # ─── Content ─────────────────────────────────
    def _seed_content(self):
        cats = [
            ("tips", "Советы"),
            ("reviews", "Обзоры"),
            ("news", "Новости"),
        ]
        blog_cats = {}
        for slug, title in cats:
            bc, _ = BlogCategory.objects.get_or_create(slug=slug, defaults={"title": title})
            blog_cats[slug] = bc

        posts = [
            ("Как выбрать тетрадь для школьника", "tips",
             "Разбираемся в форматах, линовках и плотности бумаги.",
             "Выбор тетради — не такая простая задача, как кажется. Формат A5 или A4? Клетка или линейка? "
             "48 или 96 листов? Плотность бумаги 60 или 80 г/м2?\n\n"
             "Для младших классов рекомендуем тетради формата A5 с крупной клеткой и плотной обложкой — "
             "они удобнее помещаются в ранец и выдерживают активное использование.\n\n"
             "Для старшеклассников и студентов подойдут тетради A4 на спирали с 96 листами — "
             "в них удобно вести конспекты лекций. Обратите внимание на плотность бумаги: "
             "если пишете гелевыми ручками, выбирайте от 70 г/м2."),
            ("Чем акварельные карандаши отличаются от обычных", "reviews",
             "Подробное сравнение двух типов карандашей для рисования.",
             "Акварельные карандаши выглядят как обычные цветные, но содержат водорастворимый пигмент. "
             "После нанесения рисунка достаточно провести мокрой кистью — и штрихи превращаются в акварель.\n\n"
             "Обычные цветные карандаши дают более контролируемый результат и лучше подходят для детального рисования. "
             "Акварельные — для художественных эффектов и мягких переходов.\n\n"
             "Наши рекомендации: Faber-Castell для начинающих, Koh-I-Noor для профессионалов."),
            ("Как организовать рабочее место в офисе", "tips",
             "5 простых шагов к порядку на столе и продуктивности.",
             "Шаг 1: Уберите всё лишнее со стола. Оставьте только то, что используете каждый день.\n\n"
             "Шаг 2: Заведите органайзер для ручек, карандашей и мелочей. Вертикальный органайзер экономит место.\n\n"
             "Шаг 3: Используйте лотки для бумаг — входящие документы, в работе, на подпись.\n\n"
             "Шаг 4: Подпишите все папки-регистраторы. Используйте цветовую кодировку для разных проектов.\n\n"
             "Шаг 5: Держите под рукой стикеры и блокнот для быстрых заметок."),
            ("Обзор новинок канцелярии 2025", "news",
             "Самые интересные новинки от ведущих брендов этого года.",
             "В этом году бренды удивили экологичными материалами и эргономичным дизайном.\n\n"
             "Erich Krause представил серию тетрадей из переработанной бумаги — качество не уступает обычным, "
             "а углеродный след на 40% меньше.\n\n"
             "Pilot выпустил новые гелевые ручки с технологией быстрого высыхания — чернила не размазываются "
             "даже при быстром письме. Идеально для левшей.\n\n"
             "Maped удивил серией фломастеров со смываемыми чернилами — отстирываются с любой ткани при 40°C."),
            ("Как собрать набор для первоклассника", "tips",
             "Полный чек-лист для родителей будущих школьников.",
             "Сборы в первый класс — волнительный момент. Чтобы ничего не забыть, "
             "подготовили полный список.\n\n"
             "Письменные принадлежности: 10 тетрадей в клетку, 10 в косую линейку, "
             "набор шариковых ручек (синяя, чёрная, зелёная, красная), простые карандаши HB (3 шт), "
             "ластик, точилка с контейнером.\n\n"
             "Для рисования: альбом 40 листов, цветные карандаши 12 цветов, "
             "фломастеры 12 цветов, акварель 12 цветов, кисти (№3 и №5), стакан-непроливайка.\n\n"
             "Для труда: цветная бумага, цветной картон, клей-карандаш, ножницы с закруглёнными концами, пластилин."),
            ("Топ-5 ручек для ежедневного письма", "reviews",
             "Сравниваем популярные ручки: от бюджетных до премиальных.",
             "1. Pilot BPS-GP — классика за 80₽. Мягкое письмо, долговечный стержень.\n\n"
             "2. Erich Krause R-301 — эргономичный грип, не устаёт рука. ~60₽.\n\n"
             "3. Pentel BK77 — японское качество, тонкая линия 0.5мм. ~120₽.\n\n"
             "4. Uni Jetstream — технология низкого трения, пишет на любой бумаге. ~250₽.\n\n"
             "5. Parker Jotter — премиальная шариковая ручка с металлическим корпусом. ~1200₽. "
             "Идеальна как подарок."),
            ("Что подарить учителю: идеи от Paperly", "tips",
             "Подборка подарков для педагогов на любой бюджет.",
             "День учителя, 8 марта, выпускной — поводов поблагодарить учителя много. "
             "Мы подобрали подарки, которые точно пригодятся.\n\n"
             "До 500₽: подарочная ручка в футляре, ежедневник с мягкой обложкой, набор стикеров.\n\n"
             "500–1500₽: набор для каллиграфии, подарочный сертификат Paperly, настольный органайзер.\n\n"
             "От 1500₽: кожаный ежедневник с гравировкой, подарочный набор Parker, "
             "набор профессиональных маркеров для скетчинга."),
            ("Скетчинг для начинающих: с чего начать", "reviews",
             "Гид по материалам и техникам для первых шагов в скетчинге.",
             "Скетчинг — быстрые зарисовки маркерами или линерами. "
             "Это отличный способ развить навыки рисования.\n\n"
             "Что нужно для старта: скетчбук с плотной бумагой (от 160 г/м2), "
             "набор спиртовых маркеров 12 базовых цветов, линер 0.3мм для контуров.\n\n"
             "Первое упражнение: нарисуйте простые объекты — чашку, яблоко, ручку. "
             "Не старайтесь сделать идеально — скетчинг ценит лёгкость и скорость."),
            ("Как выбрать краски для ребёнка", "tips",
             "Акварель, гуашь или пальчиковые — какие краски подойдут по возрасту.",
             "До 3 лет: пальчиковые краски — безопасные, легко смываются, яркие цвета. "
             "Дети рисуют руками, развивая мелкую моторику.\n\n"
             "3–6 лет: медовая акварель — классические школьные краски. Легко смешиваются, "
             "быстро сохнут. 12 цветов достаточно.\n\n"
             "6–10 лет: гуашь — плотные, насыщенные цвета. Перекрывают друг друга, "
             "что важно при обучении живописи. 12–18 цветов.\n\n"
             "10+ лет: художественная акварель (Невская Палитра, Сонет) — "
             "профессиональные пигменты для серьёзных занятий."),
            ("Тренды канцелярии 2026: пастельные тона и экологичность", "news",
             "Что будет в моде в следующем учебном году.",
             "Главные тренды наступающего сезона:\n\n"
             "1. Пастельные цвета — нежно-розовый, мятный, лавандовый. "
             "Тетради, пеналы и ранцы в приглушённых тонах.\n\n"
             "2. Экологичные материалы — бумага из вторсырья, бамбуковые ручки, "
             "многоразовые обложки.\n\n"
             "3. Модульные системы — сменные блоки для тетрадей, собирайте свой набор.\n\n"
             "4. Мини-формат — компактные блокноты и органайзеры для тех, кто всё носит с собой."),
            ("Paperly открывает 3 новых пункта выдачи в Курске", "news",
             "Теперь забрать заказ можно ещё ближе к дому.",
             "Мы расширяем сеть пунктов выдачи! С этого месяца заказы можно получить "
             "в трёх новых точках:\n\n"
             "ПВЗ Левобережный — ул. Сумская, 37А (рядом с Левобережным рынком)\n\n"
             "ПВЗ КЗТЗ — пр-т Кулакова, 12 (район завода КЗТЗ)\n\n"
             "ПВЗ Энтузиастов — ул. Энтузиастов, 4 (рядом с ТЦ Барабашово)\n\n"
             "Все пункты работают ежедневно с 10:00 до 21:00. Срок хранения заказа — 5 дней."),
            ("Как правильно хранить краски и кисти", "tips",
             "Простые правила, которые продлят жизнь вашим художественным материалам.",
             "Кисти — самый капризный инструмент. После каждого использования промывайте их "
             "тёплой водой с мылом. Никогда не оставляйте кисть в стакане ворсом вниз.\n\n"
             "Храните кисти горизонтально или ворсом вверх. Дайте им полностью высохнуть "
             "перед упаковкой.\n\n"
             "Акварель в кюветах хранится годами, но защищайте от прямых солнечных лучей. "
             "Тюбики гуаши после вскрытия закрывайте плотно — гуашь быстро засыхает.\n\n"
             "Маркеры и фломастеры храните горизонтально, чтобы чернила распределялись равномерно."),
        ]
        # Палитра обложек блога — варьируем, чтобы посты не были однотонные
        blog_palettes = ["NB", "WR", "AR", "OF", "KD", "PP"]
        for idx, (title, cat_key, excerpt, content) in enumerate(posts):
            bp, created = BlogPost.objects.get_or_create(
                slug=f"post-{idx + 1}",
                defaults={
                    "title": title,
                    "category": blog_cats[cat_key],
                    "excerpt": excerpt,
                    "content": content,
                    "status": BlogPost.PostStatus.PUBLISHED,
                    "published_at": timezone.now() - timedelta(days=idx * 5),
                },
            )
            # Идемпотентно: перепривязываем обложку только если её нет
            if not bp.cover:
                img_file = f"blog/post_{idx + 1:02d}.jpg"
                _attach_image(
                    bp, "cover", img_file,
                    label=title,
                    subtitle=blog_cats[cat_key].title.upper(),
                    palette_key=blog_palettes[idx % len(blog_palettes)],
                    stdout=self.stdout,
                )

        pages = [
            (SitePage.PageType.INDEX, "Главная", ""),
            (SitePage.PageType.ABOUT, "О магазине", ""),
            (SitePage.PageType.DELIVERY, "Доставка и оплата", ""),
            (SitePage.PageType.GUARANTEE, "Гарантия и возврат", ""),
            (SitePage.PageType.WHOLESALE, "Оптовым клиентам", ""),
            (SitePage.PageType.PICKUP, "Пункты самовывоза", ""),
            (SitePage.PageType.PRIVACY, "Политика конфиденциальности",
             "<h2>Политика конфиденциальности</h2>"
             "<p>Мы обрабатываем персональные данные в соответствии с ФЗ-152 «О персональных данных». "
             "Данные используются исключительно для обработки заказов и информирования о статусе доставки.</p>"),
            (SitePage.PageType.TERMS, "Пользовательское соглашение",
             "<h2>Пользовательское соглашение</h2>"
             "<p>Используя сайт, вы соглашаетесь с условиями настоящего соглашения. "
             "Администрация оставляет за собой право изменять условия без предварительного уведомления.</p>"),
            (SitePage.PageType.OFFER, "Договор оферты",
             "<h2>Публичная оферта</h2>"
             "<p>Настоящий документ является официальным предложением (офертой) интернет-магазина Paperly. "
             "Оформление заказа является акцептом данной оферты.</p>"),
        ]
        for page_type, title, content in pages:
            SitePage.objects.get_or_create(
                slug=slugify(page_type),
                defaults={"title": title, "page_type": page_type, "content": content},
            )

    # ─── Wholesale ───────────────────────────────
    def _seed_wholesale(self):
        # ВАЖНО: slug'и задаём явно латиницей. Django'вский slugify() без
        # allow_unicode=True на кириллице возвращает пустую строку → все
        # три записи получают slug="" → IntegrityError на UNIQUE → вся
        # транзакция seed отката → картинки товаров и обложки блога НЕ
        # сохраняются. Этот баг уже ломал Render-деплой.
        pricelists = [
            ("wholesale-business", WholesalePriceList.Segment.BUSINESS, "Прайс для юрлиц"),
            ("wholesale-school", WholesalePriceList.Segment.SCHOOL, "Прайс для школ"),
            ("wholesale-university", WholesalePriceList.Segment.UNIVERSITY, "Прайс для университетов"),
        ]
        for slug, segment, title in pricelists:
            WholesalePriceList.objects.get_or_create(
                slug=slug,
                defaults={"title": title, "segment": segment, "file_url": "#"},
            )

        orgs = [
            ("ООО Офис Снаб", WholesaleRequest.OrganizationType.LLC, "Иван Петров", "+7 (999) 000-11-22", "office@example.com", "Поставка для 3 офисов"),
            ("Школа №25 г. Курск", WholesaleRequest.OrganizationType.SCHOOL, "Елена Сидорова", "+7 (999) 333-44-55", "school25@example.com", "Нужны тетради и ручки на 300 учеников"),
            ("КГУ", WholesaleRequest.OrganizationType.UNIVERSITY, "Андрей Козлов", "+7 (999) 666-77-88", "kgu@example.com", "Бумага A4 и канцтовары для кафедр"),
        ]
        for name, otype, contact, phone, email, comment in orgs:
            WholesaleRequest.objects.get_or_create(
                organization_name=name,
                defaults={
                    "organization_type": otype, "contact_person": contact,
                    "phone": phone, "email": email, "comment": comment,
                },
            )

    # ─── Filters ─────────────────────────────────
    def _seed_filters(self, brands):
        categories = Category.objects.filter(parent__isnull=True, is_active=True)
        cat_options = [(c.name, c.slug) for c in categories]

        sheets_values = (
            Product.objects.exclude(sheets_count__isnull=True)
            .values_list("sheets_count", flat=True)
            .distinct()
            .order_by("sheets_count")
        )
        sheets_options = [(f"{v} л.", str(v)) for v in sheets_values]

        groups = [
            ("Категория", "category", cat_options, 1),
            ("Бренд", "brand", [(b.name, b.slug) for b in brands.values()], 2),
            ("Формат", "product_format", [("A3", "A3"), ("A4", "A4"), ("A5", "A5"), ("Другой", "other")], 3),
            ("Назначение", "purpose", [("Школа", "school"), ("Офис", "office"), ("Творчество", "creative"), ("Универсальное", "universal")], 4),
            ("Кол-во листов", "sheets_count", sheets_options, 5),
            ("Наличие", "in_stock", [("В наличии", "true")], 6),
            ("Скидка", "has_discount", [("Со скидкой", "true")], 7),
            ("Акции", "has_promotion", [("Участвует в акции", "true")], 8),
            ("Новинки", "is_new", [("Новинка", "true")], 9),
            ("Хиты продаж", "is_hit", [("Хит", "true")], 10),
            ("Рекомендуемые", "is_featured", [("Рекомендуемый", "true")], 11),
        ]
        for title, param, options, sort in groups:
            fg, _ = CatalogFilterGroup.objects.get_or_create(
                slug=slugify(title),
                defaults={"title": title, "sort_order": sort},
            )
            for opt_idx, (label, value) in enumerate(options, 1):
                CatalogFilterOption.objects.get_or_create(
                    group=fg,
                    label=label,
                    defaults={"query_param": param, "value": value, "sort_order": opt_idx},
                )

    # ─── Customer data ───────────────────────────
    def _seed_customer_data(self, products):
        User = get_user_model()
        from datetime import date

        # ── User 1: demo ──
        user, _ = User.objects.get_or_create(
            username="demo",
            defaults={"email": "demo@paperly.ru", "first_name": "Антон", "last_name": "Князев"},
        )
        user.set_password("demo12345")
        user.save(update_fields=["password"])

        profile, _ = CustomerProfile.objects.get_or_create(
            user=user,
            defaults={
                "first_name": "Антон", "last_name": "Князев",
                "phone": "+7 (999) 100-00-00", "birth_date": date(1995, 3, 15),
            },
        )
        Address.objects.get_or_create(
            profile=profile,
            city="Курск",
            street="ул. Ленина, 11",
            defaults={
                "address_type": Address.AddressType.SHIPPING, "is_default": True,
                "entrance": "2", "flat_or_office": "кв. 45", "postal_code": "305000",
            },
        )
        NotificationSetting.objects.get_or_create(
            profile=profile,
            defaults={"order_status": True, "promotions": True, "restock": False},
        )

        # ── User 2: maria ──
        user2, _ = User.objects.get_or_create(
            username="maria",
            defaults={"email": "maria@paperly.ru", "first_name": "Мария", "last_name": "Сидорова"},
        )
        user2.set_password("maria12345")
        user2.save(update_fields=["password"])

        profile2, _ = CustomerProfile.objects.get_or_create(
            user=user2,
            defaults={
                "first_name": "Мария", "last_name": "Сидорова",
                "phone": "+7 (910) 222-33-44", "birth_date": date(1990, 8, 22),
            },
        )
        Address.objects.get_or_create(
            profile=profile2,
            city="Курск",
            street="пр-т Клыкова, 52",
            defaults={
                "address_type": Address.AddressType.SHIPPING, "is_default": True,
                "entrance": "1", "flat_or_office": "кв. 12", "postal_code": "305018",
            },
        )
        NotificationSetting.objects.get_or_create(
            profile=profile2,
            defaults={"order_status": True, "promotions": False, "restock": True},
        )

        # ── Favorites ──
        for product in products[:7]:
            Favorite.objects.get_or_create(user=user, product=product)
        for product in products[5:10]:
            Favorite.objects.get_or_create(user=user2, product=product)

        # ── Carts ──
        cart, _ = Cart.objects.get_or_create(user=user)
        for product in products[:4]:
            CartItem.objects.get_or_create(
                cart=cart, product=product,
                defaults={"quantity": random.randint(1, 3), "price_snapshot": product.price},
            )

        cart2, _ = Cart.objects.get_or_create(user=user2)
        for product in products[3:6]:
            CartItem.objects.get_or_create(
                cart=cart2, product=product,
                defaults={"quantity": 1, "price_snapshot": product.price},
            )

        # ── Orders ──
        pickup = PickupPoint.objects.first()

        # Status transition chains for realistic history
        STATUS_CHAINS = {
            Order.OrderStatus.DONE: [
                Order.OrderStatus.NEW, Order.OrderStatus.CONFIRMED,
                Order.OrderStatus.PAID, Order.OrderStatus.SHIPPED, Order.OrderStatus.DONE,
            ],
            Order.OrderStatus.SHIPPED: [
                Order.OrderStatus.NEW, Order.OrderStatus.CONFIRMED,
                Order.OrderStatus.PAID, Order.OrderStatus.SHIPPED,
            ],
            Order.OrderStatus.PAID: [
                Order.OrderStatus.NEW, Order.OrderStatus.CONFIRMED, Order.OrderStatus.PAID,
            ],
            Order.OrderStatus.CONFIRMED: [
                Order.OrderStatus.NEW, Order.OrderStatus.CONFIRMED,
            ],
            Order.OrderStatus.NEW: [Order.OrderStatus.NEW],
            Order.OrderStatus.CANCELED: [
                Order.OrderStatus.NEW, Order.OrderStatus.CANCELED,
            ],
        }

        orders_data = [
            ("ORD-001001", Order.OrderStatus.DONE, Order.DeliveryType.PICKUP, Order.PaymentType.CARD, user, products[:3]),
            ("ORD-001002", Order.OrderStatus.SHIPPED, Order.DeliveryType.COURIER, Order.PaymentType.SBP, user, products[3:6]),
            ("ORD-001003", Order.OrderStatus.PAID, Order.DeliveryType.COURIER, Order.PaymentType.CASH, user, products[6:8]),
            ("ORD-001004", Order.OrderStatus.NEW, Order.DeliveryType.PICKUP, Order.PaymentType.CARD, user2, products[8:10]),
            ("ORD-001005", Order.OrderStatus.CANCELED, Order.DeliveryType.COURIER, Order.PaymentType.CARD, user, products[10:12]),
            ("ORD-001006", Order.OrderStatus.DONE, Order.DeliveryType.PICKUP, Order.PaymentType.SBP, user2, products[2:5]),
            ("ORD-001007", Order.OrderStatus.CONFIRMED, Order.DeliveryType.COURIER, Order.PaymentType.CARD, user2, products[12:14]),
        ]
        for number, status, delivery, pay_type, order_user, order_products in orders_data:
            if not order_products:
                continue
            delivery_price = 350 if delivery == Order.DeliveryType.COURIER else 0
            subtotal = sum(p.price for p in order_products)
            order, created = Order.objects.get_or_create(
                number=number,
                defaults={
                    "user": order_user,
                    "full_name": order_user.get_full_name(),
                    "phone": "+7 (999) 100-00-00",
                    "email": order_user.email,
                    "city": "Курск",
                    "address": "ул. Ленина, 11",
                    "delivery_type": delivery,
                    "payment_type": pay_type,
                    "pickup_point": pickup if delivery == Order.DeliveryType.PICKUP else None,
                    "status": status,
                    "subtotal": subtotal,
                    "delivery_price": delivery_price,
                    "discount_amount": 0,
                    "total": subtotal + delivery_price,
                },
            )
            if created:
                for p in order_products:
                    OrderItem.objects.create(
                        order=order, product=p,
                        title_snapshot=p.title, sku_snapshot=p.sku,
                        quantity=1, unit_price=p.price,
                    )
                # Full status chain history
                chain = STATUS_CHAINS.get(status, [status])
                for step_idx, step_status in enumerate(chain):
                    OrderStatusHistory.objects.create(
                        order=order, status=step_status,
                        comment=f"Статус: {Order.OrderStatus(step_status).label}",
                    )

    # ─── Gift certificates ────────────────────────
    def _seed_gift_certificates(self):
        certs = [
            ("Сертификат 500 ₽", 500, "Подарочный сертификат на 500 рублей. Действует 6 месяцев."),
            ("Сертификат 1 000 ₽", 1000, "Подарочный сертификат на 1 000 рублей. Действует 6 месяцев."),
            ("Сертификат 2 000 ₽", 2000, "Подарочный сертификат на 2 000 рублей. Действует 1 год."),
            ("Сертификат 5 000 ₽", 5000, "Подарочный сертификат на 5 000 рублей. Действует 1 год. Идеален для корпоративных подарков."),
        ]
        for title, nominal, desc in certs:
            GiftCertificate.objects.get_or_create(
                slug=slugify(f"cert-{nominal}"),
                defaults={"title": title, "nominal": nominal, "description": desc},
            )

    # ─── Returns ─────────────────────────────────
    def _seed_returns(self):
        done_order = Order.objects.filter(status=Order.OrderStatus.DONE).first()
        if not done_order:
            return
        user = done_order.user
        order_items = list(done_order.items.all())
        if not order_items:
            return

        # Return 1: approved
        ret1, created1 = ReturnRequest.objects.get_or_create(
            order=done_order,
            return_type=ReturnRequest.ReturnType.GOOD_QUALITY,
            defaults={
                "user": user,
                "reason": "Товар не подошёл по формату, хочу обменять на A5.",
                "status": ReturnRequest.ReturnStatus.APPROVED,
            },
        )
        if created1 and order_items:
            ReturnRequestItem.objects.create(
                return_request=ret1, order_item=order_items[0], quantity=1,
                comment="Тетрадь A4 — нужна A5",
            )

        shipped_order = Order.objects.filter(status=Order.OrderStatus.SHIPPED).first()
        if shipped_order:
            shipped_items = list(shipped_order.items.all())
            ret2, created2 = ReturnRequest.objects.get_or_create(
                order=shipped_order,
                return_type=ReturnRequest.ReturnType.DEFECT,
                defaults={
                    "user": shipped_order.user,
                    "reason": "Получен товар с повреждённой упаковкой.",
                    "status": ReturnRequest.ReturnStatus.CHECKING,
                },
            )
            if created2 and shipped_items:
                ReturnRequestItem.objects.create(
                    return_request=ret2, order_item=shipped_items[0], quantity=1,
                    comment="Помятая коробка, царапины на корпусе",
                )

    # ─── Site settings ───────────────────────────
    def _seed_site_settings(self):
        setting = SiteSetting.load()
        setting.site_name = "Paperly"
        setting.tagline = "Канцтовары для школы, офиса и творчества"
        setting.phone = "+7 (4712) 39-10-10"
        setting.email = "info@paperly.ru"
        setting.city = "Курск"
        setting.address = "ул. Ленина, 11, офис 205"
        setting.copyright_text = "Paperly — интернет-магазин канцтоваров, 2020–2026"
        setting.save()
