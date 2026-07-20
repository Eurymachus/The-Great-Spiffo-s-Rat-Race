import json

from django.contrib.auth.models import Group
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from registry.models import Participant

from .models import Page, PageBlock, PageSection, SectionItem


class ManagedPageTests(TestCase):
    def setUp(self):
        self.page = Page.objects.get(slug="home")
        self.section = self.page.sections.get(position=0)

    def editor_payload(self, section=None):
        section = section or self.section
        return [{
            "id": section.pk,
            "is_visible": section.is_visible,
            "width": section.width,
            "layout": section.layout,
            "background": section.background,
            "full_bleed_background": section.full_bleed_background,
            "blocks": [{
                "id": block.pk,
                "column": block.column,
                "is_visible": block.is_visible,
                "block_type": block.block_type,
                "content": block.content,
                "audience": block.audience,
                "destination": block.destination,
                "style": block.style,
                "items": [{
                    "id": item.pk,
                    "heading": item.heading,
                    "description": item.description,
                } for item in block.items.all()],
            } for block in section.blocks.all()],
        }]

    def login_superuser(self, email="editor@example.com"):
        user = Participant.objects.create_superuser(
            email=email, nickname="Page Editor", password="test-password-only"
        )
        self.client.force_login(user)

    def post_payload(self, payload, **page_overrides):
        data = {
            "title": self.page.title,
            "content_width": self.page.content_width,
            "navigation_label": self.page.navigation_label,
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
        self.assertContains(response, "A survival challenge measured in stories")
        self.assertContains(response, "Join The Rat Race")
        content = response.content.decode()
        self.assertLess(content.index("Reserve your name"), content.index("Verify your email"))
        self.assertLess(content.index("Verify your email"), content.index("Get race-ready"))

    def test_sections_blocks_and_cards_render_in_order(self):
        second = PageSection.objects.create(page=self.page, position=20)
        heading = PageBlock.objects.create(
            section=second, position=0, block_type=PageBlock.BlockType.HEADING,
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

    def test_hidden_section_is_not_rendered(self):
        hidden_text = self.section.blocks.first().content
        self.section.is_visible = False
        self.section.save(update_fields=("is_visible",))
        self.assertNotContains(self.client.get(reverse("registry:home")), hidden_text)

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
        heading = next(block for block in payload[0]["blocks"] if block["block_type"] == "heading")
        heading["content"] = "Edited main heading"
        card_group = next(block for block in payload[0]["blocks"] if block["block_type"] == "card_group")
        card_group["items"][0]["heading"] = "Edited existing card"
        card_group["items"].append({"heading": "New nested card", "description": "Created here."})
        response = self.post_payload(payload)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(PageBlock.objects.filter(section=self.section, content="Edited main heading").exists())
        self.assertEqual(
            list(self.section.blocks.get(block_type="card_group").items.values_list("heading", flat=True))[-1],
            "New nested card",
        )

    def test_page_editor_saves_responsive_layout(self):
        self.login_superuser("layout-editor@example.com")
        payload = self.editor_payload()
        payload[0].update({"width": "wide", "layout": "two", "background": "alternate", "full_bleed_background": True})
        for index, block in enumerate(payload[0]["blocks"]):
            block["column"] = index % 2
        response = self.post_payload(
            payload, content_width=Page.ContentWidth.WIDE,
            navigation_label="Start", show_in_navigation="on",
        )
        self.assertEqual(response.status_code, 302)
        self.section.refresh_from_db()
        self.assertEqual(self.section.layout, PageSection.Layout.TWO)
        public_response = self.client.get(reverse("registry:home"))
        self.assertContains(public_response, "managed-page-width-wide")
        self.assertContains(public_response, "managed-section-layout-two")

    def test_homepage_cannot_be_deleted_or_have_address_changed(self):
        self.login_superuser("page-admin@example.com")
        response = self.client.get(reverse("admin:pages_page_change", args=(self.page.pk,)))
        self.assertNotContains(response, 'class="deletelink"')
        self.assertContains(response, "field-slug")
        self.assertNotContains(response, 'name="slug"')

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
