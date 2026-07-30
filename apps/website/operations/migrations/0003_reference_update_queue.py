from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("operations", "0002_reference_source_connection_fields"),
    ]

    operations = [
        migrations.RenameField(
            model_name="referenceupdatejob",
            old_name="started_at",
            new_name="requested_at",
        ),
        migrations.AddField(
            model_name="referenceupdatejob",
            name="started_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="referenceupdatejob",
            name="trigger",
            field=models.CharField(
                choices=[("manual", "Manual"), ("scheduled", "Scheduled")],
                default="manual",
                max_length=16,
            ),
        ),
        migrations.AddField(
            model_name="referenceupdatejob",
            name="requested_by",
            field=models.ForeignKey(
                blank=True,
                editable=False,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="+",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AlterField(
            model_name="referenceupdatejob",
            name="status",
            field=models.CharField(
                choices=[
                    ("queued", "Queued"),
                    ("running", "Running"),
                    ("unchanged", "No update available"),
                    ("updated", "Updated"),
                    ("authentication_required", "Authentication required"),
                    ("failed", "Failed"),
                ],
                max_length=32,
            ),
        ),
        migrations.AlterModelOptions(
            name="referenceupdatejob",
            options={"ordering": ("-requested_at", "-pk")},
        ),
        migrations.RunSQL(
            "UPDATE operations_referenceupdatejob "
            "SET started_at = requested_at WHERE started_at IS NULL",
            migrations.RunSQL.noop,
        ),
    ]
