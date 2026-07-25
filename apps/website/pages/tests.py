import json

from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from branding.models import ManagedImage
from config.context_processors import navigation_tree
from registry.models import Participant

from .models import NavigationItem, Page, PageBlock, PageGalleryImage, PageSection, SectionItem


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
                "alignment": block.alignment,
                "text_role": block.text_role,
                "text_font": block.text_font,
                "text_size": block.text_size,
                "text_weight": block.text_weight,
                "audience": block.audience,
                "destination": block.destination,
                "style": block.style,
                "card_columns": block.card_columns,
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
                "gallery_images": [{
                    "image": item.image_id,
                    "alternative_text": item.alternative_text,
                    "caption": item.caption,
                } for item in block.gallery_images.all()],
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
            "public_path": self.page.public_path,
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
        self.assertContains(response, "A survival challenge measured in stories")
        self.assertContains(response, "Join The Rat Race")
        content = response.content.decode()
        self.assertLess(content.index("Reserve your name"), content.index("Verify your email"))
        self.assertLess(content.index("Verify your email"), content.index("Get race-ready"))

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
        card_group = next(block for block in payload[0]["blocks"] if block["block_type"] == "card_group")
        card_group["items"][0]["heading"] = "Edited existing card"
        card_group["items"].append({"heading": "New nested card", "description": "Created here."})
        card_group["card_columns"] = "2"
        response = self.post_payload(payload)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(PageBlock.objects.filter(section=self.section, content="Edited main heading").exists())
        self.assertEqual(
            list(self.section.blocks.get(block_type="card_group").items.values_list("heading", flat=True))[-1],
            "New nested card",
        )
        self.assertEqual(self.section.blocks.get(block_type="card_group").card_columns, "2")
        self.assertContains(self.client.get(reverse("registry:home")), "managed-card-columns-2")

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

    def test_homepage_cannot_be_deleted_or_have_address_changed(self):
        self.login_superuser("page-admin@example.com")
        response = self.client.get(reverse("admin:pages_page_change", args=(self.page.pk,)))
        self.assertNotContains(response, 'class="deletelink"')
        self.assertContains(response, "field-public_path")
        self.assertContains(response, 'name="public_path"')
        self.assertContains(response, 'name="public_path" class="vTextField" maxlength="240" disabled')

    def test_navigation_items_are_managed_separately_from_page_content(self):
        self.login_superuser("navigation-order-editor@example.com")
        second_page = Page.objects.create(
            title="Rules", public_path="rules", is_published=True,
        )
        item = NavigationItem.objects.create(label="Rules", page=second_page, position=5)
        response = self.client.get(reverse("admin:pages_navigationitem_change", args=(item.pk,)))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Rules")

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

        tree = navigation_tree()

        self.assertEqual([node["item"].label for node in tree], ["Useful menu"])
        self.assertEqual([node["item"].label for node in tree[0]["children"]], ["Home link"])
        self.assertTrue(NavigationItem.objects.filter(pk=empty_root.pk).exists())
        self.assertTrue(NavigationItem.objects.filter(pk=empty_child.pk).exists())

    def test_navigation_tree_order_can_be_saved_together(self):
        self.login_superuser("navigation-tree-save@example.com")
        NavigationItem.objects.all().delete()
        media = NavigationItem.objects.create(label="Media", position=0)
        gallery = NavigationItem.objects.create(label="Gallery", position=10)
        rules = NavigationItem.objects.create(label="Rules", position=20)

        response = self.client.post(
            reverse("admin:pages_navigationitem_reorder"),
            data=json.dumps({"items": [
                {"id": media.pk, "parent_id": None, "position": 0, "label": "Media centre", "page_id": None, "is_visible": True},
                {"id": gallery.pk, "parent_id": media.pk, "position": 0, "label": "Gallery", "page_id": None, "is_visible": False},
                {"id": rules.pk, "parent_id": None, "position": 10, "label": "Rules", "page_id": None, "is_visible": True},
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
                {"id": media.pk, "parent_id": gallery.pk, "position": 0, "label": "Media", "page_id": None, "is_visible": True},
                {"id": gallery.pk, "parent_id": media.pk, "position": 0, "label": "Gallery", "page_id": None, "is_visible": True},
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
