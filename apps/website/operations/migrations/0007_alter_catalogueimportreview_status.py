from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("operations", "0006_catalogueimportreview_wiki_icon_status"),
    ]

    operations = [
        migrations.AlterField(
            model_name="catalogueimportreview",
            name="status",
            field=models.CharField(
                choices=[
                    ("queued", "Queued"),
                    ("generating", "Generating"),
                    ("ready", "Ready for review"),
                    ("approved", "Approved"),
                    ("reverted", "Reverted"),
                    ("rejected", "Rejected"),
                    ("stale", "Source changed"),
                    ("failed", "Failed"),
                ],
                default="queued",
                max_length=16,
            ),
        ),
    ]
