from django.db import migrations


REPLACEMENTS = (
    ("official Stable Rat Race runs", "Rat Race 2.0 runs"),
    ("Historical Unstable material is preserved for context but does not override the current rules.", "Rat Race 1.0 is still running under its own rules; its material does not override Rat Race 2.0 rules."),
    ("Rat Race (Unstable) leaderboard", "Rat Race 1.0 Leaderboard"),
    ("latest approved Unstable run update", "latest approved Rat Race 1.0 run update. Rat Race 1.0 is still running"),
    ("Legacy rankings", "Rat Race 1.0 rankings"),
    ("Current leaderboard", "Rat Race 2.0 Leaderboard"),
    ("The final historical standings from the Unstable Rat Race challenge.",
     "Personal bests from Rat Race 1.0. The original challenge is still running; active runs can continue submitting updates."),
    ("Legacy Hall of Fame", "Rat Race 1.0 Hall of Fame"),
    ("Legacy Leaderboard", "Rat Race 1.0 Leaderboard"),
    ("Legacy Rat Race", "Rat Race 1.0"),
    ("Unstable Rat Race", "Rat Race 1.0"),
    ("Unstable challenge", "Rat Race 1.0, still running"),
    ("Unstable archive", "Rat Race 1.0"),
    ("Stable challenge", "Rat Race 2.0"),
    ("Rat Race leaderboard", "Rat Race 2.0 Leaderboard"),
)


def edition_copy(value):
    if value == "Legacy":
        return "Rat Race 1.0"
    for old, new in REPLACEMENTS:
        value = value.replace(old, new)
    return value


def update_edition_wording(apps, schema_editor):
    alias = schema_editor.connection.alias
    for model_name, fields in (
        ("Page", ("title",)),
        ("NavigationItem", ("label",)),
        ("PageSection", ("name",)),
        ("PageBlock", ("content",)),
    ):
        model = apps.get_model("pages", model_name)
        for row in model.objects.using(alias).all().iterator():
            changed = []
            for field in fields:
                old = getattr(row, field)
                new = edition_copy(old)
                if old != new:
                    setattr(row, field, new)
                    changed.append(field)
            if model_name == "PageBlock" and row.block_type == "ranking_table":
                config = dict(row.ranking_config or {})
                updated = dict(config)
                for key in ("heading", "eyebrow", "introduction"):
                    if key in updated:
                        updated[key] = edition_copy(updated[key])
                if config.get("source") in {"legacy_leaderboard", "legacy_hall_of_fame"} and config.get("eyebrow") == "B42 Unstable":
                    updated["eyebrow"] = "Rat Race 1.0, still running"
                if config.get("source") == "verified_runs" and config.get("eyebrow") == "Current challenge":
                    updated["eyebrow"] = "Rat Race 2.0"
                if updated != config:
                    row.ranking_config = updated
                    changed.append("ranking_config")
            if changed:
                row.save(using=alias, update_fields=changed)


class Migration(migrations.Migration):
    dependencies = [("pages", "0042_add_council_exploit_rulings")]
    operations = [migrations.RunPython(update_edition_wording, migrations.RunPython.noop)]
