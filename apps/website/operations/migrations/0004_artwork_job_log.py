from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("operations", "0003_catalogue_review_log")]
    operations = [migrations.AddField(
        model_name="pzwikiartworksyncjob", name="log_output",
        field=models.TextField(blank=True, editable=False),
    )]
