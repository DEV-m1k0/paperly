"""
Management command: fetch_wb_images

Читает wb_mapping.csv, для каждого товара с заполненным wb_nm_id:
  1. Определяет CDN-basket по vol (с авто-пробингом для новых диапазонов).
  2. Скачивает минимум MIN_IMAGES картинок (.webp → .jpg).
  3. Сохраняет в media/products/{sku}-{n}.jpg.
  4. Создаёт ProductImage записи: первая is_primary=True, остальные по sort_order.

Идемпотентно: пропускает уже скачанные файлы (--force для перезаписи).
"""
import csv
import io
import json
import ssl
import time
import urllib.error
import urllib.request
from pathlib import Path

import certifi
import django.db
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from PIL import Image

from shop.models import Product, ProductImage


# --------------------------------------------------------------------------- #
# WB CDN helpers
# --------------------------------------------------------------------------- #

# vol → basket table (официально известные диапазоны по состоянию на 2024-25)
_BASKET_TABLE = [
    (143,  1), (287,  2), (431,  3), (719,  4), (1007,  5),
    (1061, 6), (1115, 7), (1169, 8), (1313,  9), (1601, 10),
    (1655, 11), (1919, 12), (2045, 13), (2189, 14), (2405, 15),
    (2621, 16), (2837, 17), (3053, 18), (3269, 19), (3485, 20),
    (3701, 21),
]
_BASKET_STEP = 216          # шаг vol для basket 22+
_BASKET_BASE_VOL = 3486     # начало диапазона basket 22
_BASKET_BASE_NUM = 22
_PROBE_MAX_BASKET = 50      # не идём выше


def vol_from_nm(nm_id: int) -> int:
    return nm_id // 100_000


def part_from_nm(nm_id: int) -> int:
    return nm_id // 1_000


def expected_basket(nm_id: int) -> int:
    vol = vol_from_nm(nm_id)
    for threshold, basket in _BASKET_TABLE:
        if vol <= threshold:
            return basket
    # экстраполяция для basket 22+
    return _BASKET_BASE_NUM + (vol - _BASKET_BASE_VOL) // _BASKET_STEP


def image_url(nm_id: int, basket: int, n: int) -> str:
    vol = vol_from_nm(nm_id)
    part = part_from_nm(nm_id)
    return (
        f"https://basket-{basket:02d}.wbbasket.ru"
        f"/vol{vol}/part{part}/{nm_id}/images/big/{n}.webp"
    )


SSL_CTX = ssl.create_default_context(cafile=certifi.where())
UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)


def _get(url: str, timeout: float = 10.0) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout, context=SSL_CTX) as r:
        return r.read()


def card_json_url(nm_id: int, basket: int) -> str:
    vol = vol_from_nm(nm_id)
    part = part_from_nm(nm_id)
    return (
        f"https://basket-{basket:02d}.wbbasket.ru"
        f"/vol{vol}/part{part}/{nm_id}/info/ru/card.json"
    )


def find_basket_and_photo_count(nm_id: int) -> tuple[int, int] | tuple[None, None]:
    """
    Пробует basket'ы через лёгкий card.json (не качает картинки).
    Возвращает (basket, photo_count) или (None, None) если не нашёл.
    """
    exp = expected_basket(nm_id)
    # Проверяем ожидаемый ± широкий диапазон (CDN-распределение нелинейно)
    candidates = sorted(
        range(1, _PROBE_MAX_BASKET + 1),
        key=lambda b: abs(b - exp),
    )
    for b in candidates:
        try:
            raw = _get(card_json_url(nm_id, b), timeout=6)
            data = json.loads(raw)
            photo_count = (data.get("media") or {}).get("photo_count") or 0
            return b, photo_count
        except urllib.error.HTTPError as e:
            if e.code == 404:
                continue
            raise
        except Exception:
            continue
    return None, None


def download_image(nm_id: int, basket: int, n: int) -> bytes:
    """Скачивает webp, возвращает байты JPEG."""
    raw = _get(image_url(nm_id, basket, n))
    img = Image.open(io.BytesIO(raw)).convert("RGB")
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=90)
    return buf.getvalue()


# --------------------------------------------------------------------------- #
# Management command
# --------------------------------------------------------------------------- #

class Command(BaseCommand):
    help = "Скачивает картинки с WB CDN по wb_mapping.csv и создаёт ProductImage записи."

    def add_arguments(self, parser):
        parser.add_argument("--csv",       default="wb_mapping.csv", help="Путь к CSV-файлу.")
        parser.add_argument("--min-imgs",  type=int, default=3,      help="Минимум картинок на товар.")
        parser.add_argument("--max-imgs",  type=int, default=5,      help="Максимум картинок на товар.")
        parser.add_argument("--delay",     type=float, default=0.5,  help="Пауза между скачиваниями (сек).")
        parser.add_argument("--force",     action="store_true",      help="Перезаписать уже скачанные файлы.")
        parser.add_argument("--limit",     type=int, default=0,      help="Обработать только первые N товаров.")
        parser.add_argument("--sku",       help="Обработать только конкретный SKU.")

    def handle(self, *args, **options):
        csv_path = Path(options["csv"]).resolve()
        if not csv_path.exists():
            raise CommandError(f"Файл не найден: {csv_path}")

        media_root = Path(settings.MEDIA_ROOT)
        products_dir = media_root / "products"
        products_dir.mkdir(parents=True, exist_ok=True)

        rows = self._load_csv(csv_path, only_sku=options["sku"])
        min_imgs = options["min_imgs"]
        max_imgs = options["max_imgs"]
        delay = options["delay"]
        force = options["force"]
        limit = options["limit"]

        ok = skip = fail = 0

        for i, row in enumerate(rows):
            if limit and i >= limit:
                break

            sku = row["sku"]
            nm_str = row.get("wb_nm_id", "").strip()
            notes = row.get("notes", "").lower()

            if not nm_str or "skip" in notes:
                self.stdout.write(f"[{sku}] пропущен (нет nm_id или notes=skip)")
                skip += 1
                continue

            try:
                nm_id = int(nm_str)
            except ValueError:
                self.stderr.write(self.style.ERROR(f"[{sku}] некорректный nm_id: {nm_str!r}"))
                fail += 1
                continue

            self.stdout.write(f"[{sku}] nm_id={nm_id} …")

            # Проверяем, есть ли уже скачанные файлы
            existing = sorted(products_dir.glob(f"{sku}-*.jpg"))
            if existing and not force:
                self.stdout.write(f"  уже скачано {len(existing)} файлов, пропускаем (--force чтобы перезаписать)")
                skip += 1
                continue

            # Находим CDN basket + количество фото через card.json
            basket, available = find_basket_and_photo_count(nm_id)
            if basket is None:
                self.stderr.write(self.style.ERROR(f"  CDN basket не найден для nm_id={nm_id}"))
                fail += 1
                continue
            self.stdout.write(f"  basket={basket:02d} photo_count={available}")

            if available < min_imgs:
                self.stderr.write(self.style.WARNING(
                    f"  только {available} картинок (нужно {min_imgs}), пропускаем"
                ))
                fail += 1
                continue

            n_to_dl = min(available, max_imgs)
            self.stdout.write(f"  доступно {available}, скачиваем {n_to_dl}")

            # Скачиваем
            saved_paths = []
            for n in range(1, n_to_dl + 1):
                out_path = products_dir / f"{sku}-{n}.jpg"
                if out_path.exists() and not force:
                    saved_paths.append(out_path)
                    continue
                try:
                    jpeg = download_image(nm_id, basket, n)
                    out_path.write_bytes(jpeg)
                    saved_paths.append(out_path)
                    self.stdout.write(f"  ✓ {out_path.name} ({len(jpeg):,} bytes)")
                    time.sleep(delay)
                except Exception as e:
                    self.stderr.write(self.style.ERROR(f"  ✗ img {n}: {e}"))

            if len(saved_paths) < min_imgs:
                self.stderr.write(self.style.ERROR(
                    f"  скачано только {len(saved_paths)} из {min_imgs} нужных, пропускаем запись в БД"
                ))
                fail += 1
                continue

            # Сохраняем в БД
            try:
                product = Product.objects.get(sku=sku)
            except Product.DoesNotExist:
                self.stderr.write(self.style.ERROR(f"  товар {sku} не найден в БД"))
                fail += 1
                continue

            self._save_to_db(product, saved_paths, media_root, force)
            ok += 1

        self.stdout.write(self.style.SUCCESS(
            f"\nГотово. Успешно: {ok}, пропущено: {skip}, ошибок: {fail}."
        ))

    def _load_csv(self, path: Path, only_sku: str | None) -> list[dict]:
        with path.open("r", encoding="utf-8", newline="") as fh:
            rows = list(csv.DictReader(fh))
        if only_sku:
            rows = [r for r in rows if r["sku"] == only_sku]
        return rows

    def _save_to_db(self, product: Product, paths: list[Path], media_root: Path, force: bool):
        """Создаёт ProductImage записи. Первая — primary, остальные по sort_order."""
        with django.db.transaction.atomic():
            if force:
                product.images.all().delete()

            for i, path in enumerate(paths):
                relative = str(path.relative_to(media_root))
                is_primary = (i == 0)

                existing_qs = product.images.filter(image=relative)
                if existing_qs.exists():
                    continue

                # Если force=False, просим убрать старый primary перед добавлением нового
                if is_primary and not force:
                    product.images.filter(is_primary=True).update(is_primary=False)

                ProductImage.objects.create(
                    product=product,
                    image=relative,
                    alt_text=product.title,
                    is_primary=is_primary,
                    sort_order=i,
                )
                self.stdout.write(f"  DB ✓ {relative} (primary={is_primary})")
