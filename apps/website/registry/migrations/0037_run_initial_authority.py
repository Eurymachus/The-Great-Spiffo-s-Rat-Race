from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("registry", "0036_lock_deployment_exploit_rulings"),
        ("zomboid_catalogue", "0009_seed_tgsrr_geography"),
    ]

    operations = [
        migrations.CreateModel(
            name="RunContractState",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("projection_schema", models.PositiveSmallIntegerField()),
                ("run", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="contract_state", to="registry.challengerun")),
            ],
        ),
        migrations.CreateModel(
            name="RunCharacter",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("starting_forename", models.CharField(blank=True, max_length=160)),
                ("starting_surname", models.CharField(blank=True, max_length=160)),
                ("starting_display_name", models.CharField(blank=True, max_length=160)),
                ("starting_occupation_raw_id", models.CharField(blank=True, max_length=255)),
                ("current_forename", models.CharField(blank=True, max_length=160)),
                ("current_surname", models.CharField(blank=True, max_length=160)),
                ("current_display_name", models.CharField(blank=True, max_length=160)),
                ("current_occupation_raw_id", models.CharField(blank=True, max_length=255)),
                ("selected_traits_partial", models.BooleanField(default=False)),
                ("selected_traits_captured_utc", models.PositiveBigIntegerField(blank=True, null=True)),
                ("current_occupation", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="current_run_characters", to="zomboid_catalogue.catalogueentry")),
                ("run", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="character_record", to="registry.challengerun")),
                ("starting_occupation", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="starting_run_characters", to="zomboid_catalogue.catalogueentry")),
            ],
        ),
        migrations.CreateModel(
            name="RunStartingLocation",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("chosen_region_schema", models.PositiveSmallIntegerField(blank=True, null=True)),
                ("selection_mode", models.CharField(blank=True, choices=[("explicit", "Explicit"), ("random", "Random")], max_length=16)),
                ("resolved_region_raw_id", models.CharField(blank=True, max_length=255)),
                ("chosen_region_captured_utc", models.PositiveBigIntegerField(blank=True, null=True)),
                ("x", models.IntegerField(blank=True, null=True)),
                ("y", models.IntegerField(blank=True, null=True)),
                ("z", models.IntegerField(blank=True, null=True)),
                ("building_def_id", models.CharField(blank=True, max_length=160)),
                ("captured_utc", models.PositiveBigIntegerField(blank=True, null=True)),
                ("world_age_hours", models.FloatField(blank=True, null=True)),
                ("partial", models.BooleanField(default=False)),
                ("registered_kind", models.CharField(blank=True, max_length=24)),
                ("registered_raw_id", models.CharField(blank=True, max_length=255)),
                ("registry_version", models.PositiveIntegerField(blank=True, null=True)),
                ("catalogue_entry", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="observed_run_starting_locations", to="zomboid_catalogue.catalogueentry")),
                ("map_location_version", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="run_starting_locations", to="zomboid_catalogue.maplocationversion")),
                ("resolved_region_catalogue", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="resolved_starting_regions", to="zomboid_catalogue.catalogueentry")),
                ("run", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="starting_location", to="registry.challengerun")),
            ],
        ),
        migrations.CreateModel(
            name="RunCharacterTrait",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("raw_trait_id", models.CharField(max_length=255)),
                ("phase", models.CharField(choices=[("selected_starting", "Selected starting"), ("spawned_starting", "Spawned starting"), ("current", "Current")], max_length=24)),
                ("position", models.PositiveIntegerField(default=0)),
                ("catalogue_entry", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="run_character_traits", to="zomboid_catalogue.catalogueentry")),
                ("character", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="traits", to="registry.runcharacter")),
            ],
            options={"ordering": ("phase", "position", "raw_trait_id")},
        ),
        migrations.AddConstraint(
            model_name="runcharactertrait",
            constraint=models.UniqueConstraint(fields=("character", "phase", "raw_trait_id"), name="unique_run_character_trait_phase"),
        ),
    ]
