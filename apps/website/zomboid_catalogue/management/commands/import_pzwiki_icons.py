import hashlib
import argparse
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote, unquote
from urllib.request import Request, urlopen

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError

from zomboid_catalogue.models import CatalogueAsset, CatalogueEntry


PZWIKI_FILE_REDIRECT = "https://pzwiki.net/wiki/Special:Redirect/file/{filename}"
PZWIKI_PAGE = "https://pzwiki.net/wiki/{title}"
USER_AGENT = "TGSRR catalogue importer/1.0 (Project Zomboid community website)"
PZWIKI_FILENAME_OVERRIDES = {
    # PZwiki preserves this historical filename typo.
    "base:claustrophobic": "Trait_claustophobic.png",
    # The installed game uses profession-trait filenames for these
    # pixel-identical PZwiki images.
    "base:herbalist_prof": "Trait_herbalist.png",
    "base:inventive_prof": "Trait_inventive.png",
    "base:mechanics2": "Trait_mechanics.png",
}
PZWIKI_SKILL_PAGE_OVERRIDES = {
    # "Axe" is ambiguous with the item page.
    "Axe": "Axe (skill)",
}


class InfoboxArtworkParser(HTMLParser):
    """Find the representative file linked by the page's infobox."""

    def __init__(self):
        super().__init__()
        self.infobox_depth = 0
        self.filename = ""

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        classes = attributes.get("class", "").split()
        if tag in ("div", "table") and "infobox" in classes:
            self.infobox_depth = 1
        elif self.infobox_depth and tag in ("div", "table"):
            self.infobox_depth += 1
        if self.infobox_depth and tag == "a":
            href = attributes.get("href", "")
            marker = "/wiki/File:"
            if marker in href and not self.filename:
                self.filename = unquote(href.split(marker, 1)[1].split("#", 1)[0])

    def handle_endtag(self, tag):
        if self.infobox_depth and tag in ("div", "table"):
            self.infobox_depth -= 1


def skill_wiki_page_title(entry):
    return PZWIKI_SKILL_PAGE_OVERRIDES.get(
        entry.display_name,
        str(entry.display_name or "").strip(),
    )


def discover_skill_wiki_filename(entry, timeout):
    page_title = skill_wiki_page_title(entry)
    if not page_title:
        return ""
    source_url = PZWIKI_PAGE.format(title=quote(page_title.replace(" ", "_")))
    request = Request(source_url, headers={"User-Agent": USER_AGENT})
    with urlopen(request, timeout=timeout) as response:
        content_type = response.headers.get_content_type()
        payload = response.read()
    if content_type != "text/html":
        raise CommandError(
            f"PZwiki did not return an HTML page for skill {entry.display_name}."
        )
    parser = InfoboxArtworkParser()
    parser.feed(payload.decode("utf-8", errors="replace"))
    return parser.filename


def clear_non_wiki_presentation(entry):
    asset = CatalogueAsset.objects.filter(
        entry=entry,
        role=CatalogueAsset.Role.ICON,
        source_key=entry.icon_key,
    ).first()
    if not asset or asset.source_type in (
        CatalogueAsset.SourceType.PZWIKI,
        CatalogueAsset.SourceType.MANUAL,
    ):
        return
    if asset.file:
        asset.file.delete(save=False)
    asset.file = ""
    asset.source_type = CatalogueAsset.SourceType.UNKNOWN
    asset.source_path = ""
    asset.source_checksum = ""
    asset.availability = CatalogueAsset.Availability.MISSING
    asset.save()


def wiki_filename(entry):
    if entry.stable_id in PZWIKI_FILENAME_OVERRIDES:
        return PZWIKI_FILENAME_OVERRIDES[entry.stable_id]
    key = str(entry.icon_key or "").strip()
    if not key:
        return ""
    if entry.kind == CatalogueEntry.Kind.TRAIT and key.casefold().startswith("trait_"):
        return f"Trait_{key[6:]}.png"
    if (
        entry.kind == CatalogueEntry.Kind.OCCUPATION
        and key.casefold().startswith("profession_")
    ):
        return f"Profession_{key[11:]}.png"
    if entry.kind == CatalogueEntry.Kind.ITEM:
        return f"{key}.png"
    return ""


class Command(BaseCommand):
    help = (
        "Import supported catalogue artwork from PZwiki into managed catalogue media."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--game-version",
            help="Limit the import to catalogue entries introduced in this version.",
        )
        parser.add_argument(
            "--timeout",
            type=float,
            default=15,
            help="Per-image download timeout in seconds (default: 15).",
        )
        parser.add_argument(
            "--report-output",
            default=None,
            help=argparse.SUPPRESS,
        )

    def handle(self, *args, **options):
        entries = CatalogueEntry.objects.filter(
            kind__in=(
                CatalogueEntry.Kind.TRAIT,
                CatalogueEntry.Kind.OCCUPATION,
                CatalogueEntry.Kind.SKILL,
                CatalogueEntry.Kind.ITEM,
            ),
            is_active=True,
        )
        if options.get("game_version"):
            entries = entries.filter(introduced_in=options["game_version"])

        entries = entries.order_by("kind", "display_name", "stable_id", "pk")
        imported = unchanged = missing = protected = 0
        unavailable = []
        downloads = {}
        skill_filenames = {}
        for entry in entries.iterator():
            if entry.kind == CatalogueEntry.Kind.SKILL:
                page_title = skill_wiki_page_title(entry)
                if page_title not in skill_filenames:
                    try:
                        skill_filenames[page_title] = discover_skill_wiki_filename(
                            entry,
                            options["timeout"],
                        )
                    except HTTPError as exc:
                        if exc.code == 404:
                            skill_filenames[page_title] = ""
                        else:
                            raise CommandError(
                                f"PZwiki returned HTTP {exc.code} for skill page "
                                f"{page_title}."
                            ) from exc
                    except (OSError, URLError) as exc:
                        raise CommandError(
                            f"Could not inspect PZwiki skill page {page_title}: {exc}"
                        ) from exc
                filename = skill_filenames[page_title]
            else:
                filename = wiki_filename(entry)
            if not filename:
                unavailable_reason = (
                    "no_infobox_artwork_on_pzwiki"
                    if entry.kind == CatalogueEntry.Kind.SKILL
                    else "no_supported_icon_key"
                )
                missing += 1
                unavailable.append(
                    {
                        "kind": entry.kind,
                        "stable_id": entry.stable_id,
                        "display_name": entry.display_name,
                        "icon_key": entry.icon_key or "",
                        "expected_filename": "",
                        "reason": unavailable_reason,
                    }
                )
                clear_non_wiki_presentation(entry)
                self.stdout.write(
                    self.style.WARNING(
                        f"Skipped {entry.kind} {entry.stable_id}: "
                        + (
                            "no representative artwork was found on its PZWiki page."
                            if unavailable_reason == "no_infobox_artwork_on_pzwiki"
                            else "no supported icon key."
                        )
                    )
                )
                continue

            if filename not in downloads:
                source_url = PZWIKI_FILE_REDIRECT.format(filename=quote(filename))
                try:
                    request = Request(source_url, headers={"User-Agent": USER_AGENT})
                    with urlopen(request, timeout=options["timeout"]) as response:
                        content_type = response.headers.get_content_type()
                        payload = response.read()
                        resolved_url = response.geturl()
                except HTTPError as exc:
                    if exc.code == 404:
                        downloads[filename] = None
                    else:
                        raise CommandError(
                            f"PZwiki returned HTTP {exc.code} for {filename}."
                        ) from exc
                except (OSError, URLError) as exc:
                    raise CommandError(f"Could not download {filename}: {exc}") from exc
                else:
                    if content_type != "image/png" or not payload.startswith(
                        b"\x89PNG\r\n\x1a\n"
                    ):
                        raise CommandError(f"PZwiki did not return a PNG for {filename}.")
                    downloads[filename] = (
                        payload,
                        resolved_url,
                        hashlib.sha256(payload).hexdigest(),
                    )

            download = downloads[filename]
            if download is None:
                missing += 1
                unavailable.append(
                    {
                        "kind": entry.kind,
                        "stable_id": entry.stable_id,
                        "display_name": entry.display_name,
                        "icon_key": entry.icon_key or "",
                        "expected_filename": filename,
                        "reason": "not_found_on_pzwiki",
                    }
                )
                clear_non_wiki_presentation(entry)
                self.stdout.write(
                    self.style.WARNING(
                        f"Missing on PZwiki: {filename} ({entry.stable_id})"
                    )
                )
                continue
            payload, resolved_url, checksum = download
            asset, _created = CatalogueAsset.objects.get_or_create(
                entry=entry,
                role=CatalogueAsset.Role.ICON,
                source_key=entry.icon_key,
                defaults={"alt_text": entry.display_name},
            )
            if (
                asset.file
                and asset.source_type == CatalogueAsset.SourceType.MANUAL
            ):
                protected += 1
                continue
            if (
                asset.source_checksum == checksum
                and asset.file
                and asset.availability == CatalogueAsset.Availability.IMPORTED
                and asset.source_type == CatalogueAsset.SourceType.PZWIKI
                and asset.source_path == resolved_url
            ):
                unchanged += 1
                continue

            asset.alt_text = entry.display_name
            asset.source_type = CatalogueAsset.SourceType.PZWIKI
            asset.source_path = resolved_url
            asset.source_checksum = checksum
            asset.availability = CatalogueAsset.Availability.IMPORTED
            if asset.file:
                asset.file.delete(save=False)
            asset.file.save(
                Path(filename).name,
                ContentFile(payload),
                save=False,
            )
            asset.save()
            imported += 1

        report_output = options.get("report_output")
        if isinstance(report_output, list):
            report_output.extend(unavailable)
        self.stdout.write(
            self.style.SUCCESS(
                f"PZwiki icons: {imported} imported, {unchanged} unchanged, "
                f"{missing} unavailable, {protected} manual assets protected."
            )
        )
