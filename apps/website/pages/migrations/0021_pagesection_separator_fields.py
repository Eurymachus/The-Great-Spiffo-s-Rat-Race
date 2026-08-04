from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("pages", "0020_page_audience")]

    operations = [
        migrations.AddField(
            model_name="pagesection",
            name="section_type",
            field=models.CharField(
                choices=[("content", "Content section"), ("separator", "Separator")],
                default="content",
                max_length=16,
            ),
        ),
        migrations.AddField(
            model_name="pagesection",
            name="separator_style",
            field=models.CharField(
                choices=[("space", "Space only"), ("line", "Subtle line"), ("accent", "Accent line")],
                default="space",
                max_length=16,
            ),
        ),
        migrations.AddField(
            model_name="pagesection",
            name="separator_spacing",
            field=models.CharField(
                choices=[("small", "Small"), ("standard", "Standard"), ("large", "Large")],
                default="standard",
                max_length=16,
            ),
        ),
    ]
