from django.db import migrations, models
import django.db.models.deletion


def create_reference_source(apps, schema_editor):
    ReferenceSource = apps.get_model("operations", "ReferenceSource")
    ReferenceSource.objects.get_or_create(
        app_id=108600, defaults={"name": "Project Zomboid"}
    )


class Migration(migrations.Migration):
    initial = True
    dependencies = []
    operations = [
        migrations.CreateModel(
            name="ReferenceSource",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(default="Project Zomboid", max_length=80)),
                ("app_id", models.PositiveIntegerField(default=108600, editable=False)),
                ("authentication_status", models.CharField(choices=[("not_configured", "Not configured"), ("authentication_required", "Authentication required"), ("authenticated", "Authenticated"), ("error", "Error")], default="not_configured", editable=False, max_length=32)),
                ("installed_build_id", models.CharField(blank=True, editable=False, max_length=32)),
                ("last_checked_at", models.DateTimeField(blank=True, editable=False, null=True)),
                ("last_updated_at", models.DateTimeField(blank=True, editable=False, null=True)),
                ("last_error", models.TextField(blank=True, editable=False)),
            ],
            options={"verbose_name": "Project Zomboid reference source", "verbose_name_plural": "Project Zomboid reference source"},
        ),
        migrations.CreateModel(
            name="ReferenceUpdateJob",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("status", models.CharField(choices=[("running", "Running"), ("unchanged", "No update available"), ("updated", "Updated"), ("authentication_required", "Authentication required"), ("failed", "Failed")], max_length=32)),
                ("previous_build_id", models.CharField(blank=True, max_length=32)),
                ("installed_build_id", models.CharField(blank=True, max_length=32)),
                ("started_at", models.DateTimeField(auto_now_add=True)),
                ("finished_at", models.DateTimeField(blank=True, null=True)),
                ("summary", models.TextField(blank=True)),
                ("source", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="jobs", to="operations.referencesource")),
            ],
            options={"ordering": ("-started_at", "-pk")},
        ),
        migrations.RunPython(create_reference_source, migrations.RunPython.noop),
    ]
