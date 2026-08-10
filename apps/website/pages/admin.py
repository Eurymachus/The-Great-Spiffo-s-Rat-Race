from django.contrib import admin
from django.db import transaction
from django.db.models import Max
import json

from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.template.loader import render_to_string
from django.urls import path, reverse
from django.utils import timezone

from .forms import PageEditorForm
from .models import (
    CodeManagedPage,
    NavigationItem,
    Page,
    PageBlock,
    PageSection,
    SectionItem,
)


@admin.register(CodeManagedPage)
class CodeManagedPageAdmin(admin.ModelAdmin):
    list_display = ("title", "address", "audience", "availability", "navigation_status")
    list_filter = ("audience", "availability")
    search_fields = ("title", "key", "description", "address")
    fields = (
        "title", "key", "description", "address", "audience", "availability",
        "route_name", "navigation_status",
    )
    readonly_fields = fields

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    @admin.display(description="Navigation")
    def navigation_status(self, obj):
        return "Selectable" if obj.is_navigation_target else "Not selectable"


@admin.register(Page)
class PageAdmin(admin.ModelAdmin):
    form = PageEditorForm
    change_form_template = "admin/pages/page/change_form.html"
    list_display = (
        "title", "public_address", "audience", "content_width", "is_published", "updated_at",
    )
    list_editable = ("is_published",)
    list_filter = ("audience", "is_published")
    search_fields = ("title", "public_path")
    readonly_fields = ("updated_at",)
    fieldsets = (
        ("Page", {"fields": (
            "title", "public_path", "is_published", "audience", "content_width",
            "page_builder_data",
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

    def changeform_view(self, request, object_id=None, form_url="", extra_context=None):
        from registry.models import ChallengeMode, ChallengeRun, Participant

        context = dict(extra_context or {})
        context["ranking_editor_options"] = {
            "challenge_modes": [
                {"value": mode.pk, "label": mode.display_name}
                for mode in ChallengeMode.objects.order_by("display_order", "display_name")
            ],
            "participants": [
                {"value": participant.pk, "label": participant.nickname}
                for participant in Participant.objects.order_by("nickname")
            ],
            "lifecycles": [
                {"value": value, "label": label}
                for value, label in ChallengeRun.Lifecycle.choices
            ],
        }
        return super().changeform_view(request, object_id, form_url, context)

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
        sections = form.cleaned_data.get("page_builder_data")
        if sections is None:
            return
        with transaction.atomic():
            retained_sections = []
            retained_blocks = []
            for section_data in sections:
                submitted_section = section_data["model"]
                section = submitted_section
                if section_data["id"]:
                    section = form.instance.sections.get(pk=section_data["id"])
                    for field in (
                        "position", "name", "is_visible", "section_type", "width", "layout",
                        "background", "full_bleed_background", "separator_style",
                        "separator_spacing", "vertical_padding", "tabs_orientation", "tabs_config",
                    ):
                        setattr(section, field, getattr(submitted_section, field))
                section.page = form.instance
                section.save()
                retained_sections.append(section.pk)

                for block_data in section_data["blocks"]:
                    submitted_block = block_data["model"]
                    block = submitted_block
                    if block_data["id"]:
                        block = PageBlock.objects.get(
                            pk=block_data["id"], section__page=form.instance
                        )
                        for field in (
                            "position", "column", "is_visible", "block_type",
                            "content", "audience", "alignment", "text_role", "text_font",
                            "text_size", "text_weight", "destination", "style",
                            "card_columns",
                            "separator_style", "separator_spacing",
                            "image_asset", "image_alt", "image_fit", "image_height",
                            "image_custom_height", "image_position", "image_expandable",
                            "gallery_auto_scroll", "gallery_scroll_speed", "gallery_loop",
                            "gallery_show_controls", "gallery_show_captions", "gallery_expandable",
                            "ranking_config",
                            "community_stats_config",
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
                            for field in (
                                "position", "heading", "description", "card_type", "card_label", "audience",
                                "alt_text", "destination_url",
                            ):
                                setattr(item, field, getattr(submitted_item, field))
                        item.block = block
                        item.save()
                        retained_items.append(item.pk)
                    block.items.exclude(pk__in=retained_items).delete()
                    block.gallery_images.all().delete()
                    for gallery_image in block_data["gallery_images"]:
                        gallery_image.block = block
                        gallery_image.save()
            PageBlock.objects.filter(section__page=form.instance).exclude(
                pk__in=retained_blocks
            ).delete()
            form.instance.sections.exclude(pk__in=retained_sections).delete()

    def has_add_permission(self, request):
        return super().has_add_permission(request)

    def has_delete_permission(self, request, obj=None):
        permitted = super().has_delete_permission(request, obj)
        return permitted and (obj is None or obj.slug != "home")

    def get_readonly_fields(self, request, obj=None):
        return list(self.readonly_fields)

    def get_actions(self, request):
        actions = super().get_actions(request)
        actions.pop("delete_selected", None)
        return actions

    @admin.display(description="Public address", ordering="public_path")
    def public_address(self, obj):
        return "/" if obj.slug == "home" else f"/{obj.public_path}/"


@admin.register(NavigationItem)
class NavigationItemAdmin(admin.ModelAdmin):
    change_list_template = "admin/pages/navigationitem/change_list.html"
    list_display = ("menu_location", "destination", "audience", "position", "is_visible")
    list_editable = ("position", "is_visible")
    list_filter = ("audience", "is_visible", "parent")
    search_fields = (
        "label", "page__title", "page__public_path", "code_page__title",
        "code_page__key",
    )
    autocomplete_fields = ("page", "code_page", "parent")
    ordering = ("parent_id", "position", "label")
    fieldsets = (
        ("Menu entry", {"fields": ("label", "page", "code_page", "parent")}),
        ("Presentation", {"fields": ("audience", "position", "is_visible")}),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("parent", "page", "code_page")

    def get_urls(self):
        return [
            path(
                "<int:object_id>/add-child/",
                self.admin_site.admin_view(self.add_child_view),
                name="pages_navigationitem_add_child",
            ),
            path(
                "<int:object_id>/remove/",
                self.admin_site.admin_view(self.remove_item_view),
                name="pages_navigationitem_remove",
            ),
            path(
                "reorder/",
                self.admin_site.admin_view(self.reorder_view),
                name="pages_navigationitem_reorder",
            ),
        ] + super().get_urls()

    def add_child_view(self, request, object_id):
        parent = get_object_or_404(NavigationItem, pk=object_id)
        if request.method != "POST" or not self.has_add_permission(request):
            return JsonResponse({"created": False}, status=403)
        depth = 1
        ancestor = parent
        while ancestor.parent_id:
            depth += 1
            ancestor = ancestor.parent
        if depth >= 3:
            return JsonResponse({"created": False, "error": "Navigation supports at most three levels."}, status=400)
        position = (parent.children.aggregate(highest=Max("position"))["highest"] or 0) + 10
        child = NavigationItem.objects.create(label="New item", parent=parent, position=position)
        node = {"item": child, "children": [], "depth": depth + 1}
        html = render_to_string(
            "admin/pages/navigationitem/_tree_items.html",
            {
                "nodes": [node],
                "navigation_pages": Page.objects.order_by("title", "public_path"),
                "navigation_code_pages": CodeManagedPage.objects.filter(
                    availability=CodeManagedPage.Availability.AVAILABLE
                ).exclude(route_name="").order_by("title"),
            },
            request=request,
        )
        return JsonResponse({"created": True, "html": html, "id": child.pk})

    def remove_item_view(self, request, object_id):
        item = get_object_or_404(NavigationItem, pk=object_id)
        if request.method != "POST" or not self.has_delete_permission(request, item):
            return JsonResponse({"removed": False}, status=403)
        # Deleting a menu removes its complete nested branch through the model's
        # cascading parent relationship.
        item.delete()
        return JsonResponse({"removed": True})

    def changelist_view(self, request, extra_context=None):
        items = list(self.get_queryset(request).order_by("parent_id", "position", "label"))
        nodes = {item.pk: {"item": item, "children": []} for item in items}
        roots = []
        for node in nodes.values():
            parent = nodes.get(node["item"].parent_id)
            if parent:
                parent["children"].append(node)
            else:
                roots.append(node)
        def assign_depth(branches, depth=1):
            for node in branches:
                node["depth"] = depth
                assign_depth(node["children"], depth + 1)
        assign_depth(roots)
        extra_context = {
            **(extra_context or {}),
            "navigation_tree": roots,
            "navigation_pages": Page.objects.order_by("title", "public_path"),
            "navigation_code_pages": CodeManagedPage.objects.filter(
                availability=CodeManagedPage.Availability.AVAILABLE
            ).exclude(route_name="").order_by("title"),
            "navigation_reorder_url": reverse("admin:pages_navigationitem_reorder"),
        }
        return super().changelist_view(request, extra_context=extra_context)

    def reorder_view(self, request):
        if request.method != "POST" or not self.has_change_permission(request):
            return JsonResponse({"saved": False}, status=403)
        try:
            submitted = json.loads(request.body)
            rows = submitted["items"]
            updates = {
                int(row["id"]): {
                    "parent_id": int(row["parent_id"]) if row.get("parent_id") is not None else None,
                    "position": int(row["position"]),
                    "label": str(row["label"]).strip(),
                    "destination_type": str(row.get("destination_type") or ""),
                    "destination_id": int(row["destination_id"]) if row.get("destination_id") is not None else None,
                    "audience": str(row.get("audience") or NavigationItem.Audience.EVERYONE),
                    "is_visible": bool(row["is_visible"]),
                }
                for row in rows
            }
        except (KeyError, TypeError, ValueError, json.JSONDecodeError):
            return JsonResponse({"saved": False, "error": "The navigation order could not be read."}, status=400)

        items = list(NavigationItem.objects.all())
        item_ids = {item.pk for item in items}
        page_ids = set(Page.objects.values_list("pk", flat=True))
        code_page_ids = set(
            CodeManagedPage.objects.filter(
                availability=CodeManagedPage.Availability.AVAILABLE
            ).exclude(route_name="").values_list("pk", flat=True)
        )
        if set(updates) != item_ids:
            return JsonResponse({"saved": False, "error": "Navigation changed while it was being edited. Reload and try again."}, status=409)
        for item_id, update in updates.items():
            parent_id = update["parent_id"]
            if not update["label"] or len(update["label"]) > 80:
                return JsonResponse({"saved": False, "error": "Every navigation item needs a label of 80 characters or fewer."}, status=400)
            destination_type = update["destination_type"]
            destination_id = update["destination_id"]
            if destination_type not in ("", "page", "code"):
                return JsonResponse({"saved": False, "error": "A destination type was not recognised."}, status=400)
            if destination_type == "page" and destination_id not in page_ids:
                return JsonResponse({"saved": False, "error": "A selected editorial page no longer exists."}, status=400)
            if destination_type == "code" and destination_id not in code_page_ids:
                return JsonResponse({"saved": False, "error": "That code-managed page is not an available navigation destination."}, status=400)
            if not destination_type and destination_id is not None:
                return JsonResponse({"saved": False, "error": "A menu group cannot have a destination."}, status=400)
            if parent_id is not None and parent_id not in item_ids:
                return JsonResponse({"saved": False, "error": "A parent menu item no longer exists."}, status=400)
            if update["audience"] not in NavigationItem.Audience.values:
                return JsonResponse({"saved": False, "error": "A navigation audience was not recognised."}, status=400)
            seen = {item_id}
            depth = 1
            while parent_id is not None:
                if parent_id in seen:
                    return JsonResponse({"saved": False, "error": "Navigation items cannot contain themselves."}, status=400)
                seen.add(parent_id)
                depth += 1
                if depth > 3:
                    return JsonResponse({"saved": False, "error": "Navigation supports at most three levels."}, status=400)
                parent_id = updates[parent_id]["parent_id"]

        for item in items:
            item.parent_id = updates[item.pk]["parent_id"]
            item.position = updates[item.pk]["position"]
            item.label = updates[item.pk]["label"]
            destination_type = updates[item.pk]["destination_type"]
            destination_id = updates[item.pk]["destination_id"]
            item.page_id = destination_id if destination_type == "page" else None
            item.code_page_id = destination_id if destination_type == "code" else None
            item.audience = updates[item.pk]["audience"]
            item.is_visible = updates[item.pk]["is_visible"]
        with transaction.atomic():
            NavigationItem.objects.bulk_update(
                items,
                ("parent", "position", "label", "page", "code_page", "audience", "is_visible"),
            )
        return JsonResponse({"saved": True})

    @admin.display(description="Destination")
    def destination(self, obj):
        return obj.page or obj.code_page or "Menu group"

    @admin.display(description="Menu location", ordering="label")
    def menu_location(self, obj):
        labels = [obj.label]
        ancestor = obj.parent
        while ancestor:
            labels.append(ancestor.label)
            ancestor = ancestor.parent
        return " › ".join(reversed(labels))
