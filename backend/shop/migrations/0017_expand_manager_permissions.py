"""Expand the Manager role for daily admin operations."""

from django.db import migrations


MANAGER_GROUP_NAME = "Менеджер"


MANAGER_PERMISSIONS = [
    ("shop", "order", ["add", "change", "view"]),
    ("shop", "orderitem", ["add", "change", "delete", "view"]),
    ("shop", "orderstatushistory", ["add", "change", "view"]),
    ("shop", "returnrequest", ["change", "view"]),
    ("shop", "returnrequestitem", ["change", "view"]),
    ("shop", "wholesalerequest", ["change", "view"]),
    ("shop", "wholesalepricelist", ["view"]),
    ("shop", "productreview", ["add", "change", "delete", "view"]),
    ("shop", "blogpost", ["add", "change", "delete", "view"]),
    ("shop", "blogcategory", ["add", "change", "delete", "view"]),
    ("shop", "product", ["view"]),
    ("shop", "brand", ["view"]),
    ("shop", "category", ["view"]),
    ("shop", "pickuppoint", ["view"]),
    ("shop", "deliverytariff", ["view"]),
    ("shop", "customerprofile", ["view"]),
    ("shop", "address", ["view"]),
    ("shop", "cart", ["view"]),
    ("shop", "cartitem", ["view"]),
    ("shop", "favorite", ["view"]),
    ("shop", "promocode", ["view"]),
]


def expand_manager_permissions(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")
    ContentType = apps.get_model("contenttypes", "ContentType")

    group, _ = Group.objects.get_or_create(name=MANAGER_GROUP_NAME)
    permissions = []

    for app_label, model_name, actions in MANAGER_PERMISSIONS:
        try:
            content_type = ContentType.objects.get(app_label=app_label, model=model_name)
        except ContentType.DoesNotExist:
            continue

        for action in actions:
            codename = f"{action}_{model_name}"
            try:
                permissions.append(Permission.objects.get(content_type=content_type, codename=codename))
            except Permission.DoesNotExist:
                continue

    group.permissions.add(*permissions)


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("shop", "0016_enrich_blog_posts"),
        ("auth", "0012_alter_user_first_name_max_length"),
        ("contenttypes", "0002_remove_content_type_name"),
    ]

    operations = [
        migrations.RunPython(expand_manager_permissions, reverse_code=noop_reverse),
    ]
