from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("registry", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="participant",
            name="deletion_request_note",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="participant",
            name="deletion_requested_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
