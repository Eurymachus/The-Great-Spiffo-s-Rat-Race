from django.db import migrations


TAB_DEFINITIONS = (
    (
        "Getting Started",
        "Starting a survivor and completing the Rat Race.",
        {"starting and winning"},
    ),
    (
        "Fair Play",
        "Mods, exploits, bugs and permitted recovery.",
        {"mods and fair play", "bugs and recovery"},
    ),
    (
        "Evidence",
        "Broadcasts, exports and supporting proof.",
        {"evidence and submissions", "run evidence"},
    ),
    (
        "Endings & Rulings",
        "Death, abandonment, moderation and authority.",
        {"run endings and moderation", "rules authority"},
    ),
)


def present_rules_as_tabs(apps, schema_editor):
    Page = apps.get_model("pages", "Page")
    PageSection = apps.get_model("pages", "PageSection")

    page = Page.objects.filter(public_path="rules").first()
    if not page or page.sections.filter(section_type="tabs").exists():
        return

    sections = list(page.sections.prefetch_related("blocks").order_by("position", "pk"))
    sources_by_tab = []
    for _, _, accepted_names in TAB_DEFINITIONS:
        matches = [section for section in sections if section.name.strip().lower() in accepted_names]
        if not matches:
            return
        sources_by_tab.append(matches)

    tabbed = PageSection.objects.create(
        page=page,
        position=10,
        name="Rules categories",
        is_visible=True,
        section_type="tabs",
        width="inherit",
        layout="four",
        background="surface",
        vertical_padding="standard",
        tabs_config=[
            {
                "label": label,
                "description": description,
                "slug": label.lower().replace(" & ", "-").replace(" ", "-"),
                "is_default": index == 0,
            }
            for index, (label, description, _) in enumerate(TAB_DEFINITIONS)
        ],
    )

    moved_section_ids = set()
    for column, source_sections in enumerate(sources_by_tab):
        position = 0
        for source in source_sections:
            moved_section_ids.add(source.pk)
            for block in source.blocks.order_by("column", "position", "pk"):
                block.section = tabbed
                block.column = column
                block.position = position
                block.save(update_fields=("section", "column", "position"))
                position += 10

    page.sections.filter(pk__in=moved_section_ids).delete()
    page.sections.filter(name="The short version").delete()
    page.sections.filter(section_type="separator").delete()


class Migration(migrations.Migration):
    dependencies = [("pages", "0036_tabbed_content_sections")]

    operations = [
        migrations.RunPython(present_rules_as_tabs, migrations.RunPython.noop),
    ]
