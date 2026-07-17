import json

from django import forms
from django.core.exceptions import ValidationError

from .models import Page, PageSection, SectionItem


class PageEditorForm(forms.ModelForm):
    page_builder_data = forms.CharField(widget=forms.HiddenInput)

    class Meta:
        model = Page
        fields = ("title", "slug", "is_published", "page_builder_data")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.is_bound and self.instance.pk:
            self.initial["page_builder_data"] = json.dumps(
                [
                    {
                        "id": section.pk,
                        "section_type": section.section_type,
                        "position": section.position,
                        "is_visible": section.is_visible,
                        "small_heading": section.small_heading,
                        "main_heading": section.main_heading,
                        "introduction": section.introduction,
                        "visitor_primary_button": section.visitor_primary_button,
                        "visitor_secondary_link": section.visitor_secondary_link,
                        "signed_in_button": section.signed_in_button,
                        "items": [
                            {
                                "id": item.pk,
                                "position": item.position,
                                "heading": item.heading,
                                "description": item.description,
                            }
                            for item in section.items.all()
                        ],
                    }
                    for section in self.instance.sections.prefetch_related("items")
                ]
            )

    def clean_page_builder_data(self):
        try:
            data = json.loads(self.cleaned_data["page_builder_data"])
        except (TypeError, ValueError, json.JSONDecodeError) as exc:
            raise ValidationError("The page content could not be read.") from exc
        if not isinstance(data, list):
            raise ValidationError("Page content must contain a list of sections.")

        section_ids = set(
            self.instance.sections.values_list("pk", flat=True)
        ) if self.instance.pk else set()
        cleaned = []
        for index, raw in enumerate(data):
            if not isinstance(raw, dict):
                raise ValidationError(f"Section {index + 1} is invalid.")
            section_id = raw.get("id")
            if section_id is not None and section_id not in section_ids:
                raise ValidationError("A section does not belong to this page.")
            section = PageSection(
                page=self.instance,
                section_type=raw.get("section_type", ""),
                position=index * 10,
                is_visible=bool(raw.get("is_visible", True)),
                small_heading=str(raw.get("small_heading", "")),
                main_heading=str(raw.get("main_heading", "")),
                introduction=str(raw.get("introduction", "")),
                visitor_primary_button=str(raw.get("visitor_primary_button", "")),
                visitor_secondary_link=str(raw.get("visitor_secondary_link", "")),
                signed_in_button=str(raw.get("signed_in_button", "")),
            )
            section.full_clean(exclude=("page",))

            item_ids = set()
            if section_id is not None:
                item_ids = set(
                    SectionItem.objects.filter(section_id=section_id).values_list(
                        "pk", flat=True
                    )
                )
            items = []
            for item_index, raw_item in enumerate(raw.get("items", [])):
                if not isinstance(raw_item, dict):
                    raise ValidationError(
                        f"Card {item_index + 1} in section {index + 1} is invalid."
                    )
                item_id = raw_item.get("id")
                if item_id is not None and item_id not in item_ids:
                    raise ValidationError("A card does not belong to its section.")
                item = SectionItem(
                    position=item_index * 10,
                    heading=str(raw_item.get("heading", "")),
                    description=str(raw_item.get("description", "")),
                )
                item.full_clean(exclude=("section",))
                items.append({"id": item_id, "model": item})
            cleaned.append({"id": section_id, "model": section, "items": items})
        return cleaned
