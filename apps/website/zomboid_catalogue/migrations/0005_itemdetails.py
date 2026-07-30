from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("zomboid_catalogue", "0004_remove_catalogueentry_category_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="ItemDetails",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "pz_item_type",
                    models.CharField(
                        blank=True,
                        help_text="The exact Project Zomboid ItemType value.",
                        max_length=120,
                    ),
                ),
                (
                    "display_category",
                    models.CharField(
                        blank=True,
                        help_text="The exact Project Zomboid DisplayCategory value.",
                        max_length=120,
                    ),
                ),
                (
                    "tags",
                    models.JSONField(
                        blank=True,
                        default=list,
                        help_text="Exact Project Zomboid item tags.",
                    ),
                ),
                (
                    "capabilities",
                    models.JSONField(
                        blank=True,
                        default=list,
                        help_text="Deterministic capabilities derived from Project Zomboid fields, such as weapon, tool, literature, book, or magazine.",
                    ),
                ),
                (
                    "weapon_categories",
                    models.JSONField(
                        blank=True,
                        default=list,
                        help_text="Exact Project Zomboid weapon category identifiers.",
                    ),
                ),
                (
                    "weapon_skill",
                    models.CharField(
                        blank=True,
                        help_text="Skill deterministically resolved from the weapon category.",
                        max_length=120,
                    ),
                ),
                ("weight", models.FloatField(blank=True, null=True)),
                (
                    "raw_properties",
                    models.JSONField(
                        blank=True,
                        default=dict,
                        help_text="The complete parsed Project Zomboid item definition.",
                    ),
                ),
                (
                    "entry",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="item_details",
                        to="zomboid_catalogue.catalogueentry",
                    ),
                ),
            ],
            options={
                "verbose_name": "item details",
                "verbose_name_plural": "item details",
            },
        ),
    ]
