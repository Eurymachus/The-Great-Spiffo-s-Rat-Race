import uuid

from django.db import migrations


REDACTED_PARTICIPANT_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


def remove_redacted_system_account(apps, schema_editor):
    participant_model = apps.get_model("registry", "Participant")
    participant_model.objects.filter(id=REDACTED_PARTICIPANT_ID).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("registry", "0004_rename_consented_at_privacy_notice_acknowledged_at"),
    ]

    operations = [
        migrations.RunPython(remove_redacted_system_account, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name="participant",
            name="is_system_account",
        ),
    ]
