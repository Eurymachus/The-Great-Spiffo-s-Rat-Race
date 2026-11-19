from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("operations", "0015_daily_leaderboard")]

    operations = [
        migrations.AddField(
            model_name="dailyleaderboardjob",
            name="force_upload",
            field=models.BooleanField(default=False),
        ),
    ]
