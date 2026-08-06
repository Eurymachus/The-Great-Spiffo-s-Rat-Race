from django.db import migrations


def bound_non_alternate_surfaces(apps, schema_editor):
    PageSection = apps.get_model("pages", "PageSection")
    PageSection.objects.exclude(background="alternate").update(
        full_bleed_background=False,
    )


class Migration(migrations.Migration):

    dependencies = [
        ("pages", "0029_remove_pageblock_card_style_sectionitem_card_type"),
    ]

    operations = [
        migrations.RunPython(bound_non_alternate_surfaces, migrations.RunPython.noop),
    ]
