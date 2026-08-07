from django.db import migrations, models


def compact_rules_introduction(apps, schema_editor):
    PageBlock = apps.get_model("pages", "PageBlock")
    PageBlock.objects.filter(
        section__page__public_path="rules",
        section__name="Rules introduction",
        block_type="separator",
    ).update(separator_spacing="minimal", is_visible=True, audience="everyone")


class Migration(migrations.Migration):
    dependencies = [("pages", "0037_present_rules_as_tabs")]

    operations = [
        migrations.AlterField(
            model_name="pageblock",
            name="separator_spacing",
            field=models.CharField(
                choices=[
                    ("minimal", "Minimal"),
                    ("very_small", "Very small"),
                    ("small", "Small"),
                    ("standard", "Standard"),
                    ("large", "Large"),
                ],
                default="standard",
                max_length=12,
            ),
        ),
        migrations.AlterField(
            model_name="pagesection",
            name="separator_spacing",
            field=models.CharField(
                choices=[
                    ("minimal", "Minimal"),
                    ("very_small", "Very small"),
                    ("small", "Small"),
                    ("standard", "Standard"),
                    ("large", "Large"),
                ],
                default="standard",
                max_length=16,
            ),
        ),
        migrations.RunPython(compact_rules_introduction, migrations.RunPython.noop),
    ]
