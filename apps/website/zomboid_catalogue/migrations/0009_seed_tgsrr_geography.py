from django.db import migrations


OUTPOSTS = (
    ("brandenburg", "Brandenburg", (2093, 6029, 0), (2068, 6002, 2099, 6045), ("6473958824083477",)),
    ("echo_creek", "Echo Creek", (3538, 11207, 0), (3531, 11198, 3555, 11224), ("12103479833133062",)),
    ("ekron", "Ekron", (443, 9923, 0), (438, 9913, 470, 9942), ("10696053409972226", "10696053409972269")),
    ("fallas_lake", "Fallas Lake", (7222, 8526, 0), (7217, 8520, 7229, 8539), ("9288794490535943",)),
    ("hog_wallow_military_base", "Hog Wallow Military Base", (5559, 12487, 0), (5536, 12439, 5583, 12505), ("13510889076424704", "13510889076424705")),
    ("irvington", "Irvington", (2433, 14227, 0), (2406, 14211, 2440, 14255), ("15481162373791744", "15481162373791782")),
    ("louisville", "Louisville", (12608, 3369, 0), (12599, 3353, 12618, 3384), ("3659385150636034",)),
    ("march_ridge", "March Ridge", (10330, 12788, 0), (10317, 12779, 10345, 12816), ("13792445657513985",)),
    ("muldraugh", "Muldraugh", (10760, 10165, 0), (10750, 10160, 10773, 10170), ("10977700185374723",)),
    ("riverside", "Riverside", (6549, 5368, 0), (6542, 5351, 6585, 5387), ("5629606908395530",)),
    ("rosewood", "Rosewood", (8134, 11518, 0), (8118, 11504, 8155, 11525), ("12385032119255075",)),
    ("valley_station", "Valley Station", (12849, 4953, 0), (12843, 4949, 12869, 4965), ("5348239305867264", "5348239305867265")),
    ("west_point", "West Point", (11970, 7000, 0), (11959, 6975, 11985, 7007), ("7600021939683331",)),
)

LANDMARKS = (
    ("star_eplex_cinema", "StarEplex Cinema", (13637, 5887, 0), ("6192677120901126",)),
    ("twiggys", "Twiggy's", (12067, 6802, 0), ("7318551257939979",)),
    ("fossoil_hq", "Fossoil Headquarters", (12083, 1605, 0), ("1689051723726860",)),
    ("gas2go_facility", "Gas2Go Facility", (12071, 1435, 0), ("1407576747016211", "1407576747016212", "1407576747016226")),
    ("gigamart_hq", "Gigamart Headquarters", (12644, 1685, 0), ("1689060313661461",)),
    ("big_spiffos", "Big Spiffo's", (12435, 3784, 0), ("3940855832379393",)),
    ("spiffos_hq", "Spiffo's Headquarters", (12708, 1607, 1), ("1689060313661459",)),
    ("scarlet_oak_distillery", "Scarlet Oak Distillery", (12015, 2040, 0), ("1970522405470208",)),
    ("scarlett_oak_airport", "Scarlett Oak Airport Distillery", (15307, 3259, 0), ("3377953123598339",)),
    ("knox_distillery", "Knox Distillery", (12906, 1368, 0), ("1407589631918092",)),
    ("grand_ohio_mall", "Grand Ohio Mall", (13623, 1365, 0), ("1126123245142018",)),
    ("wheat_dream_factory", "The Wheat Dream Factory", (15351, 3150, 1), ("3377953123598337",)),
    ("cockayne_inc", "Cockayne Inc.", (15488, 3079, 0), ("3377957418565636",)),
    ("wizards_keep", "The Wizard's Keep", (1760, 14784, 0), ("16044099442311170",)),
    ("doe_valley_bunker", "Bunker", (5576, 9365, -1), ("10133189355896832",)),
    ("muldraugh_radio_tower", "Muldraugh Radio Tower", (10253, 8734, 0), ("9570321006854147",)),
    ("riverside_radio_tower", "Riverside Radio Tower", (4833, 6279, 0), ("6755476750467072",)),
    ("brandenburg_detention_center", "Brandenburg Detention Centre", (1411, 5899, 0), ("6192470962470913",)),
    ("mccoy_estate", "McCoy Estate", (10086, 8261, 1), ("9007366758465536",)),
    ("fallas_luxury_cabins", "Remote Luxury Cabins", (6367, 7620, 2), ("8162877403824129",)),
    ("airport_atc_tower", "Airport ATC Tower", (15361, 2669, 8), ("2815003170177024",)),
)


def seed_geography(apps, schema_editor):
    Entry = apps.get_model("zomboid_catalogue", "CatalogueEntry")
    Version = apps.get_model("zomboid_catalogue", "MapLocationVersion")
    Building = apps.get_model("zomboid_catalogue", "MapLocationBuilding")

    def install(kind, location_type, stable_id, name, anchor, bounds, buildings):
        entry, _ = Entry.objects.get_or_create(
            kind=kind,
            stable_id=stable_id,
            introduced_in="42.20",
            defaults={"display_name": name, "is_active": True},
        )
        version, _ = Version.objects.update_or_create(
            entry=entry,
            game_version="42.20",
            registry_version=1,
            defaults={
                "location_type": location_type,
                "anchor_x": anchor[0], "anchor_y": anchor[1], "anchor_z": anchor[2],
                "min_x": bounds[0] if bounds else None,
                "min_y": bounds[1] if bounds else None,
                "max_x": bounds[2] if bounds else None,
                "max_y": bounds[3] if bounds else None,
            },
        )
        for building_id in buildings:
            Building.objects.get_or_create(
                location_version=version, building_id=building_id
            )

    for stable_id, name, anchor, bounds, buildings in OUTPOSTS:
        install("outpost", "outpost", stable_id, name, anchor, bounds, buildings)
    for stable_id, name, anchor, buildings in LANDMARKS:
        install("location", "landmark", stable_id, name, anchor, None, buildings)


class Migration(migrations.Migration):
    dependencies = [("zomboid_catalogue", "0008_maplocationversion_maplocationbuilding_and_more")]
    operations = [migrations.RunPython(seed_geography, migrations.RunPython.noop)]
