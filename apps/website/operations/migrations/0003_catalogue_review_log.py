from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("operations", "0002_launch_schema")]

    operations = [
        migrations.AddField(
            model_name="catalogueimportreview",
            name="log_output",
            field=models.TextField(blank=True, editable=False),
        ),
    ]
