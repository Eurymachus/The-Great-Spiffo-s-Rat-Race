from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("registry", "0080_death_thermal_evidence")]

    operations = [
        migrations.AddField(
            model_name="rundeathsummary", name="sleeping_pills_taken",
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="rundeathsummary", name="intoxication_at_death",
            field=models.FloatField(blank=True, null=True),
        ),
    ]
