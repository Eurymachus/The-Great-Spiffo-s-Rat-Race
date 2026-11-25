from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("registry", "0083_account_retention")]
    operations = [
        migrations.AddField(model_name="legacyrun", name="identity_removed", field=models.BooleanField(default=False, editable=False)),
        migrations.AddConstraint(model_name="legacyrun", constraint=models.CheckConstraint(
            condition=models.Q(identity_removed=False) | models.Q(claimed_participant__isnull=True),
            name="removed_legacy_identity_has_no_owner",
        )),
        migrations.AddField(model_name="legacydataimport", name="redacted_at", field=models.DateTimeField(blank=True, editable=False, null=True)),
    ]
