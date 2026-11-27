"""Final setup state from an empty pre-baseline installation, never host data."""
import json
from pathlib import Path

from django.core.management.color import no_style
from django.db import migrations


def install_seed(apps, schema_editor):
    connection = schema_editor.connection
    alias = connection.alias
    rows = json.loads((Path(__file__).parent / "data" / "launch_seed.json").read_text(encoding="utf-8"))
    seeded_models = set()
    relations = []
    for row in rows:
        model = apps.get_model(row["model"])
        values = {}
        for name, value in row["fields"].items():
            field = model._meta.get_field(name)
            if field.many_to_many:
                relations.append((model, row["pk"], name, value))
            else:
                values[field.attname] = value if field.is_relation else field.to_python(value)
        model.objects.using(alias).update_or_create(pk=row["pk"], defaults=values)
        seeded_models.add(model)
    for model, pk, name, values in relations:
        getattr(model.objects.using(alias).get(pk=pk), name).set(values)
    # Explicit seed IDs must not collide with the first administrator-created row.
    with connection.cursor() as cursor:
        for sql in connection.ops.sequence_reset_sql(no_style(), sorted(seeded_models, key=lambda m: m._meta.label)):
            cursor.execute(sql)


class Migration(migrations.Migration):
    dependencies = [
        ("administration", "0001_launch_schema"),
        ("branding", "0002_launch_schema"),
        ("operations", "0002_launch_schema"),
        ("pages", "0001_launch_schema"),
        ("registry", "0001_launch_schema"),
        ("zomboid_catalogue", "0001_launch_schema"),
    ]
    operations = [migrations.RunPython(install_seed, migrations.RunPython.noop)]
