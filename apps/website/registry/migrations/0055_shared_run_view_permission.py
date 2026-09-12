from django.db import migrations


def grant(apps, schema_editor):
    ContentType = apps.get_model('contenttypes', 'ContentType')
    Permission = apps.get_model('auth', 'Permission')
    Group = apps.get_model('auth', 'Group')
    content_type, _ = ContentType.objects.get_or_create(app_label='registry', model='runsavedview')
    permission, _ = Permission.objects.get_or_create(content_type=content_type, codename='manage_shared_run_views', defaults={'name': 'Can manage shared Challenge Runs views'})
    group = Group.objects.filter(name='Challenge Administrator').first()
    if group:
        group.permissions.add(permission)


class Migration(migrations.Migration):
    dependencies = [('registry', '0054_default_run_views')]
    operations = [migrations.RunPython(grant, migrations.RunPython.noop)]
