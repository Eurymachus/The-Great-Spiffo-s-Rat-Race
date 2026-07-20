import json

from django import forms
from django.core.exceptions import ValidationError

from .models import Page, PageBlock, PageSection, SectionItem


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
            "title", "slug", "is_published", "content_width",
            "navigation_label", "show_in_navigation", "page_builder_data",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.is_bound and self.instance.pk:
            self.initial["page_builder_data"] = json.dumps([
                {
                    "id": section.pk, "position": section.position,
                    "name": section.name,
                    "is_visible": section.is_visible, "width": section.width,
                    "layout": section.layout, "background": section.background,
                    "full_bleed_background": section.full_bleed_background,
                    "blocks": [
                        {
                            "id": block.pk, "position": block.position,
                            "column": block.column, "is_visible": block.is_visible,
                            "block_type": block.block_type, "content": block.content,
                            "audience": block.audience, "destination": block.destination,
                            "style": block.style,
                            "items": [
                                {"id": item.pk, "position": item.position,
                                 "heading": item.heading, "description": item.description}
                                for item in block.items.all()
                            ],
                        }
                        for block in section.blocks.all()
                    ],
                }
                for section in self.instance.sections.prefetch_related("blocks__items")
            ])

    def clean_page_builder_data(self):
        try:
            data = json.loads(self.cleaned_data["page_builder_data"])
        except (TypeError, ValueError, json.JSONDecodeError) as exc:
            raise ValidationError("The page content could not be read.") from exc
        if not isinstance(data, list):
            raise ValidationError("Page content must contain a list of sections.")

        section_ids = set(self.instance.sections.values_list("pk", flat=True)) if self.instance.pk else set()
        cleaned = []
        for section_index, raw in enumerate(data):
            if not isinstance(raw, dict):
                raise ValidationError(f"Section {section_index + 1} is invalid.")
            section_id = raw.get("id")
            if section_id is not None and section_id not in section_ids:
                raise ValidationError("A section does not belong to this page.")
            section = PageSection(
                page=self.instance, position=section_index * 10,
                name=str(raw.get("name", "Section")).strip() or "Section",
                is_visible=bool(raw.get("is_visible", True)),
                width=raw.get("width", PageSection.Width.INHERIT),
                layout=raw.get("layout", PageSection.Layout.SINGLE),
                background=raw.get("background", PageSection.Background.DEFAULT),
                full_bleed_background=bool(raw.get("full_bleed_background", False)),
            )
            section.full_clean(exclude=("page",))
            column_count = LAYOUT_COLUMNS.get(section.layout, 1)
            block_ids = set(PageBlock.objects.filter(section_id=section_id).values_list("pk", flat=True)) if section_id else set()
            blocks = []
            for block_index, raw_block in enumerate(raw.get("blocks", [])):
                if not isinstance(raw_block, dict):
                    raise ValidationError(f"Block {block_index + 1} in section {section_index + 1} is invalid.")
                block_id = raw_block.get("id")
                if block_id is not None and block_id not in block_ids:
                    raise ValidationError("A block does not belong to its section.")
                column = int(raw_block.get("column", 0))
                if column < 0 or column >= column_count:
                    raise ValidationError("A block is assigned to a column that is not in its section layout.")
                block = PageBlock(
                    position=block_index * 10, column=column,
                    is_visible=bool(raw_block.get("is_visible", True)),
                    block_type=raw_block.get("block_type", ""),
                    content=str(raw_block.get("content", "")),
                    audience=raw_block.get("audience", PageBlock.Audience.EVERYONE),
                    destination=raw_block.get("destination", PageBlock.Destination.NONE),
                    style=raw_block.get("style", PageBlock.Style.DEFAULT),
                )
                block.full_clean(exclude=("section",))
                item_ids = set(SectionItem.objects.filter(block_id=block_id).values_list("pk", flat=True)) if block_id else set()
                items = []
                raw_items = raw_block.get("items", [])
                if not isinstance(raw_items, list):
                    raise ValidationError("Card data must be a list.")
                if block.block_type != PageBlock.BlockType.CARD_GROUP and raw_items:
                    raise ValidationError("Only card-group blocks can contain cards.")
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
                    )
                    item.full_clean(exclude=("block",))
                    items.append({"id": item_id, "model": item})
                blocks.append({"id": block_id, "model": block, "items": items})
            cleaned.append({"id": section_id, "model": section, "blocks": blocks})
        return cleaned
