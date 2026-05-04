from pathlib import Path

from django.conf import settings
from django.core.files import File
from django.core.files.storage import FileSystemStorage, default_storage
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Sync bundled demo media from MEDIA_ROOT to the configured default storage."

    def add_arguments(self, parser):
        parser.add_argument(
            "--overwrite",
            action="store_true",
            help="Replace files that already exist in the target storage.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Print what would be synced without writing anything.",
        )

    def handle(self, *args, **options):
        source_root = Path(settings.MEDIA_ROOT)
        if not source_root.exists():
            raise CommandError(f"MEDIA_ROOT does not exist: {source_root}")

        if self._is_same_local_storage(source_root):
            self.stdout.write(self.style.SUCCESS("Default storage is local MEDIA_ROOT; media sync is not needed."))
            return

        uploaded = skipped = overwritten = 0
        overwrite = options["overwrite"]
        dry_run = options["dry_run"]

        for source_path in sorted(source_root.rglob("*")):
            if not source_path.is_file() or source_path.name.startswith("."):
                continue

            relative_name = source_path.relative_to(source_root).as_posix()
            exists = default_storage.exists(relative_name)

            if exists and not overwrite:
                skipped += 1
                continue

            if dry_run:
                self.stdout.write(f"{'overwrite' if exists else 'upload'} {relative_name}")
                continue

            if exists:
                default_storage.delete(relative_name)
                overwritten += 1
            else:
                uploaded += 1

            with source_path.open("rb") as file_obj:
                default_storage.save(relative_name, File(file_obj))

        if dry_run:
            self.stdout.write(self.style.WARNING("Dry run complete; no files were written."))
            return

        self.stdout.write(
            self.style.SUCCESS(
                f"Media sync complete: uploaded={uploaded}, overwritten={overwritten}, skipped={skipped}."
            )
        )

    @staticmethod
    def _is_same_local_storage(source_root: Path) -> bool:
        if not isinstance(default_storage, FileSystemStorage):
            return False
        storage_location = getattr(default_storage, "location", None)
        if not storage_location:
            return False
        try:
            return Path(storage_location).resolve() == source_root.resolve()
        except OSError:
            return False
