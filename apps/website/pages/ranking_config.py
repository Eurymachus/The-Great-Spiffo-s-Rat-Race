from django.core.exceptions import ValidationError


SELECTION_CHOICES = {"all", "best_per_participant", "latest_per_participant"}
SOURCE_CHOICES = {"verified_runs", "legacy_hall_of_fame"}
ORDERING_CHOICES = {"weighted_completion", "kills", "outposts", "skills", "verified_at", "source_rank"}
LIFECYCLE_CHOICES = {"active", "deceased", "abandoned", "completed", "invalidated"}
COLUMN_CHOICES = {
    "participant", "survivor", "build", "progress", "kills",
    "outposts", "skills", "day", "verified",
}
DEFAULT_COLUMNS = [
    "participant", "survivor", "build", "progress", "kills",
    "outposts", "skills", "day", "verified",
]


def default_ranking_config():
    return {
        "source": "verified_runs",
        "challenge_modes": [],
        "game_builds": [],
        "challenge_builds": [],
        "lifecycles": ["active"],
        "participants": [],
        "selection": "best_per_participant",
        "ordering": "weighted_completion",
        "limit": 100,
        "columns": list(DEFAULT_COLUMNS),
        "show_heading": True,
        "eyebrow": "Current challenge",
        "heading": "Rat Race leaderboard",
        "introduction": "Each Rat Racer's highest-ranked eligible survivor, calculated from the latest approved run update.",
        "show_weighting": True,
        "show_build": True,
        "show_details": True,
    }


def _integer_list(value, label):
    if not isinstance(value, list):
        raise ValidationError(f"{label} must be a list.")
    try:
        values = [int(item) for item in value]
    except (TypeError, ValueError) as exc:
        raise ValidationError(f"{label} contains an invalid value.") from exc
    if any(item <= 0 for item in values) or len(values) != len(set(values)):
        raise ValidationError(f"{label} must contain unique positive identifiers.")
    return values


def _string_list(value, label, allowed=None, maximum=20):
    if not isinstance(value, list):
        raise ValidationError(f"{label} must be a list.")
    values = [str(item).strip() for item in value]
    if any(not item or len(item) > 80 for item in values) or len(values) != len(set(values)):
        raise ValidationError(f"{label} contains an invalid or repeated value.")
    if len(values) > maximum or (allowed is not None and not set(values) <= allowed):
        raise ValidationError(f"{label} contains an unsupported value.")
    return values


def validate_ranking_config(value):
    if value in (None, {}):
        value = default_ranking_config()
    if not isinstance(value, dict):
        raise ValidationError("Ranking table configuration must be an object.")
    unknown = set(value) - set(default_ranking_config())
    if unknown:
        raise ValidationError(f"Unsupported ranking option: {sorted(unknown)[0]}.")
    config = default_ranking_config()
    config.update(value)
    if config["source"] not in SOURCE_CHOICES:
        raise ValidationError("Choose a supported ranking source.")
    config["challenge_modes"] = _integer_list(config["challenge_modes"], "Challenge modes")
    config["participants"] = _integer_list(config["participants"], "Participants")
    config["game_builds"] = _string_list(config["game_builds"], "Game builds")
    config["challenge_builds"] = _string_list(config["challenge_builds"], "Challenge builds")
    config["lifecycles"] = _string_list(config["lifecycles"], "Run lifecycles", LIFECYCLE_CHOICES)
    config["columns"] = _string_list(config["columns"], "Columns", COLUMN_CHOICES, len(COLUMN_CHOICES))
    if not config["columns"]:
        raise ValidationError("Choose at least one ranking column.")
    if config["selection"] not in SELECTION_CHOICES:
        raise ValidationError("Choose a supported result selection.")
    if config["ordering"] not in ORDERING_CHOICES:
        raise ValidationError("Choose a supported ranking order.")
    if config["source"] == "verified_runs" and config["ordering"] == "source_rank":
        raise ValidationError("Imported historical rank is only available for the Legacy Hall of Fame source.")
    try:
        config["limit"] = int(config["limit"])
    except (TypeError, ValueError) as exc:
        raise ValidationError("Maximum rows must be a number.") from exc
    if not 1 <= config["limit"] <= 500:
        raise ValidationError("Maximum rows must be between 1 and 500.")
    for key in ("show_heading", "show_weighting", "show_build", "show_details"):
        if not isinstance(config[key], bool):
            raise ValidationError(f"{key.replace('_', ' ').title()} must be on or off.")
    config["heading"] = str(config["heading"]).strip()[:120]
    config["eyebrow"] = str(config["eyebrow"]).strip()[:80]
    config["introduction"] = str(config["introduction"]).strip()[:500]
    return config
