from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("registry", "0029_legacyleaderboardentry_legacyleaderboardclaim"),
    ]

    operations = [
        migrations.AddField(
            model_name="participant",
            name="primary_streaming_account",
            field=models.ForeignKey(
                blank=True,
                help_text="The connected Twitch or YouTube channel shown on public rankings.",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="primary_for_participants",
                to="registry.streamingaccount",
            ),
        ),
    ]
