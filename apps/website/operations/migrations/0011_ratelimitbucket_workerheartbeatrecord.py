from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("operations", "0010_pzwikiartworksyncjob_unavailable_artwork"),
    ]

    operations = [
        migrations.CreateModel(
            name="RateLimitBucket",
            fields=[
                ("key", models.CharField(max_length=96, primary_key=True, serialize=False)),
                ("attempts", models.PositiveIntegerField(default=0)),
                ("expires_at", models.DateTimeField(db_index=True)),
            ],
            options={
                "verbose_name": "operational rate-limit bucket",
                "verbose_name_plural": "operational rate-limit buckets",
            },
        ),
        migrations.CreateModel(
            name="WorkerHeartbeatRecord",
            fields=[
                ("key", models.CharField(max_length=64, primary_key=True, serialize=False)),
                ("worker_id", models.CharField(max_length=64)),
                ("release_id", models.CharField(max_length=128)),
                ("process_id", models.PositiveIntegerField()),
                ("recorded_at", models.DateTimeField()),
            ],
            options={
                "verbose_name": "worker heartbeat",
                "verbose_name_plural": "worker heartbeats",
            },
        ),
    ]
