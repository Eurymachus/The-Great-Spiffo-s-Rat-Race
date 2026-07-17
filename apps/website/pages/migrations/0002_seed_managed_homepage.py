from django.db import migrations


DEFAULTS = {
    "small_heading": "Welcome to The Rat Race",
    "main_heading": (
        "A survival challenge measured in stories, statistics and stubbornness."
    ),
    "introduction": (
        "The Great Spiffo's Rat Race is a long-form Project Zomboid challenge. "
        "Create your participant account now and you will be ready when the live "
        "challenge platform opens."
    ),
    "visitor_primary_button": "Join The Rat Race",
    "visitor_secondary_link": "I already have an account",
    "signed_in_button": "Go to your account",
}

DEFAULT_ITEMS = (
    (
        "Reserve your name",
        "Choose the nickname other Rat Racers will know you by.",
    ),
    (
        "Verify your email",
        "Confirm the address used to secure your participant account.",
    ),
    (
        "Get race-ready",
        "Your account will be waiting for run updates when mod integration opens.",
    ),
)


def seed_homepage(apps, schema_editor):
    Page = apps.get_model("pages", "Page")
    PageSection = apps.get_model("pages", "PageSection")
    SectionItem = apps.get_model("pages", "SectionItem")
    SiteBranding = apps.get_model("branding", "SiteBranding")

    branding = SiteBranding.objects.filter(pk=1).first()
    section_values = dict(DEFAULTS)
    items = list(DEFAULT_ITEMS)
    if branding:
        section_values = {
            "small_heading": branding.homepage_small_heading,
            "main_heading": branding.homepage_main_heading,
            "introduction": branding.homepage_introduction,
            "visitor_primary_button": branding.homepage_primary_button,
            "visitor_secondary_link": branding.homepage_secondary_link,
            "signed_in_button": branding.homepage_account_button,
        }
        items = [
            (branding.join_step_1_heading, branding.join_step_1_description),
            (branding.join_step_2_heading, branding.join_step_2_description),
            (branding.join_step_3_heading, branding.join_step_3_description),
        ]

    page, _ = Page.objects.get_or_create(
        slug="home", defaults={"title": "Homepage", "is_published": True}
    )
    section, _ = PageSection.objects.update_or_create(
        page=page,
        position=0,
        defaults={
            "section_type": "introduction",
            "is_visible": True,
            **section_values,
        },
    )
    for position, (heading, description) in enumerate(items, start=1):
        SectionItem.objects.update_or_create(
            section=section,
            position=position,
            defaults={"heading": heading, "description": description},
        )


class Migration(migrations.Migration):
    dependencies = [
        ("branding", "0008_sitebranding_homepage_account_button_and_more"),
        ("pages", "0001_initial"),
    ]

    operations = [migrations.RunPython(seed_homepage, migrations.RunPython.noop)]
