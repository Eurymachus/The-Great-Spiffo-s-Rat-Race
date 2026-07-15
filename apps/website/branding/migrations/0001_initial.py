from django.db import migrations, models


def create_default_branding(apps, schema_editor):
    site_branding = apps.get_model("branding", "SiteBranding")
    site_branding.objects.get_or_create(
        pk=1,
        defaults={
            "full_title": "The Great Spiffo's Rat Race",
            "short_title": "The Rat Race",
            "tagline": "The official Rat Race challenge",
            "welcome_message": "Welcome to the Rat Race!",
            "former_participant_label": "Former Rat Racer",
            "disclaimer": "Not affiliated with or endorsed by The Indie Stone.",
        },
    )


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="SiteBranding",
            fields=[
                ("id", models.PositiveSmallIntegerField(default=1, editable=False, primary_key=True, serialize=False)),
                ("full_title", models.CharField(default="The Great Spiffo's Rat Race", max_length=120)),
                ("short_title", models.CharField(default="The Rat Race", max_length=60)),
                ("tagline", models.CharField(default="The official Rat Race challenge", max_length=160)),
                ("welcome_message", models.CharField(default="Welcome to the Rat Race!", max_length=160)),
                ("former_participant_label", models.CharField(default="Former Rat Racer", max_length=60)),
                ("disclaimer", models.CharField(default="Not affiliated with or endorsed by The Indie Stone.", max_length=240)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "site branding",
                "verbose_name_plural": "site branding",
            },
        ),
        migrations.RunPython(create_default_branding, migrations.RunPython.noop),
    ]
