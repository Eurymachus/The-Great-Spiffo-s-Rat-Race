from django.db import migrations, models


ALT_TEXT_BY_HEADING = {
    "Enter the Rat Race": "Sign up to enter the Rat Race",
    "Check Your Mods": "View the Rat Race mod rulings",
    "Follow the Competition": "View the Rat Race rankings",
}


def improve_homepage_alt_text(apps, schema_editor):
    SectionItem = apps.get_model("pages", "SectionItem")
    for heading, alt_text in ALT_TEXT_BY_HEADING.items():
        SectionItem.objects.filter(
            block__section__page__slug="home",
            block__block_type="cta_cards",
            heading=heading,
        ).update(alt_text=alt_text)


class Migration(migrations.Migration):
    dependencies = [
        ("pages", "0024_alternate_full_width_surface"),
    ]

    operations = [
        migrations.RenameField(
            model_name="sectionitem",
            old_name="button_label",
            new_name="alt_text",
        ),
        migrations.AlterField(
            model_name="sectionitem",
            name="alt_text",
            field=models.CharField(
                blank=True,
                help_text="Accessible text describing where the linked card leads.",
                max_length=160,
            ),
        ),
        migrations.RunPython(improve_homepage_alt_text, migrations.RunPython.noop),
    ]
