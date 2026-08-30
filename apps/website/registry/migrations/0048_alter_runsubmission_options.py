from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("registry", "0047_immutable_submission_preapproval"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="runsubmission",
            options={
                "ordering": ("-submitted_at",),
                "verbose_name_plural": "run reviews",
            },
        ),
    ]
