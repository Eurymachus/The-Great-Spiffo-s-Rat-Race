from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("pages", "0035_create_rules_page")]

    operations = [
        migrations.AddField(
            model_name="pagesection",
            name="tabs_config",
            field=models.JSONField(
                blank=True,
                default=list,
                help_text="Managed labels and descriptions for a tabbed section's column panels.",
                verbose_name="tabs",
            ),
        ),
        migrations.AlterField(
            model_name="pagesection",
            name="section_type",
            field=models.CharField(
                choices=[
                    ("content", "Content section"),
                    ("tabs", "Tabbed content"),
                    ("separator", "Separator"),
                ],
                default="content",
                max_length=16,
            ),
        ),
    ]
