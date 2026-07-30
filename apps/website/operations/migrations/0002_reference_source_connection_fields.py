from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("operations", "0001_initial")]
    operations = [
        migrations.AddField(
            model_name="referencesource",
            name="account_name",
            field=models.CharField(blank=True, max_length=80),
        ),
        migrations.AddField(
            model_name="referencesource",
            name="authenticated_at",
            field=models.DateTimeField(blank=True, editable=False, null=True),
        ),
        migrations.AddField(
            model_name="referencesource",
            name="install_root",
            field=models.CharField(blank=True, max_length=500),
        ),
        migrations.AddField(
            model_name="referencesource",
            name="steamcmd_path",
            field=models.CharField(blank=True, max_length=500),
        ),
    ]

