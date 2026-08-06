from django.db import migrations


def add_real_hours_raced(apps, schema_editor):
    PageBlock = apps.get_model("pages", "PageBlock")
    for block in PageBlock.objects.filter(block_type="community_stats"):
        config = dict(block.community_stats_config or {})
        metrics = list(config.get("metrics") or [])
        if "real_hours_raced" not in metrics:
            metrics.append("real_hours_raced")
            config["metrics"] = metrics
            block.community_stats_config = config
            block.save(update_fields=("community_stats_config",))


class Migration(migrations.Migration):

    dependencies = [
        ("pages", "0032_alter_pageblock_separator_spacing_and_more"),
    ]

    operations = [
        migrations.RunPython(add_real_hours_raced, migrations.RunPython.noop),
    ]
