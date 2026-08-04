from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("pages", "0019_navigationitem_audience"),
    ]

    operations = [
        migrations.AddField(
            model_name="page",
            name="audience",
            field=models.CharField(
                choices=[
                    ("everyone", "Everyone"),
                    ("visitors", "Signed-out visitors"),
                    ("signed_in", "Signed-in participants"),
                    ("staff", "Staff"),
                ],
                default="everyone",
                help_text="Choose who can open this page directly or see it in navigation.",
                max_length=16,
            ),
        ),
    ]
