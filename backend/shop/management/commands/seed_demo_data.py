import hashlib
import json
import random
import shutil
from datetime import date, timedelta
from io import BytesIO
from pathlib import Path
from urllib.parse import quote_plus

from django.conf import settings
from django.contrib.admin.models import ADDITION, CHANGE, LogEntry
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.contrib.contenttypes.models import ContentType
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


# ─────────────────────────────────────────────────────────────────────────────
# Пользователи: 20 покупателей + 3 менеджера + 2 админа.
# Пароли одинаковы внутри роли (customer12345 / manager12345 / admin12345),
# чтобы демо-доступ из README был лаконичным.
# ─────────────────────────────────────────────────────────────────────────────

# (username, first_name, last_name, phone, birth_date, city, street, postal_code)
CUSTOMER_SEEDS = [
    ("customer",   "Антон",    "Князев",   "+7 (999) 100-00-00", date(1995, 3, 15),  "Курск",             "ул. Ленина, 11",         "305000"),
    ("customer2",  "Мария",    "Сидорова", "+7 (910) 222-33-44", date(1990, 8, 22),  "Курск",             "пр-т Клыкова, 52",       "305018"),
    ("customer3",  "Дмитрий",  "Соколов",  "+7 (915) 111-22-33", date(1988, 5, 3),   "Курск",             "ул. Карла Маркса, 65",   "305001"),
    ("customer4",  "Елена",    "Иванова",  "+7 (926) 333-44-55", date(1992, 11, 17), "Москва",            "ул. Арбат, 20",          "119019"),
    ("customer5",  "Павел",    "Козлов",   "+7 (903) 777-88-99", date(1985, 2, 8),   "Курск",             "ул. Сумская, 37А",       "305002"),
    ("customer6",  "Ольга",    "Смирнова", "+7 (905) 444-55-66", date(1996, 7, 29),  "Курск",             "пр-т Кулакова, 12",      "305016"),
    ("customer7",  "Алексей",  "Попов",    "+7 (916) 555-66-77", date(1991, 10, 12), "Санкт-Петербург",   "Невский пр., 28",        "191186"),
    ("customer8",  "Наталья",  "Фёдорова", "+7 (925) 666-77-88", date(1987, 4, 19),  "Курск",             "ул. Энтузиастов, 4",     "305044"),
    ("customer9",  "Михаил",   "Волков",   "+7 (902) 888-99-00", date(1993, 9, 6),   "Воронеж",           "пр-т Революции, 15",     "394018"),
    ("customer10", "Татьяна",  "Морозова", "+7 (936) 111-00-99", date(1989, 12, 25), "Курск",             "ул. Магистральная, 21",  "305029"),
    ("customer11", "Кирилл",   "Беляев",   "+7 (920) 314-15-92", date(1997, 1, 10),  "Курск",             "ул. Радищева, 22",       "305004"),
    ("customer12", "Софья",    "Орлова",   "+7 (904) 271-82-81", date(2001, 6, 2),   "Курск",             "ул. Дзержинского, 41",   "305035"),
    ("customer13", "Виктор",   "Громов",   "+7 (915) 742-20-10", date(1984, 3, 27),  "Белгород",          "ул. Победы, 84",         "308015"),
    ("customer14", "Алина",    "Егорова",  "+7 (906) 580-44-12", date(1994, 9, 14),  "Курск",             "ул. Союзная, 9",         "305023"),
    ("customer15", "Роман",    "Титов",    "+7 (910) 611-72-30", date(1986, 12, 5),  "Орел",              "ул. Комсомольская, 88",  "302001"),
    ("customer16", "Вера",     "Лебедева", "+7 (926) 490-17-55", date(1999, 4, 18),  "Курск",             "пр-т Дружбы, 31",        "305040"),
    ("customer17", "Георгий",  "Семенов",  "+7 (903) 218-64-70", date(1982, 7, 23),  "Москва",            "ул. Тверская, 17",       "125009"),
    ("customer18", "Полина",   "Зайцева",  "+7 (925) 883-49-20", date(1998, 10, 8),  "Курск",             "ул. Бойцов 9-й дивизии, 6", "305018"),
    ("customer19", "Илья",     "Фомин",    "+7 (999) 430-91-12", date(1991, 2, 11),  "Липецк",            "ул. Советская, 55",      "398001"),
    ("customer20", "Дарья",    "Крылова",  "+7 (936) 902-13-44", date(1996, 5, 29),  "Курск",             "ул. Хрущева, 18",        "305048"),
]

# (username, first_name, last_name)
MANAGER_SEEDS = [
    ("manager",  "Екатерина", "Романова"),
    ("manager2", "Игорь",     "Белов"),
    ("manager3", "Ксения",    "Новикова"),
]

ADMIN_SEEDS = [
    ("admin",  "Admin",  "Paperly"),
    ("admin2", "Сергей", "Николаев"),
]

BRAND_ASSETS = {
    "erich-krause": ("https://erichkrause.com/", "erichkrause.com"),
    "kores": ("https://www.kores.com/", "kores.com"),
    "brauberg": ("https://www.brauberg.com/", "brauberg.com"),
    "maped": ("https://www.maped.com/", "maped.com"),
    "pilot": ("https://www.pilotpen.eu/", "pilotpen.eu"),
    "faber-castell": ("https://www.faber-castell.com/", "faber-castell.com"),
    "hatber": ("https://hatber.ru/", "hatber.ru"),
    "bg": ("https://bg-corp.ru/", "bg-corp.ru"),
    "berlingo": ("https://berlingo.ru/", "berlingo.ru"),
    "pentel": ("https://www.pentel.com/", "pentel.com"),
}

PRODUCT_IMAGE_QUERIES = {
    "NB": "notebook stationery",
    "PP": "office paper stationery",
    "WR": "pens pencils stationery",
    "AR": "art supplies watercolor brushes",
    "OF": "office supplies desk stationery",
    "KD": "school supplies kids backpack",
}

EXTRA_PRODUCT_SEEDS = [
    ("NB-007", "Тетрадь A5 48 листов линейка Pastel", 135, "paper", "bg", "A5", 48, "school", "Тетрадь в линейку с мягкой пастельной обложкой для ежедневных школьных записей."),
    ("NB-008", "Тетрадь предметная по математике 48 листов", 145, "paper", "hatber", "A5", 48, "school", "Предметная тетрадь с тематической обложкой и справочным блоком по математике."),
    ("NB-009", "Тетрадь предметная по английскому 48 листов", 145, "paper", "hatber", "A5", 48, "school", "Тетрадь для занятий английским языком с плотной белой бумагой."),
    ("NB-010", "Блокнот A6 на резинке 96 листов", 210, "paper", "berlingo", "other", 96, "office", "Компактный блокнот для быстрых заметок, списков задач и планирования дня."),
    ("NB-011", "Ежедневник недатированный A5 Soft Touch", 690, "paper", "brauberg", "A5", 160, "office", "Недатированный ежедневник с мягкой обложкой, ляссе и удобной разметкой."),
    ("NB-012", "Планер настольный недельный 60 листов", 360, "paper", "brauberg", "other", 60, "office", "Настольный планер для недельного расписания, задач и рабочих заметок."),
    ("PP-006", "Бумага офисная A4 пастельная 100 листов", 330, "paper", "kores", "A4", 100, "creative", "Набор пастельной бумаги для объявлений, презентаций и творческих работ."),
    ("PP-007", "Бумага для акварели A4 20 листов", 420, "paper", "faber-castell", "A4", 20, "creative", "Плотная фактурная бумага для акварели, гуаши и смешанных техник."),
    ("PP-008", "Бумага для черчения A3 20 листов", 510, "paper", "hatber", "A3", 20, "school", "Белая бумага повышенной плотности для чертежей, схем и технических работ."),
    ("PP-009", "Калька рулонная 297 мм × 20 м", 640, "paper", "brauberg", "other", None, "creative", "Прозрачная калька в рулоне для копирования, макетов и черчения."),
    ("PP-010", "Блок самоклеящийся 51×76 мм 12 цветов", 250, "paper", "berlingo", "other", 1200, "office", "Набор узких закладок и стикеров для учебников, документов и каталогов."),
    ("PP-011", "Папка для черчения A4 24 листа", 290, "paper", "hatber", "A4", 24, "school", "Папка с листами для черчения и графических работ."),
    ("PP-012", "Конверты C5 белые 50 штук", 310, "paper", "brauberg", "other", 50, "office", "Белые почтовые конверты для документов, писем и деловой корреспонденции."),
    ("WR-013", "Ручка гелевая черная 0.5 мм", 70, "writing", "pilot", "other", None, "office", "Гелевая ручка с насыщенными черными чернилами и плавным письмом."),
    ("WR-014", "Ручка гелевая синяя стираемая", 155, "writing", "pilot", "other", None, "school", "Стираемая гелевая ручка для аккуратных конспектов без помарок."),
    ("WR-015", "Ручка шариковая масляная красная", 45, "writing", "erich-krause", "other", None, "office", "Красная ручка для проверки работ, пометок и выделения важных правок."),
    ("WR-016", "Набор линеров 0.1–0.8 мм 6 штук", 620, "writing", "pentel", "other", None, "creative", "Линеры разной толщины для скетчинга, черчения и иллюстраций."),
    ("WR-017", "Карандаш механический 0.5 мм", 230, "writing", "pentel", "other", None, "school", "Механический карандаш с металлическим клипом и мягким грипом."),
    ("WR-018", "Грифели HB 0.5 мм 12 штук", 95, "writing", "pentel", "other", None, "school", "Запасные грифели для механических карандашей."),
    ("WR-019", "Ластик белый мягкий", 55, "writing", "faber-castell", "other", None, "school", "Мягкий ластик для графитных карандашей, не повреждает бумагу."),
    ("WR-020", "Точилка с контейнером двойная", 140, "writing", "maped", "other", None, "school", "Двойная точилка для стандартных и толстых карандашей."),
    ("WR-021", "Набор маркеров для доски 4 цвета", 390, "writing", "kores", "other", None, "office", "Маркеры для белых досок с яркими стираемыми чернилами."),
    ("WR-022", "Текстовыделитель желтый классический", 80, "writing", "erich-krause", "other", None, "office", "Классический желтый текстовыделитель со скошенным наконечником."),
    ("WR-023", "Набор акварельных карандашей 24 цвета", 790, "writing", "faber-castell", "other", None, "creative", "Акварельные карандаши с мягким водорастворимым грифелем."),
    ("WR-024", "Маркеры спиртовые для скетчинга 12 цветов", 1290, "writing", "berlingo", "other", None, "creative", "Двусторонние спиртовые маркеры для скетчей, иллюстраций и дизайна."),
    ("AR-011", "Палитра пластиковая овальная", 120, "art", "maped", "other", None, "creative", "Легкая палитра с ячейками для смешивания красок."),
    ("AR-012", "Стакан-непроливайка для кистей", 110, "art", "erich-krause", "other", None, "school", "Безопасный стакан для воды с крышкой-непроливайкой."),
    ("AR-013", "Мольберт настольный деревянный", 1490, "art", "faber-castell", "other", None, "creative", "Компактный настольный мольберт для рисования и демонстрации работ."),
    ("AR-014", "Холст на подрамнике 30×40 см", 430, "art", "brauberg", "other", None, "creative", "Грунтованный холст для акрила, масла и смешанных техник."),
    ("AR-015", "Акриловые краски 12 цветов", 760, "art", "faber-castell", "other", None, "creative", "Набор акриловых красок с плотным укрывистым цветом."),
    ("AR-016", "Пальчиковые краски 6 цветов", 390, "art", "erich-krause", "other", None, "creative", "Безопасные пальчиковые краски для малышей и первых творческих опытов."),
    ("AR-017", "Набор кистей щетина 5 штук", 340, "art", "maped", "other", None, "creative", "Плоские кисти из щетины для гуаши, акрила и декоративных работ."),
    ("AR-018", "Папка для акварели A3 10 листов", 580, "art", "hatber", "A3", 10, "creative", "Акварельная бумага большого формата для учебных и художественных работ."),
    ("AR-019", "Набор угля художественного 10 штук", 260, "art", "faber-castell", "other", None, "creative", "Художественный уголь для набросков, штриховки и тональных работ."),
    ("AR-020", "Линейка металлическая 30 см", 160, "art", "brauberg", "other", None, "school", "Прочная металлическая линейка для черчения и резки макетов."),
    ("AR-021", "Набор геометрический 4 предмета", 240, "art", "maped", "other", None, "school", "Линейка, транспортир и угольники для школы и черчения."),
    ("OF-009", "Скрепки 28 мм оцинкованные 100 штук", 75, "office", "brauberg", "other", None, "office", "Оцинкованные скрепки для аккуратного крепления документов."),
    ("OF-010", "Зажимы для бумаг 25 мм 12 штук", 160, "office", "berlingo", "other", None, "office", "Черные металлические зажимы для документов и папок."),
    ("OF-011", "Лоток горизонтальный для бумаг", 390, "office", "brauberg", "A4", None, "office", "Настольный лоток формата A4 для входящих и рабочих документов."),
    ("OF-012", "Папка-уголок A4 прозрачная 10 штук", 210, "office", "berlingo", "A4", None, "office", "Набор прозрачных папок-уголков для документов и презентаций."),
    ("OF-013", "Файл-вкладыш A4 100 мкм 100 штук", 520, "office", "brauberg", "A4", None, "office", "Плотные файлы-вкладыши для архивов, договоров и учебных материалов."),
    ("OF-014", "Маркер перманентный черный толстый", 120, "office", "erich-krause", "other", None, "office", "Толстый перманентный маркер для коробок, папок и упаковки."),
    ("OF-015", "Клейкая лента упаковочная 48 мм × 66 м", 190, "office", "kores", "other", None, "office", "Прочная упаковочная лента для посылок и коробок."),
    ("OF-016", "Диспенсер для скотча настольный", 480, "office", "berlingo", "other", None, "office", "Тяжелый настольный диспенсер для удобной работы со скотчем."),
    ("OF-017", "Бейдж горизонтальный с клипом 10 штук", 260, "office", "brauberg", "other", None, "office", "Прозрачные бейджи для мероприятий, офиса и конференций."),
    ("OF-018", "Штемпельная подушка синяя", 170, "office", "kores", "other", None, "office", "Синяя штемпельная подушка для печатей и штампов."),
    ("KD-007", "Набор обложек для тетрадей 10 штук", 150, "kids", "bg", "A5", None, "school", "Прозрачные обложки для защиты школьных тетрадей."),
    ("KD-008", "Набор обложек для учебников универсальный", 260, "kids", "hatber", "other", None, "school", "Регулируемые обложки для учебников разных форматов."),
    ("KD-009", "Пенал-тубус пластиковый", 240, "kids", "maped", "other", None, "school", "Легкий пенал-тубус для ручек, карандашей и фломастеров."),
    ("KD-010", "Набор закладок магнитных 8 штук", 180, "kids", "berlingo", "other", None, "school", "Яркие магнитные закладки для учебников и ежедневников."),
    ("KD-011", "Папка для труда A4 на молнии", 360, "kids", "bg", "A4", None, "school", "Папка на молнии для цветной бумаги, картона и творческих принадлежностей."),
    ("KD-012", "Набор наклеек школьных 12 листов", 220, "kids", "hatber", "other", 12, "creative", "Набор декоративных наклеек для дневников, тетрадей и поделок."),
    ("KD-013", "Сумка для сменной обуви", 390, "kids", "erich-krause", "other", None, "school", "Легкая школьная сумка для сменной обуви с прочными шнурами."),
]


def _remote_product_image_url(item, index):
    sku_prefix = item["sku"].split("-")[0]
    query = f"{item['title']} {PRODUCT_IMAGE_QUERIES.get(sku_prefix, 'stationery')}"
    return f"https://source.unsplash.com/900x900/?{quote_plus(query)}&sig=paperly-{index:03d}"


def _brand_logo_url(domain):
    return f"https://www.google.com/s2/favicons?domain={domain}&sz=256"


def _set_timestamps(obj, created_at, updated_at=None):
    fields = {"created_at": created_at, "updated_at": updated_at or created_at}
    obj.__class__.objects.filter(pk=obj.pk).update(**fields)


def _safe_console_text(value):
    return str(value).encode("cp1251", errors="replace").decode("cp1251")


def _safe_stdout_write(stdout, message):
    if stdout:
        stdout.write(_safe_console_text(message))


def _hex_to_rgb(hex_color):
    hex_color = hex_color.lstrip("#")
    return tuple(int(hex_color[i : i + 2], 16) for i in (0, 2, 4))


def _generate_placeholder_jpg(dest_path: Path, label: str, subtitle: str = "", palette_key: str = "_default"):
    """Draw a product-aware JPG fallback.

    Это не абстрактная заглушка: картинка подбирает композицию по названию
    товара, поэтому даже без внешних CDN каталог выглядит предметно и
    стабильно на локальной машине/Render.
    """
    from PIL import Image, ImageDraw, ImageFont

    start_hex, end_hex = PLACEHOLDER_COLORS.get(palette_key, PLACEHOLDER_COLORS["_default"])
    start = _hex_to_rgb(start_hex)
    end = _hex_to_rgb(end_hex)

    size = 900
    img = Image.new("RGB", (size, size), "#f7fbfa")
    draw = ImageDraw.Draw(img)

    # Мягкий студийный фон вместо однотонного прямоугольника.
    for y in range(size):
        ratio = y / size
        r = int(248 * (1 - ratio) + min(end[0] + 42, 255) * ratio)
        g = int(252 * (1 - ratio) + min(end[1] + 42, 255) * ratio)
        b = int(250 * (1 - ratio) + min(end[2] + 42, 255) * ratio)
        draw.line([(0, y), (size, y)], fill=(r, g, b))

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

    font_title = _load_font(_font_candidates_bold, 38)
    font_sub = _load_font(_font_candidates_regular, 22)
    font_sku = _load_font(_font_candidates_bold, 18)
    cyrillic_ok = font_title is not None
    if font_title is None:
        font_title = ImageFont.load_default()
    if font_sub is None:
        font_sub = ImageFont.load_default()
    if font_sku is None:
        font_sku = ImageFont.load_default()

    accent = start
    accent_2 = end
    dark = "#183f43"
    label_l = label.lower()

    def shadow(box, radius=26):
        x1, y1, x2, y2 = box
        draw.rounded_rectangle([x1 + 14, y1 + 18, x2 + 14, y2 + 18], radius=radius, fill="#cad9db")

    def rr(box, fill, outline=None, width=1, radius=26):
        draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)

    def line(points, fill=dark, width=8):
        draw.line(points, fill=fill, width=width, joint="curve")

    def draw_paper_stack():
        for offset, color in [(34, "#dce7ea"), (18, "#edf4f5"), (0, "#ffffff")]:
            rr([220 + offset, 210 - offset, 680 + offset, 690 - offset], "#fff" if not offset else color, "#d8e3e6", 3, 24)
        for y in range(300, 620, 58):
            line([(280, y), (620, y)], "#d6e3e6", 4)
        draw.rectangle([266, 210, 300, 690], fill=accent)

    def draw_notebook():
        shadow([240, 180, 660, 705])
        rr([240, 180, 660, 705], "#ffffff", "#d7e3e6", 3, 30)
        rr([278, 218, 622, 668], "#fefefe", "#e1ebed", 2, 22)
        draw.rectangle([240, 180, 325, 705], fill=accent)
        for y in range(255, 642, 48):
            line([(365, y), (590, y)], "#d8e6e8", 3)
        for y in range(225, 665, 70):
            draw.ellipse([275, y, 295, y + 20], fill="#ffffff")

    def draw_pens(count=5, marker=False):
        colors = ["#0e766e", "#f59e0b", "#e85d75", "#2563eb", "#7c3aed", "#111827"]
        x0 = 245
        for i in range(count):
            x = x0 + i * 72
            color = colors[i % len(colors)]
            rr([x, 215, x + 44, 675], color, None, 1, 22)
            rr([x + 7, 220, x + 37, 310], "#ffffff", None, 1, 14)
            if marker:
                draw.polygon([(x, 675), (x + 44, 675), (x + 31, 735), (x + 13, 735)], fill=dark)
            else:
                draw.polygon([(x, 675), (x + 44, 675), (x + 22, 740)], fill=dark)

    def draw_pencils():
        colors = ["#fbbf24", "#ef4444", "#22c55e", "#3b82f6", "#a855f7", "#fb7185"]
        for i, color in enumerate(colors):
            x = 210 + i * 76
            draw.polygon([(x, 660), (x + 28, 185), (x + 74, 185), (x + 102, 660)], fill=color)
            draw.polygon([(x, 660), (x + 102, 660), (x + 51, 750)], fill="#d8a15d")
            draw.polygon([(x + 39, 728), (x + 63, 728), (x + 51, 750)], fill=dark)
            rr([x + 30, 190, x + 72, 245], "#f8fafc", None, 1, 12)

    def draw_paint():
        rr([190, 250, 710, 610], "#ffffff", "#d8e5e8", 3, 80)
        draw.ellipse([350, 355, 550, 555], fill="#f7fbfa", outline="#d8e5e8", width=3)
        for i, color in enumerate(["#ef4444", "#f59e0b", "#22c55e", "#2563eb", "#7c3aed", "#ec4899"]):
            x = 250 + (i % 3) * 170
            y = 315 + (i // 3) * 170
            draw.ellipse([x, y, x + 86, y + 86], fill=color)
        line([(645, 170), (405, 710)], "#8b5e34", 18)
        line([(665, 150), (685, 190)], "#d4d4d8", 26)

    def draw_brushes():
        for i, color in enumerate(["#0e766e", "#f59e0b", "#e85d75", "#2563eb"]):
            x = 270 + i * 90
            line([(x, 680), (x + 70, 250)], "#8b5e34", 20)
            rr([x + 50, 215, x + 105, 300], "#d9e1e4", None, 1, 18)
            draw.polygon([(x + 56, 215), (x + 100, 215), (x + 78, 130)], fill=color)
        rr([210, 650, 690, 735], "#ffffff", "#d8e5e8", 3, 24)

    def draw_easel():
        line([(330, 720), (450, 175), (570, 720)], "#8b5e34", 18)
        line([(450, 250), (450, 740)], "#8b5e34", 14)
        rr([285, 230, 615, 540], "#ffffff", "#d8e5e8", 4, 18)
        draw.line([(335, 465), (410, 390), (480, 440), (560, 320)], fill=accent, width=9)
        draw.ellipse([520, 280, 555, 315], fill="#f59e0b")
        line([(250, 565), (650, 565)], "#8b5e34", 16)

    def draw_office():
        if any(word in label_l for word in ("ножниц",)):
            line([(320, 640), (570, 280)], "#94a3b8", 18)
            line([(580, 640), (330, 280)], "#94a3b8", 18)
            draw.ellipse([260, 590, 370, 700], outline=accent, width=18)
            draw.ellipse([530, 590, 640, 700], outline=accent, width=18)
        elif any(word in label_l for word in ("степлер", "дырокол")):
            rr([250, 365, 665, 560], accent, None, 1, 44)
            rr([285, 300, 620, 420], "#ffffff", "#d8e5e8", 3, 36)
            rr([310, 555, 640, 620], "#475569", None, 1, 22)
        elif any(word in label_l for word in ("скреп", "зажим")):
            for i in range(5):
                x = 260 + i * 75
                draw.arc([x, 285, x + 135, 605], 90, 450, fill=accent if i % 2 else "#475569", width=16)
        elif any(word in label_l for word in ("лента", "скотч", "диспенсер")):
            draw.ellipse([250, 260, 610, 620], fill="#ffffff", outline=accent, width=28)
            draw.ellipse([360, 370, 500, 510], fill="#f7fbfa", outline="#d8e5e8", width=10)
            rr([520, 500, 700, 620], "#475569", None, 1, 24)
        else:
            rr([230, 250, 660, 650], "#ffffff", "#d8e5e8", 3, 24)
            draw.rectangle([230, 250, 660, 340], fill=accent)
            for y in range(390, 610, 52):
                line([(280, y), (610, y)], "#d8e5e8", 4)

    def draw_school():
        if any(word in label_l for word in ("ранец", "сумка")):
            rr([300, 220, 600, 700], accent, None, 1, 58)
            rr([342, 285, 558, 455], "#ffffff", None, 1, 32)
            rr([345, 515, 555, 660], accent_2, None, 1, 30)
            line([(290, 335), (210, 575)], dark, 14)
            line([(610, 335), (690, 575)], dark, 14)
        elif any(word in label_l for word in ("пенал",)):
            rr([210, 355, 690, 560], accent, None, 1, 90)
            line([(270, 455), (630, 455)], "#ffffff", 10)
            draw.ellipse([600, 425, 645, 470], fill="#ffffff")
        elif any(word in label_l for word in ("накле", "заклад")):
            for i, color in enumerate(["#f59e0b", "#e85d75", "#0e766e", "#7c3aed", "#2563eb"]):
                x = 230 + i * 90
                rr([x, 270, x + 74, 610], color, None, 1, 14)
                draw.polygon([(x, 610), (x + 37, 570), (x + 74, 610)], fill="#f7fbfa")
        else:
            draw_notebook()
            draw_pens(3)

    if any(word in label_l for word in ("мольберт",)):
        draw_easel()
    elif any(word in label_l for word in ("кист",)):
        draw_brushes()
    elif any(word in label_l for word in ("краск", "акварель", "гуаш", "акрил", "пальчиков", "палитр", "пастель", "пластилин", "уголь")):
        draw_paint()
    elif any(word in label_l for word in ("ручк", "линер")):
        draw_pens(5)
    elif any(word in label_l for word in ("маркер", "фломастер", "текстовыдел")):
        draw_pens(6, marker=True)
    elif any(word in label_l for word in ("карандаш", "грифел", "ластик", "точил")):
        draw_pencils()
    elif any(word in label_l for word in ("бумага", "картон", "калька", "конверт", "файл", "папка")):
        draw_paper_stack()
    elif any(word in label_l for word in ("тетрад", "блокнот", "ежедневник", "планер", "дневник", "альбом", "скетчбук")):
        draw_notebook()
    elif palette_key == "OF":
        draw_office()
    elif palette_key == "KD":
        draw_school()
    else:
        draw_notebook()

    # Вписываем заголовок в 3 строки максимум
    if not cyrillic_ok and subtitle:
        label = subtitle
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

    rr([78, 690, 822, 830], "#ffffff", "#dbe7ea", 2, 24)
    total_h = len(lines) * 38
    y0 = 713
    for i, ln in enumerate(lines):
        bbox = draw.textbbox((0, 0), ln, font=font_title)
        w = bbox[2] - bbox[0]
        draw.text(((size - w) // 2, y0 + i * 38), ln, fill=dark, font=font_title)

    if subtitle:
        bbox = draw.textbbox((0, 0), subtitle, font=font_sku)
        w = bbox[2] - bbox[0]
        rr([size - w - 120, 76, size - 70, 120], "#ffffff", "#dbe7ea", 2, 999)
        draw.text((size - w - 95, 87), subtitle, fill=accent, font=font_sku)

    dest_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(dest_path, format="JPEG", quality=88, optimize=True)


def _attach_image(instance, field_name, src_path, *, label=None, subtitle=None, palette_key="_default", stdout=None, force=False):
    """Set model's ImageField to point at a file in MEDIA_ROOT.

    Если файл уже есть (например, закоммичен в git и доехал на сервер) —
    просто присваиваем относительный путь полю. Если нет — генерим
    plausible-placeholder через Pillow и кладём в MEDIA_ROOT, чтобы
    карточки товаров никогда не были пустыми.
    """
    full_path = MEDIA_SRC / src_path
    if force or not full_path.exists():
        if label is None:
            # Нет данных для плейсхолдера — нечем заполнить, пропускаем
            _safe_stdout_write(stdout, f"  [skip] Нет картинки {src_path}, нет label для fallback")
            return
        _safe_stdout_write(stdout, f"  [gen]  Генерим товарную картинку {src_path} для '{label}'")
        try:
            _generate_placeholder_jpg(full_path, label, subtitle or "", palette_key)
        except Exception as e:
            _safe_stdout_write(stdout, f"  [err]  Не удалось сгенерить {src_path}: {e}")
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
        parser.add_argument(
            "--remote-images",
            action="store_true",
            help="Use remote Unsplash image URLs for products instead of local generated media files",
        )

    def handle(self, *args, **options):
        random.seed(20260430)
        self.use_remote_images = options["remote_images"]
        # Каждая секция — в своей транзакции + try/except. Так если одна
        # упадёт (например, валидация новой модели), остальные — в т.ч.
        # привязка картинок к товарам/блогу — сохранятся.
        if options["reset"]:
            self.stdout.write("Resetting demo entities...")
            with transaction.atomic():
                self._reset_data()

        categories_map, brands, products = None, None, None

        def _section(label, fn, *args, **kwargs):
            _safe_stdout_write(self.stdout, f"Seeding {label}...")
            try:
                with transaction.atomic():
                    return fn(*args, **kwargs)
            except Exception as e:
                _safe_stdout_write(self.stdout, self.style.ERROR(f"  [x] {label} failed: {e}"))
                return None

        categories_map = _section("categories", self._seed_categories)
        brands = _section("brands", self._seed_brands)
        if categories_map is not None and brands is not None:
            products = _section("products", self._seed_products, categories_map, brands)
        # Пользователей создаём рано, до marketing — чтобы отзывы на товары
        # сразу линковались к реальным покупателям.
        users = _section("users", self._seed_users) or {"customers": [], "managers": [], "admins": []}
        customers = users["customers"]
        managers = users["managers"]
        admins = users["admins"]

        if products is not None:
            _section("marketing", self._seed_marketing, products, customers)
        _section("logistics", self._seed_logistics)
        _section("content", self._seed_content)
        _section("wholesale", self._seed_wholesale)
        if brands is not None:
            _section("filters", self._seed_filters, brands)
        _section("gift certificates", self._seed_gift_certificates)
        if products is not None and customers:
            _section("customer data", self._seed_customer_data, products, customers)
        _section("returns", self._seed_returns)
        if managers or admins:
            _section("admin activity", self._seed_admin_activity, managers, admins)
        _section("site settings", self._seed_site_settings)

        count = len(products) if products else 0
        _safe_stdout_write(self.stdout, self.style.SUCCESS(
            f"Done! {count} products · {len(customers)} customers · "
            f"{len(managers)} managers · {len(admins)} admins."
        ))

    def _reset_data(self):
        # LogEntry — логи админки за менеджеров/админов. Чистим, чтобы
        # повторный --reset не накапливал дубликаты.
        LogEntry.objects.all().delete()
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
            website, logo_domain = BRAND_ASSETS.get(slug, ("", ""))
            brand, _ = Brand.objects.get_or_create(
                slug=slug,
                defaults={
                    "name": name,
                    "description": desc,
                    "website": website,
                    "logo_url": _brand_logo_url(logo_domain) if logo_domain else "",
                },
            )
            brand.name = name
            brand.description = desc
            brand.website = website
            brand.logo_url = _brand_logo_url(logo_domain) if logo_domain else brand.logo_url
            # Для брендов важнее показывать настоящий логотип/фавикон бренда,
            # а не старые демо-фото из media/brands.
            brand.logo = ""
            brand.save(update_fields=["name", "description", "website", "logo_url", "logo", "updated_at"])
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
        catalog.extend(
            {
                "sku": sku,
                "title": title,
                "price": price,
                "group": group,
                "brand": brand,
                "format": product_format,
                "sheets": sheets,
                "purpose": purpose,
                "desc": desc,
            }
            for sku, title, price, group, brand, product_format, sheets, purpose, desc in EXTRA_PRODUCT_SEEDS
        )
        if len(catalog) != 100:
            raise ValueError(f"Expected 100 demo products, got {len(catalog)}")

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
            if not created:
                product.title = item["title"]
                product.slug = slugify(item["sku"])
                product.brand = brands[item["brand"]]
                product.price = item["price"]
                product.old_price = int(item["price"] * 1.15) if idx % 3 != 0 else None
                product.stock = 10 + idx * 2
                product.format = item["format"]
                product.sheets_count = item["sheets"]
                product.purpose = item["purpose"]
                product.short_description = item["desc"][:200]
                product.description = item["desc"]
                product.is_new = idx % 4 == 0
                product.is_hit = idx % 5 == 0
                product.is_featured = idx % 7 == 0
                product.weight_grams = 50 + idx * 8
                product.length_mm = 100 + idx * 3
                product.width_mm = 50 + idx * 2
                product.height_mm = 5 + idx
                product.status = Product.ProductStatus.ACTIVE
                product.save()

            # Привязываем уникальную картинку по SKU. Цвет плейсхолдера —
            # по префиксу SKU (NB/PP/WR/AR/OF/KD).
            img_file = f"products/{item['sku']}.jpg"
            sku_prefix = item["sku"].split("-")[0]
            remote_image_url = _remote_product_image_url(item, idx)
            pi1, pi_created1 = ProductImage.objects.get_or_create(
                product=product,
                sort_order=1,
                defaults={
                    "is_primary": True,
                    "alt_text": item["title"],
                    "image_url": remote_image_url,
                },
            )
            pi1.is_primary = True
            pi1.alt_text = item["title"]
            pi1.image_url = remote_image_url
            if self.use_remote_images:
                pi1.image = ""
                pi1.save(update_fields=["is_primary", "alt_text", "image_url", "image", "updated_at"])
            else:
                pi1.save(update_fields=["is_primary", "alt_text", "image_url", "updated_at"])
            # Идемпотентно: если у записи нет реального файла — всё равно
            # вызываем attach, он либо найдёт существующий файл, либо
            # сгенерит плейсхолдер.
            if not self.use_remote_images:
                _attach_image(
                    pi1, "image", img_file,
                    label=item["title"],
                    subtitle=item["sku"],
                    palette_key=sku_prefix,
                    force=True,
                    stdout=self.stdout,
                )

            # Categories
            product.categories.clear()
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
    def _seed_marketing(self, products, customers=None):
        """Promotions + product reviews.

        `customers` — список User-объектов покупателей. Если передан, ~60%
        отзывов линкуются к реальным покупателям (Review.user + author_name
        = «Имя Ф.»), остальные остаются гостевыми.
        """
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

        # Reviews: на каждом товаре 2-4 отзыва. Часть — от реальных покупателей
        # (чтобы на странице профиля показывалась их история отзывов), часть —
        # гостевые, с именами из REVIEW_NAMES.
        # customers приходят как list[dict{"user": ..., "phone": ..., ...}] от
        # _seed_users — разворачиваем в list[User].
        customer_users = [c["user"] if isinstance(c, dict) else c for c in (customers or [])]
        for product in products:
            num_reviews = random.randint(2, 4)
            for _ in range(num_reviews):
                link_to_customer = customer_users and random.random() < 0.6
                if link_to_customer:
                    user = random.choice(customer_users)
                    author_name = f"{user.first_name} {user.last_name[:1]}."
                    review, created = ProductReview.objects.get_or_create(
                        product=product,
                        user=user,
                        defaults={
                            "author_name": author_name,
                            "rating": random.choice([4, 4, 5, 5, 5, 3]),
                            "text": random.choice(REVIEW_TEXTS),
                            "is_published": True,
                        },
                    )
                else:
                    name = random.choice(REVIEW_NAMES)
                    review, created = ProductReview.objects.get_or_create(
                        product=product,
                        author_name=name,
                        user=None,
                        defaults={
                            "rating": random.choice([4, 4, 5, 5, 5, 3]),
                            "text": random.choice(REVIEW_TEXTS),
                            "is_published": True,
                        },
                    )
                if created:
                    _set_timestamps(review, timezone.now() - timedelta(days=random.randint(1, 180)))

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

    # ─── Users (3 ролей: покупатели, менеджеры, админы) ──
    def _seed_users(self):
        """Create all demo users in a single pass.

        Принудительно синхронизируем email / имя / флаги / пароль на каждом
        запуске, чтобы демо-доступы из README всегда совпадали с БД (даже
        если юзер уже существовал с другими значениями). Даты регистрации и
        последнего входа бэкдейтим, чтобы в админке `/admin/auth/user/` была
        видна реальная «возрастная» картина.
        """
        User = get_user_model()

        customers = []
        for idx, (username, first, last, phone, bday, city, street, postal) in enumerate(CUSTOMER_SEEDS):
            user, _ = User.objects.get_or_create(
                username=username,
                defaults={"email": f"{username}@paperly.ru", "first_name": first, "last_name": last},
            )
            user.email = f"{username}@paperly.ru"
            user.first_name = first
            user.last_name = last
            user.is_staff = False
            user.is_superuser = False
            user.is_active = True
            user.set_password("customer12345")
            # Разбрасываем дату регистрации — от 2 до 12 месяцев назад.
            user.date_joined = timezone.now() - timedelta(days=60 + idx * 28)
            user.last_login = timezone.now() - timedelta(hours=random.randint(1, 720))
            user.save()
            customers.append({
                "user": user, "phone": phone, "birth_date": bday,
                "city": city, "street": street, "postal_code": postal,
            })

        manager_group, _ = Group.objects.get_or_create(name="Менеджер")
        managers = []
        for idx, (username, first, last) in enumerate(MANAGER_SEEDS):
            user, _ = User.objects.get_or_create(
                username=username,
                defaults={"email": f"{username}@paperly.ru", "first_name": first, "last_name": last},
            )
            user.email = f"{username}@paperly.ru"
            user.first_name = first
            user.last_name = last
            user.is_staff = True
            user.is_superuser = False
            user.is_active = True
            user.set_password("manager12345")
            user.date_joined = timezone.now() - timedelta(days=120 + idx * 45)
            user.last_login = timezone.now() - timedelta(hours=random.randint(1, 48))
            user.save()
            user.groups.add(manager_group)
            managers.append(user)

        admins = []
        for idx, (username, first, last) in enumerate(ADMIN_SEEDS):
            user, _ = User.objects.get_or_create(
                username=username,
                defaults={"email": f"{username}@paperly.ru", "first_name": first, "last_name": last},
            )
            user.email = f"{username}@paperly.ru"
            user.first_name = first
            user.last_name = last
            user.is_staff = True
            user.is_superuser = True
            user.is_active = True
            user.set_password("admin12345")
            user.date_joined = timezone.now() - timedelta(days=400 + idx * 120)
            user.last_login = timezone.now() - timedelta(hours=random.randint(1, 24))
            user.save()
            admins.append(user)

        return {"customers": customers, "managers": managers, "admins": admins}

    # ─── Customer data ───────────────────────────
    def _seed_customer_data(self, products, customers):
        """Наполняем профили покупателей данными (профиль, адрес,
        уведомления, избранное, корзина, заказы). Каждый покупатель получает
        разный объём активности, чтобы карточки выглядели реалистично.
        """
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

        # Веса статусов: завершённые — большинство, отменённые — редкость.
        STATUS_WEIGHTS = [
            (Order.OrderStatus.DONE,      45),
            (Order.OrderStatus.SHIPPED,   15),
            (Order.OrderStatus.PAID,      10),
            (Order.OrderStatus.CONFIRMED, 10),
            (Order.OrderStatus.NEW,        8),
            (Order.OrderStatus.CANCELED,  12),
        ]
        statuses_pool = [s for s, w in STATUS_WEIGHTS for _ in range(w)]

        order_seq = 1001  # номера ORD-001001, ORD-001002, …

        for cust_idx, cust in enumerate(customers):
            user = cust["user"]

            # Профиль + адрес + уведомления — у каждого свой.
            profile, _ = CustomerProfile.objects.get_or_create(
                user=user,
                defaults={
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "phone": cust["phone"],
                    "birth_date": cust["birth_date"],
                },
            )
            Address.objects.get_or_create(
                profile=profile,
                city=cust["city"],
                street=cust["street"],
                defaults={
                    "address_type": Address.AddressType.SHIPPING, "is_default": True,
                    "entrance": str(random.randint(1, 4)),
                    "flat_or_office": f"кв. {random.randint(1, 200)}",
                    "postal_code": cust["postal_code"],
                },
            )
            NotificationSetting.objects.get_or_create(
                profile=profile,
                defaults={
                    "order_status": True,
                    "promotions": random.choice([True, False]),
                    "restock": random.choice([True, False]),
                },
            )

            # Избранное: 5–15 товаров на покупателя.
            fav_count = random.randint(5, min(15, len(products)))
            for product in random.sample(products, fav_count):
                favorite, created = Favorite.objects.get_or_create(user=user, product=product)
                if created:
                    _set_timestamps(favorite, timezone.now() - timedelta(days=random.randint(1, 180)))

            # Корзина: у части покупателей (70%) в ней что-то лежит.
            cart, _ = Cart.objects.get_or_create(user=user)
            if random.random() < 0.7:
                cart_items = random.sample(products, random.randint(1, 5))
                for product in cart_items:
                    cart_item, created = CartItem.objects.get_or_create(
                        cart=cart, product=product,
                        defaults={
                            "quantity": random.randint(1, 3),
                            "price_snapshot": product.price,
                        },
                    )
                    if created:
                        _set_timestamps(cart_item, timezone.now() - timedelta(days=random.randint(0, 45)))

            # Заказы: 3-8 штук на покупателя с разными статусами за последние 6+ месяцев.
            num_orders = random.randint(3, 8)
            for _ in range(num_orders):
                status = random.choice(statuses_pool)
                delivery = random.choice([Order.DeliveryType.COURIER, Order.DeliveryType.PICKUP])
                pay_type = random.choice([
                    Order.PaymentType.CARD, Order.PaymentType.SBP,
                    Order.PaymentType.CASH, Order.PaymentType.CARD,  # CARD вдвое чаще
                ])
                order_products = random.sample(products, random.randint(1, 4))
                delivery_price = 350 if delivery == Order.DeliveryType.COURIER else 0
                # Реалистичные количества на позицию заказа.
                line_qty = {p.id: random.randint(1, 3) for p in order_products}
                subtotal = sum(p.price * line_qty[p.id] for p in order_products)

                number = f"ORD-{order_seq:06d}"
                order_seq += 1
                created_at = timezone.now() - timedelta(days=random.randint(1, 210))
                order, created = Order.objects.get_or_create(
                    number=number,
                    defaults={
                        "user": user,
                        "full_name": user.get_full_name(),
                        "phone": cust["phone"],
                        "email": user.email,
                        "city": cust["city"],
                        "address": cust["street"],
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
                    # Бэкдейтим created_at обычным UPDATE — auto_now_add не даёт
                    # задать дату на .create(), но .update() его игнорирует.
                    Order.objects.filter(pk=order.pk).update(created_at=created_at)
                    for p in order_products:
                        OrderItem.objects.create(
                            order=order, product=p,
                            title_snapshot=p.title, sku_snapshot=p.sku,
                            quantity=line_qty[p.id], unit_price=p.price,
                        )
                    # История статусов: цепочка переходов
                    chain = STATUS_CHAINS.get(status, [status])
                    for step_idx, step_status in enumerate(chain):
                        history_item = OrderStatusHistory.objects.create(
                            order=order, status=step_status,
                            comment=f"Статус: {Order.OrderStatus(step_status).label}",
                        )
                        history_at = min(
                            created_at + timedelta(hours=4 + step_idx * 18),
                            timezone.now() - timedelta(minutes=5 + step_idx),
                        )
                        _set_timestamps(history_item, history_at)

    # ─── Admin activity (LogEntry) ───────────────
    def _seed_admin_activity(self, managers, admins):
        """Fill django_admin_log with realistic actions from managers/admins.

        LogEntry.action_time имеет `auto_now_add=True`, поэтому значение
        нельзя задать на .create() — делаем UPDATE'ом после создания.
        """

        def _log(user, obj, action_flag, fields=None, days_ago=0):
            ct = ContentType.objects.get_for_model(obj.__class__)
            change_message = (
                json.dumps([{"changed": {"fields": fields}}]) if fields
                else json.dumps([{"added": {}}])
            )
            entry = LogEntry.objects.create(
                user=user, content_type=ct,
                object_id=str(obj.pk), object_repr=str(obj)[:200],
                action_flag=action_flag, change_message=change_message,
            )
            action_time = timezone.now() - timedelta(days=days_ago, hours=random.randint(0, 23))
            LogEntry.objects.filter(pk=entry.pk).update(action_time=action_time)
            return entry

        # ── Менеджеры: модерация отзывов + публикация блога ──
        reviews = list(ProductReview.objects.all()[:40])
        posts = list(BlogPost.objects.all())
        for mgr_idx, manager in enumerate(managers):
            # 6-10 действий на менеджера, в разное время последних 30 дней.
            actions_count = random.randint(6, 10)
            for _ in range(actions_count):
                kind = random.random()
                days_ago = random.randint(0, 30)
                if kind < 0.5 and reviews:
                    # Изменение отзыва (например, toggle is_published)
                    _log(manager, random.choice(reviews), CHANGE,
                         fields=["is_published"], days_ago=days_ago)
                elif kind < 0.85 and posts:
                    _log(manager, random.choice(posts), CHANGE,
                         fields=["status", "content"], days_ago=days_ago)
                elif posts:
                    # Добавление черновика блог-поста
                    _log(manager, random.choice(posts), ADDITION, days_ago=days_ago)

        # ── Админы: более разнообразный набор действий ──
        products = list(Product.objects.all()[:20])
        orders = list(Order.objects.all()[:30])
        promos = list(Promotion.objects.all())
        brands = list(Brand.objects.all()[:5])
        pages = list(SitePage.objects.all())
        for adm_idx, admin_user in enumerate(admins):
            actions_count = random.randint(15, 25)
            for _ in range(actions_count):
                days_ago = random.randint(0, 60)
                pool = random.random()
                if pool < 0.3 and products:
                    _log(admin_user, random.choice(products), CHANGE,
                         fields=random.choice([["price"], ["stock"], ["price", "old_price"]]),
                         days_ago=days_ago)
                elif pool < 0.55 and orders:
                    _log(admin_user, random.choice(orders), CHANGE,
                         fields=["status"], days_ago=days_ago)
                elif pool < 0.7 and promos:
                    _log(admin_user, random.choice(promos), CHANGE,
                         fields=["discount_percent", "end_at"], days_ago=days_ago)
                elif pool < 0.85 and pages:
                    _log(admin_user, random.choice(pages), CHANGE,
                         fields=["content"], days_ago=days_ago)
                elif brands:
                    _log(admin_user, random.choice(brands), CHANGE,
                         fields=["description"], days_ago=days_ago)

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
        """Создаём 3-5 заявок на возврат по разным клиентам и разным статусам.

        Возвраты привязаны к реальным DONE/SHIPPED заказам, поэтому покупатель
        видит их в своём разделе «Возвраты» в ЛК, а менеджер/админ — в
        админке.
        """
        done_orders = list(Order.objects.filter(status=Order.OrderStatus.DONE).select_related("user")[:6])
        shipped_orders = list(Order.objects.filter(status=Order.OrderStatus.SHIPPED).select_related("user")[:3])

        return_templates = [
            (ReturnRequest.ReturnType.GOOD_QUALITY, ReturnRequest.ReturnStatus.APPROVED,
             "Товар не подошёл по формату, хочу обменять на A5.", "Нужен другой формат"),
            (ReturnRequest.ReturnType.GOOD_QUALITY, ReturnRequest.ReturnStatus.REFUNDED,
             "Передумал, возврат средств.", "Возврат по желанию покупателя"),
            (ReturnRequest.ReturnType.DEFECT, ReturnRequest.ReturnStatus.CHECKING,
             "Получен товар с повреждённой упаковкой.", "Помятая коробка, царапины на корпусе"),
            (ReturnRequest.ReturnType.DEFECT, ReturnRequest.ReturnStatus.NEW,
             "Не работает механизм — нужен обмен.", "Брак, не пишет"),
            (ReturnRequest.ReturnType.DEFECT, ReturnRequest.ReturnStatus.REJECTED,
             "Следы использования — отклонено.", "Отклонено модератором"),
        ]

        idx = 0
        for order in done_orders[:3] + shipped_orders[:2]:
            if idx >= len(return_templates):
                break
            rtype, rstatus, reason, item_comment = return_templates[idx]
            items = list(order.items.all())
            if not items:
                continue
            ret, created = ReturnRequest.objects.get_or_create(
                order=order,
                return_type=rtype,
                defaults={"user": order.user, "reason": reason, "status": rstatus},
            )
            if created:
                ReturnRequestItem.objects.create(
                    return_request=ret, order_item=items[0],
                    quantity=1, comment=item_comment,
                )
            idx += 1

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
