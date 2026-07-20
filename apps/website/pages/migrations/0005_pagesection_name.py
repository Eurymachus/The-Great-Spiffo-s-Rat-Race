from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("pages", "0004_alter_sectionitem_options_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="pagesection",
            name="name",
            field=models.CharField(default="Section", max_length=120),
        ),
    ]
