from django.core.exceptions import ValidationError


METRICS = {
    "active_runs": "Rats in the Race",
    "total_kills": "Zombies Eliminated",
    "total_days": "Days Endured",
    "outposts_claimed": "Outposts Claimed",
    "fallen_survivors": "Fallen Survivors",
    "average_kills_per_day": "Average Kills per Day",
    "real_hours_raced": "Real Hours Raced",
}

DEFAULT_METRICS = list(METRICS)


def default_community_stats_config():
    return {
        "metrics": list(DEFAULT_METRICS),
        "eyebrow": "The race so far",
        "heading": "Rat Race by the numbers",
        "show_heading": False,
    }


def validate_community_stats_config(raw_config):
    config = default_community_stats_config()
    if raw_config:
        if not isinstance(raw_config, dict):
            raise ValidationError("Community statistics configuration must be an object.")
        config.update(raw_config)
    metrics = config.get("metrics")
    if not isinstance(metrics, list) or not metrics:
        raise ValidationError("Choose at least one community statistic.")
    if len(metrics) != len(set(metrics)):
        raise ValidationError("Each community statistic can be selected once.")
    unknown = set(metrics) - set(METRICS)
    if unknown:
        raise ValidationError("A selected community statistic is not supported.")
    config["metrics"] = metrics
    config["eyebrow"] = str(config.get("eyebrow", ""))[:120]
    config["heading"] = str(config.get("heading", ""))[:160]
    config["show_heading"] = bool(config.get("show_heading", False))
    return config


def _survival_days(run):
    world_ages = [
        event.get("world_age_hours")
        for event in (run.latest_events or [])
        if isinstance(event, dict)
        and isinstance(event.get("world_age_hours"), (int, float))
    ]
    return max(world_ages, default=0) / 24


def _completed_outposts(run):
    authoritative = list(run.authoritative_outposts.all())
    if authoritative:
        return sum(outpost.complete for outpost in authoritative)
    projection = run.approved_submission.projection or {}
    outposts = projection.get("outposts", []) if isinstance(projection, dict) else []
    return sum(bool(item.get("complete")) for item in outposts if isinstance(item, dict))


def _real_hours_raced(projection):
    active_gameplay = projection.get("activeGameplay", {}) if isinstance(projection, dict) else {}
    milliseconds = active_gameplay.get("milliseconds", 0) if isinstance(active_gameplay, dict) else 0
    if not isinstance(milliseconds, (int, float)) or milliseconds < 0:
        return 0
    return milliseconds / 3_600_000


def _display_value(key, value):
    if key in ("average_kills_per_day", "real_hours_raced"):
        return f"{value:,.1f}"
    return f"{value:,}"


def build_community_stats(raw_config=None):
    from registry.models import ChallengeRun

    config = validate_community_stats_config(raw_config or {})
    runs = list(
        ChallengeRun.objects.filter(
            status=ChallengeRun.Status.OFFICIAL,
            participant__isnull=False,
            approved_submission__isnull=False,
        ).select_related("approved_submission").prefetch_related(
            "authoritative_outposts"
        )
    )
    total_kills = sum(run.approved_submission.current_kills for run in runs)
    total_days = sum(_survival_days(run) for run in runs)
    values = {
        "active_runs": sum(
            run.lifecycle_status == ChallengeRun.Lifecycle.ACTIVE for run in runs
        ),
        "total_kills": total_kills,
        "total_days": round(total_days),
        "outposts_claimed": sum(
            _completed_outposts(run) for run in runs
        ),
        "fallen_survivors": sum(
            run.lifecycle_status == ChallengeRun.Lifecycle.DECEASED for run in runs
        ),
        "average_kills_per_day": round(total_kills / total_days, 1) if total_days else 0,
        "real_hours_raced": round(sum(
            _real_hours_raced(run.approved_submission.projection or {})
            for run in runs
        ), 1),
    }
    return {
        "config": config,
        "metrics": [
            {
                "key": key,
                "label": METRICS[key],
                "value": _display_value(key, values[key]),
            }
            for key in config["metrics"]
        ],
    }
