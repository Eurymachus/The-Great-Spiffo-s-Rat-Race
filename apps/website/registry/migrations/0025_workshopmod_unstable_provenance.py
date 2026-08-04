from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("registry", "0024_workshop_mods"),
    ]

    operations = [
        migrations.AddField(
            model_name="workshopmod",
            name="previous_unstable_ruling",
            field=models.CharField(
                choices=[
                    ("allowed", "Allowed"),
                    ("disallowed", "Disallowed"),
                    ("not_reviewed", "Not reviewed"),
                    ("unknown", "Unknown"),
                ],
                default="not_reviewed",
                max_length=16,
            ),
        ),
        migrations.AddField(
            model_name="workshopmod",
            name="unstable_ruling_notes",
            field=models.TextField(blank=True),
        ),
    ]
