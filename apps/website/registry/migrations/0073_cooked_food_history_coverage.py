from django.db import migrations


def mark_existing_days_unknown(apps, schema_editor):
    # Before this collector, sealed rows have no cooked-food collection observations.
    # Mark that absence once so incremental approvals cannot turn it into zero.
    Daily = apps.get_model("registry", "RunDailyRecord")
    pending = []
    for day in Daily.objects.using(schema_editor.connection.alias).all().iterator(chunk_size=500):
        flags = list(day.partial_metrics or [])
        if "cookedFood" not in flags:
            day.partial_metrics = [*flags, "cookedFood"]
            day.partial = True
            pending.append(day)
        if len(pending) >= 500:
            Daily.objects.using(schema_editor.connection.alias).bulk_update(pending, ["partial_metrics", "partial"])
            pending = []
    if pending:
        Daily.objects.using(schema_editor.connection.alias).bulk_update(pending, ["partial_metrics", "partial"])


class Migration(migrations.Migration):
    dependencies = [("registry", "0072_cooked_food_collected")]
    operations = [migrations.RunPython(mark_existing_days_unknown, migrations.RunPython.noop)]
