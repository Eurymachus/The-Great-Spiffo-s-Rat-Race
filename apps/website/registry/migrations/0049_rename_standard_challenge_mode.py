from django.db import migrations


def rename_standard_mode(apps, schema_editor):
    ChallengeMode = apps.get_model("registry", "ChallengeMode")
    ChallengeMode.objects.filter(
        key="TGSRR",
        display_name="TGSRR - Standard",
    ).update(display_name="TGSRR")


def restore_standard_mode_name(apps, schema_editor):
    ChallengeMode = apps.get_model("registry", "ChallengeMode")
    ChallengeMode.objects.filter(
        key="TGSRR",
        display_name="TGSRR",
    ).update(display_name="TGSRR - Standard")


class Migration(migrations.Migration):
    dependencies = [
        ("registry", "0048_alter_runsubmission_options"),
    ]

    operations = [
        migrations.RunPython(rename_standard_mode, restore_standard_mode_name),
    ]
