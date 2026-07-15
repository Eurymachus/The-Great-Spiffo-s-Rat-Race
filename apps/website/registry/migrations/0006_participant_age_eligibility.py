from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("registry", "0005_remove_redacted_system_account"),
    ]

    operations = [
        migrations.AddField(
            model_name="participant",
            name="age_eligibility_confirmed_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="participant",
            name="age_policy_version",
            field=models.CharField(blank=True, max_length=20),
        ),
    ]
