from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("pages", "0009_pageblock_card_columns")]

    operations = [
        migrations.AddField(
            model_name="page",
            name="navigation_order",
            field=models.PositiveIntegerField(
                default=0,
                help_text="Lower numbers appear earlier in the public navigation menu.",
            ),
        ),
    ]
