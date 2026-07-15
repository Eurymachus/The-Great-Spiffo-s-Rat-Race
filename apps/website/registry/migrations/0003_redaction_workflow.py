from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("registry", "0002_participant_deletion_request"),
    ]

    operations = [
        migrations.AddField(
            model_name="participant",
            name="deletion_request_reference",
            field=models.UUIDField(blank=True, editable=False, null=True),
        ),
        migrations.AddField(
            model_name="participant",
            name="is_system_account",
            field=models.BooleanField(default=False),
        ),
        migrations.CreateModel(
            name="AccountClosureRecord",
            fields=[
                (
                    "reference",
                    models.UUIDField(editable=False, primary_key=True, serialize=False),
                ),
                ("requested_at", models.DateTimeField()),
                ("processed_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={"ordering": ("-processed_at",)},
        ),
    ]
