from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("operations", "0004_referencesource_decompiled_at_and_more"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]
    operations = [
        migrations.CreateModel(
            name="CatalogueImportReview",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("status", models.CharField(choices=[("queued", "Queued"), ("generating", "Generating"), ("ready", "Ready for review"), ("approved", "Approved"), ("rejected", "Rejected"), ("stale", "Source changed"), ("failed", "Failed")], default="queued", max_length=16)),
                ("game_version", models.CharField(max_length=32)),
                ("installed_build_id", models.CharField(max_length=32)),
                ("decompiled_build_id", models.CharField(max_length=32)),
                ("install_root", models.CharField(max_length=500)),
                ("decompiled_root", models.CharField(max_length=500)),
                ("requested_at", models.DateTimeField(auto_now_add=True)),
                ("started_at", models.DateTimeField(blank=True, null=True)),
                ("finished_at", models.DateTimeField(blank=True, null=True)),
                ("reviewed_at", models.DateTimeField(blank=True, null=True)),
                ("summary", models.TextField(blank=True)),
                ("snapshot", models.JSONField(blank=True, default=list, editable=False)),
                ("diff", models.JSONField(blank=True, default=dict, editable=False)),
                ("requested_by", models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="+", to=settings.AUTH_USER_MODEL)),
                ("reviewed_by", models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="+", to=settings.AUTH_USER_MODEL)),
                ("source", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="catalogue_reviews", to="operations.referencesource")),
            ],
            options={"verbose_name": "catalogue import review", "verbose_name_plural": "catalogue import reviews", "ordering": ("-requested_at", "-pk")},
        ),
    ]
