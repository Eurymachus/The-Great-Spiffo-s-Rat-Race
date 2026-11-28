"""Exact game sprite fallback for moveables without an inventory icon."""
import hashlib
import re
from pathlib import Path

from django.core.files.base import ContentFile

from .item_artwork import item_icon_key
from .models import CatalogueAsset, ItemDetails
from .management.commands.import_health_body_artwork import textures


def world_sprite_key(entry, properties):
    if (entry.kind != "item" or entry.icon_key or item_icon_key(properties)
            or properties.get("ItemType") != "base:moveable"):
        return ""
    key = str(properties.get("WorldObjectSprite", ""))
    return key if re.fullmatch(r"[A-Za-z0-9_]+", key) else ""


class WorldArtwork:
    def __init__(self, game_root):
        self.game_root = Path(game_root) if game_root else None
        self.cache = None

    def apply(self, entry, properties, entries):
        key = world_sprite_key(entry, properties)
        if not key:
            return False
        existing = CatalogueAsset.objects.filter(
            entry=entry, role="icon", availability="imported"
        ).exclude(file="")
        # Wiki and manual presentation remain authoritative.
        for asset in existing:
            if asset.source_type in ("manual", "pzwiki") and asset.file.storage.exists(asset.file.name):
                return True
        if not self.game_root:
            return any(asset.source_type == "game" and asset.source_key == key
                       and asset.file.storage.exists(asset.file.name) for asset in existing)
        if self.cache is None:
            wanted = set()
            for details in ItemDetails.objects.filter(entry__in=entries).select_related("entry"):
                candidate = world_sprite_key(details.entry, details.raw_properties)
                if candidate:
                    wanted.add(candidate)
            pack = self.game_root / "media/texturepacks/Tiles2x.pack"
            self.cache = dict(textures(pack, wanted))
        payload = self.cache.get(key)
        if not payload:
            return False
        checksum = hashlib.sha256(payload).hexdigest()
        asset, _ = CatalogueAsset.objects.get_or_create(entry=entry, role="icon", source_key=key)
        if asset.source_type == "manual":
            return True
        if (asset.source_type == "game" and asset.source_checksum == checksum
                and asset.file and asset.file.storage.exists(asset.file.name)):
            return True
        path = f"media/texturepacks/Tiles2x.pack#{key}"
        asset.file.save(key + ".png", ContentFile(payload), save=False)
        asset.alt_text = entry.display_name
        asset.source_type = "game"
        asset.source_path = path
        asset.source_checksum = checksum
        asset.game_availability = "packed"
        asset.game_source_path = path
        asset.game_source_checksum = checksum
        asset.availability = "imported"
        asset.save()
        return True
