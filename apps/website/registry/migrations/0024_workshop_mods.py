from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def seed_required_mod(apps, schema_editor):
    WorkshopMod = apps.get_model("registry", "WorkshopMod")
    WorkshopMod.objects.update_or_create(
        workshop_id="3554864233",
        defaults={
            "title": "The Great Spiffo's Rat Race",
            "steam_url": "https://steamcommunity.com/sharedfiles/filedetails/?id=3554864233",
            "ruling": "required",
            "public_rationale": "Required for official Rat Race challenge runs.",
        },
    )


class Migration(migrations.Migration):
    dependencies = [
        ("registry", "0023_starting_challenge_evidence"),
    ]

    operations = [
        migrations.CreateModel(
            name="WorkshopMod",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("workshop_id", models.CharField(max_length=20, unique=True)),
                ("title", models.CharField(max_length=255)),
                ("steam_url", models.URLField(max_length=500)),
                ("preview_url", models.URLField(blank=True, max_length=1000)),
                ("creator_steam_id", models.CharField(blank=True, max_length=32)),
                ("ruling", models.CharField(choices=[("required", "Required"), ("allowed", "Allowed"), ("disallowed", "Disallowed"), ("pending", "Pending review")], db_index=True, default="pending", max_length=16)),
                ("public_rationale", models.TextField(blank=True)),
                ("submission_reason", models.TextField(blank=True)),
                ("steam_checked_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("submitted_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="submitted_workshop_mods", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "verbose_name": "Workshop mod",
                "verbose_name_plural": "Workshop mods",
                "ordering": ("title", "workshop_id"),
            },
        ),
        migrations.RunPython(seed_required_mod, migrations.RunPython.noop),
    ]
