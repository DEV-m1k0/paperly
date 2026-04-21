"""
Promote an existing user to the «Менеджер» role.

Usage:
    python manage.py make_manager <username_or_email>
    python manage.py make_manager demo
    python manage.py make_manager editor@paperly.ru
    python manage.py make_manager demo --revoke      # remove manager role

The command:
  • finds the user by username or email
  • sets is_staff=True (needed to enter the admin)
  • adds them to the «Менеджер» group (permissions configured in
    shop/migrations/0010_create_manager_group.py)
"""

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand, CommandError


MANAGER_GROUP_NAME = "Менеджер"


class Command(BaseCommand):
    help = "Add or remove the «Менеджер» role for a user by username or email."

    def add_arguments(self, parser):
        parser.add_argument("identifier", help="Username or email of the user.")
        parser.add_argument(
            "--revoke", action="store_true",
            help="Remove the manager role instead of granting it.",
        )

    def handle(self, *args, **options):
        User = get_user_model()
        identifier = options["identifier"].strip()

        user = (
            User.objects.filter(username__iexact=identifier).first()
            or User.objects.filter(email__iexact=identifier).first()
        )
        if not user:
            raise CommandError(f"Пользователь «{identifier}» не найден.")

        try:
            group = Group.objects.get(name=MANAGER_GROUP_NAME)
        except Group.DoesNotExist:
            raise CommandError(
                f"Группа «{MANAGER_GROUP_NAME}» не существует. "
                "Выполните `manage.py migrate` — она создаётся миграцией shop/0010."
            )

        if options["revoke"]:
            user.groups.remove(group)
            # Leave is_staff alone — another group might still need it.
            self.stdout.write(self.style.SUCCESS(
                f"У пользователя «{user.username}» роль «{MANAGER_GROUP_NAME}» снята."
            ))
            return

        if not user.is_staff:
            user.is_staff = True
            user.save(update_fields=["is_staff"])
        user.groups.add(group)

        self.stdout.write(self.style.SUCCESS(
            f"Пользователю «{user.username}» выдана роль «{MANAGER_GROUP_NAME}».\n"
            f"  Вход в админку: /admin/  · is_staff={user.is_staff}\n"
            f"  Может: модерировать отзывы, публиковать блог-посты."
        ))
