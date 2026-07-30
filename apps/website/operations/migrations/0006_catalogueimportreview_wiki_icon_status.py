from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("operations", "0005_catalogueimportreview"),
    ]

    operations = [
        migrations.AddField(
            model_name="catalogueimportreview",
            name="wiki_icon_status",
            field=models.CharField(
                choices=[
                    ("not_requested", "Not requested"),
                    ("queued", "Queued"),
                    ("running", "Running"),
                    ("complete", "Complete"),
                    ("failed", "Failed"),
                ],
                default="not_requested",
                editable=False,
                max_length=16,
            ),
        ),
        migrations.AddField(
            model_name="catalogueimportreview",
            name="wiki_icon_summary",
            field=models.TextField(blank=True, editable=False),
        ),
    ]
