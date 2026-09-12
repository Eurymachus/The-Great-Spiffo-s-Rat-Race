from django.db import migrations


def active_audit_view(apps, schema_editor):
    View = apps.get_model("registry", "RunSavedView")
    for view in View.objects.using(schema_editor.connection.alias).filter(system_key="audit", shared=True):
        view.filters = {**view.filters, "lifecycle_status": "active"}
        view.save(update_fields=["filters"])


class Migration(migrations.Migration):
    dependencies = [("registry", "0056_challenge_mode_evidence_required")]
    operations = [migrations.RunPython(active_audit_view, migrations.RunPython.noop)]
