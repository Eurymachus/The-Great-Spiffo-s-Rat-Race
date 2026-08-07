import json
from datetime import datetime, timezone

from django.contrib.auth.models import AnonymousUser, Group
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.test import RequestFactory, TestCase
from django.urls import reverse

from branding.models import ManagedImage
from config.context_processors import navigation_tree
from registry.models import ChallengeRun, Participant, RunSubmission

from .models import (
    CodeManagedPage,
    NavigationItem,
    Page,
    PageBlock,
    PageGalleryImage,
    PageSection,
    SectionItem,
)


class ManagedPageTests(TestCase):
    def setUp(self):
        self.page = Page.objects.get(slug="home")
        self.section = self.page.sections.get(position=0)

    def editor_payload(self, section=None):
        section = section or self.section
        return [{
            "id": section.pk,
            "name": section.name,
            "is_visible": section.is_visible,
            "section_type": section.section_type,
            "width": section.width,
            "layout": section.layout,
            "background": section.background,
            "full_bleed_background": section.full_bleed_background,
            "vertical_padding": section.vertical_padding,
            "separator_style": section.separator_style,
            "separator_spacing": section.separator_spacing,
            "tabs_config": section.tabs_config,
            "blocks": [{
                "id": block.pk,
                "column": block.column,
                "is_visible": block.is_visible,
                "block_type": block.block_type,
                "content": block.content,
                "alignment": block.alignment,
                "text_role": block.text_role,
                "text_font": block.text_font,
                "text_size": block.text_size,
                "text_weight": block.text_weight,
                "audience": block.audience,
                "destination": block.destination,
                "style": block.style,
                "card_columns": block.card_columns,
                "separator_style": block.separator_style,
                "separator_spacing": block.separator_spacing,
                "image_asset": block.image_asset_id,
                "image_alt": block.image_alt,
                "image_fit": block.image_fit,
                "image_height": block.image_height,
                "image_custom_height": block.image_custom_height,
                "image_position": block.image_position,
                "image_expandable": block.image_expandable,
                "gallery_auto_scroll": block.gallery_auto_scroll,
                "gallery_scroll_speed": block.gallery_scroll_speed,
                "gallery_loop": block.gallery_loop,
                "gallery_show_controls": block.gallery_show_controls,
                "gallery_show_captions": block.gallery_show_captions,
                "gallery_expandable": block.gallery_expandable,
                "ranking_config": block.ranking_config,
                "community_stats_config": block.community_stats_config,
                "gallery_images": [{
                    "image": item.image_id,
                    "alternative_text": item.alternative_text,
                    "caption": item.caption,
                } for item in block.gallery_images.all()],
                "items": [{
                    "id": item.pk,
                    "heading": item.heading,
                    "description": item.description,
                    "card_type": item.card_type,
                    "card_label": item.card_label,
                    "audience": item.audience,
                    "alt_text": item.alt_text,
                    "destination_url": item.destination_url,
                } for item in block.items.all()],
            } for block in section.blocks.all()],
        }]

    def login_superuser(self, email="editor@example.com"):
        user = Participant.objects.create_superuser(
            email=email, nickname="Page Editor", password="test-password-only"
        )
        self.client.force_login(user)

    def test_seeded_rules_page_is_public_managed_content(self):
        rules = Page.objects.get(public_path="rules")

        response = self.client.get(rules.get_absolute_url())

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Rules of the Race")
        self.assertContains(response, "Getting Started")
        self.assertContains(response, "Endings &amp; Rulings")
        self.assertContains(response, 'data-managed-tabs')
        self.assertContains(response, "1,000,000 zombie kills")
        self.assertContains(response, 'href="/mods/"')
        self.assertTrue(
            NavigationItem.objects.filter(
                label="Rules", page=rules, is_visible=True
            ).exists()
        )

    def post_payload(self, payload, **page_overrides):
        data = {
            "title": self.page.title,
            "public_path": self.page.public_path,
            "audience": self.page.audience,
            "content_width": self.page.content_width,
            "is_published": "on",
            "page_builder_data": json.dumps(payload),
            "_save": "Save",
        }
        data.update(page_overrides)
        return self.client.post(
            reverse("admin:pages_page_change", args=(self.page.pk,)), data
        )

    def test_seeded_homepage_preserves_existing_content_and_order(self):
        response = self.client.get(reverse("registry:home"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Enter the Rat Race")
        self.assertContains(response, "Rats in the Race")
        content = response.content.decode()
        self.assertLess(content.index("Enter the Rat Race"), content.index("Check Your Mods"))
        self.assertLess(content.index("Check Your Mods"), content.index("Follow the Competition"))

    def test_community_statistics_use_only_approved_canonical_runs(self):
        participant = Participant.objects.create_user(
            email="statistics@example.com",
            nickname="Statistics Racer",
            password="test-password-only",
            status=Participant.Status.VERIFIED,
            is_active=True,
        )
        recorded = datetime(2026, 8, 1, 12, 0, tzinfo=timezone.utc)
        run = ChallengeRun.objects.create(
            participant=participant,
            run_id="statistics-approved-run",
            status=ChallengeRun.Status.OFFICIAL,
            lifecycle_status=ChallengeRun.Lifecycle.ACTIVE,
            export_format=3,
            generated_at=recorded,
            current_kills=240,
            event_sequence=1,
            event_hash="a" * 64,
            character_name="Stat Rat",
            latest_events=[{"world_age_hours": 48}],
        )
        submission = RunSubmission.objects.create(
            run=run,
            submitter=participant,
            status=RunSubmission.Status.APPROVED,
            checksum="b" * 64,
            raw_export="approved-statistics-export",
            export_format=3,
            generated_at=recorded,
            current_kills=240,
            event_sequence=1,
            event_hash="a" * 64,
            projection={
                "activeGameplay": {"milliseconds": 7_200_000, "unit": "millisecond"},
                "outposts": [
                    {"id": "one", "complete": True},
                    {"id": "two", "complete": False},
                ],
            },
            reviewed_at=recorded,
        )
        run.approved_submission = submission
        run.save(update_fields=("approved_submission",))

        response = self.client.get(reverse("registry:home"))

        self.assertContains(response, "Rats in the Race")
        self.assertContains(response, "Zombies Eliminated")
        self.assertContains(response, ">240<")
        self.assertContains(response, "Days Endured")
        self.assertContains(response, ">2<")
        self.assertContains(response, "Outposts Claimed")
        self.assertContains(response, ">120.0<")
        self.assertContains(response, "Real Hours Raced")
        self.assertContains(response, ">2.0<")

    def test_call_to_action_cards_render_destinations(self):
        response = self.client.get(reverse("registry:home"))

        self.assertContains(response, 'class="managed-cta-card"', count=3)
        self.assertContains(
            response,
            'href="/signup/#sign-up" aria-label="Sign up to enter the Rat Race"',
        )
        self.assertContains(response, 'href="/mods/"')
        self.assertContains(response, 'href="/leaderboard/"')
        self.assertNotContains(response, "managed-cta-link")

    def test_card_group_can_mix_standard_and_linked_cards(self):
        block = self.section.blocks.get(block_type=PageBlock.BlockType.CARD_GROUP)
        standard_card = block.items.all()[1]
        standard_card.card_type = SectionItem.CardType.STANDARD
        standard_card.save(update_fields=("card_type",))

        response = self.client.get(reverse("registry:home"))

        self.assertContains(response, 'class="managed-cta-card"', count=2)
        self.assertContains(response, "Check Your Mods")
        self.assertNotContains(response, 'href="/mods/"')

    def test_page_editor_saves_manual_call_to_action_card_labels(self):
        self.login_superuser("cta-number-editor@example.com")
        payload = self.editor_payload()
        cards = next(
            block for block in payload[0]["blocks"]
            if block["block_type"] == PageBlock.BlockType.CARD_GROUP
        )
        cards["items"][0]["card_label"] = "JOIN"
        cards["items"][1]["card_label"] = ""

        response = self.post_payload(payload)

        self.assertEqual(response.status_code, 302)
        block = self.section.blocks.get(block_type=PageBlock.BlockType.CARD_GROUP)
        self.assertEqual(block.items.all()[0].card_label, "JOIN")
        self.assertEqual(block.items.all()[1].card_label, "")
        public_response = self.client.get(reverse("registry:home"))
        self.assertContains(public_response, ">JOIN<")

    def test_card_audience_can_inherit_or_override_its_group(self):
        block = self.section.blocks.get(block_type=PageBlock.BlockType.CARD_GROUP)
        block.audience = PageBlock.Audience.VISITORS
        block.save(update_fields=("audience",))
        inherited, participants, hidden = block.items.all()
        participants.audience = SectionItem.Audience.SIGNED_IN
        participants.save(update_fields=("audience",))
        hidden.audience = SectionItem.Audience.HIDDEN
        hidden.save(update_fields=("audience",))

        anonymous_response = self.client.get(reverse("registry:home"))

        self.assertContains(anonymous_response, inherited.heading)
        self.assertNotContains(anonymous_response, participants.heading)
        self.assertNotContains(anonymous_response, hidden.heading)

        participant = Participant.objects.create_user(
            email="card-audience@example.com",
            nickname="Card Audience",
            password="test-password-only",
            status=Participant.Status.VERIFIED,
            is_active=True,
        )
        self.client.force_login(participant)
        signed_in_response = self.client.get(reverse("registry:home"))

        self.assertNotContains(signed_in_response, inherited.heading)
        self.assertContains(signed_in_response, participants.heading)
        self.assertNotContains(signed_in_response, hidden.heading)

    def test_page_editor_saves_community_stat_selection_and_order(self):
        self.login_superuser("statistics-editor@example.com")
        section = self.page.sections.get(name="Community statistics")
        payload = self.editor_payload(section)
        stats = payload[0]["blocks"][0]
        stats["community_stats_config"] = {
            "metrics": ["total_kills", "active_runs"],
            "eyebrow": "Verified challenge data",
            "heading": "The race in numbers",
            "show_heading": True,
        }

        response = self.post_payload(payload)

        self.assertEqual(response.status_code, 302)
        block = PageBlock.objects.get(block_type=PageBlock.BlockType.COMMUNITY_STATS)
        self.assertEqual(
            block.community_stats_config["metrics"],
            ["total_kills", "active_runs"],
        )
        public_response = self.client.get(reverse("registry:home"))
        content = public_response.content.decode()
        self.assertContains(public_response, "Verified challenge data")
        self.assertLess(content.index("Zombies Eliminated"), content.index("Rats in the Race"))

    def test_sections_blocks_and_cards_render_in_order(self):
        second = PageSection.objects.create(page=self.page, position=20)
        heading = PageBlock.objects.create(
            section=second, position=0, block_type=PageBlock.BlockType.TEXT,
            text_role=PageBlock.TextRole.HEADING,
            content="What happens next",
        )
        cards = PageBlock.objects.create(
            section=second, position=10, block_type=PageBlock.BlockType.CARD_GROUP,
        )
        SectionItem.objects.create(block=cards, position=2, heading="Second configured item")
        SectionItem.objects.create(block=cards, position=1, heading="First configured item")
        response = self.client.get(reverse("registry:home"))
        content = response.content.decode()
        self.assertContains(response, heading.content)
        self.assertLess(content.index("First configured item"), content.index("Second configured item"))

    def test_image_block_renders_managed_image_and_presentation_settings(self):
        image = ManagedImage.objects.bulk_create([ManagedImage(
            name="Page feature", image="branding/library/page-feature.png",
            original_filename="page-feature.png",
        )])[0]
        PageBlock.objects.create(
            section=self.section, position=99, block_type=PageBlock.BlockType.IMAGE,
            image_asset=image, image_alt="Spiffo at the starting line",
            image_fit=PageBlock.ImageFit.CONTAIN,
            image_height=PageBlock.ImageHeight.CUSTOM,
            image_custom_height=30,
            image_position=PageBlock.ImagePosition.BOTTOM_RIGHT,
            image_expandable=True,
        )

        response = self.client.get(reverse("registry:home"))

        self.assertContains(response, "/media/branding/library/page-feature.png")
        self.assertContains(response, 'alt="Spiffo at the starting line"')
        self.assertContains(response, "managed-image-height-custom")
        self.assertContains(response, "--managed-image-fit:contain")
        self.assertContains(response, "--managed-image-custom-height:30rem")
        self.assertContains(response, "data-image-expand")

    def test_image_expanded_view_is_disabled_by_default(self):
        image = ManagedImage.objects.bulk_create([ManagedImage(
            name="Static image", image="branding/library/static.png",
            original_filename="static.png",
        )])[0]
        block = PageBlock.objects.create(
            section=self.section, position=98, block_type=PageBlock.BlockType.IMAGE,
            image_asset=image, image_alt="Static image",
        )

        self.assertFalse(block.image_expandable)
        self.assertNotContains(
            self.client.get(reverse("registry:home")),
            "data-image-expand",
        )

    def test_page_editor_saves_image_expanded_view_option(self):
        self.login_superuser("image-editor@example.com")
        image = ManagedImage.objects.bulk_create([ManagedImage(
            name="Expandable image", image="branding/library/expandable.png",
            original_filename="expandable.png",
        )])[0]
        payload = self.editor_payload()
        payload[0]["blocks"].append({
            "column": 0, "is_visible": True, "block_type": "image", "content": "",
            "image_asset": image.pk, "image_alt": "Expandable image",
            "image_fit": "contain", "image_height": "natural",
            "image_custom_height": 24, "image_position": "center center",
            "image_expandable": True, "items": [], "gallery_images": [],
        })

        response = self.post_payload(payload)

        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            self.section.blocks.get(image_asset=image).image_expandable
        )

    def test_gallery_block_renders_images_controls_and_expand_option(self):
        images = ManagedImage.objects.bulk_create([
            ManagedImage(name="Race start", image="branding/library/start.png", original_filename="start.png"),
            ManagedImage(name="Race finish", image="branding/library/finish.png", original_filename="finish.png"),
        ])
        gallery = PageBlock.objects.create(
            section=self.section, position=100, block_type=PageBlock.BlockType.GALLERY,
            gallery_auto_scroll=True, gallery_scroll_speed=7, gallery_expandable=True,
        )
        PageGalleryImage.objects.create(block=gallery, image=images[0], position=0, alternative_text="Start", caption="Leaving the line")
        PageGalleryImage.objects.create(block=gallery, image=images[1], position=10, alternative_text="Finish")

        response = self.client.get(reverse("registry:home"))

        self.assertContains(response, 'data-auto-scroll="true"')
        self.assertContains(response, 'data-scroll-speed="7"')
        self.assertContains(response, "/media/branding/library/start.png")
        self.assertContains(response, "Leaving the line")
        self.assertContains(response, "data-gallery-expand")

    def test_page_editor_saves_gallery_selection_and_options(self):
        self.login_superuser("gallery-editor@example.com")
        images = ManagedImage.objects.bulk_create([
            ManagedImage(name="One", image="branding/library/one.png", original_filename="one.png"),
            ManagedImage(name="Two", image="branding/library/two.png", original_filename="two.png"),
        ])
        payload = self.editor_payload()
        payload[0]["blocks"].append({
            "column": 0, "is_visible": True, "block_type": "gallery", "content": "",
            "gallery_auto_scroll": True, "gallery_scroll_speed": 4, "gallery_loop": False,
            "gallery_show_controls": True, "gallery_show_captions": True, "gallery_expandable": True,
            "gallery_images": [
                {"image": images[1].pk, "alternative_text": "Second", "caption": "Second caption"},
                {"image": images[0].pk, "alternative_text": "First", "caption": "First caption"},
            ], "items": [],
        })

        response = self.post_payload(payload)

        self.assertEqual(response.status_code, 302)
        gallery = self.section.blocks.get(block_type=PageBlock.BlockType.GALLERY)
        self.assertTrue(gallery.gallery_auto_scroll)
        self.assertFalse(gallery.gallery_loop)
        self.assertEqual(gallery.gallery_scroll_speed, 4)
        self.assertEqual(list(gallery.gallery_images.values_list("image_id", flat=True)), [images[1].pk, images[0].pk])

    def test_hidden_section_is_not_rendered(self):
        hidden_text = self.section.blocks.first().content
        self.section.is_visible = False
        self.section.save(update_fields=("is_visible",))
        self.assertNotContains(self.client.get(reverse("registry:home")), hidden_text)

    def test_block_can_be_hidden_after_participant_logs_in(self):
        block = PageBlock.objects.create(
            section=self.section, position=101, block_type=PageBlock.BlockType.TEXT,
            content="Visitor-only invitation", audience=PageBlock.Audience.VISITORS,
        )
        self.assertContains(self.client.get(reverse("registry:home")), block.content)
        participant = Participant.objects.create_user(
            email="signed-in@example.com", nickname="Signed In Racer",
            password="test-password-only", is_active=True,
            status=Participant.Status.VERIFIED,
        )
        self.client.force_login(participant)
        self.assertNotContains(self.client.get(reverse("registry:home")), block.content)

    def test_text_blocks_render_safe_inline_links_without_allowing_html(self):
        PageBlock.objects.create(
            section=self.section,
            position=102,
            block_type=PageBlock.BlockType.TEXT,
            content=(
                'Join us in [Discord](https://discord.gg/example). '
                '<strong>Not HTML</strong> '
                '[Unsafe](javascript:alert(1))'
            ),
        )

        response = self.client.get(reverse("registry:home"))

        self.assertContains(response, '<a href="https://discord.gg/example">Discord</a>', html=True)
        self.assertContains(response, '&lt;strong&gt;Not HTML&lt;/strong&gt;')
        self.assertNotContains(response, 'href="javascript:')
        self.assertContains(response, '[Unsafe](javascript:alert(1))')

    def test_branding_administrator_can_edit_pages_but_not_participants(self):
        call_command("bootstrap_roles", verbosity=0)
        editor = Participant.objects.create_user(
            email="content-editor@example.com", nickname="Content Editor",
            password="test-password-only", is_active=True,
            status=Participant.Status.VERIFIED,
        )
        editor.groups.add(Group.objects.get(name="Branding Administrator"))
        self.client.force_login(editor)
        page_response = self.client.get(reverse("admin:pages_page_change", args=(self.page.pk,)))
        self.assertEqual(page_response.status_code, 200)
        self.assertContains(page_response, "Page sections")
        self.assertContains(page_response, "data-page-editor")
        self.assertEqual(self.client.get(reverse("admin:registry_participant_changelist")).status_code, 403)

    def test_page_editor_saves_nested_blocks_and_cards(self):
        self.login_superuser("nested-editor@example.com")
        payload = self.editor_payload()
        heading = next(block for block in payload[0]["blocks"] if block["text_role"] == "heading")
        heading["content"] = "Edited main heading"
        card_group = next(
            block for block in payload[0]["blocks"]
            if block["block_type"] == "card_group"
        )
        card_group["items"][0]["heading"] = "Edited existing card"
        card_group["items"].append({
            "heading": "New nested card", "description": "Created here.",
            "card_type": "linked", "card_label": "NEW", "audience": "signed_in",
            "alt_text": "Open the new card", "destination_url": "/new-card/",
        })
        card_group["card_columns"] = "2"
        response = self.post_payload(payload)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(PageBlock.objects.filter(section=self.section, content="Edited main heading").exists())
        self.assertEqual(
            list(self.section.blocks.get(block_type="card_group").items.values_list("heading", flat=True))[-1],
            "New nested card",
        )
        saved_card = self.section.blocks.get(block_type="card_group").items.last()
        self.assertEqual(saved_card.card_type, SectionItem.CardType.LINKED)
        self.assertEqual(saved_card.card_label, "NEW")
        self.assertEqual(saved_card.audience, SectionItem.Audience.SIGNED_IN)
        self.assertEqual(self.section.blocks.get(block_type="card_group").card_columns, "2")
        self.assertContains(self.client.get(reverse("registry:home")), "managed-card-columns-2")

    def test_page_editor_saves_and_renders_ranking_table_configuration(self):
        self.login_superuser("ranking-editor@example.com")
        payload = self.editor_payload()
        payload[0]["blocks"].append({
            "column": 0,
            "is_visible": True,
            "block_type": "ranking_table",
            "content": "",
            "ranking_config": {
                "challenge_modes": [],
                "game_builds": ["42.12.3"],
                "challenge_builds": [],
                "lifecycles": ["active", "deceased"],
                "participants": [],
                "selection": "latest_per_participant",
                "ordering": "verified_at",
                "limit": 25,
                "columns": ["participant", "survivor", "progress"],
                "show_heading": True,
                "eyebrow": "Current challenge",
                "heading": "Configured ranking",
                "introduction": "A managed ranking table.",
                "show_weighting": False,
                "show_build": False,
                "show_details": True,
            },
            "items": [],
            "gallery_images": [],
        })

        response = self.post_payload(payload)

        self.assertEqual(response.status_code, 302)
        block = self.section.blocks.get(block_type=PageBlock.BlockType.RANKING_TABLE)
        self.assertEqual(block.ranking_config["lifecycles"], ["active", "deceased"])
        self.assertEqual(block.ranking_config["columns"], ["participant", "survivor", "progress"])
        rendered = self.client.get(reverse("registry:home"))
        self.assertContains(rendered, "Configured ranking")
        self.assertContains(rendered, "managed-ranking-table")

    def test_ranking_table_rejects_unsupported_configuration(self):
        block = PageBlock(
            section=self.section,
            position=999,
            block_type=PageBlock.BlockType.RANKING_TABLE,
            ranking_config={"lifecycles": ["unknown"]},
        )
        with self.assertRaises(ValidationError):
            block.full_clean()

    def test_page_editor_saves_existing_section_name(self):
        self.login_superuser("section-name-editor@example.com")
        payload = self.editor_payload()
        payload[0]["name"] = "Main introduction"

        response = self.post_payload(payload)

        self.assertEqual(response.status_code, 302)
        self.section.refresh_from_db()
        self.assertEqual(self.section.name, "Main introduction")

    def test_page_editor_saves_and_renders_block_alignment(self):
        self.login_superuser("alignment-editor@example.com")
        payload = self.editor_payload()
        heading = next(block for block in payload[0]["blocks"] if block["text_role"] == "heading")
        heading["alignment"] = PageBlock.Alignment.CENTRE
        heading["text_font"] = PageBlock.TextFont.DISPLAY
        heading["text_size"] = PageBlock.TextSize.EXTRA_LARGE
        heading["text_weight"] = PageBlock.TextWeight.BOLD

        response = self.post_payload(payload)

        self.assertEqual(response.status_code, 302)
        public_response = self.client.get(reverse("registry:home"))
        self.assertContains(public_response, "managed-block-align-centre")
        self.assertContains(public_response, "managed-text-font-display")
        self.assertContains(public_response, "managed-text-size-extra_large")
        self.assertContains(public_response, "managed-text-weight-bold")

    def test_page_editor_saves_responsive_layout(self):
        self.login_superuser("layout-editor@example.com")
        payload = self.editor_payload()
        payload[0].update({"width": "wide", "layout": "two", "background": "alternate", "full_bleed_background": True})
        for index, block in enumerate(payload[0]["blocks"]):
            block["column"] = index % 2
        response = self.post_payload(
            payload, content_width=Page.ContentWidth.WIDE,
        )
        self.assertEqual(response.status_code, 302)
        self.section.refresh_from_db()
        self.assertEqual(self.section.layout, PageSection.Layout.TWO)
        public_response = self.client.get(reverse("registry:home"))
        self.assertContains(public_response, "managed-page-width-wide")
        self.assertContains(public_response, "managed-section-layout-two")

    def test_alternate_full_width_surface_owns_its_edge_treatment(self):
        self.login_superuser("full-width-surface@example.com")
        payload = self.editor_payload()
        payload[0].update({
            "background": PageSection.Background.ALTERNATE_FULL,
            "full_bleed_background": True,
        })

        response = self.post_payload(payload)

        self.assertEqual(response.status_code, 302)
        self.section.refresh_from_db()
        self.assertEqual(
            self.section.background,
            PageSection.Background.ALTERNATE_FULL,
        )
        self.assertFalse(self.section.full_bleed_background)
        public_response = self.client.get(reverse("registry:home"))
        self.assertContains(
            public_response,
            "managed-section-background-alternate_full",
        )

    def test_page_editor_saves_compact_section_padding(self):
        self.login_superuser("compact-padding@example.com")
        payload = self.editor_payload()
        payload[0]["vertical_padding"] = PageSection.VerticalPadding.COMPACT

        response = self.post_payload(payload)

        self.assertEqual(response.status_code, 302)
        self.section.refresh_from_db()
        self.assertEqual(self.section.vertical_padding, PageSection.VerticalPadding.COMPACT)
        public_response = self.client.get(reverse("registry:home"))
        self.assertContains(public_response, "managed-section-padding-compact")

    def test_community_stats_use_a_responsive_disclosure(self):
        public_response = self.client.get(reverse("registry:home"))

        self.assertContains(public_response, 'class="community-stats-disclosure"')
        self.assertContains(public_response, 'class="community-stats-disclosure" open')
        self.assertContains(public_response, 'class="community-stats-summary">Community Stats</summary>')

    def test_raised_surface_cannot_extend_beyond_its_border(self):
        self.login_superuser("bounded-raised-surface@example.com")
        payload = self.editor_payload()
        payload[0].update({
            "background": PageSection.Background.SURFACE,
            "full_bleed_background": True,
        })

        response = self.post_payload(payload)

        self.assertEqual(response.status_code, 302)
        self.section.refresh_from_db()
        self.assertFalse(self.section.full_bleed_background)

    def test_page_editor_saves_and_renders_separator_section(self):
        self.login_superuser("separator-editor@example.com")
        payload = self.editor_payload()
        payload.append({
            "id": None,
            "name": "Leaderboard separator",
            "is_visible": True,
            "section_type": PageSection.SectionType.SEPARATOR,
            "width": PageSection.Width.WIDE,
            "layout": PageSection.Layout.SINGLE,
            "background": PageSection.Background.DEFAULT,
            "full_bleed_background": False,
            "separator_style": PageSection.SeparatorStyle.ACCENT,
            "separator_spacing": PageSection.SeparatorSpacing.LARGE,
            "blocks": [],
        })

        response = self.post_payload(payload)

        self.assertEqual(response.status_code, 302)
        separator = self.page.sections.get(name="Leaderboard separator")
        self.assertEqual(separator.section_type, PageSection.SectionType.SEPARATOR)
        public_response = self.client.get(reverse("registry:home"))
        self.assertContains(public_response, "managed-separator-style-accent")
        self.assertContains(public_response, "managed-separator-spacing-large")

    def test_page_editor_saves_and_renders_accessible_tabbed_content(self):
        self.login_superuser("tabbed-content-editor@example.com")
        payload = self.editor_payload()
        payload[0].update({
            "name": "Rules categories",
            "section_type": PageSection.SectionType.TABS,
            "layout": PageSection.Layout.THREE,
            "tabs_config": [
                {"label": "Getting Started", "description": "Begin your run.", "is_default": True},
                {"label": "Fair Play", "description": "Play cleanly.", "is_default": False},
                {"label": "Evidence", "description": "Show your work.", "is_default": False},
            ],
        })
        for index, block in enumerate(payload[0]["blocks"]):
            block["column"] = index % 3

        response = self.post_payload(payload)

        self.assertEqual(response.status_code, 302)
        self.section.refresh_from_db()
        self.assertEqual(self.section.section_type, PageSection.SectionType.TABS)
        self.assertEqual(
            [tab["slug"] for tab in self.section.tabs_config],
            ["getting-started", "fair-play", "evidence"],
        )
        public_response = self.client.get(reverse("registry:home"))
        self.assertContains(public_response, 'data-managed-tabs')
        self.assertContains(public_response, 'role="tablist" aria-label="Rules categories"')
        self.assertContains(public_response, 'data-tab-slug="fair-play"')
        self.assertContains(public_response, 'role="tabpanel"')
        self.assertContains(public_response, "Begin your run.")

    def test_tabbed_content_requires_two_to_four_tabs(self):
        self.login_superuser("invalid-tabbed-content@example.com")
        payload = self.editor_payload()
        payload[0].update({
            "section_type": PageSection.SectionType.TABS,
            "layout": PageSection.Layout.SINGLE,
            "tabs_config": [{"label": "Only tab", "is_default": True}],
        })

        response = self.post_payload(payload)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Tabbed content must contain two, three or four tabs.")

    def test_page_editor_saves_and_renders_separator_block(self):
        self.login_superuser("separator-block-editor@example.com")
        payload = self.editor_payload()
        payload[0]["blocks"].append({
            "column": 0,
            "is_visible": True,
            "block_type": PageBlock.BlockType.SEPARATOR,
            "audience": PageBlock.Audience.EVERYONE,
            "separator_style": PageBlock.SeparatorStyle.ACCENT,
            "separator_spacing": PageBlock.SeparatorSpacing.VERY_SMALL,
            "items": [],
            "gallery_images": [],
        })

        response = self.post_payload(payload)

        self.assertEqual(response.status_code, 302)
        separator = self.section.blocks.get(block_type=PageBlock.BlockType.SEPARATOR)
        self.assertEqual(separator.separator_style, PageBlock.SeparatorStyle.ACCENT)
        self.assertEqual(separator.separator_spacing, PageBlock.SeparatorSpacing.VERY_SMALL)
        public_response = self.client.get(reverse("registry:home"))
        self.assertContains(
            public_response,
            "managed-block managed-separator-spacing-very_small managed-separator-style-accent",
        )

    def test_homepage_cannot_be_deleted_or_have_address_changed(self):
        self.login_superuser("page-admin@example.com")
        response = self.client.get(reverse("admin:pages_page_change", args=(self.page.pk,)))
        self.assertNotContains(response, 'class="deletelink"')
        self.assertContains(response, "field-public_path")
        self.assertContains(response, 'name="public_path"')
        self.assertContains(response, 'name="public_path" class="vTextField" maxlength="240" disabled')
        self.assertContains(
            response,
            'class="viewsitelink" target="_blank" rel="noopener"',
        )

    def test_navigation_items_are_managed_separately_from_page_content(self):
        self.login_superuser("navigation-order-editor@example.com")
        second_page = Page.objects.create(
            title="Participant guide", public_path="participant-guide", is_published=True,
        )
        item = NavigationItem.objects.create(label="Guide", page=second_page, position=5)
        response = self.client.get(reverse("admin:pages_navigationitem_change", args=(item.pk,)))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Guide")

    def test_navigation_changelist_uses_the_tree_editor(self):
        self.login_superuser("navigation-tree-editor@example.com")
        NavigationItem.objects.all().delete()
        root = NavigationItem.objects.create(label="Media", position=0)
        NavigationItem.objects.create(label="Gallery", parent=root, position=0)

        response = self.client.get(reverse("admin:pages_navigationitem_changelist"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Navigation structure")
        self.assertContains(response, 'data-navigation-tree')
        self.assertContains(response, 'data-navigation-item', count=2)
        self.assertContains(response, 'data-navigation-label')
        self.assertContains(response, 'data-navigation-page')
        self.assertContains(response, 'data-navigation-save')
        self.assertContains(response, 'data-navigation-destination')
        self.assertContains(response, 'data-tooltip="Menu group')
        self.assertContains(response, 'data-navigation-remove', count=2)
        self.assertContains(response, "Gallery")

    def test_navigation_item_and_its_nested_branch_can_be_removed(self):
        self.login_superuser("navigation-tree-remove@example.com")
        NavigationItem.objects.all().delete()
        root = NavigationItem.objects.create(label="Media", position=0)
        child = NavigationItem.objects.create(label="Gallery", parent=root, position=0)
        NavigationItem.objects.create(label="Screenshots", parent=child, position=0)
        survivor = NavigationItem.objects.create(label="Rules", position=10)

        response = self.client.post(
            reverse("admin:pages_navigationitem_remove", args=(root.pk,)),
        )

        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(response.content, {"removed": True})
        self.assertFalse(NavigationItem.objects.filter(pk=root.pk).exists())
        self.assertFalse(NavigationItem.objects.filter(pk=child.pk).exists())
        self.assertTrue(NavigationItem.objects.filter(pk=survivor.pk).exists())

    def test_child_navigation_item_can_be_added_up_to_three_levels(self):
        self.login_superuser("navigation-tree-child@example.com")
        NavigationItem.objects.all().delete()
        root = NavigationItem.objects.create(label="Media", position=0)
        child = NavigationItem.objects.create(label="Gallery", parent=root, position=0)
        grandchild = NavigationItem.objects.create(label="Screenshots", parent=child, position=0)

        page = self.client.get(reverse("admin:pages_navigationitem_changelist"))
        self.assertContains(page, 'data-navigation-add-child', count=2)

        response = self.client.post(reverse("admin:pages_navigationitem_add_child", args=(root.pk,)))
        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertTrue(result["created"])
        created = NavigationItem.objects.get(pk=result["id"])
        self.assertEqual(created.parent, root)
        self.assertEqual(created.label, "New item")
        self.assertIn("data-navigation-item", result["html"])

        response = self.client.post(reverse("admin:pages_navigationitem_add_child", args=(grandchild.pk,)))
        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.json()["created"])

    def test_empty_menu_groups_are_omitted_from_public_navigation(self):
        NavigationItem.objects.all().delete()
        empty_root = NavigationItem.objects.create(label="Empty menu", position=0)
        empty_child = NavigationItem.objects.create(label="Empty child", parent=empty_root, position=0)
        useful_root = NavigationItem.objects.create(label="Useful menu", position=10)
        NavigationItem.objects.create(label="Home link", page=self.page, parent=useful_root, position=0)

        request = RequestFactory().get("/")
        request.user = AnonymousUser()
        tree = navigation_tree(request)

        self.assertEqual([node["item"].label for node in tree], ["Useful menu"])
        self.assertEqual([node["item"].label for node in tree[0]["children"]], ["Home link"])
        self.assertTrue(NavigationItem.objects.filter(pk=empty_root.pk).exists())
        self.assertTrue(NavigationItem.objects.filter(pk=empty_child.pk).exists())

    def test_navigation_audience_controls_public_tree(self):
        NavigationItem.objects.all().delete()
        everyone = NavigationItem.objects.create(label="Everyone")
        visitors = NavigationItem.objects.create(
            label="Visitors", audience=NavigationItem.Audience.VISITORS
        )
        participants = NavigationItem.objects.create(
            label="Participants", audience=NavigationItem.Audience.SIGNED_IN
        )
        staff = NavigationItem.objects.create(
            label="Staff", audience=NavigationItem.Audience.STAFF
        )
        for item in (everyone, visitors, participants, staff):
            item.page = self.page
            item.save(update_fields=("page",))

        request = RequestFactory().get("/")
        request.user = AnonymousUser()
        self.assertEqual(
            [node["item"].label for node in navigation_tree(request)],
            ["Everyone", "Visitors"],
        )

        participant = Participant.objects.create_user(
            email="menu-audience@example.com",
            nickname="Menu Audience",
            password="test-password-only",
            is_active=True,
            status=Participant.Status.VERIFIED,
        )
        request.user = participant
        self.assertEqual(
            [node["item"].label for node in navigation_tree(request)],
            ["Everyone", "Participants"],
        )
        participant.is_staff = True
        self.assertEqual(
            [node["item"].label for node in navigation_tree(request)],
            ["Everyone", "Participants", "Staff"],
        )

    def test_page_audience_controls_navigation_and_direct_access(self):
        participant_page = Page.objects.create(
            title="Participant guide",
            public_path="participant-guide",
            audience=Page.Audience.SIGNED_IN,
        )
        NavigationItem.objects.create(label="Participant guide", page=participant_page)
        url = participant_page.get_absolute_url()

        self.assertEqual(self.client.get(url).status_code, 404)
        request = RequestFactory().get("/")
        request.user = AnonymousUser()
        self.assertNotIn(
            "Participant guide",
            [node["item"].label for node in navigation_tree(request)],
        )

        participant = Participant.objects.create_user(
            email="managed-page-audience@example.com",
            nickname="Managed Page Audience",
            password="test-password-only",
            is_active=True,
            status=Participant.Status.VERIFIED,
        )
        self.client.force_login(participant)
        self.assertEqual(self.client.get(url).status_code, 200)
        request.user = participant
        self.assertIn(
            "Participant guide",
            [node["item"].label for node in navigation_tree(request)],
        )

        participant_page.audience = Page.Audience.STAFF
        participant_page.save(update_fields=("audience",))
        self.assertEqual(self.client.get(url).status_code, 404)
        participant.is_staff = True
        participant.save(update_fields=("is_staff",))
        self.client.force_login(participant)
        self.assertEqual(self.client.get(url).status_code, 200)

    def test_code_managed_pages_are_seeded_with_honest_availability(self):
        account = CodeManagedPage.objects.get(key="account")
        run_detail = CodeManagedPage.objects.get(key="run-detail")

        self.assertFalse(CodeManagedPage.objects.filter(key="home").exists())
        self.assertFalse(CodeManagedPage.objects.filter(key="leaderboard").exists())
        self.assertTrue(account.is_navigation_target)
        self.assertEqual(account.get_absolute_url(), reverse("registry:account"))
        self.assertEqual(run_detail.availability, CodeManagedPage.Availability.AVAILABLE)
        self.assertFalse(run_detail.is_navigation_target)

    def test_current_leaderboard_is_a_managed_page_with_ranking_block(self):
        leaderboard = Page.objects.get(public_path="leaderboard")

        self.assertTrue(leaderboard.is_published)
        self.assertEqual(leaderboard.get_absolute_url(), reverse("registry:page", kwargs={"page_path": "leaderboard"}))
        ranking = PageBlock.objects.get(
            section__page=leaderboard,
            block_type=PageBlock.BlockType.RANKING_TABLE,
        )
        self.assertEqual(ranking.ranking_config["lifecycles"], ["active"])
        self.assertEqual(ranking.ranking_config["selection"], "best_per_participant")

    def test_code_managed_page_admin_is_a_viewer_without_form_actions(self):
        self.login_superuser("code-page-viewer@example.com")
        page = CodeManagedPage.objects.get(key="account")

        response = self.client.get(
            reverse("admin:pages_codemanagedpage_change", args=(page.pk,))
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "View code-managed page")
        self.assertNotContains(response, 'class="submit-row"')
        self.assertNotContains(response, ">Close<")

    def test_admin_sidebar_renders_collapsible_section_controls(self):
        self.login_superuser("collapsible-admin-sidebar@example.com")

        response = self.client.get(reverse("admin:pages_codemanagedpage_changelist"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "admin-sidebar-section-toggle")
        self.assertContains(response, 'aria-controls="admin-sidebar-section-pages"')
        self.assertContains(response, "admin_sidebar_sections.js")

    def test_navigation_rejects_multiple_or_unavailable_destinations(self):
        account = CodeManagedPage.objects.get(key="account")
        planned_page = CodeManagedPage.objects.get(key="top-ten")

        multiple = NavigationItem(
            label="Invalid", page=self.page, code_page=account
        )
        with self.assertRaises(ValidationError):
            multiple.full_clean()

        unavailable = NavigationItem(label="Soon", code_page=planned_page)
        with self.assertRaises(ValidationError):
            unavailable.full_clean()

    def test_code_managed_navigation_respects_code_enforced_audience(self):
        account = CodeManagedPage.objects.get(key="account")
        NavigationItem.objects.all().delete()
        NavigationItem.objects.create(label="Account", code_page=account)
        request = RequestFactory().get("/")
        request.user = AnonymousUser()

        self.assertEqual(navigation_tree(request), [])

        participant = Participant.objects.create_user(
            email="navigation-audience@example.com",
            nickname="Navigation Audience",
            password="test-password-only",
            is_active=True,
            status=Participant.Status.VERIFIED,
        )
        request.user = participant
        tree = navigation_tree(request)
        self.assertEqual([node["item"].label for node in tree], ["Account"])
        self.assertEqual(tree[0]["url"], reverse("registry:account"))

    def test_code_managed_navigation_highlights_only_the_current_route(self):
        NavigationItem.objects.all().delete()
        leaderboard = Page.objects.get(public_path="leaderboard")
        mods = CodeManagedPage.objects.get(key="mods")
        NavigationItem.objects.create(label="Leaderboard", page=leaderboard)
        NavigationItem.objects.create(label="Mods", code_page=mods)

        response = self.client.get(reverse("registry:leaderboard"))
        menu = response.content.decode().split(
            '<nav class="site-nav"', 1
        )[1].split("</nav>", 1)[0]

        self.assertIn(
            f'href="{leaderboard.get_absolute_url()}" aria-current="page"',
            menu,
        )
        self.assertIn(f'href="{mods.get_absolute_url()}"', menu)
        self.assertNotIn(
            f'href="{mods.get_absolute_url()}" aria-current="page"',
            menu,
        )

    def test_navigation_tree_order_can_be_saved_together(self):
        self.login_superuser("navigation-tree-save@example.com")
        NavigationItem.objects.all().delete()
        media = NavigationItem.objects.create(label="Media", position=0)
        gallery = NavigationItem.objects.create(label="Gallery", position=10)
        rules = NavigationItem.objects.create(label="Rules", position=20)

        response = self.client.post(
            reverse("admin:pages_navigationitem_reorder"),
            data=json.dumps({"items": [
                {"id": media.pk, "parent_id": None, "position": 0, "label": "Media centre", "destination_type": "", "destination_id": None, "is_visible": True},
                {"id": gallery.pk, "parent_id": media.pk, "position": 0, "label": "Gallery", "destination_type": "", "destination_id": None, "is_visible": False},
                {"id": rules.pk, "parent_id": None, "position": 10, "label": "Rules", "destination_type": "", "destination_id": None, "is_visible": True},
            ]}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        gallery.refresh_from_db()
        rules.refresh_from_db()
        self.assertEqual(gallery.parent, media)
        self.assertEqual(gallery.position, 0)
        self.assertFalse(gallery.is_visible)
        media.refresh_from_db()
        self.assertEqual(media.label, "Media centre")
        self.assertEqual(rules.position, 10)

    def test_navigation_tree_save_rejects_cycles(self):
        self.login_superuser("navigation-tree-cycle@example.com")
        NavigationItem.objects.all().delete()
        media = NavigationItem.objects.create(label="Media", position=0)
        gallery = NavigationItem.objects.create(label="Gallery", parent=media, position=0)

        response = self.client.post(
            reverse("admin:pages_navigationitem_reorder"),
            data=json.dumps({"items": [
                {"id": media.pk, "parent_id": gallery.pk, "position": 0, "label": "Media", "destination_type": "", "destination_id": None, "is_visible": True},
                {"id": gallery.pk, "parent_id": media.pk, "position": 0, "label": "Gallery", "destination_type": "", "destination_id": None, "is_visible": True},
            ]}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        media.refresh_from_db()
        self.assertIsNone(media.parent)

    def test_page_addresses_reject_application_routes(self):
        page = Page(title="Not an account page", public_path="account/help")
        with self.assertRaises(ValidationError):
            page.full_clean()

    def test_navigation_is_limited_to_three_levels_and_rejects_cycles(self):
        root = NavigationItem.objects.create(label="Media")
        child = NavigationItem.objects.create(label="Images", parent=root)
        grandchild = NavigationItem.objects.create(label="Screenshots", parent=child)
        too_deep = NavigationItem(label="Archive", parent=grandchild)
        with self.assertRaises(ValidationError):
            too_deep.full_clean()
        root.parent = grandchild
        with self.assertRaises(ValidationError):
            root.full_clean()

    def test_destructive_removal_cascades_within_builder(self):
        self.login_superuser("destructive-editor@example.com")
        card_group = self.section.blocks.get(block_type=PageBlock.BlockType.CARD_GROUP)
        retained = card_group.items.first()
        removed = SectionItem.objects.create(block=card_group, position=99, heading="Remove immediately")
        response = self.client.post(reverse("admin:pages_page_remove_content", args=(self.page.pk, "card", removed.pk)))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(SectionItem.objects.filter(pk=removed.pk).exists())
        self.assertTrue(SectionItem.objects.filter(pk=retained.pk).exists())
        section_id = self.section.pk
        block_ids = list(self.section.blocks.values_list("pk", flat=True))
        response = self.client.post(reverse("admin:pages_page_remove_content", args=(self.page.pk, "section", section_id)))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(PageSection.objects.filter(pk=section_id).exists())
        self.assertFalse(PageBlock.objects.filter(pk__in=block_ids).exists())

    def test_existing_block_can_move_between_sections_atomically(self):
        destination = PageSection.objects.create(
            page=self.page,
            position=99,
            name="Destination",
            layout=PageSection.Layout.SINGLE,
        )
        moved = self.section.blocks.filter(block_type=PageBlock.BlockType.TEXT).first()
        payload = self.editor_payload()
        source_blocks = payload[0]["blocks"]
        moved_payload = next(block for block in source_blocks if block["id"] == moved.pk)
        source_blocks.remove(moved_payload)
        payload.append({
            "id": destination.pk,
            "name": destination.name,
            "is_visible": True,
            "section_type": PageSection.SectionType.CONTENT,
            "width": PageSection.Width.INHERIT,
            "layout": PageSection.Layout.SINGLE,
            "background": PageSection.Background.DEFAULT,
            "full_bleed_background": False,
            "vertical_padding": PageSection.VerticalPadding.STANDARD,
            "separator_style": PageSection.SeparatorStyle.SPACE,
            "separator_spacing": PageSection.SeparatorSpacing.STANDARD,
            "blocks": [{**moved_payload, "column": 0}],
        })

        self.login_superuser("cross-section-editor@example.com")
        response = self.post_payload(payload)

        self.assertEqual(response.status_code, 302)
        moved.refresh_from_db()
        self.assertEqual(moved.section, destination)
        public_response = self.client.get(reverse("registry:home"))
        self.assertContains(public_response, moved.content)

    def test_block_move_survives_removal_of_its_empty_source_section(self):
        source = PageSection.objects.create(
            page=self.page,
            position=98,
            name="Temporary source",
            layout=PageSection.Layout.SINGLE,
        )
        moved = PageBlock.objects.create(
            section=source,
            position=0,
            block_type=PageBlock.BlockType.TEXT,
            content="Moved before its old section is removed",
        )
        payload = self.editor_payload()
        payload[0]["blocks"].append({
            "id": moved.pk,
            "column": 0,
            "is_visible": True,
            "block_type": PageBlock.BlockType.TEXT,
            "content": moved.content,
            "alignment": PageBlock.Alignment.LEFT,
            "text_role": PageBlock.TextRole.PARAGRAPH,
            "text_font": PageBlock.TextFont.THEME,
            "text_size": PageBlock.TextSize.STANDARD,
            "text_weight": PageBlock.TextWeight.THEME,
            "audience": PageBlock.Audience.EVERYONE,
            "destination": PageBlock.Destination.NONE,
            "style": PageBlock.Style.DEFAULT,
            "card_columns": PageBlock.CardColumns.AUTO,
            "separator_style": PageBlock.SeparatorStyle.SPACE,
            "separator_spacing": PageBlock.SeparatorSpacing.STANDARD,
            "image_asset": None,
            "image_alt": "",
            "image_fit": PageBlock.ImageFit.COVER,
            "image_height": PageBlock.ImageHeight.STANDARD,
            "image_custom_height": 24,
            "image_position": PageBlock.ImagePosition.CENTRE,
            "image_expandable": False,
            "gallery_auto_scroll": False,
            "gallery_scroll_speed": 5,
            "gallery_loop": True,
            "gallery_show_controls": True,
            "gallery_show_captions": True,
            "gallery_expandable": True,
            "ranking_config": {},
            "community_stats_config": {},
            "gallery_images": [],
            "items": [],
        })

        self.login_superuser("move-and-remove-editor@example.com")
        response = self.post_payload(payload)

        self.assertEqual(response.status_code, 302)
        moved.refresh_from_db()
        self.assertEqual(moved.section, self.section)
        self.assertFalse(PageSection.objects.filter(pk=source.pk).exists())

    def test_deleted_ghost_block_is_recreated_from_bound_editor_content(self):
        payload = self.editor_payload()
        ghost = payload[0]["blocks"][0]
        deleted_id = ghost["id"]
        PageBlock.objects.filter(pk=deleted_id).delete()
        ghost["content"] = "Recovered from the still-open page editor"

        self.login_superuser("ghost-block-editor@example.com")
        response = self.post_payload(payload)

        self.assertEqual(response.status_code, 302)
        self.assertFalse(PageBlock.objects.filter(pk=deleted_id).exists())
        self.assertTrue(
            self.section.blocks.filter(
                content="Recovered from the still-open page editor"
            ).exists()
        )

    def test_block_id_from_another_page_is_still_rejected(self):
        other_page = Page.objects.create(
            title="Other page", public_path="other-page", is_published=True
        )
        other_section = PageSection.objects.create(page=other_page, name="Other")
        foreign_block = PageBlock.objects.create(
            section=other_section,
            block_type=PageBlock.BlockType.TEXT,
            content="Not available to this editor",
        )
        payload = self.editor_payload()
        payload[0]["blocks"][0]["id"] = foreign_block.pk

        self.login_superuser("foreign-block-editor@example.com")
        response = self.post_payload(payload)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "A block does not belong to this page.")
        foreign_block.refresh_from_db()
        self.assertEqual(foreign_block.section, other_section)

    def test_deleted_ghost_section_is_recreated_from_bound_editor_content(self):
        ghost_section = PageSection.objects.create(
            page=self.page,
            position=90,
            name="Ghost section",
            layout=PageSection.Layout.SINGLE,
        )
        payload = self.editor_payload(ghost_section)
        deleted_id = ghost_section.pk
        ghost_section.delete()
        payload[0]["name"] = "Recovered section"

        self.login_superuser("ghost-section-editor@example.com")
        response = self.post_payload(payload)

        self.assertEqual(response.status_code, 302)
        self.assertFalse(PageSection.objects.filter(pk=deleted_id).exists())
        self.assertTrue(
            self.page.sections.filter(name="Recovered section").exists()
        )

    def test_section_id_from_another_page_is_still_rejected(self):
        other_page = Page.objects.create(
            title="Foreign section page",
            public_path="foreign-section-page",
            is_published=True,
        )
        foreign_section = PageSection.objects.create(
            page=other_page, name="Foreign section"
        )
        payload = self.editor_payload()
        payload[0]["id"] = foreign_section.pk

        self.login_superuser("foreign-section-editor@example.com")
        response = self.post_payload(payload)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "A section does not belong to this page.")
        foreign_section.refresh_from_db()
        self.assertEqual(foreign_section.page, other_page)
