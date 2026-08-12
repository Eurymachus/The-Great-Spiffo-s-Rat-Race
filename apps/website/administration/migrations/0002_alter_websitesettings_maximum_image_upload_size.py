from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("administration", "0001_initial")]

    operations = [
        migrations.AlterField(
            model_name="websitesettings",
            name="maximum_image_upload_size",
            field=models.PositiveSmallIntegerField(
                default=10,
                help_text="The largest individual image accepted by the media library, from 1 to 100 MB.",
                validators=[MinValueValidator(1), MaxValueValidator(100)],
                verbose_name="maximum image upload size (MB)",
            ),
        ),
    ]
