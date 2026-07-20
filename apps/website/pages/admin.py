from django.contrib import admin
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.urls import path
from django.utils import timezone

from .forms import PageEditorForm
from .models import Page, PageBlock, PageSection, SectionItem


@admin.register(Page)
class PageAdmin(admin.ModelAdmin):
    form = PageEditorForm
    change_form_template = "admin/pages/page/change_form.html"
    list_display = ("title", "slug", "content_width", "show_in_navigation", "is_published", "updated_at")
    list_filter = ("is_published",)
    search_fields = ("title", "slug")
    readonly_fields = ("updated_at",)
    fieldsets = (
        ("Page", {"fields": (
            "title", "slug", "is_published", "content_width",
            "navigation_label", "show_in_navigation", "page_builder_data",
        )}),
        ("Record", {"fields": ("updated_at",)}),
    )

    def get_urls(self):
        custom_urls = [
            path(
                "<path:object_id>/remove-content/<str:content_type>/<int:content_id>/",
                self.admin_site.admin_view(self.remove_content_view),
                name="pages_page_remove_content",
            ),
        ]
        return custom_urls + super().get_urls()

    def remove_content_view(self, request, object_id, content_type, content_id):
        page = get_object_or_404(Page, pk=object_id)
        if request.method != "POST" or not self.has_change_permission(request, page):
            return JsonResponse({"removed": False}, status=403)

        if content_type == "section":
            content = get_object_or_404(page.sections, pk=content_id)
        elif content_type == "block":
            content = get_object_or_404(
                PageBlock.objects.filter(section__page=page), pk=content_id
            )
        elif content_type == "card":
            content = get_object_or_404(
                SectionItem.objects.filter(block__section__page=page), pk=content_id
            )
        else:
            return JsonResponse({"removed": False}, status=400)

        with transaction.atomic():
            content.delete()
            Page.objects.filter(pk=page.pk).update(updated_at=timezone.now())
        return JsonResponse({"removed": True})

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        sections = form.cleaned_data["page_builder_data"]
        with transaction.atomic():
            retained_sections = []
            for section_data in sections:
                submitted_section = section_data["model"]
                section = submitted_section
                if section_data["id"]:
                    section = form.instance.sections.get(pk=section_data["id"])
                    for field in (
                        "position", "is_visible", "width", "layout",
                        "background", "full_bleed_background",
                    ):
                        setattr(section, field, getattr(submitted_section, field))
                section.page = form.instance
                section.save()
                retained_sections.append(section.pk)

                retained_blocks = []
                for block_data in section_data["blocks"]:
                    submitted_block = block_data["model"]
                    block = submitted_block
                    if block_data["id"]:
                        block = section.blocks.get(pk=block_data["id"])
                        for field in (
                            "position", "column", "is_visible", "block_type",
                            "content", "audience", "destination", "style",
                        ):
                            setattr(block, field, getattr(submitted_block, field))
                    block.section = section
                    block.save()
                    retained_blocks.append(block.pk)

                    retained_items = []
                    for item_data in block_data["items"]:
                        submitted_item = item_data["model"]
                        item = submitted_item
                        if item_data["id"]:
                            item = block.items.get(pk=item_data["id"])
                            for field in ("position", "heading", "description"):
                                setattr(item, field, getattr(submitted_item, field))
                        item.block = block
                        item.save()
                        retained_items.append(item.pk)
                    block.items.exclude(pk__in=retained_items).delete()
                section.blocks.exclude(pk__in=retained_blocks).delete()
            form.instance.sections.exclude(pk__in=retained_sections).delete()

    def has_add_permission(self, request):
        return not Page.objects.exists() and super().has_add_permission(request)

    def has_delete_permission(self, request, obj=None):
        permitted = super().has_delete_permission(request, obj)
        return permitted and (obj is None or obj.slug != "home")

    def get_readonly_fields(self, request, obj=None):
        fields = list(self.readonly_fields)
        if obj and obj.slug == "home":
            fields.append("slug")
        return fields

    def get_actions(self, request):
        actions = super().get_actions(request)
        actions.pop("delete_selected", None)
        return actions
