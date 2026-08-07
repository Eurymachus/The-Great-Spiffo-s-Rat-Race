import json

from django import forms
from django.core.exceptions import ValidationError

from .models import Page, PageBlock, PageGalleryImage, PageSection, SectionItem


LAYOUT_COLUMNS = {
    PageSection.Layout.SINGLE: 1,
    PageSection.Layout.TWO: 2,
    PageSection.Layout.WIDE_LEFT: 2,
    PageSection.Layout.WIDE_RIGHT: 2,
    PageSection.Layout.THREE: 3,
    PageSection.Layout.FOUR: 4,
}


class PageEditorForm(forms.ModelForm):
    page_builder_data = forms.CharField(widget=forms.HiddenInput)

    class Meta:
        model = Page
        fields = (
            "title", "public_path", "is_published", "audience", "content_width",
            "page_builder_data",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.slug == "home":
            self.fields["public_path"].disabled = True
        else:
            self.fields["public_path"].required = True
        if not self.is_bound and self.instance.pk:
            self.initial["page_builder_data"] = json.dumps([
                {
                    "id": section.pk, "position": section.position,
                    "name": section.name,
                    "is_visible": section.is_visible, "width": section.width,
                    "section_type": section.section_type,
                    "layout": section.layout, "background": section.background,
                    "full_bleed_background": section.full_bleed_background,
                    "vertical_padding": section.vertical_padding,
                    "separator_style": section.separator_style,
                    "separator_spacing": section.separator_spacing,
                    "tabs_config": section.normalised_tabs() if section.section_type == PageSection.SectionType.TABS else [],
                    "blocks": [
                        {
                            "id": block.pk, "position": block.position,
                            "column": block.column, "is_visible": block.is_visible,
                            "block_type": block.block_type, "content": block.content,
                            "alignment": block.alignment,
                            "text_role": block.text_role, "text_font": block.text_font,
                            "text_size": block.text_size, "text_weight": block.text_weight,
                            "audience": block.audience, "destination": block.destination,
                            "style": block.style,
                            "card_columns": block.card_columns,
                            "separator_style": block.separator_style,
                            "separator_spacing": block.separator_spacing,
                            "image_asset": block.image_asset_id,
                            "image_alt": block.image_alt, "image_fit": block.image_fit,
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
                            "gallery_images": [
                                {"id": item.pk, "image": item.image_id,
                                 "alternative_text": item.alternative_text, "caption": item.caption}
                                for item in block.gallery_images.all()
                            ],
                            "items": [
                                {"id": item.pk, "position": item.position,
                                 "heading": item.heading, "description": item.description,
                                 "card_type": item.card_type,
                                 "card_label": item.card_label, "audience": item.audience,
                                 "alt_text": item.alt_text,
                                 "destination_url": item.destination_url}
                                for item in block.items.all()
                            ],
                        }
                        for block in section.blocks.all()
                    ],
                }
                for section in self.instance.sections.prefetch_related("blocks__items", "blocks__gallery_images")
            ])

    def clean_page_builder_data(self):
        try:
            data = json.loads(self.cleaned_data["page_builder_data"])
        except (TypeError, ValueError, json.JSONDecodeError) as exc:
            raise ValidationError("The page content could not be read.") from exc
        if not isinstance(data, list):
            raise ValidationError("Page content must contain a list of sections.")

        section_ids = set(self.instance.sections.values_list("pk", flat=True)) if self.instance.pk else set()
        submitted_section_ids = set()
        page_block_ids = set(
            PageBlock.objects.filter(section__page=self.instance).values_list("pk", flat=True)
        ) if self.instance.pk else set()
        submitted_block_ids = set()
        cleaned = []
        for section_index, raw in enumerate(data):
            if not isinstance(raw, dict):
                raise ValidationError(f"Section {section_index + 1} is invalid.")
            section_id = raw.get("id")
            if section_id is not None:
                if section_id not in section_ids:
                    if PageSection.objects.filter(pk=section_id).exists():
                        raise ValidationError("A section does not belong to this page.")
                    # Preserve a section left in a bound editor after its
                    # database row was deleted during an earlier failed move.
                    section_id = None
                if section_id in submitted_section_ids:
                    raise ValidationError("A page section can appear only once.")
                if section_id is not None:
                    submitted_section_ids.add(section_id)
            section = PageSection(
                page=self.instance, position=section_index * 10,
                name=str(raw.get("name", "Section")).strip() or "Section",
                is_visible=bool(raw.get("is_visible", True)),
                section_type=raw.get("section_type", PageSection.SectionType.CONTENT),
                width=raw.get("width", PageSection.Width.INHERIT),
                layout=raw.get("layout", PageSection.Layout.SINGLE),
                background=raw.get("background", PageSection.Background.DEFAULT),
                full_bleed_background=bool(raw.get("full_bleed_background", False)),
                vertical_padding=raw.get("vertical_padding", PageSection.VerticalPadding.STANDARD),
                separator_style=raw.get("separator_style", PageSection.SeparatorStyle.SPACE),
                separator_spacing=raw.get("separator_spacing", PageSection.SeparatorSpacing.STANDARD),
                tabs_config=raw.get("tabs_config") or [],
            )
            section.full_clean(exclude=("page",))
            if section.section_type == PageSection.SectionType.TABS:
                if section.layout not in (
                    PageSection.Layout.TWO,
                    PageSection.Layout.THREE,
                    PageSection.Layout.FOUR,
                ):
                    raise ValidationError("Tabbed content must contain two, three or four tabs.")
                section.tabs_config = section.normalised_tabs()
            else:
                section.tabs_config = []
            raw_blocks = raw.get("blocks", [])
            if section.section_type == PageSection.SectionType.SEPARATOR and raw_blocks:
                raise ValidationError("Separator sections cannot contain content blocks.")
            column_count = LAYOUT_COLUMNS.get(section.layout, 1)
            blocks = []
            for block_index, raw_block in enumerate(raw_blocks):
                if not isinstance(raw_block, dict):
                    raise ValidationError(f"Block {block_index + 1} in section {section_index + 1} is invalid.")
                block_id = raw_block.get("id")
                if block_id is not None:
                    if block_id not in page_block_ids:
                        if PageBlock.objects.filter(pk=block_id).exists():
                            raise ValidationError("A block does not belong to this page.")
                        # A previously deleted block can remain in a bound editor after
                        # a failed save. Preserve its submitted content as a new block.
                        block_id = None
                    if block_id in submitted_block_ids:
                        raise ValidationError("A content block can appear only once on a page.")
                    if block_id is not None:
                        submitted_block_ids.add(block_id)
                column = int(raw_block.get("column", 0))
                if column < 0 or column >= column_count:
                    raise ValidationError("A block is assigned to a column that is not in its section layout.")
                block = PageBlock(
                    position=block_index * 10, column=column,
                    is_visible=bool(raw_block.get("is_visible", True)),
                    block_type=raw_block.get("block_type", ""),
                    content=str(raw_block.get("content", "")),
                    alignment=raw_block.get("alignment", PageBlock.Alignment.LEFT),
                    text_role=raw_block.get("text_role", PageBlock.TextRole.PARAGRAPH),
                    text_font=raw_block.get("text_font", PageBlock.TextFont.THEME),
                    text_size=raw_block.get("text_size", PageBlock.TextSize.STANDARD),
                    text_weight=raw_block.get("text_weight", PageBlock.TextWeight.THEME),
                    audience=raw_block.get("audience", PageBlock.Audience.EVERYONE),
                    destination=raw_block.get("destination", PageBlock.Destination.NONE),
                    style=raw_block.get("style", PageBlock.Style.DEFAULT),
                    card_columns=raw_block.get("card_columns", PageBlock.CardColumns.AUTO),
                    separator_style=raw_block.get("separator_style", PageBlock.SeparatorStyle.SPACE),
                    separator_spacing=raw_block.get("separator_spacing", PageBlock.SeparatorSpacing.STANDARD),
                    image_asset_id=raw_block.get("image_asset") or None,
                    image_alt=str(raw_block.get("image_alt", "")),
                    image_fit=raw_block.get("image_fit", PageBlock.ImageFit.COVER),
                    image_height=raw_block.get("image_height", PageBlock.ImageHeight.STANDARD),
                    image_custom_height=int(raw_block.get("image_custom_height") or 24),
                    image_position=raw_block.get("image_position", PageBlock.ImagePosition.CENTRE),
                    image_expandable=bool(raw_block.get("image_expandable", False)),
                    gallery_auto_scroll=bool(raw_block.get("gallery_auto_scroll", False)),
                    gallery_scroll_speed=int(raw_block.get("gallery_scroll_speed") or 5),
                    gallery_loop=bool(raw_block.get("gallery_loop", True)),
                    gallery_show_controls=bool(raw_block.get("gallery_show_controls", True)),
                    gallery_show_captions=bool(raw_block.get("gallery_show_captions", True)),
                    gallery_expandable=bool(raw_block.get("gallery_expandable", True)),
                    ranking_config=raw_block.get("ranking_config") or {},
                    community_stats_config=raw_block.get("community_stats_config") or {},
                )
                block.full_clean(exclude=("section",))
                if block.block_type == PageBlock.BlockType.RANKING_TABLE:
                    from registry.models import ChallengeMode, Participant

                    config = block.ranking_config
                    if ChallengeMode.objects.filter(pk__in=config["challenge_modes"]).count() != len(config["challenge_modes"]):
                        raise ValidationError("A selected challenge mode no longer exists.")
                    if Participant.objects.filter(pk__in=config["participants"]).count() != len(config["participants"]):
                        raise ValidationError("A selected participant no longer exists.")
                item_ids = set(SectionItem.objects.filter(block_id=block_id).values_list("pk", flat=True)) if block_id else set()
                items = []
                raw_items = raw_block.get("items", [])
                if not isinstance(raw_items, list):
                    raise ValidationError("Card data must be a list.")
                if block.block_type != PageBlock.BlockType.CARD_GROUP and raw_items:
                    raise ValidationError("Only card blocks can contain cards.")
                for item_index, raw_item in enumerate(raw_items):
                    if not isinstance(raw_item, dict):
                        raise ValidationError("Each card must be an object.")
                    item_id = raw_item.get("id")
                    if item_id is not None and item_id not in item_ids:
                        raise ValidationError("A card does not belong to its card group.")
                    item = SectionItem(
                        position=item_index * 10,
                        heading=str(raw_item.get("heading", "")),
                        description=str(raw_item.get("description", "")),
                        card_type=raw_item.get("card_type", SectionItem.CardType.STANDARD),
                        card_label=str(raw_item.get("card_label", "")),
                        audience=raw_item.get("audience", SectionItem.Audience.INHERIT),
                        alt_text=str(raw_item.get("alt_text", "")),
                        destination_url=str(raw_item.get("destination_url", "")),
                    )
                    item.full_clean(exclude=("block",))
                    if (
                        block.block_type == PageBlock.BlockType.CARD_GROUP
                        and item.card_type == SectionItem.CardType.LINKED
                    ):
                        from .destinations import is_safe_managed_destination

                        if not item.alt_text.strip():
                            raise ValidationError("Each call-to-action card needs alt text.")
                        if not is_safe_managed_destination(item.destination_url):
                            raise ValidationError(
                                "Each call-to-action card needs a site-relative path or an https address."
                            )
                    items.append({"id": item_id, "model": item})
                gallery_images = []
                raw_gallery_images = raw_block.get("gallery_images", [])
                if not isinstance(raw_gallery_images, list):
                    raise ValidationError("Gallery images must be a list.")
                if block.block_type != PageBlock.BlockType.GALLERY and raw_gallery_images:
                    raise ValidationError("Only gallery blocks can contain gallery images.")
                if block.block_type == PageBlock.BlockType.GALLERY and not raw_gallery_images:
                    raise ValidationError("Choose at least one gallery image.")
                seen_images = set()
                for gallery_index, raw_image in enumerate(raw_gallery_images):
                    image_id = int(raw_image.get("image") or 0)
                    if not image_id or image_id in seen_images:
                        raise ValidationError("Each gallery image must be selected once.")
                    seen_images.add(image_id)
                    gallery_image = PageGalleryImage(
                        position=gallery_index * 10, image_id=image_id,
                        alternative_text=str(raw_image.get("alternative_text", "")),
                        caption=str(raw_image.get("caption", "")),
                    )
                    gallery_image.full_clean(exclude=("block",))
                    gallery_images.append(gallery_image)
                blocks.append({"id": block_id, "model": block, "items": items, "gallery_images": gallery_images})
            cleaned.append({"id": section_id, "model": section, "blocks": blocks})
        return cleaned
