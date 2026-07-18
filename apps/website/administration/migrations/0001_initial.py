from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="WebsiteSettings",
            fields=[
                (
                    "id",
                    models.PositiveSmallIntegerField(
                        default=1, editable=False, primary_key=True, serialize=False
                    ),
                ),
                (
                    "maximum_image_upload_size",
                    models.PositiveSmallIntegerField(
                        default=5,
                        help_text="The largest individual image accepted by the media library, from 1 to 100 MB.",
                        validators=[MinValueValidator(1), MaxValueValidator(100)],
                        verbose_name="maximum image upload size (MB)",
                    ),
                ),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "website settings",
                "verbose_name_plural": "website settings",
            },
        ),
    ]
