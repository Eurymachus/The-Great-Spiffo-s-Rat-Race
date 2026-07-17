from django.contrib.auth.models import Group
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

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
        self.assertContains(page_response, "Introduction and actions")
        self.assertContains(page_response, "Visitor primary button")
        self.assertEqual(participant_response.status_code, 403)

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
