from django.db import migrations


class Migration(migrations.Migration):
    # Keep the applied dependency node; obsolete development-history backfill is retired.
    dependencies = [("registry", "0070_entertainment_literature")]
    operations = []
