from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="CatalogueEntry",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("kind", models.CharField(choices=[("skill", "Skill"), ("trait", "Trait"), ("item", "Item"), ("recipe", "Recipe"), ("town", "Town"), ("location", "Location"), ("outpost", "Outpost"), ("deliverable", "Deliverable"), ("mod", "Mod")], max_length=24)),
                ("stable_id", models.CharField(help_text="The exact stable identifier exported by Project Zomboid or TGSRR.", max_length=255)),
                ("display_name", models.CharField(max_length=255)),
                ("category", models.CharField(blank=True, max_length=120)),
                ("introduced_in", models.CharField(blank=True, help_text="First supported game version, for example 42.19.", max_length=32)),
                ("removed_in", models.CharField(blank=True, help_text="First game version where this mapping no longer applies.", max_length=32)),
                ("icon_key", models.CharField(blank=True, help_text="Optional static icon key or asset identifier.", max_length=255)),
                ("is_active", models.BooleanField(default=True)),
                ("notes", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "catalogue entry",
                "verbose_name_plural": "catalogue entries",
                "ordering": ("kind", "display_name", "stable_id"),
            },
        ),
        migrations.CreateModel(
            name="CatalogueAlias",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("stable_id", models.CharField(help_text="A legacy or alternate identifier that resolves to this entry.", max_length=255)),
                ("introduced_in", models.CharField(blank=True, max_length=32)),
                ("removed_in", models.CharField(blank=True, max_length=32)),
                ("notes", models.CharField(blank=True, max_length=255)),
                ("entry", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="aliases", to="zomboid_catalogue.catalogueentry")),
            ],
            options={
                "verbose_name": "catalogue alias",
                "verbose_name_plural": "catalogue aliases",
                "ordering": ("stable_id",),
            },
        ),
        migrations.AddConstraint(
            model_name="catalogueentry",
            constraint=models.UniqueConstraint(fields=("kind", "stable_id", "introduced_in"), name="unique_catalogue_entry_version_start"),
        ),
        migrations.AddConstraint(
            model_name="cataloguealias",
            constraint=models.UniqueConstraint(fields=("stable_id", "introduced_in"), name="unique_catalogue_alias_version_start"),
        ),
    ]
