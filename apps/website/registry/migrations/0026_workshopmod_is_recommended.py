from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("registry", "0025_workshopmod_unstable_provenance"),
    ]

    operations = [
        migrations.AddField(
            model_name="workshopmod",
            name="is_recommended",
            field=models.BooleanField(
                default=False,
                help_text="Feature this Allowed mod in the public Recommended section.",
            ),
        ),
        migrations.AddConstraint(
            model_name="workshopmod",
            constraint=models.CheckConstraint(
                condition=models.Q(is_recommended=False) | models.Q(ruling="allowed"),
                name="recommended_workshop_mod_is_allowed",
            ),
        ),
    ]
