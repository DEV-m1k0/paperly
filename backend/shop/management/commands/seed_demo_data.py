from datetime import timedelta

from django.contrib.auth import get_user_model
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
    Category,
    CustomerProfile,
    DeliveryTariff,
    Favorite,
    GiftCertificate,
    Order,
    OrderItem,
    PickupPoint,
    Product,
    ProductImage,
    ProductReview,
    ProductSpecification,
    Promotion,
    SitePage,
    WholesalePriceList,
    WholesaleRequest,
)


class Command(BaseCommand):
    help = "Seed database with demo data for Paperly"

    def add_arguments(self, parser):
        parser.add_argument("--reset", action="store_true", help="Delete old demo entities before seeding")

    @transaction.atomic
    def handle(self, *args, **options):
        if options["reset"]:
            self.stdout.write("Resetting demo entities...")
            self._reset_data()

        categories_map = self._seed_categories()
        brands = self._seed_brands()
        products = self._seed_products(categories_map, brands)
        self._seed_marketing(products)
        self._seed_logistics()
        self._seed_content()
        self._seed_wholesale()
        self._seed_customer_data(products)

        self.stdout.write(self.style.SUCCESS("Demo data generated successfully."))

    def _reset_data(self):
        # Order matters due to foreign keys.
        for model in [
            ProductReview,
            ProductImage,
            ProductSpecification,
            Favorite,
            CartItem,
            OrderItem,
            Product,
            Promotion,
            Cart,
            Order,
            WholesaleRequest,
            SitePage,
            GiftCertificate,
            BlogPost,
            BlogCategory,
            DeliveryTariff,
            PickupPoint,
            WholesalePriceList,
            Address,
            CustomerProfile,
            Category,
            Brand,
        ]:
            model.objects.all().delete()

    def _seed_categories(self):
        tree = {
            "paper": {
                "title": "Бумажная продукция",
                "children": [
                    "Тетради",
                    "Блокноты и ежедневники",
                    "Альбомы и папки для черчения",
                    "Бумага для офисной техники",
                    "Цветная бумага и картон",
                ],
            },
            "writing": {
                "title": "Письменные принадлежности",
                "children": ["Ручки", "Карандаши", "Маркеры и текстовыделители", "Фломастеры"],
            },
            "art": {
                "title": "Чертежные и художественные товары",
                "children": ["Краски", "Кисти", "Пастель и уголь", "Лепка", "Чертежные инструменты"],
            },
            "office": {
                "title": "Товары для офиса",
                "children": ["Архивация", "Органайзеры", "Канцелярские мелочи", "Расходники для оргтехники"],
            },
            "kids": {
                "title": "Школа и творчество",
                "children": ["Наборы первоклассника", "Пеналы и ранцы", "Наборы для творчества"],
            },
        }

        categories_map = {}
        for idx, (key, payload) in enumerate(tree.items(), start=1):
            parent, _ = Category.objects.get_or_create(
                slug=key,
                defaults={"name": payload["title"], "sort_order": idx},
            )
            categories_map[key] = [parent]
            for child_idx, child in enumerate(payload["children"], start=1):
                child_obj, _ = Category.objects.get_or_create(
                    slug=f"{parent.slug}-{child_idx}",
                    defaults={"name": child, "parent": parent, "sort_order": child_idx},
                )
                categories_map[key].append(child_obj)

        return categories_map

    def _seed_brands(self):
        brands_seed = [
            ("erich-krause", "Erich Krause"),
            ("kores", "Kores"),
            ("brauberg", "Brauberg"),
            ("maped", "Maped"),
            ("pilot", "Pilot"),
            ("faber-castell", "Faber-Castell"),
        ]

        by_slug = {}
        for slug, name in brands_seed:
            brand, _ = Brand.objects.get_or_create(
                slug=slug,
                defaults={
                    "name": name,
                    "description": f"Официальный бренд {name}",
                    "logo_url": "https://i.pinimg.com/736x/3b/64/64/3b6464b038975404becbc54011c06000.jpg",
                },
            )
            by_slug[slug] = brand

        return by_slug

    def _seed_products(self, categories_map, brands):
        catalog = [
            {
                "title": "Тетрадь A5 48 листов клетка",
                "sku": "NB-001",
                "price": 120,
                "group": "paper",
                "brand": "erich-krause",
                "format": Product.ProductFormat.A5,
                "sheets": 48,
                "purpose": Product.ProductPurpose.SCHOOL,
            },
            {
                "title": "Тетрадь A4 96 листов на спирали",
                "sku": "NB-002",
                "price": 290,
                "group": "paper",
                "brand": "brauberg",
                "format": Product.ProductFormat.A4,
                "sheets": 96,
                "purpose": Product.ProductPurpose.OFFICE,
            },
            {
                "title": "Ежедневник датированный A5",
                "sku": "NB-003",
                "price": 590,
                "group": "paper",
                "brand": "maped",
                "format": Product.ProductFormat.A5,
                "sheets": 176,
                "purpose": Product.ProductPurpose.OFFICE,
            },
            {
                "title": "Бумага офисная A4 500 листов",
                "sku": "PP-001",
                "price": 760,
                "group": "paper",
                "brand": "brauberg",
                "format": Product.ProductFormat.A4,
                "sheets": 500,
                "purpose": Product.ProductPurpose.OFFICE,
            },
            {
                "title": "Цветной картон A4 10 листов",
                "sku": "PP-002",
                "price": 180,
                "group": "paper",
                "brand": "kores",
                "format": Product.ProductFormat.A4,
                "sheets": 10,
                "purpose": Product.ProductPurpose.CREATIVE,
            },
            {
                "title": "Ручка шариковая синяя",
                "sku": "WR-001",
                "price": 80,
                "group": "writing",
                "brand": "pilot",
                "format": Product.ProductFormat.OTHER,
                "sheets": None,
                "purpose": Product.ProductPurpose.SCHOOL,
            },
            {
                "title": "Набор гелевых ручек 12 цветов",
                "sku": "WR-002",
                "price": 420,
                "group": "writing",
                "brand": "pilot",
                "format": Product.ProductFormat.OTHER,
                "sheets": None,
                "purpose": Product.ProductPurpose.CREATIVE,
            },
            {
                "title": "Карандаши цветные 24 цвета",
                "sku": "WR-003",
                "price": 490,
                "group": "writing",
                "brand": "faber-castell",
                "format": Product.ProductFormat.OTHER,
                "sheets": None,
                "purpose": Product.ProductPurpose.CREATIVE,
            },
            {
                "title": "Маркеры двусторонние 12 шт",
                "sku": "WR-004",
                "price": 370,
                "group": "writing",
                "brand": "maped",
                "format": Product.ProductFormat.OTHER,
                "sheets": None,
                "purpose": Product.ProductPurpose.CREATIVE,
            },
            {
                "title": "Фломастеры смываемые 12 шт",
                "sku": "WR-005",
                "price": 290,
                "group": "writing",
                "brand": "maped",
                "format": Product.ProductFormat.OTHER,
                "sheets": None,
                "purpose": Product.ProductPurpose.SCHOOL,
            },
            {
                "title": "Краски акварель 24 цвета",
                "sku": "AR-001",
                "price": 690,
                "group": "art",
                "brand": "faber-castell",
                "format": Product.ProductFormat.OTHER,
                "sheets": None,
                "purpose": Product.ProductPurpose.CREATIVE,
            },
            {
                "title": "Кисти синтетика 6 шт",
                "sku": "AR-002",
                "price": 360,
                "group": "art",
                "brand": "maped",
                "format": Product.ProductFormat.OTHER,
                "sheets": None,
                "purpose": Product.ProductPurpose.CREATIVE,
            },
            {
                "title": "Пастель сухая 24 цвета",
                "sku": "AR-003",
                "price": 520,
                "group": "art",
                "brand": "faber-castell",
                "format": Product.ProductFormat.OTHER,
                "sheets": None,
                "purpose": Product.ProductPurpose.CREATIVE,
            },
            {
                "title": "Пластилин мягкий 18 цветов",
                "sku": "AR-004",
                "price": 310,
                "group": "art",
                "brand": "erich-krause",
                "format": Product.ProductFormat.OTHER,
                "sheets": None,
                "purpose": Product.ProductPurpose.CREATIVE,
            },
            {
                "title": "Циркуль металлический",
                "sku": "AR-005",
                "price": 240,
                "group": "art",
                "brand": "maped",
                "format": Product.ProductFormat.OTHER,
                "sheets": None,
                "purpose": Product.ProductPurpose.SCHOOL,
            },
            {
                "title": "Папка-регистратор A4",
                "sku": "OF-001",
                "price": 210,
                "group": "office",
                "brand": "brauberg",
                "format": Product.ProductFormat.A4,
                "sheets": None,
                "purpose": Product.ProductPurpose.OFFICE,
            },
            {
                "title": "Органайзер настольный",
                "sku": "OF-002",
                "price": 540,
                "group": "office",
                "brand": "kores",
                "format": Product.ProductFormat.OTHER,
                "sheets": None,
                "purpose": Product.ProductPurpose.OFFICE,
            },
            {
                "title": "Степлер офисный",
                "sku": "OF-003",
                "price": 330,
                "group": "office",
                "brand": "kores",
                "format": Product.ProductFormat.OTHER,
                "sheets": None,
                "purpose": Product.ProductPurpose.OFFICE,
            },
            {
                "title": "Набор первоклассника",
                "sku": "KD-001",
                "price": 1990,
                "group": "kids",
                "brand": "erich-krause",
                "format": Product.ProductFormat.OTHER,
                "sheets": None,
                "purpose": Product.ProductPurpose.SCHOOL,
            },
            {
                "title": "Пенал с отделениями",
                "sku": "KD-002",
                "price": 420,
                "group": "kids",
                "brand": "maped",
                "format": Product.ProductFormat.OTHER,
                "sheets": None,
                "purpose": Product.ProductPurpose.SCHOOL,
            },
        ]

        products = []
        for idx, item in enumerate(catalog, start=1):
            product, _ = Product.objects.get_or_create(
                sku=item["sku"],
                defaults={
                    "title": item["title"],
                    "slug": item["sku"].lower(),
                    "brand": brands[item["brand"]],
                    "price": item["price"],
                    "old_price": int(item["price"] * 1.15),
                    "stock": 12 + idx * 3,
                    "format": item["format"],
                    "sheets_count": item["sheets"],
                    "purpose": item["purpose"],
                    "short_description": "Демо-описание товара",
                    "description": f"Полное описание для товара: {item['title']}",
                    "is_new": idx % 3 == 0,
                    "is_hit": idx % 4 == 0,
                    "is_featured": idx % 5 == 0,
                    "weight_grams": 80 + idx * 10,
                    "length_mm": 100 + idx * 3,
                    "width_mm": 50 + idx * 2,
                    "height_mm": 10 + idx,
                },
            )

            # Keep brand актуальным даже при повторном запуске без --reset.
            if product.brand_id != brands[item["brand"]].id:
                product.brand = brands[item["brand"]]
                product.format = item["format"]
                product.sheets_count = item["sheets"]
                product.purpose = item["purpose"]
                product.save(update_fields=["brand", "format", "sheets_count", "purpose", "updated_at"])

            for cat in categories_map[item["group"]][:2]:
                product.categories.add(cat)

            ProductImage.objects.get_or_create(
                product=product,
                image_url="https://i.pinimg.com/736x/6f/50/58/6f50589b1dfb1a83c2a2ac5d9882a1c6.jpg",
                defaults={"is_primary": True, "sort_order": 1},
            )
            ProductImage.objects.get_or_create(
                product=product,
                image_url="https://i.pinimg.com/736x/6f/50/58/6f50589b1dfb1a83c2a2ac5d9882a1c6.jpg",
                defaults={"is_primary": False, "sort_order": 2},
            )

            ProductSpecification.objects.get_or_create(product=product, name="Формат", defaults={"value": item["format"]})
            ProductSpecification.objects.get_or_create(product=product, name="Назначение", defaults={"value": item["purpose"]})

            products.append(product)

        return products

    def _seed_marketing(self, products):
        promo, _ = Promotion.objects.get_or_create(
            slug="back-to-school",
            defaults={
                "title": "Снова в школу",
                "description": "Скидки до 30% на базовые наборы",
                "discount_percent": 30,
                "start_at": timezone.now() - timedelta(days=3),
                "end_at": timezone.now() + timedelta(days=20),
            },
        )
        promo.products.set(products[:8])

        for nominal in [1000, 3000, 5000]:
            GiftCertificate.objects.get_or_create(
                slug=f"gift-{nominal}",
                defaults={"title": f"Сертификат {nominal} ₽", "nominal": nominal},
            )

        for idx, product in enumerate(products[:10], start=1):
            ProductReview.objects.get_or_create(
                product=product,
                author_name=f"Покупатель {idx}",
                defaults={
                    "rating": 5 if idx % 2 else 4,
                    "text": "Отличный товар, соответствует описанию.",
                },
            )

    def _seed_logistics(self):
        points = [
            ("msk-tverskaya", "ПВЗ Тверская", "Москва", "Тверская ул., 10", 55.765611, 37.605110),
            ("msk-sokolniki", "ПВЗ Сокольники", "Москва", "Русаковская ул., 24", 55.792412, 37.679088),
            ("spb-nevsky", "ПВЗ Невский", "Санкт-Петербург", "Невский пр., 88", 59.931058, 30.360909),
        ]
        for point_slug, name, city, address, lat, lon in points:
            PickupPoint.objects.get_or_create(
                slug=point_slug,
                defaults={
                    "name": name,
                    "city": city,
                    "address": address,
                    "latitude": lat,
                    "longitude": lon,
                    "opening_hours": "Ежедневно 10:00-21:00",
                },
            )

        DeliveryTariff.objects.get_or_create(
            title="Курьер по Москве",
            city="Москва",
            delivery_type=DeliveryTariff.DeliveryType.COURIER,
            defaults={"price": 350, "free_from_amount": 2500, "eta_min_days": 1, "eta_max_days": 2},
        )
        DeliveryTariff.objects.get_or_create(
            title="Самовывоз",
            city="",
            delivery_type=DeliveryTariff.DeliveryType.PICKUP,
            defaults={"price": 0, "eta_min_days": 0, "eta_max_days": 1},
        )

    def _seed_content(self):
        blog_cat, _ = BlogCategory.objects.get_or_create(title="Советы", slug="tips")

        posts = [
            "Как выбрать дневник на учебный год",
            "Чем акварельные карандаши отличаются от обычных",
            "Как собрать офисный набор на месяц",
        ]
        for idx, title in enumerate(posts, start=1):
            BlogPost.objects.get_or_create(
                slug=f"blog-{idx}",
                defaults={
                    "title": title,
                    "category": blog_cat,
                    "excerpt": "Краткое описание статьи",
                    "content": "Подробный SEO-текст статьи для блога.",
                    "status": BlogPost.PostStatus.PUBLISHED,
                    "published_at": timezone.now(),
                },
            )

        pages = [
            (SitePage.PageType.ABOUT, "О магазине"),
            (SitePage.PageType.DELIVERY, "Доставка и оплата"),
            (SitePage.PageType.GUARANTEE, "Гарантия и возврат"),
            (SitePage.PageType.WHOLESALE, "Оптовым клиентам"),
            (SitePage.PageType.PRIVACY, "Политика конфиденциальности"),
            (SitePage.PageType.TERMS, "Пользовательское соглашение"),
            (SitePage.PageType.OFFER, "Договор оферты"),
        ]
        for page_type, title in pages:
            SitePage.objects.get_or_create(
                slug=slugify(page_type),
                defaults={"title": title, "page_type": page_type, "content": f"Текст страницы: {title}"},
            )

    def _seed_wholesale(self):
        for segment, title in [
            (WholesalePriceList.Segment.BUSINESS, "Прайс для юрлиц"),
            (WholesalePriceList.Segment.SCHOOL, "Прайс для школ"),
            (WholesalePriceList.Segment.UNIVERSITY, "Прайс для университетов"),
        ]:
            WholesalePriceList.objects.get_or_create(
                slug=slugify(title),
                defaults={
                    "title": title,
                    "segment": segment,
                    "file_url": "https://example.com/price-list.pdf",
                },
            )

        WholesaleRequest.objects.get_or_create(
            organization_name="ООО Офис Снаб",
            organization_type=WholesaleRequest.OrganizationType.LLC,
            contact_person="Иван Петров",
            phone="+7 (999) 000-11-22",
            email="office@example.com",
            defaults={"comment": "Нужна поставка для 3 офисов"},
        )

    def _seed_customer_data(self, products):
        user_model = get_user_model()
        user, _ = user_model.objects.get_or_create(
            username="demo",
            defaults={"email": "demo@paperly.local", "first_name": "Demo"},
        )
        user.set_password("demo12345")
        user.save(update_fields=["password"])

        profile, _ = CustomerProfile.objects.get_or_create(
            user=user,
            defaults={"first_name": "Антон", "last_name": "Князев", "phone": "+7 (999) 100-00-00"},
        )
        Address.objects.get_or_create(
            profile=profile,
            city="Москва",
            street="Ленинский проспект, 1",
            defaults={"address_type": Address.AddressType.SHIPPING, "is_default": True},
        )

        for product in products[:5]:
            Favorite.objects.get_or_create(user=user, product=product)

        cart, _ = Cart.objects.get_or_create(user=user)
        for product in products[:3]:
            CartItem.objects.get_or_create(
                cart=cart,
                product=product,
                defaults={"quantity": 1, "price_snapshot": product.price},
            )

        pickup = PickupPoint.objects.first()
        order, _ = Order.objects.get_or_create(
            number="ORD-1001",
            defaults={
                "user": user,
                "full_name": "Антон Князев",
                "phone": "+7 (999) 100-00-00",
                "email": "demo@paperly.local",
                "city": "Москва",
                "address": "Ленинский проспект, 1",
                "delivery_type": Order.DeliveryType.PICKUP,
                "payment_type": Order.PaymentType.CARD,
                "pickup_point": pickup,
                "subtotal": 1770,
                "delivery_price": 0,
                "discount_amount": 100,
                "total": 1670,
            },
        )

        for product in products[:3]:
            OrderItem.objects.get_or_create(
                order=order,
                title_snapshot=product.title,
                defaults={
                    "product": product,
                    "sku_snapshot": product.sku,
                    "quantity": 1,
                    "unit_price": product.price,
                },
            )
