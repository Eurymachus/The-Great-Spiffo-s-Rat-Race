import hashlib
import io
import struct
import tempfile
from pathlib import Path

from PIL import Image
from django.core.files.base import ContentFile
from django.core.management import call_command
from django.test import TestCase, override_settings

from .item_artwork import missing_icon_reason
from .models import CatalogueAsset, CatalogueEntry, ItemDetails
from .world_artwork import world_sprite_key


class MissingKeyArtworkTests(TestCase):
    def item(self, stable_id="Base.Skull_Wall", icon_key="", **properties):
        entry = CatalogueEntry.objects.create(kind="item", stable_id=stable_id,
            introduced_in="test-world", display_name="Wall skull", icon_key=icon_key)
        ItemDetails.objects.create(entry=entry, raw_properties=properties)
        return entry

    def test_classification_keeps_hidden_materials_distinct_from_inventory_icons(self):
        entry = self.item()
        overlay = {"hidden": "true", "ItemType": "base:clothing", "ClothingItem": "Bandage_Head"}
        self.assertEqual(missing_icon_reason(entry, overlay), "hidden_character_overlay_no_inventory_icon")
        self.assertEqual(missing_icon_reason(entry, {**overlay, "hidden": "false"}), "no_supported_icon_key")
        self.assertEqual(world_sprite_key(entry, overlay), "")
        occupation = CatalogueEntry(kind="occupation", stable_id="base:unemployed")
        self.assertEqual(missing_icon_reason(occupation), "occupation_has_no_source_icon")
        occupation.stable_id = "mod:unknown"
        self.assertEqual(missing_icon_reason(occupation), "no_supported_icon_key")

    def test_world_mapping_requires_moveable_with_explicit_sprite_and_no_icon(self):
        entry = self.item()
        props = {"ItemType": "base:moveable", "WorldObjectSprite": "tiles_01_48"}
        self.assertEqual(world_sprite_key(entry, props), "tiles_01_48")
        self.assertEqual(world_sprite_key(entry, {**props, "Icon": "Specific"}), "")
        self.assertEqual(world_sprite_key(entry, {**props, "WorldObjectSprite": "../other"}), "")
        entry.icon_key = "default"
        self.assertEqual(world_sprite_key(entry, props), "tiles_01_48")

    def test_extract_preserve_and_repair_world_artwork(self):
        entry = self.item(icon_key="default", Icon="default", ItemType="base:moveable", WorldObjectSprite="tiles_01_48")
        with tempfile.TemporaryDirectory() as directory, override_settings(MEDIA_ROOT=directory):
            root = Path(directory) / "game"
            pack = root / "media/texturepacks/Tiles2x.pack"
            pack.parent.mkdir(parents=True)
            image = io.BytesIO()
            Image.new("RGBA", (2, 2), (255, 0, 0, 255)).save(image, format="PNG")
            def number(value):
                return struct.pack("<i", value)
            def name(value):
                data = value.encode()
                return number(len(data)) + data
            # One real PZPK page, with a crop placed at its original canvas offset.
            pack.write_bytes(b"PZPK" + number(1) + number(1) + name("page")
                + number(1) + number(1) + name("tiles_01_48")
                + struct.pack("<8i", 0, 0, 2, 2, 1, 1, 4, 4)
                + number(len(image.getvalue())) + image.getvalue())
            def run():
                report = []
                call_command("import_pzwiki_icons", game_version="test-world", game_root=root,
                    missing_only=True, report_output=report, stdout=io.StringIO())
                self.assertEqual(report, [])
            run()
            asset = CatalogueAsset.objects.get(entry=entry)
            original = asset.file.name
            data = asset.file.read()
            self.assertEqual(asset.source_type, "game")
            self.assertEqual(asset.source_checksum, hashlib.sha256(data).hexdigest())
            self.assertTrue(asset.source_path.endswith("#tiles_01_48"))
            with Image.open(io.BytesIO(data)) as extracted:
                self.assertEqual(extracted.size, (4, 4))
                self.assertEqual(extracted.getpixel((1, 1)), (255, 0, 0, 255))
            run()
            asset.refresh_from_db()
            self.assertEqual(asset.file.name, original)
            asset.file.delete(save=False)
            run()
            asset.refresh_from_db()
            self.assertTrue(asset.file.storage.exists(asset.file.name))
            for source in ("manual", "pzwiki"):
                asset.source_type = source
                asset.file.save("protected.png", ContentFile(data), save=False)
                asset.save()
                protected = asset.file.name
                run()
                asset.refresh_from_db()
                self.assertEqual(asset.source_type, source)
                self.assertEqual(asset.file.name, protected)

    def test_custom_occupation_uses_approved_website_icon(self):
        entry = CatalogueEntry.objects.create(kind="occupation", stable_id="base:unemployed",
            introduced_in="custom-test", display_name="Custom Occupation")
        with tempfile.TemporaryDirectory() as directory, override_settings(MEDIA_ROOT=directory):
            for _ in range(2):
                report = []
                call_command("import_pzwiki_icons", game_version="custom-test",
                    report_output=report, stdout=io.StringIO())
                self.assertEqual(report, [])
            asset = CatalogueAsset.objects.get(entry=entry)
            self.assertEqual(asset.source_type, "manual")
            self.assertEqual(asset.source_path, "static/registry/images/Profession_custom.png")
            self.assertTrue(asset.file.storage.exists(asset.file.name))
