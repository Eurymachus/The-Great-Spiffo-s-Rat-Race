from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("registry", "0075_merge_reading_cooked_food")]

    operations = [
        migrations.AddField(
            model_name="participant", name="retention_hold",
            field=models.BooleanField(default=False, help_text="Pause deletion for an active dispute or obligation. Record the reason and review date in admin notes."),
        ),
        migrations.CreateModel(
            name="RetentionFileDeletion",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("kind", models.CharField(choices=[("avatar", "Avatar"), ("quarantine", "Quarantine")], max_length=16)),
                ("name", models.CharField(max_length=255)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={"constraints": [models.UniqueConstraint(fields=("kind", "name"), name="unique_retention_file_deletion")]},
        ),
    ]
