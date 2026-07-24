import uuid

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("registry", "0011_challengerun_review_reason"),
    ]

    operations = [
        migrations.CreateModel(
            name="StreamingAccount",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("provider", models.CharField(choices=[("twitch", "Twitch"), ("youtube", "YouTube")], max_length=16)),
                ("provider_identity", models.CharField(help_text="The provider's immutable account identifier.", max_length=255)),
                ("channel_identity", models.CharField(help_text="The immutable broadcaster or channel identifier.", max_length=255)),
                ("display_name", models.CharField(max_length=255)),
                ("channel_url", models.URLField(max_length=500)),
                ("granted_scopes", models.JSONField(blank=True, default=list)),
                ("status", models.CharField(choices=[("connected", "Connected"), ("reconnect_required", "Reconnect required"), ("disconnected", "Disconnected")], default="connected", max_length=24)),
                ("connected_at", models.DateTimeField(auto_now_add=True)),
                ("refreshed_at", models.DateTimeField(blank=True, null=True)),
                ("token_expires_at", models.DateTimeField(blank=True, null=True)),
                ("disconnected_at", models.DateTimeField(blank=True, null=True)),
                ("participant", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="streaming_accounts", to="registry.participant")),
            ],
            options={"ordering": ("provider",)},
        ),
        migrations.AddConstraint(
            model_name="streamingaccount",
            constraint=models.UniqueConstraint(fields=("participant", "provider"), name="unique_streaming_provider_per_participant"),
        ),
        migrations.AddConstraint(
            model_name="streamingaccount",
            constraint=models.UniqueConstraint(fields=("provider", "provider_identity"), name="unique_streaming_provider_identity"),
        ),
        migrations.AddConstraint(
            model_name="streamingaccount",
            constraint=models.UniqueConstraint(fields=("provider", "channel_identity"), name="unique_streaming_channel_identity"),
        ),
    ]
