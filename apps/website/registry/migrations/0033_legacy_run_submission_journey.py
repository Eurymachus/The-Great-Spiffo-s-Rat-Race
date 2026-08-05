from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("registry", "0032_remove_legacyleaderboardentry_claimed_participant_and_more")]

    operations = [
        migrations.AddField(model_name="legacyrunsubmission", name="survival_time_input", field=models.CharField(blank=True, max_length=255)),
        migrations.AddField(model_name="legacyrunsubmission", name="survival_time_full", field=models.CharField(blank=True, max_length=32)),
        migrations.AddField(model_name="legacyrunsubmission", name="reports_death", field=models.BooleanField(default=False)),
        migrations.AddField(model_name="legacyrunsubmission", name="evidence_provider", field=models.CharField(blank=True, max_length=16)),
        migrations.AddField(model_name="legacyrunsubmission", name="evidence_media_type", field=models.CharField(blank=True, max_length=12)),
        migrations.AddField(model_name="legacyrunsubmission", name="evidence_media_id", field=models.CharField(blank=True, max_length=255)),
        migrations.AddField(model_name="legacyrunsubmission", name="evidence_url", field=models.URLField(blank=True, max_length=1000)),
        migrations.AddField(model_name="legacyrunsubmission", name="evidence_title", field=models.CharField(blank=True, max_length=500)),
        migrations.AddField(model_name="legacyrunsubmission", name="evidence_start_seconds", field=models.PositiveIntegerField(blank=True, null=True)),
        migrations.AddField(model_name="legacyrunsubmission", name="evidence_end_seconds", field=models.PositiveIntegerField(blank=True, null=True)),
    ]
