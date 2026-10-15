from django.test import TestCase
from django.utils import timezone
from zomboid_catalogue.models import CatalogueEntry, MapLocationVersion
from .models import ChallengeRun, RunStartingLocation
from .run_public import build_public_run_context


class LocationMapLinkTests(TestCase):
    def test_catalogue_anchors_and_raw_spawn_label(self):
        run = ChallengeRun.objects.create(run_id="map-links", export_format=4,
            generated_at=timezone.now(), event_hash="0" * 64)
        RunStartingLocation.objects.create(run=run, selection_mode="explicit",
            resolved_region_raw_id="muldraugh")
        for kind, identifier, location_type in (("outpost", "test_outpost", "outpost"),
                ("location", "test_landmark", "landmark")):
            entry = CatalogueEntry.objects.create(kind=kind, stable_id=identifier,
                display_name=identifier, introduced_in="42.21")
            MapLocationVersion.objects.create(entry=entry, location_type=location_type,
                game_version="42.21", anchor_x=1234, anchor_y=5678, anchor_z=0)
        CatalogueEntry.objects.create(kind="location", stable_id="unknown_position",
            display_name="Unknown position", introduced_in="42.21")
        context = build_public_run_context(run)
        self.assertEqual(context["spawn_choice"], "Muldraugh")
        self.assertEqual(next(row for row in context["outposts"] if row["id"] == "test_outpost")["map_url"], "https://map.projectzomboid.com?1234x5678x0")
        landmarks = {row["id"]: row for row in context["landmarks"]}
        self.assertEqual(landmarks["test_landmark"]["map_url"], "https://map.projectzomboid.com?1234x5678x0")
        self.assertEqual(landmarks["unknown_position"]["map_url"], "")
