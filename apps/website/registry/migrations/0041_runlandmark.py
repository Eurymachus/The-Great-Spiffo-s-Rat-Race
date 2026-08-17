from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("registry", "0040_rundailyrecord_rundailymetric_and_more")]

    operations = [
        migrations.CreateModel(
            name="RunLandmark",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("raw_location_id", models.CharField(max_length=255)),
                ("registry_version", models.PositiveIntegerField(blank=True, null=True)),
                ("partial", models.BooleanField(default=False)),
                ("first_visit_utc", models.PositiveBigIntegerField(blank=True, null=True)),
                ("first_visit_world_age_hours", models.FloatField(blank=True, null=True)),
                ("building_id", models.CharField(blank=True, max_length=160)),
                ("point_id", models.CharField(blank=True, max_length=160)),
                ("discovery_method", models.CharField(blank=True, max_length=160)),
                ("x", models.IntegerField(blank=True, null=True)),
                ("y", models.IntegerField(blank=True, null=True)),
                ("catalogue_entry", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="run_landmark_records", to="zomboid_catalogue.catalogueentry")),
                ("run", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="authoritative_landmarks", to="registry.challengerun")),
            ],
            options={"ordering": ("raw_location_id",)},
        ),
        migrations.AddConstraint(
            model_name="runlandmark",
            constraint=models.UniqueConstraint(fields=("run", "raw_location_id"), name="unique_run_authoritative_landmark"),
        ),
    ]
