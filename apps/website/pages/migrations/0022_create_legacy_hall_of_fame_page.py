from django.db import migrations


LEGACY_CONFIG = {
    "source": "legacy_hall_of_fame",
    "challenge_modes": [],
    "game_builds": [],
    "challenge_builds": [],
    "lifecycles": [],
    "participants": [],
    "selection": "all",
    "ordering": "source_rank",
    "limit": 500,
    "columns": ["participant", "progress", "kills", "outposts", "skills", "day"],
    "show_heading": True,
    "eyebrow": "Unstable challenge",
    "heading": "Legacy Hall of Fame",
    "introduction": "The final historical standings from the Unstable Rat Race challenge.",
    "show_weighting": False,
    "show_build": False,
    "show_details": False,
}


def create_legacy_page(apps, schema_editor):
    NavigationItem = apps.get_model("pages", "NavigationItem")
    Page = apps.get_model("pages", "Page")
    PageBlock = apps.get_model("pages", "PageBlock")
    PageSection = apps.get_model("pages", "PageSection")

    page, _ = Page.objects.update_or_create(
        public_path="legacyhalloffame",
        defaults={
            "title": "Legacy Hall of Fame",
            "is_published": True,
            "audience": "everyone",
            "content_width": "wide",
        },
    )
    if not page.slug:
        page.slug = "legacy-hall-of-fame"
        page.save(update_fields=("slug",))
    block = PageBlock.objects.filter(section__page=page, block_type="ranking_table").first()
    if block is None:
        section = PageSection.objects.create(
            page=page,
            position=0,
            name="Legacy rankings",
            is_visible=True,
            width="inherit",
            layout="single",
            background="default",
            full_bleed_background=False,
        )
        PageBlock.objects.create(
            section=section,
            position=0,
            column=0,
            is_visible=True,
            block_type="ranking_table",
            content="",
            ranking_config=LEGACY_CONFIG,
        )
    else:
        block.ranking_config = LEGACY_CONFIG
        block.save(update_fields=("ranking_config",))
    NavigationItem.objects.filter(label="Legacy Hall of Fame").update(page=page, code_page=None)


class Migration(migrations.Migration):
    dependencies = [("pages", "0021_pagesection_separator_fields")]

    operations = [migrations.RunPython(create_legacy_page, migrations.RunPython.noop)]
