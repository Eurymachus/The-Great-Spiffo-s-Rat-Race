from django.test import TestCase
from django.utils import timezone
from zomboid_catalogue.models import CatalogueEntry, CatalogueAsset
from zomboid_catalogue.management.commands.import_health_body_artwork import PARTS
from .models import ChallengeRun, RunStatisticSummary, RunStatisticMetric
from .injury_body import injury_body_data


class InjuryBodyTests(TestCase):
    def setUp(self):
        self.run = ChallengeRun.objects.create(run_id="body-test", export_format=4, generated_at=timezone.now(), event_hash="0"*64)
        for sex in ("male", "female"):
            for part in ("body", *PARTS):
                entry = CatalogueEntry.objects.create(kind="body_part", stable_id=f"{sex}:{part}")
                CatalogueAsset.objects.create(entry=entry, source_key=part, availability="imported",
                    source_type="game", file=f"test/{sex}-{part}.png")

    def test_approved_character_sex_and_legacy_unknown(self):
        from .run_authority import refresh_initial_run_authority
        from .models import RunCharacter
        for value in ("female", "male", "", "invalid"):
            refresh_initial_run_authority(self.run, {"schema": 1, "character": {
                "starting": {"sex": value}, "current": {"sex": value}}}, [])
            run = ChallengeRun.objects.get(pk=self.run.pk)
            expected = value if value in ("male", "female") else ""
            self.assertEqual(run.character_record.current_sex, expected)
            self.assertEqual(run.character_record.starting_sex, expected)
            self.assertEqual(injury_body_data(run, {"character": {"current": {"sex": "female"}}})["sex"], expected)
        RunCharacter.objects.filter(run=self.run).update(starting_sex="female", current_sex="")
        self.assertEqual(injury_body_data(ChallengeRun.objects.get(pk=self.run.pk), {})["sex"], "female")

    def test_paired_details_and_unclassified_remainder(self):
        summary = RunStatisticSummary.objects.create(run=self.run, kind="injuries", value=5)
        RunStatisticMetric.objects.create(summary=summary, dimension="body_part", raw_primary_id="Hand_L", value=5)
        RunStatisticMetric.objects.create(summary=summary, dimension="injury_pair", raw_primary_id="scratch", raw_secondary_id="Hand_L", value=3)
        data = injury_body_data(self.run, {})
        hand = next(p for p in data["parts"] if p["id"] == "Hand_L")
        self.assertEqual(hand["total"], 5)
        self.assertEqual(hand["unclassified"], 2)
        self.assertEqual(hand["injuries"], [{"name": "Scratch", "count": 3}])
        self.assertEqual(set(data["views"]), {"male", "female"})

    def test_empty_authority_does_not_use_legacy_pairs(self):
        RunStatisticSummary.objects.create(run=self.run, kind="injuries", value=0)
        data = injury_body_data(self.run, {"injuries": {"all": {"pairs": [
            {"injuryType": "burn", "bodyPart": "Hand_L", "count": 10}]}}})
        self.assertTrue(all(p["total"] == 0 for p in data["parts"]))

    def test_legacy_totals_do_not_invent_types_and_preserve_unknown_parts(self):
        data = injury_body_data(self.run, {"injuries": {"all": {"byBodyPart": [
            {"id": "Hand_L", "count": 2}, {"id": "Unknown", "count": 1}]}}})
        hand = next(p for p in data["parts"] if p["id"] == "Hand_L")
        self.assertEqual(hand["injuries"], [])
        self.assertEqual(hand["unclassified"], 2)
        self.assertEqual(data["unmapped"], [{"name": "Unknown", "count": 1}])

    def test_missing_artwork_uses_existing_list(self):
        CatalogueAsset.objects.all().delete()
        self.assertIsNone(injury_body_data(self.run, {}))


    def test_pack_extraction_restores_offsets(self):
        import io
        import struct
        import tempfile
        from pathlib import Path
        from PIL import Image
        from zomboid_catalogue.management.commands.import_health_body_artwork import textures
        output = io.BytesIO()
        Image.new("RGBA", (2, 2), (255, 255, 255, 255)).save(output, format="PNG")
        payload = output.getvalue()
        def integer(value): return struct.pack("<i", value)
        def string(value): return integer(len(value)) + value.encode()
        pack = (b"PZPK" + integer(1) + integer(1) + string("page") + integer(1) + integer(0)
                + string("part") + struct.pack("<8i", 0, 0, 2, 2, 3, 4, 8, 9)
                + integer(len(payload)) + payload)
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "UI2.pack"
            path.write_bytes(pack)
            image = Image.open(io.BytesIO(dict(textures(path, {"part"}))["part"]))
            self.assertEqual(image.size, (8, 9))
            self.assertEqual(image.getpixel((3, 4))[3], 255)
            self.assertEqual(image.getpixel((0, 0))[3], 0)
