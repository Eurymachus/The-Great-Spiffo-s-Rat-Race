from io import StringIO
import json
import tempfile
from pathlib import Path
from unittest.mock import patch

from django.contrib.auth.models import Group
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse

from registry.models import Participant

from .models import (
    AnimalDetails,
    CatalogueAlias,
    CatalogueAsset,
    CatalogueEntry,
    DeliverableDetails,
    ItemDisplayCategory,
    ItemDetails,
    OccupationDetails,
    SkillDetails,
    TraitDetails,
)
from .resolver import resolve_identifier


class CatalogueResolverTests(TestCase):
    def test_resolves_direct_identifier_for_applicable_version(self):
        entry = CatalogueEntry.objects.create(
            kind=CatalogueEntry.Kind.SKILL,
            stable_id="Woodwork",
            display_name="Carpentry",
            introduced_in="42.0",
        )
        self.assertEqual(
            resolve_identifier(CatalogueEntry.Kind.SKILL, "Woodwork", "42.19"),
            entry,
        )

    def test_resolves_versioned_alias(self):
        entry = CatalogueEntry.objects.create(
            kind=CatalogueEntry.Kind.ITEM,
            stable_id="Base.NewItem",
            display_name="New item",
            introduced_in="42.0",
        )
        CatalogueAlias.objects.create(
            entry=entry,
            stable_id="Base.OldItem",
            removed_in="43.0",
        )
        self.assertEqual(
            resolve_identifier(CatalogueEntry.Kind.ITEM, "Base.OldItem", "42.19"),
            entry,
        )
        self.assertIsNone(
            resolve_identifier(CatalogueEntry.Kind.ITEM, "Base.OldItem", "43.0")
        )

    def test_bundled_catalogue_import_is_idempotent(self):
        call_command("import_zomboid_catalogue", stdout=StringIO())
        first_count = CatalogueEntry.objects.count()
        self.assertGreaterEqual(first_count, 60)
        self.assertEqual(
            resolve_identifier(
                CatalogueEntry.Kind.SKILL, "Woodwork", "42.19"
            ).display_name,
            "Carpentry",
        )
        self.assertEqual(
            resolve_identifier(
                CatalogueEntry.Kind.OUTPOST,
                "hog_wallow_military_base",
                "42.19",
            ).display_name,
            "Hog Wallow Military Base",
        )
        rabbit_kit = resolve_identifier(
            CatalogueEntry.Kind.ANIMAL, "rabbitkit", "42.19"
        )
        self.assertEqual(rabbit_kit.display_name, "Rabbit, baby")
        self.assertEqual(rabbit_kit.animal_details.species_id, "rabbit")
        self.assertEqual(rabbit_kit.animal_details.category, "Mammal")
        self.assertEqual(rabbit_kit.animal_details.life_stage, "baby")
        kills = resolve_identifier(
            CatalogueEntry.Kind.DELIVERABLE, "kills", "42.19"
        )
        self.assertEqual(
            DeliverableDetails.objects.get(entry=kills).category,
            "Challenge objective",
        )

        output = StringIO()
        call_command("import_zomboid_catalogue", stdout=output)
        self.assertEqual(CatalogueEntry.objects.count(), first_count)
        self.assertIn(f"{first_count} unchanged", output.getvalue())

    def test_installed_game_import_builds_typed_records_and_asset_links(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            trait_path = (
                root / "media/scripts/generated/characters/character_traits.txt"
            )
            occupation_path = (
                root / "media/scripts/generated/characters/character_professions.txt"
            )
            translation_path = root / "media/lua/shared/Translate/EN/UI.json"
            ig_translation_path = root / "media/lua/shared/Translate/EN/IG_UI.json"
            item_translation_path = (
                root / "media/lua/shared/Translate/EN/ItemName.json"
            )
            item_path = root / "media/scripts/generated/items/weapon.txt"
            perk_path = (
                root
                / "zombie_decompiled/zombie/characters/skills/PerkFactory.java"
            )
            for path in (
                trait_path,
                occupation_path,
                translation_path,
                ig_translation_path,
                item_translation_path,
                item_path,
                perk_path,
            ):
                path.parent.mkdir(parents=True, exist_ok=True)
            trait_path.write_text(
                """module Base {
                character_trait_definition base:brave {
                    IsProfessionTrait = false,
                    DisabledInMultiplayer = false,
                    Cost = 4,
                    UIName = UI_trait_brave,
                    UIDescription = UI_trait_bravedesc,
                    XPBoosts = Aiming=1,
                    MutuallyExclusiveTraits = base:cowardly,
                }
                }""",
                encoding="utf-8",
            )
            occupation_path.write_text(
                """module Base {
                character_profession_definition base:carpenter {
                    Cost = -2,
                    UIName = UI_prof_Carpenter,
                    IconPathName = profession_hammer2,
                    XPBoosts = Woodwork=4,
                    GrantedTraits = base:handy,
                }
                }""",
                encoding="utf-8",
            )
            translation_path.write_text(
                json.dumps(
                    {
                        "UI_trait_brave": "Brave",
                        "UI_trait_bravedesc": "Less prone to panic.",
                        "UI_prof_Carpenter": "Carpenter",
                    }
                ),
                encoding="utf-8",
            )
            ig_translation_path.write_text(
                json.dumps(
                    {
                        "IGUI_perks_FlintKnapping": "Knapping",
                        "IGUI_perks_Knapping_Description": "Shape stone tools.",
                        "IGUI_perks_Axe": "Axe",
                        "IGUI_perks_SmallBlunt": "Small Blunt",
                        "IGUI_perks_Crafting": "Crafting",
                        "IGUI_perks_CombatMelee": "Combat",
                        "IGUI_ItemCat_ToolWeapon": "Tool/Weapon",
                    }
                ),
                encoding="utf-8",
            )
            item_translation_path.write_text(
                json.dumps({"Base.TestHammer": "Test Claw Hammer"}),
                encoding="utf-8",
            )
            item_path.write_text(
                """module Base {
                item TestHammer {
                    DisplayCategory = ToolWeapon,
                    ItemType = base:weapon,
                    Icon = Hammer,
                    Weight = 1.5,
                    Categories = base:smallblunt,
                    Tags = base:hammer;base:canbewapon,
                }
                }""",
                encoding="utf-8",
            )
            perk_path.write_text(
                'PerkFactory.AddPerk(Perks.FlintKnapping, "FlintKnapping", Perks.Crafting, '
                "50, 100, 200, 500, 1000, 2000, 3000, 4000, 5000, 6000);\n"
                'AddPerk(PerkFactory.Perks.Axe, "Axe", PerkFactory.Perks.Combat, '
                "50, 100, 200, 500, 1000, 2000, 3000, 4000, 5000, 6000);\n"
                'AddPerk(PerkFactory.Perks.SmallBlunt, "SmallBlunt", '
                "PerkFactory.Perks.Combat, 50, 100, 200, 500, 1000, 2000, "
                "3000, 4000, 5000, 6000);",
                encoding="utf-8",
            )

            output = StringIO()
            call_command(
                "import_pz_catalogue",
                game_root=root,
                game_version="42.test",
                no_assets=True,
                stdout=output,
            )

        trait = CatalogueEntry.objects.get(kind="trait", stable_id="base:brave")
        occupation = CatalogueEntry.objects.get(
            kind="occupation", stable_id="base:carpenter"
        )
        skill = CatalogueEntry.objects.get(kind="skill", stable_id="FlintKnapping")
        axe = CatalogueEntry.objects.get(kind="skill", stable_id="Axe")
        item = CatalogueEntry.objects.get(kind="item", stable_id="Base.TestHammer")
        self.assertEqual(TraitDetails.objects.get(entry=trait).xp_boosts, {"Aiming": 1})
        self.assertEqual(OccupationDetails.objects.get(entry=occupation).point_cost, -2)
        self.assertEqual(SkillDetails.objects.get(entry=skill).level_xp[-1], 6000)
        self.assertEqual(skill.display_name, "Knapping")
        self.assertEqual(SkillDetails.objects.get(entry=skill).category, "Crafting")
        self.assertEqual(SkillDetails.objects.get(entry=axe).category, "Combat")
        self.assertEqual(
            SkillDetails.objects.get(entry=skill).description,
            "Shape stone tools.",
        )
        self.assertEqual(
            CatalogueAsset.objects.get(entry=occupation).source_key,
            "profession_hammer2",
        )
        item_details = ItemDetails.objects.get(entry=item)
        self.assertEqual(item.display_name, "Test Claw Hammer")
        self.assertEqual(item_details.capabilities, ["tool", "weapon"])
        self.assertEqual(item_details.display_category.stable_id, "ToolWeapon")
        self.assertEqual(item_details.display_category.display_name, "Tool/Weapon")
        self.assertEqual(item_details.weapon_skill.entry.stable_id, "SmallBlunt")
        self.assertEqual(item_details.weapon_skill.entry.display_name, "Small Blunt")
        self.assertEqual(item_details.weight, 1.5)
        self.assertEqual(item_details.raw_properties["Icon"], "Hammer")
        self.assertIn("6 created", output.getvalue())

    def test_pzwiki_icon_import_uses_catalogue_texture_keys(self):
        trait = CatalogueEntry.objects.create(
            kind=CatalogueEntry.Kind.TRAIT,
            stable_id="base:nightvision",
            display_name="Cat's Eyes",
            introduced_in="42.test",
            icon_key="trait_nightvision",
        )
        occupation = CatalogueEntry.objects.create(
            kind=CatalogueEntry.Kind.OCCUPATION,
            stable_id="base:carpenter",
            display_name="Carpenter",
            introduced_in="42.test",
            icon_key="profession_hammer2",
        )
        item_one = CatalogueEntry.objects.create(
            kind=CatalogueEntry.Kind.ITEM,
            stable_id="Base.BookAiming1",
            display_name="Better Aiming",
            introduced_in="42.test",
            icon_key="Book12",
        )
        item_two = CatalogueEntry.objects.create(
            kind=CatalogueEntry.Kind.ITEM,
            stable_id="Base.BookAiming2",
            display_name="Drawing and Shooting",
            introduced_in="42.test",
            icon_key="Book12",
        )
        skill = CatalogueEntry.objects.create(
            kind=CatalogueEntry.Kind.SKILL,
            stable_id="Aiming",
            display_name="Aiming",
            introduced_in="42.test",
            icon_key="perk_Aiming",
        )
        png = b"\x89PNG\r\n\x1a\n" + b"catalogue-test"

        class Headers:
            def __init__(self, content_type):
                self.content_type = content_type

            def get_content_type(self):
                return self.content_type

        class Response:
            def __init__(self, request):
                self.url = request.full_url
                self.is_skill_page = self.url.endswith("/Aiming")
                self.headers = Headers(
                    "text/html" if self.is_skill_page else "image/png"
                )

            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            def read(self):
                if self.is_skill_page:
                    return (
                        b'<div class="infobox"><div>'
                        b'<a href="/wiki/File:Skill_Aiming.png">Aiming</a>'
                        b"</div></div>"
                    )
                return png

            def geturl(self):
                return self.url

        with tempfile.TemporaryDirectory() as media_root:
            with override_settings(MEDIA_ROOT=media_root):
                unavailable = []
                with patch(
                    "zomboid_catalogue.management.commands.import_pzwiki_icons.urlopen",
                    side_effect=lambda request, timeout: Response(request),
                ) as mocked_open:
                    call_command(
                        "import_pzwiki_icons",
                        game_version="42.test",
                        report_output=unavailable,
                        stdout=StringIO(),
                    )

                requested_urls = [
                    call.args[0].full_url for call in mocked_open.call_args_list
                ]
                self.assertTrue(
                    any("Trait_nightvision.png" in url for url in requested_urls)
                )
                self.assertTrue(
                    any("Profession_hammer2.png" in url for url in requested_urls)
                )
                self.assertTrue(any("Book12.png" in url for url in requested_urls))
                self.assertEqual(
                    sum("Book12.png" in url for url in requested_urls),
                    1,
                )
                self.assertTrue(
                    any("Skill_Aiming.png" in url for url in requested_urls)
                )
                self.assertEqual(unavailable, [])
                for entry in (trait, occupation, item_one, item_two, skill):
                    asset = CatalogueAsset.objects.get(entry=entry)
                    self.assertEqual(
                        asset.availability,
                        CatalogueAsset.Availability.IMPORTED,
                    )
                    self.assertEqual(
                        asset.source_type,
                        CatalogueAsset.SourceType.PZWIKI,
                    )
                    self.assertTrue(asset.file.name.endswith(".png"))

                protected_asset = CatalogueAsset.objects.get(entry=trait)
                protected_asset.source_type = CatalogueAsset.SourceType.MANUAL
                protected_asset.save(update_fields=("source_type", "imported_at"))
                rerun_output = StringIO()
                with patch(
                    "zomboid_catalogue.management.commands.import_pzwiki_icons.urlopen",
                    side_effect=lambda request, timeout: Response(request),
                ):
                    call_command(
                        "import_pzwiki_icons",
                        game_version="42.test",
                        stdout=rerun_output,
                    )
                protected_asset.refresh_from_db()
                self.assertEqual(
                    protected_asset.source_type,
                    CatalogueAsset.SourceType.MANUAL,
                )
                self.assertIn(
                    "1 manual assets protected",
                    rerun_output.getvalue(),
                )

        claustrophobic = CatalogueEntry(
            kind=CatalogueEntry.Kind.TRAIT,
            stable_id="base:claustrophobic",
            icon_key="trait_claustrophobic",
        )
        from zomboid_catalogue.management.commands.import_pzwiki_icons import (
            wiki_filename,
        )

        self.assertEqual(
            wiki_filename(claustrophobic),
            "Trait_claustophobic.png",
        )
        for stable_id, expected_filename in {
            "Base.Hammer": "Hammer.png",
            "Base.BallPeenHammer": "BallPeenHammer.png",
        }.items():
            entry = CatalogueEntry(
                kind=CatalogueEntry.Kind.ITEM,
                stable_id=stable_id,
            )
            self.assertEqual(wiki_filename(entry), expected_filename)
        profession_variants = {
            "base:herbalist_prof": "Trait_herbalist.png",
            "base:inventive_prof": "Trait_inventive.png",
            "base:mechanics2": "Trait_mechanics.png",
        }
        for stable_id, expected_filename in profession_variants.items():
            entry = CatalogueEntry(
                kind=CatalogueEntry.Kind.TRAIT,
                stable_id=stable_id,
                icon_key=f"trait_{stable_id.removeprefix('base:')}",
            )
            self.assertEqual(wiki_filename(entry), expected_filename)


class CatalogueAdminTests(TestCase):
    def test_catalogue_role_can_open_catalogue_admin(self):
        call_command("bootstrap_roles")
        user = Participant.objects.create_user(
            email="integration@example.com",
            nickname="Integration",
            password="Local-test-password-482!",
            is_active=True,
        )
        user.groups.add(Group.objects.get(name="Zomboid Integration"))
        user.refresh_from_db()
        self.assertTrue(user.is_staff)
        self.client.force_login(user)

        response = self.client.get(
            reverse("admin:zomboid_catalogue_catalogueentry_changelist")
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Project Zomboid Catalogue")
        self.assertEqual(
            self.client.get(
                reverse("admin:zomboid_catalogue_traitdetails_changelist")
            ).status_code,
            200,
        )
        self.assertEqual(
            self.client.get(
                reverse("admin:zomboid_catalogue_catalogueasset_changelist")
            ).status_code,
            200,
        )
