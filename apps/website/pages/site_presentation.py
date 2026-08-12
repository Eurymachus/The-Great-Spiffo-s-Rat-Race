import hashlib
import json
import shutil
from pathlib import Path

from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.db import transaction

from branding.models import ManagedImage, SiteBranding, WebsiteTheme
from pages.code_pages import synchronise_code_managed_pages
from pages.models import (
    CodeManagedPage,
    NavigationItem,
    Page,
    PageBlock,
    PageGalleryImage,
    PageSection,
    SectionItem,
)
from registry.models import (
    ChallengeMode,
    ChallengeModeAlias,
    ExploitRuling,
    ExploitRulingImage,
)


PACKAGE_VERSION = 1
PRESENTATION_FILENAME = "presentation.json"
MANIFEST_FILENAME = "manifest.json"
MEDIA_DIRECTORY = "media"
EXCLUDED_FIELDS = {
    "id", "pk", "created_at", "updated_at", "uploaded_at", "uploaded_by",
}


class PresentationPackageError(ValueError):
    pass


def _canonical_json(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _checksum(payload):
    return hashlib.sha256(payload).hexdigest()


def _ordinary_fields(instance, *, exclude=()):
    excluded = EXCLUDED_FIELDS | set(exclude)
    values = {}
    for field in instance._meta.concrete_fields:
        if field.name in excluded or field.is_relation or field.get_internal_type() == "FileField":
            continue
        values[field.name] = field.value_from_object(instance)
    return values


def _image_key(image):
    if not image or not image.image:
        return None
    payload = image.image.read()
    image.image.close()
    return f"{_checksum(payload)}:{image.name}"


def build_presentation():
    images = []
    image_keys = {}
    for image in ManagedImage.objects.exclude(image="").order_by("name", "pk"):
        key = _image_key(image)
        image_keys[image.pk] = key
        images.append({
            "key": key,
            "name": image.name,
            "original_filename": image.original_filename,
            "filename": f"{_checksum(key.encode())}{Path(image.image.name).suffix.lower()}",
            "checksum": key.split(":", 1)[0],
        })

    themes = []
    for theme in WebsiteTheme.objects.order_by("name", "pk"):
        themes.append({"key": theme.name, "fields": _ordinary_fields(theme)})

    pages = []
    for page in Page.objects.order_by("slug"):
        page_data = {"key": page.slug, "fields": _ordinary_fields(page)}
        sections = []
        for section_index, section in enumerate(page.sections.order_by("position", "pk")):
            section_key = f"{page.slug}:section:{section_index}"
            section_data = {
                "key": section_key,
                "fields": _ordinary_fields(section, exclude=("page",)),
                "blocks": [],
            }
            for block_index, block in enumerate(section.blocks.order_by("column", "position", "pk")):
                block_key = f"{section_key}:block:{block_index}"
                block_data = {
                    "key": block_key,
                    "fields": _ordinary_fields(block, exclude=("section", "image_asset")),
                    "image": image_keys.get(block.image_asset_id),
                    "items": [
                        _ordinary_fields(item, exclude=("block",))
                        for item in block.items.order_by("position", "pk")
                    ],
                    "gallery": [
                        {
                            "fields": _ordinary_fields(item, exclude=("block", "image")),
                            "image": image_keys.get(item.image_id),
                        }
                        for item in block.gallery_images.order_by("position", "pk")
                    ],
                }
                section_data["blocks"].append(block_data)
            sections.append(section_data)
        page_data["sections"] = sections
        pages.append(page_data)

    navigation = []
    nav_keys = {}
    ordered_nav = list(NavigationItem.objects.order_by("parent_id", "position", "pk"))
    for index, item in enumerate(ordered_nav):
        nav_keys[item.pk] = f"navigation:{index}"
    for item in ordered_nav:
        navigation.append({
            "key": nav_keys[item.pk],
            "fields": _ordinary_fields(item, exclude=("page", "code_page", "parent")),
            "page": item.page.slug if item.page_id else None,
            "code_page": item.code_page.key if item.code_page_id else None,
            "parent": nav_keys.get(item.parent_id),
        })

    challenge_modes = []
    for mode in ChallengeMode.objects.order_by("key"):
        challenge_modes.append({
            "key": mode.key,
            "fields": _ordinary_fields(mode),
            "aliases": list(mode.aliases.order_by("key").values_list("key", flat=True)),
        })

    exploit_rulings = []
    for ruling in ExploitRuling.objects.order_by("position", "slug"):
        exploit_rulings.append({
            "key": ruling.slug,
            "fields": _ordinary_fields(ruling),
            "images": [
                {
                    "fields": _ordinary_fields(item, exclude=("ruling", "image")),
                    "image": image_keys.get(item.image_id),
                }
                for item in ruling.example_images.order_by("position", "pk")
            ],
        })

    branding = SiteBranding.current()
    branding_data = None
    if branding:
        branding_data = {
            "fields": _ordinary_fields(
                branding,
                exclude=(
                    "header_logo_asset", "favicon_asset", "social_image_asset",
                    "homepage_feature_image_asset", "background_image_asset", "active_theme",
                ),
            ),
            "active_theme": branding.active_theme.name if branding.active_theme_id else None,
            "images": {
                name: image_keys.get(getattr(branding, f"{name}_id"))
                for name in (
                    "header_logo_asset", "favicon_asset", "social_image_asset",
                    "homepage_feature_image_asset", "background_image_asset",
                )
            },
        }

    return {
        "version": PACKAGE_VERSION,
        "branding": branding_data,
        "themes": themes,
        "managed_images": images,
        "pages": pages,
        "navigation": navigation,
        "challenge_modes": challenge_modes,
        "exploit_rulings": exploit_rulings,
    }


def export_presentation(package_path):
    package_path = Path(package_path).resolve()
    staging = package_path.with_name(f"{package_path.name}.staging")
    if staging.exists():
        shutil.rmtree(staging)
    staging.mkdir(parents=True)
    media_path = staging / MEDIA_DIRECTORY
    media_path.mkdir()

    presentation = build_presentation()
    by_key = {item["key"]: item for item in presentation["managed_images"]}
    for image in ManagedImage.objects.exclude(image="").order_by("name", "pk"):
        item = by_key[_image_key(image)]
        destination = media_path / item["filename"]
        with image.image.open("rb") as source, destination.open("wb") as target:
            shutil.copyfileobj(source, target)

    payload = (_canonical_json(presentation) + "\n").encode("utf-8")
    (staging / PRESENTATION_FILENAME).write_bytes(payload)
    files = {PRESENTATION_FILENAME: _checksum(payload)}
    for file in sorted(media_path.iterdir()):
        files[f"{MEDIA_DIRECTORY}/{file.name}"] = _checksum(file.read_bytes())
    manifest = {
        "version": PACKAGE_VERSION,
        "presentation_checksum": files[PRESENTATION_FILENAME],
        "files": files,
    }
    (staging / MANIFEST_FILENAME).write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    if package_path.exists():
        shutil.rmtree(package_path)
    staging.replace(package_path)
    return presentation


def load_and_validate_package(package_path):
    package_path = Path(package_path).resolve()
    try:
        manifest = json.loads((package_path / MANIFEST_FILENAME).read_text(encoding="utf-8"))
        payload = (package_path / PRESENTATION_FILENAME).read_bytes()
        presentation = json.loads(payload)
    except (OSError, json.JSONDecodeError) as exc:
        raise PresentationPackageError(f"Unable to read presentation package: {exc}") from exc
    if manifest.get("version") != PACKAGE_VERSION or presentation.get("version") != PACKAGE_VERSION:
        raise PresentationPackageError("Unsupported presentation package version.")
    expected_files = manifest.get("files")
    if not isinstance(expected_files, dict) or not expected_files:
        raise PresentationPackageError("Presentation manifest has no file checksums.")
    actual_names = {PRESENTATION_FILENAME}
    media_path = package_path / MEDIA_DIRECTORY
    if media_path.exists():
        actual_names |= {f"{MEDIA_DIRECTORY}/{file.name}" for file in media_path.iterdir() if file.is_file()}
    if actual_names != set(expected_files):
        raise PresentationPackageError("Presentation package files do not match the manifest.")
    for relative_name, checksum in expected_files.items():
        if relative_name == PRESENTATION_FILENAME:
            checked_payload = (_canonical_json(presentation) + "\n").encode("utf-8")
        else:
            checked_payload = (package_path / relative_name).read_bytes()
        if _checksum(checked_payload) != checksum:
            raise PresentationPackageError(f"Checksum mismatch: {relative_name}")
    _validate_references(presentation)
    image_keys = [item.get("key") for item in presentation["managed_images"]]
    if len(image_keys) != len(set(image_keys)) or None in image_keys:
        raise PresentationPackageError("Managed image keys must be present and unique.")
    image_names = [item.get("name") for item in presentation["managed_images"]]
    if len(image_names) != len(set(image_names)) or None in image_names:
        raise PresentationPackageError("Managed image names must be present and unique.")
    return presentation, package_path


def _validate_references(presentation):
    required_lists = (
        "themes", "managed_images", "pages", "navigation",
        "challenge_modes", "exploit_rulings",
    )
    if any(not isinstance(presentation.get(name), list) for name in required_lists):
        raise PresentationPackageError("Presentation data is missing a required collection.")

    image_keys = {item["key"] for item in presentation["managed_images"]}
    theme_keys = {item.get("key") for item in presentation["themes"]}
    page_keys = {item.get("key") for item in presentation["pages"]}
    navigation_keys = {item.get("key") for item in presentation["navigation"]}
    code_page_keys = set(CodeManagedPage.objects.values_list("key", flat=True))

    branding = presentation.get("branding")
    if branding:
        if branding.get("active_theme") and branding["active_theme"] not in theme_keys:
            raise PresentationPackageError("Branding references an unknown theme.")
        for image_key in branding.get("images", {}).values():
            if image_key and image_key not in image_keys:
                raise PresentationPackageError("Branding references an unknown managed image.")

    for page in presentation["pages"]:
        for section in page.get("sections", []):
            for block in section.get("blocks", []):
                if block.get("image") and block["image"] not in image_keys:
                    raise PresentationPackageError("A page block references an unknown managed image.")
                for gallery_item in block.get("gallery", []):
                    if gallery_item.get("image") not in image_keys:
                        raise PresentationPackageError("A gallery references an unknown managed image.")

    for item in presentation["navigation"]:
        if item.get("page") and item["page"] not in page_keys:
            raise PresentationPackageError("Navigation references an unknown editorial page.")
        if item.get("code_page") and item["code_page"] not in code_page_keys:
            raise PresentationPackageError("Navigation references an unknown code-managed page.")
        if item.get("parent") and item["parent"] not in navigation_keys:
            raise PresentationPackageError("Navigation references an unknown parent item.")

    for ruling in presentation["exploit_rulings"]:
        for image_item in ruling.get("images", []):
            if image_item.get("image") not in image_keys:
                raise PresentationPackageError("An exploit ruling references an unknown managed image.")


def _validated(instance):
    try:
        instance.full_clean()
    except ValidationError as exc:
        raise PresentationPackageError(f"Invalid {instance._meta.label}: {exc}") from exc
    instance.save()
    return instance


@transaction.atomic
def import_presentation(package_path):
    presentation, package_path = load_and_validate_package(package_path)
    synchronise_code_managed_pages(CodeManagedPage)

    images = {}
    package_image_keys = {item["key"] for item in presentation["managed_images"]}
    for item in presentation["managed_images"]:
        source = package_path / MEDIA_DIRECTORY / item["filename"]
        payload = source.read_bytes()
        if _checksum(payload) != item["checksum"]:
            raise PresentationPackageError(f"Managed image checksum mismatch: {item['name']}")
        image = ManagedImage.objects.filter(name=item["name"]).first() or ManagedImage(name=item["name"])
        image.original_filename = item["original_filename"]
        current_checksum = ""
        if image.pk and image.image:
            try:
                current_checksum = _checksum(image.image.read())
                image.image.close()
            except OSError:
                current_checksum = ""
        if current_checksum != item["checksum"]:
            image.image = ContentFile(payload, name=item["filename"])
        elif image.pk:
            images[item["key"]] = image
            continue
        image.uploaded_by = None
        _validated(image)
        images[item["key"]] = image

    theme_names = set()
    themes = {}
    for item in presentation["themes"]:
        theme_names.add(item["key"])
        theme, _ = WebsiteTheme.objects.update_or_create(name=item["key"], defaults=item["fields"])
        themes[item["key"]] = theme

    NavigationItem.objects.all().delete()
    Page.objects.all().delete()
    pages = {}
    for item in presentation["pages"]:
        page = _validated(Page(**item["fields"]))
        pages[item["key"]] = page
        for section_item in item["sections"]:
            section = _validated(PageSection(page=page, **section_item["fields"]))
            for block_item in section_item["blocks"]:
                block = _validated(PageBlock(
                    section=section,
                    image_asset=images.get(block_item["image"]),
                    **block_item["fields"],
                ))
                for card_fields in block_item["items"]:
                    _validated(SectionItem(block=block, **card_fields))
                for gallery_item in block_item["gallery"]:
                    image = images.get(gallery_item["image"])
                    if not image:
                        raise PresentationPackageError("A gallery references an unknown managed image.")
                    _validated(PageGalleryImage(block=block, image=image, **gallery_item["fields"]))

    navigation = {}
    pending = list(presentation["navigation"])
    while pending:
        progress = False
        for item in pending[:]:
            if item["parent"] and item["parent"] not in navigation:
                continue
            code_page = None
            if item["code_page"]:
                code_page = CodeManagedPage.objects.filter(key=item["code_page"]).first()
                if not code_page:
                    raise PresentationPackageError(f"Unknown code-managed page: {item['code_page']}")
            navigation[item["key"]] = _validated(NavigationItem(
                page=pages.get(item["page"]),
                code_page=code_page,
                parent=navigation.get(item["parent"]),
                **item["fields"],
            ))
            pending.remove(item)
            progress = True
        if not progress:
            raise PresentationPackageError("Navigation contains a missing or circular parent reference.")

    for item in presentation["challenge_modes"]:
        mode, _ = ChallengeMode.objects.update_or_create(key=item["key"], defaults=item["fields"])
        mode.aliases.exclude(key__in=item["aliases"]).delete()
        for alias in item["aliases"]:
            ChallengeModeAlias.objects.update_or_create(key=alias, defaults={"challenge_mode": mode})

    ExploitRuling.objects.all().delete()
    for item in presentation["exploit_rulings"]:
        ruling = _validated(ExploitRuling(**item["fields"]))
        for image_item in item["images"]:
            image = images.get(image_item["image"])
            if not image:
                raise PresentationPackageError("An exploit ruling references an unknown managed image.")
            _validated(ExploitRulingImage(ruling=ruling, image=image, **image_item["fields"]))

    branding_data = presentation.get("branding")
    if branding_data:
        branding = SiteBranding.current() or SiteBranding()
        for name, value in branding_data["fields"].items():
            setattr(branding, name, value)
        branding.active_theme = themes.get(branding_data["active_theme"])
        for name, key in branding_data["images"].items():
            setattr(branding, name, images.get(key))
        _validated(branding)

    WebsiteTheme.objects.exclude(name__in=theme_names).delete()

    referenced_image_ids = set(images[key].pk for key in package_image_keys)
    ManagedImage.objects.exclude(pk__in=referenced_image_ids).delete()
    return presentation
