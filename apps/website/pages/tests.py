from django.contrib.auth.models import Group
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
import json

from registry.models import Participant

from .models import Page, PageSection, SectionItem


class ManagedPageTests(TestCase):
    def setUp(self):
        self.page = Page.objects.get(slug="home")
        self.section = self.page.sections.get(position=0)

    def test_seeded_homepage_preserves_existing_content_and_order(self):
        response = self.client.get(reverse("registry:home"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "A survival challenge measured in stories")
        self.assertContains(response, "Join The Rat Race")
        content = response.content.decode()
        self.assertLess(content.index("Reserve your name"), content.index("Verify your email"))
        self.assertLess(content.index("Verify your email"), content.index("Get race-ready"))

    def test_sections_and_items_are_rendered_in_configured_order(self):
        second = PageSection.objects.create(
            page=self.page,
            section_type=PageSection.SectionType.STEPS,
            position=20,
            small_heading="More information",
            main_heading="What happens next",
        )
        SectionItem.objects.create(
            section=second,
            position=2,
            heading="Second configured item",
            description="Second description.",
        )
        SectionItem.objects.create(
            section=second,
            position=1,
            heading="First configured item",
            description="First description.",
        )

        response = self.client.get(reverse("registry:home"))
        content = response.content.decode()

        self.assertContains(response, "What happens next")
        self.assertLess(
            content.index("First configured item"),
            content.index("Second configured item"),
        )

    def test_hidden_section_is_not_rendered(self):
        self.section.is_visible = False
        self.section.save(update_fields=("is_visible",))

        response = self.client.get(reverse("registry:home"))

        self.assertNotContains(response, self.section.main_heading)

    def test_branding_administrator_can_edit_pages_but_not_participants(self):
        call_command("bootstrap_roles", verbosity=0)
        editor = Participant.objects.create_user(
            email="content-editor@example.com",
            nickname="Content Editor",
            password="test-password-only",
            is_active=True,
            status=Participant.Status.VERIFIED,
        )
        editor.groups.add(Group.objects.get(name="Branding Administrator"))
        self.client.force_login(editor)

        page_response = self.client.get(
            reverse("admin:pages_page_change", args=(self.page.pk,))
        )
        participant_response = self.client.get(
            reverse("admin:registry_participant_changelist")
        )

        self.assertEqual(page_response.status_code, 200)
        self.assertContains(page_response, "Page sections")
        self.assertContains(page_response, "data-page-editor")
        self.assertContains(page_response, "page_editor.js")
        self.assertEqual(participant_response.status_code, 403)

    def test_page_editor_saves_sections_and_cards_together(self):
        superuser = Participant.objects.create_superuser(
            email="nested-editor@example.com",
            nickname="Nested Editor",
            password="test-password-only",
        )
        self.client.force_login(superuser)
        existing_item = self.section.items.first()
        payload = [
            {
                "id": self.section.pk,
                "section_type": "introduction",
                "is_visible": True,
                "small_heading": "Edited small heading",
                "main_heading": "Edited main heading",
                "introduction": "Edited introduction.",
                "visitor_primary_button": "Edited join button",
                "visitor_secondary_link": "Edited login link",
                "signed_in_button": "Edited account button",
                "items": [
                    {
                        "id": existing_item.pk,
                        "heading": "Edited existing card",
                        "description": "Edited existing description.",
                    },
                    {
                        "heading": "New nested card",
                        "description": "Created on the page editor.",
                    },
                ],
            }
        ]

        response = self.client.post(
            reverse("admin:pages_page_change", args=(self.page.pk,)),
            {
                "title": self.page.title,
                "content_width": Page.ContentWidth.STANDARD,
                "navigation_label": "",
                "is_published": "on",
                "page_builder_data": json.dumps(payload),
                "_save": "Save",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.section.refresh_from_db()
        self.assertEqual(self.section.main_heading, "Edited main heading")
        self.assertEqual(
            list(self.section.items.values_list("heading", flat=True)),
            ["Edited existing card", "New nested card"],
        )

    def test_page_editor_saves_responsive_page_and_section_layout(self):
        superuser = Participant.objects.create_superuser(
            email="layout-editor@example.com",
            nickname="Layout Editor",
            password="test-password-only",
        )
        self.client.force_login(superuser)
        payload = [
            {
                "id": self.section.pk,
                "section_type": "introduction",
                "is_visible": True,
                "width": "wide",
                "layout": "two",
                "background": "alternate",
                "full_bleed_background": True,
                "small_heading": self.section.small_heading,
                "main_heading": self.section.main_heading,
                "introduction": self.section.introduction,
                "visitor_primary_button": self.section.visitor_primary_button,
                "visitor_secondary_link": self.section.visitor_secondary_link,
                "signed_in_button": self.section.signed_in_button,
                "items": [],
            }
        ]

        response = self.client.post(
            reverse("admin:pages_page_change", args=(self.page.pk,)),
            {
                "title": self.page.title,
                "content_width": Page.ContentWidth.WIDE,
                "navigation_label": "Start",
                "show_in_navigation": "on",
                "is_published": "on",
                "page_builder_data": json.dumps(payload),
                "_save": "Save",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.page.refresh_from_db()
        self.section.refresh_from_db()
        self.assertEqual(self.page.content_width, Page.ContentWidth.WIDE)
        self.assertEqual(self.page.navigation_label, "Start")
        self.assertTrue(self.page.show_in_navigation)
        self.assertEqual(self.section.width, PageSection.Width.WIDE)
        self.assertEqual(self.section.layout, PageSection.Layout.TWO)
        self.assertEqual(self.section.background, PageSection.Background.ALTERNATE)
        self.assertTrue(self.section.full_bleed_background)

        public_response = self.client.get(reverse("registry:home"))
        self.assertContains(public_response, "managed-page-width-wide")
        self.assertContains(public_response, "managed-section-layout-two")

    def test_homepage_cannot_be_deleted_or_have_its_address_changed(self):
        superuser = Participant.objects.create_superuser(
            email="page-admin@example.com",
            nickname="Page Admin",
            password="test-password-only",
        )
        self.client.force_login(superuser)

        response = self.client.get(
            reverse("admin:pages_page_change", args=(self.page.pk,))
        )

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'class="deletelink"')
        self.assertContains(response, "field-slug")
        self.assertNotContains(response, 'name="slug"')

    def test_page_editor_can_destructively_remove_one_card(self):
        superuser = Participant.objects.create_superuser(
            email="destructive-editor@example.com",
            nickname="Destructive Editor",
            password="test-password-only",
        )
        self.client.force_login(superuser)
        retained_item = self.section.items.first()
        removed_item = SectionItem.objects.create(
            section=self.section,
            position=99,
            heading="Remove immediately",
        )

        response = self.client.post(
            reverse(
                "admin:pages_page_remove_content",
                args=(self.page.pk, "card", removed_item.pk),
            )
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(SectionItem.objects.filter(pk=removed_item.pk).exists())
        self.assertTrue(SectionItem.objects.filter(pk=retained_item.pk).exists())

    def test_removing_a_section_also_removes_its_nested_cards(self):
        superuser = Participant.objects.create_superuser(
            email="section-remover@example.com",
            nickname="Section Remover",
            password="test-password-only",
        )
        self.client.force_login(superuser)
        section_id = self.section.pk
        item_ids = list(self.section.items.values_list("pk", flat=True))

        response = self.client.post(
            reverse(
                "admin:pages_page_remove_content",
                args=(self.page.pk, "section", section_id),
            )
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(PageSection.objects.filter(pk=section_id).exists())
        self.assertFalse(SectionItem.objects.filter(pk__in=item_ids).exists())
