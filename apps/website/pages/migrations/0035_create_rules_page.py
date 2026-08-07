from django.db import migrations


def add_text(PageBlock, section, position, content, role="paragraph", column=0, **extra):
    PageBlock.objects.create(
        section=section,
        position=position,
        column=column,
        is_visible=True,
        block_type="text",
        content=content,
        text_role=role,
        audience="everyone",
        **extra,
    )


def create_rules_page(apps, schema_editor):
    NavigationItem = apps.get_model("pages", "NavigationItem")
    Page = apps.get_model("pages", "Page")
    PageBlock = apps.get_model("pages", "PageBlock")
    PageSection = apps.get_model("pages", "PageSection")
    SectionItem = apps.get_model("pages", "SectionItem")

    page, created = Page.objects.get_or_create(
        public_path="rules",
        defaults={
            "title": "Challenge Rules",
            "slug": "challenge-rules",
            "is_published": True,
            "audience": "everyone",
            "content_width": "wide",
        },
    )

    if created or not page.sections.exists():
        hero = PageSection.objects.create(
            page=page,
            position=0,
            name="Rules introduction",
            is_visible=True,
            width="full",
            layout="single",
            background="alternate_full",
            vertical_padding="compact",
        )
        add_text(
            PageBlock,
            hero,
            0,
            "The Stable Rat Race",
            role="eyebrow",
            alignment="centre",
            text_weight="bold",
        )
        add_text(
            PageBlock,
            hero,
            10,
            "Rules of the Race",
            role="heading",
            alignment="centre",
            text_font="display",
            text_size="extra_large",
            text_weight="bold",
        )
        add_text(
            PageBlock,
            hero,
            20,
            "One survivor. One world. No exploits. Every official result backed by evidence.",
            alignment="centre",
            text_size="large",
        )

        essentials = PageSection.objects.create(
            page=page,
            position=10,
            name="The short version",
            is_visible=True,
            width="inherit",
            layout="single",
            background="surface",
            vertical_padding="standard",
        )
        add_text(PageBlock, essentials, 0, "The short version", role="eyebrow", alignment="centre")
        add_text(
            PageBlock,
            essentials,
            10,
            "Race clean. Race honestly.",
            role="heading",
            alignment="centre",
            text_font="display",
            text_size="large",
        )
        cards = PageBlock.objects.create(
            section=essentials,
            position=20,
            column=0,
            is_visible=True,
            block_type="card_group",
            content="",
            card_columns="3",
            audience="everyone",
            alignment="centre",
        )
        for position, label, heading, description in (
            (0, "01", "Ironman", "Use one character and one world for each attempt. Death ends that survivor's run."),
            (10, "02", "Fair play", "Do not use exploits or unapproved advantages. If something feels like a shortcut around the challenge, stop and ask."),
            (20, "03", "Show your work", "Keep the required run export and broadcast evidence. Only approved submissions become official results."),
        ):
            SectionItem.objects.create(
                block=cards,
                card_type="standard",
                position=position,
                heading=heading,
                description=description,
                card_label=label,
                audience="inherit",
            )

        objective = PageSection.objects.create(
            page=page,
            position=20,
            name="Starting and winning",
            is_visible=True,
            width="inherit",
            layout="two",
            background="surface",
            vertical_padding="standard",
        )
        add_text(PageBlock, objective, 0, "Starting a run", role="heading", column=0)
        add_text(
            PageBlock,
            objective,
            10,
            "Start through the official Great Spiffo's Rat Race challenge mode. You may choose any occupation and any valid combination of character traits. Each attempt uses one survivor in one world. You may begin another attempt after a run ends, subject to the active-run limit shown by the website.",
            column=0,
        )
        add_text(PageBlock, objective, 0, "Winning the Rat Race", role="heading", column=1)
        add_text(
            PageBlock,
            objective,
            10,
            "A winning survivor must reach Level 10 in all 35 player skills, complete all 13 published outpost objectives, and record 1,000,000 zombie kills. The website calculates progress from approved run data. Completing only part of the objective still earns a place in the race, but it is not a win.",
            column=1,
        )

        setup = PageSection.objects.create(
            page=page,
            position=30,
            name="Mods and fair play",
            is_visible=True,
            width="inherit",
            layout="two",
            background="default",
            vertical_padding="compact",
        )
        add_text(PageBlock, setup, 0, "Mods", role="eyebrow", column=0)
        add_text(PageBlock, setup, 10, "Check before you play", role="heading", column=0)
        add_text(
            PageBlock,
            setup,
            20,
            "The Rat Race mod is required. Other mods may be used only when the [Mods catalogue](/mods/) lists them as Allowed or Required. Disallowed, Pending, and unlisted mods cannot be used in an official run. Submit an unlisted mod for review before adding it to your game.",
            column=0,
        )
        add_text(PageBlock, setup, 0, "Fair play", role="eyebrow", column=1)
        add_text(PageBlock, setup, 10, "No exploits", role="heading", column=1)
        add_text(
            PageBlock,
            setup,
            20,
            "Avoid exploits as far as reasonably possible. Do not deliberately duplicate resources, bypass challenge requirements, manipulate recorded statistics, or use another unintended advantage. Public rulings apply consistently to everyone, even when an exploit exists in the base game.",
            column=1,
        )

        evidence = PageSection.objects.create(
            page=page,
            position=40,
            name="Evidence and submissions",
            is_visible=True,
            width="inherit",
            layout="two",
            background="surface",
            vertical_padding="standard",
        )
        add_text(PageBlock, evidence, 0, "Broadcast evidence", role="heading", column=0)
        add_text(
            PageBlock,
            evidence,
            10,
            "Keep a Twitch or YouTube broadcast of the run wherever broadcast evidence is required. Select the relevant broadcast when submitting and add supporting clips when they help a moderator verify a milestone, unusual event, recovery, or death. Evidence must belong to the connected channel on your account.",
            column=0,
        )
        add_text(PageBlock, evidence, 0, "Run exports", role="heading", column=1)
        add_text(
            PageBlock,
            evidence,
            10,
            "Submit the export produced by the current Rat Race mod. The website verifies its integrity and stores each submission unchanged for review. A run becomes official only when its first submission is approved. Later approved submissions advance the official record; pending or declined submissions do not.",
            column=1,
        )

        recovery = PageSection.objects.create(
            page=page,
            position=50,
            name="Bugs and recovery",
            is_visible=True,
            width="standard",
            layout="single",
            background="surface",
            vertical_padding="compact",
        )
        add_text(PageBlock, recovery, 0, "Bugs, debug, and recovery", role="heading")
        add_text(
            PageBlock,
            recovery,
            10,
            "Debug tools are not part of ordinary play. They may be used only to recover from a lethal or run-ending game bug that can be shown not to be player error. Preserve evidence of the incident and the smallest corrective action taken, then disclose it with the submission. A moderator decides whether the recovered run remains valid.",
        )

        endings = PageSection.objects.create(
            page=page,
            position=60,
            name="Run endings and moderation",
            is_visible=True,
            width="inherit",
            layout="two",
            background="default",
            vertical_padding="compact",
        )
        add_text(PageBlock, endings, 0, "Ending a run", role="heading", column=0)
        add_text(
            PageBlock,
            endings,
            10,
            "A survivor death ends the attempt. Submit the final export so the run can be recorded as Deceased. You may instead abandon an active run from your dashboard; abandonment is irreversible and releases that challenge slot. A completed run remains subject to evidence and moderation like any other result.",
            column=0,
        )
        add_text(PageBlock, endings, 0, "Moderation and rulings", role="heading", column=1)
        add_text(
            PageBlock,
            endings,
            10,
            "Moderators review evidence, exports, declared recovery actions, and published rulings. They may approve, decline, or invalidate a result when the evidence does not support it. Ask rules questions publicly in the Discord discussions area so the answer can help every racer. Do not seek private rulings by direct message.",
            column=1,
        )

        final = PageSection.objects.create(
            page=page,
            position=70,
            name="Rules authority",
            is_visible=True,
            width="standard",
            layout="single",
            background="alternate_full",
            vertical_padding="compact",
        )
        add_text(PageBlock, final, 0, "When in doubt, ask before acting.", role="heading", alignment="centre")
        add_text(
            PageBlock,
            final,
            10,
            "The current website rules, mod catalogue, and published team rulings govern official Stable Rat Race runs. Historical Unstable material is preserved for context but does not override the current rules.",
            alignment="centre",
        )

    navigation = NavigationItem.objects.filter(parent__isnull=True, label="Rules").first()
    if navigation:
        navigation.page = page
        navigation.code_page = None
        navigation.is_visible = True
        navigation.audience = "everyone"
        navigation.save(update_fields=("page", "code_page", "is_visible", "audience"))
    else:
        NavigationItem.objects.create(
            label="Rules",
            page=page,
            position=20,
            is_visible=True,
            audience="everyone",
        )


def remove_rules_page(apps, schema_editor):
    Page = apps.get_model("pages", "Page")
    Page.objects.filter(public_path="rules").delete()


class Migration(migrations.Migration):
    dependencies = [("pages", "0034_pagesection_vertical_padding")]

    operations = [migrations.RunPython(create_rules_page, remove_rules_page)]
