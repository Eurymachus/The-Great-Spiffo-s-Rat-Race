from django.db import migrations


RANKING_CONFIG = {
    "challenge_modes": [],
    "game_builds": [],
    "challenge_builds": [],
    "lifecycles": ["active"],
    "participants": [],
    "selection": "best_per_participant",
    "ordering": "weighted_completion",
    "limit": 100,
    "columns": [
        "participant", "survivor", "build", "progress", "kills",
        "outposts", "skills", "day", "verified",
    ],
    "show_heading": True,
    "heading": "Rat Race leaderboard",
    "introduction": "Each Rat Racer's highest-ranked active survivor, calculated from the latest approved run update.",
    "show_weighting": True,
    "show_build": True,
    "show_details": True,
}


def convert_leaderboard(apps, schema_editor):
    CodeManagedPage = apps.get_model("pages", "CodeManagedPage")
    NavigationItem = apps.get_model("pages", "NavigationItem")
    Page = apps.get_model("pages", "Page")
    PageBlock = apps.get_model("pages", "PageBlock")
    PageSection = apps.get_model("pages", "PageSection")

    page, _ = Page.objects.update_or_create(
        public_path="leaderboard",
        defaults={
            "title": "Current leaderboard",
            "is_published": True,
            "content_width": "wide",
        },
    )
    if not page.slug:
        page.slug = "current-leaderboard"
        page.save(update_fields=("slug",))

    if not PageBlock.objects.filter(
        section__page=page, block_type="ranking_table"
    ).exists():
        section = PageSection.objects.create(
            page=page,
            position=0,
            name="Current challenge rankings",
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
            ranking_config=RANKING_CONFIG,
        )

    code_page = CodeManagedPage.objects.filter(key="leaderboard").first()
    if code_page:
        NavigationItem.objects.filter(code_page=code_page).update(
            page=page, code_page=None
        )
        code_page.delete()


class Migration(migrations.Migration):
    dependencies = [
        ("pages", "0017_pageblock_ranking_config_alter_pageblock_block_type"),
    ]

    operations = [
        migrations.RunPython(convert_leaderboard, migrations.RunPython.noop),
    ]
