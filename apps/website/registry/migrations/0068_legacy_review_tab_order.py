from django.db import migrations


def reorder_defaults(apps, schema_editor):
    Preference = apps.get_model("registry", "LegacyViewPreference")
    old = ("all", "active", "updates", "claims", "imports")
    new = ("claims", "updates", "all", "active", "imports")
    records = Preference.objects.using(schema_editor.connection.alias)
    for user_id in records.order_by().values_list("user_id", flat=True).distinct():
        prefs = list(records.filter(user_id=user_id).select_related("view").order_by("position", "pk"))
        keys = [pref.view.system_key for pref in prefs]
        if keys != [key for key in old if key in keys]:
            continue
        for position, pref in enumerate(sorted(prefs, key=lambda pref: new.index(pref.view.system_key))):
            records.filter(pk=pref.pk).update(position=position)


class Migration(migrations.Migration):
    dependencies = [("registry", "0067_legacy_saved_views")]
    operations = [migrations.RunPython(reorder_defaults, migrations.RunPython.noop)]
