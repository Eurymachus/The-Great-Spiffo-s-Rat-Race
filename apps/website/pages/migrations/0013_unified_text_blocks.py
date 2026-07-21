from django.db import migrations, models


def migrate_typography_blocks(apps, schema_editor):
    PageBlock = apps.get_model("pages", "PageBlock")
    PageBlock.objects.filter(block_type="small_heading").update(
        block_type="text", text_role="eyebrow"
    )
    PageBlock.objects.filter(block_type="heading").update(
        block_type="text", text_role="heading"
    )


class Migration(migrations.Migration):
    dependencies = [("pages", "0012_pageblock_alignment")]

    operations = [
        migrations.AddField(
            model_name="pageblock",
            name="text_role",
            field=models.CharField(choices=[("eyebrow", "Eyebrow"), ("heading", "Heading"), ("subheading", "Subheading"), ("paragraph", "Paragraph")], default="paragraph", max_length=12),
        ),
        migrations.AddField(
            model_name="pageblock",
            name="text_font",
            field=models.CharField(choices=[("theme", "Theme default"), ("display", "Theme display font"), ("heading", "Theme heading font"), ("body", "Theme body font")], default="theme", max_length=8),
        ),
        migrations.AddField(
            model_name="pageblock",
            name="text_size",
            field=models.CharField(choices=[("small", "Small"), ("standard", "Standard"), ("large", "Large"), ("extra_large", "Extra large")], default="standard", max_length=12),
        ),
        migrations.AddField(
            model_name="pageblock",
            name="text_weight",
            field=models.CharField(choices=[("theme", "Theme default"), ("regular", "Regular"), ("bold", "Bold")], default="theme", max_length=8),
        ),
        migrations.RunPython(migrate_typography_blocks, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="pageblock",
            name="block_type",
            field=models.CharField(choices=[("text", "Text"), ("action", "Button or link"), ("card_group", "Card group"), ("image", "Image"), ("gallery", "Gallery")], max_length=24),
        ),
    ]
