from django.db import migrations
from django.db.models import F


def migrate_homepage_feature_image(apps, schema_editor):
    SiteBranding = apps.get_model("branding", "SiteBranding")
    Page = apps.get_model("pages", "Page")
    PageBlock = apps.get_model("pages", "PageBlock")

    branding = SiteBranding.objects.filter(pk=1).first()
    page = Page.objects.filter(slug="home").first()
    section = page.sections.order_by("position", "pk").first() if page else None
    if not branding or not section or not branding.enable_homepage_feature_image or not branding.homepage_feature_image_asset_id:
        return

    section.blocks.filter(column=0).update(position=F("position") + 10)
    PageBlock.objects.create(
        section=section,
        position=0,
        column=0,
        is_visible=True,
        block_type="image",
        image_asset_id=branding.homepage_feature_image_asset_id,
        image_alt=branding.homepage_feature_image_alt,
        image_fit=branding.homepage_feature_fit,
        image_height=branding.homepage_feature_height,
        image_custom_height=branding.homepage_feature_custom_height,
        image_position=branding.homepage_feature_position,
    )


class Migration(migrations.Migration):
    dependencies = [
        ("branding", "0012_sitebranding_background_image_brightness_and_more"),
        ("pages", "0006_pageblock_image_alt_pageblock_image_asset_and_more"),
    ]

    operations = [
        migrations.RunPython(migrate_homepage_feature_image, migrations.RunPython.noop),
    ]
