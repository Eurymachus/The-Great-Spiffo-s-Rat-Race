from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("registry", "0026_workshopmod_is_recommended"),
    ]

    operations = [
        migrations.AddField(
            model_name="workshopmod",
            name="reviewed_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="workshopmod",
            name="reviewed_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="reviewed_workshop_mods",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
