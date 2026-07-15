from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("registry", "0003_redaction_workflow"),
    ]

    operations = [
        migrations.RenameField(
            model_name="participant",
            old_name="consented_at",
            new_name="privacy_notice_acknowledged_at",
        ),
    ]
