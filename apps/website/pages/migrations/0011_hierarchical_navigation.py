from django.db import migrations, models
import django.db.models.deletion


def migrate_paths_and_navigation(apps, schema_editor):
    Page = apps.get_model("pages", "Page")
    NavigationItem = apps.get_model("pages", "NavigationItem")
    for page in Page.objects.all():
        page.public_path = "" if page.slug == "home" else page.slug
        page.save(update_fields=("public_path",))
        if page.slug != "home" and page.show_in_navigation:
            NavigationItem.objects.create(
                label=page.navigation_label or page.title,
                page=page,
                position=page.navigation_order,
                is_visible=True,
            )


class Migration(migrations.Migration):
    dependencies = [("pages", "0010_page_navigation_order")]

    operations = [
        migrations.AddField(
            model_name="page",
            name="public_path",
            field=models.CharField(blank=True, max_length=240, null=True, verbose_name="public address"),
        ),
        migrations.CreateModel(
            name="NavigationItem",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("label", models.CharField(max_length=80)),
                ("position", models.PositiveIntegerField(default=0)),
                ("is_visible", models.BooleanField(default=True)),
                ("page", models.ForeignKey(blank=True, help_text="Optional. Leave empty to create a non-clickable menu heading.", null=True, on_delete=django.db.models.deletion.CASCADE, related_name="navigation_items", to="pages.page")),
                ("parent", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="children", to="pages.navigationitem")),
            ],
            options={"ordering": ("parent_id", "position", "label")},
        ),
        migrations.RunPython(migrate_paths_and_navigation, migrations.RunPython.noop),
        migrations.RemoveField(model_name="page", name="navigation_label"),
        migrations.RemoveField(model_name="page", name="navigation_order"),
        migrations.RemoveField(model_name="page", name="show_in_navigation"),
        migrations.AlterField(
            model_name="page",
            name="public_path",
            field=models.CharField(blank=True, help_text="A root or nested address such as 'gallery' or 'media/gallery'.", max_length=240, unique=True, verbose_name="public address"),
        ),
        migrations.AlterField(
            model_name="page",
            name="slug",
            field=models.SlugField(blank=True, editable=False, help_text="A stable internal identifier retained for legacy links.", max_length=120, unique=True),
        ),
    ]
