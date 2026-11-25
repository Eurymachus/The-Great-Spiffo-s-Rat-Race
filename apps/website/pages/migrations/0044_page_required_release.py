from django.db import migrations, models


def classify_existing_rr2_pages(apps, schema_editor):
    Page = apps.get_model("pages", "Page")
    Page.objects.using(schema_editor.connection.alias).filter(
        slug__in=("challenge-rules", "current-leaderboard", "hall-of-fame", "exploits"),
    ).update(required_release="rr2")


class Migration(migrations.Migration):
    dependencies = [("pages", "0043_challenge_edition_wording")]
    operations = [
        migrations.AddField(model_name="page", name="required_release", field=models.CharField(
            blank=True, default="", max_length=16,
            choices=[("", "Always available"), ("rr2", "Rat Race 2.0")],
            help_text="Keep this page and its navigation hidden until the selected release is enabled.",
        )),
        migrations.RunPython(classify_existing_rr2_pages, migrations.RunPython.noop),
    ]
