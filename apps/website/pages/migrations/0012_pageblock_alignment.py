from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("pages", "0011_hierarchical_navigation")]

    operations = [
        migrations.AddField(
            model_name="pageblock",
            name="alignment",
            field=models.CharField(
                choices=[("left", "Left"), ("centre", "Centre"), ("right", "Right")],
                default="left",
                max_length=8,
            ),
        ),
    ]
