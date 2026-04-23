"""Data migration: create the «Менеджер» auth group and grant it the right
permissions — moderate product reviews, author blog posts/categories, read
products + brands for context.

Re-running migrate is safe: the migration uses get_or_create and the reverse
operation simply deletes the group.
"""

from django.db import migrations


MANAGER_GROUP_NAME = "Менеджер"


# (app_label, model_name, [action1, action2, ...])
MANAGER_PERMISSIONS = [
    # Product reviews — full CRUD so the manager can approve/reject/delete.
    ("shop", "productreview", ["add", "change", "delete", "view"]),
    # Blog — author/edit posts and categories.
    ("shop", "blogpost", ["add", "change", "delete", "view"]),
    ("shop", "blogcategory", ["add", "change", "delete", "view"]),
    # Read-only context: managers often need to look up a product or brand
    # while editing reviews/articles, but should not modify them.
    ("shop", "product", ["view"]),
    ("shop", "brand", ["view"]),
    ("shop", "category", ["view"]),
]


def create_manager_group(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")
    ContentType = apps.get_model("contenttypes", "ContentType")

    group, _ = Group.objects.get_or_create(name=MANAGER_GROUP_NAME)

    permissions_to_assign = []
    for app_label, model_name, actions in MANAGER_PERMISSIONS:
        try:
            ct = ContentType.objects.get(app_label=app_label, model=model_name)
        except ContentType.DoesNotExist:
            continue
        for action in actions:
            codename = f"{action}_{model_name}"
            try:
                perm = Permission.objects.get(content_type=ct, codename=codename)
            except Permission.DoesNotExist:
                continue
            permissions_to_assign.append(perm)

    group.permissions.set(permissions_to_assign)


def delete_manager_group(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Group.objects.filter(name=MANAGER_GROUP_NAME).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("shop", "0009_promocode_is_public"),
        ("auth", "0012_alter_user_first_name_max_length"),
        ("contenttypes", "0002_remove_content_type_name"),
    ]

    operations = [
        migrations.RunPython(create_manager_group, reverse_code=delete_manager_group),
    ]
