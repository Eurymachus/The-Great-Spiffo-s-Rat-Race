from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("pages", "0039_create_exploits_page"),
    ]

    operations = [
        migrations.AddField(
            model_name="pagesection",
            name="tabs_orientation",
            field=models.CharField(
                choices=[("horizontal", "Horizontal"), ("vertical", "Vertical")],
                default="horizontal",
                max_length=16,
            ),
        ),
    ]
