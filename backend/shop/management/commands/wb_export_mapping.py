import csv
from pathlib import Path

from django.core.management.base import BaseCommand

from shop.models import Product


class Command(BaseCommand):
    help = "Экспортирует CSV-шаблон для ручного сопоставления SKU → WB nm_id."

    def add_arguments(self, parser):
        parser.add_argument(
            "--output",
            default="wb_mapping.csv",
            help="Путь к выходному CSV-файлу (по умолчанию ./wb_mapping.csv)",
        )

    def handle(self, *args, **options):
        out_path = Path(options["output"]).resolve()

        products = Product.objects.order_by("sku").values_list("sku", "title")

        with out_path.open("w", encoding="utf-8", newline="") as fh:
            writer = csv.writer(fh)
            writer.writerow(["sku", "title", "wb_nm_id", "notes"])
            for sku, title in products:
                writer.writerow([sku, title, "", ""])

        self.stdout.write(self.style.SUCCESS(
            f"Записано {len(products)} строк в {out_path}"
        ))
