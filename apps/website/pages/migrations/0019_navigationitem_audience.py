from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("pages", "0018_convert_leaderboard_to_managed_page"),
    ]

    operations = [
        migrations.AddField(
            model_name="navigationitem",
            name="audience",
            field=models.CharField(
                choices=[
                    ("everyone", "Everyone"),
                    ("visitors", "Signed-out visitors"),
                    ("signed_in", "Signed-in participants"),
                    ("staff", "Staff"),
                ],
                default="everyone",
                help_text="Choose who can see this navigation item and its nested branch.",
                max_length=16,
            ),
        ),
    ]
