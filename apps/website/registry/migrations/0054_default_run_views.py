from django.db import migrations


def seed(apps, schema_editor):
    View = apps.get_model('registry', 'RunSavedView')
    for key, name, filters in [
        ('review', 'Needs Review', {'work': 'review'}),
        ('audit', 'No Recent Audit', {'audit': 'unaudited'}),
        ('active', 'Active', {'lifecycle_status': 'active'}),
        ('all', 'All', {}),
    ]:
        View.objects.get_or_create(system_key=key, defaults={'name': name, 'shared': True, 'filters': filters})


class Migration(migrations.Migration):
    dependencies = [('registry', '0053_saved_run_views')]
    operations = [migrations.RunPython(seed, migrations.RunPython.noop)]
