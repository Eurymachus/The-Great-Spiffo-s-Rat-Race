"""Import original health-panel textures, retaining their full-canvas offsets."""
import hashlib
import io
import struct
from pathlib import Path
from PIL import Image
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from zomboid_catalogue.models import CatalogueEntry, CatalogueAsset

PARTS = dict(zip(
    ("Hand_L", "Hand_R", "ForeArm_L", "ForeArm_R", "UpperArm_L", "UpperArm_R",
     "Torso_Upper", "Torso_Lower", "Head", "Neck", "Groin", "UpperLeg_L", "UpperLeg_R",
     "LowerLeg_L", "LowerLeg_R", "Foot_L", "Foot_R"),
    ("left-hand", "right-hand", "lower-left-arm", "lower-right-arm", "upper-left-arm",
     "upper-right-arm", "chest", "abdomen", "head", "neck", "groin", "left-thigh",
     "right-thigh", "left-calf", "right-calf", "left-foot", "right-foot")))


def textures(path, wanted):
    with path.open("rb") as stream:
        def integer():
            return struct.unpack("<i", stream.read(4))[0]
        def string():
            size = integer()
            if not 0 <= size <= 4096:
                raise ValueError("Invalid texture name length")
            return stream.read(size).decode("utf-8")
        if stream.read(4) != b"PZPK" or integer() != 1:
            raise ValueError(f"Unsupported texture pack: {path}")
        for _ in range(integer()):
            string()
            count = integer()
            integer()
            entries = []
            for _ in range(count):
                name = string()
                rect = struct.unpack("<8i", stream.read(32))
                if name in wanted:
                    entries.append((name, rect))
            size = integer()
            if not entries:
                stream.seek(size, 1)
                continue
            atlas = Image.open(io.BytesIO(stream.read(size))).convert("RGBA")
            for name, (x, y, w, h, ox, oy, fw, fh) in entries:
                image = Image.new("RGBA", (fw, fh))
                image.paste(atlas.crop((x, y, x+w, y+h)), (ox, oy))
                output = io.BytesIO()
                image.save(output, format="PNG")
                yield name, output.getvalue()


class Command(BaseCommand):
    help = "Import game health body artwork into managed catalogue media."

    def add_arguments(self, parser):
        parser.add_argument("--game-root", type=Path, required=True)
        parser.add_argument("--game-version", required=True)

    def handle(self, *args, **options):
        wanted = {}
        for sex in ("male", "female"):
            wanted[f"{sex}_base_white"] = (sex, "body")
            wanted[f"bps_{sex}_outlines"] = (sex, "outline")
            for part, filename in PARTS.items():
                wanted[f"bps_{sex}_{filename}"] = (sex, part)
        found = {}
        for filename in ("UI2.pack",):
            path = options["game_root"] / "media/texturepacks" / filename
            found.update(textures(path, wanted))
        missing = set(wanted) - set(found)
        if missing:
            raise CommandError("Missing health textures: " + ", ".join(sorted(missing)))
        for key, payload in found.items():
            sex, part = wanted[key]
            entry, _ = CatalogueEntry.objects.update_or_create(kind="body_part",
                stable_id=f"{sex}:{part}", introduced_in=options["game_version"],
                defaults={"display_name": part, "icon_key": key})
            asset, _ = CatalogueAsset.objects.get_or_create(entry=entry, role="icon", source_key=key)
            checksum = hashlib.sha256(payload).hexdigest()
            if asset.source_type == "manual" or (asset.source_checksum == checksum and asset.file and asset.file.storage.exists(asset.file.name)):
                continue
            asset.file.save(key + ".png", ContentFile(payload), save=False)
            asset.source_type = "game"
            asset.game_availability = "packed"
            asset.source_path = "media/texturepacks/UI2.pack"
            asset.source_checksum = checksum
            asset.availability = "imported"
            asset.save()
        self.stdout.write(f"Health artwork ready: {len(found)} catalogue assets.")
