from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("pages", "0033_add_real_hours_raced_metric"),
    ]

    operations = [
        migrations.AddField(
            model_name="pagesection",
            name="vertical_padding",
            field=models.CharField(
                choices=[
                    ("standard", "Standard"),
                    ("compact", "Compact"),
                    ("none", "None"),
                ],
                default="standard",
                max_length=16,
            ),
        ),
    ]
