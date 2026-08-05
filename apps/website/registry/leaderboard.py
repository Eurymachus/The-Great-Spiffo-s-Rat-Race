from .models import ChallengeRun, LegacyRun
from .run_public import build_public_run_context
from pages.ranking_config import default_ranking_config, validate_ranking_config
from zomboid_catalogue.models import CatalogueAsset


LEADERBOARD_CATEGORY_WEIGHTS = {
    "kills": 2,
    "outposts": 1,
    "skills": 1,
}


def _ratio(value):
    return max(0.0, min(1.0, value if isinstance(value, (int, float)) else 0.0))


def weighted_completion(projection):
    categories = projection.get("challengeProgress", {}).get("categories", {})
    weighted_total = 0.0
    applied_weight = 0.0
    for key, weight in LEADERBOARD_CATEGORY_WEIGHTS.items():
        category = categories.get(key, {}) if isinstance(categories, dict) else {}
        if not isinstance(category, dict) or not category.get("available"):
            continue
        weighted_total += _ratio(category.get("progress")) * weight
        applied_weight += weight
    return round(weighted_total / applied_weight * 100, 2) if applied_weight else 0.0


def _projection_build_value(projection, kind):
    metadata = projection.get("metadata", {}) if isinstance(projection, dict) else {}
    challenge = projection.get("challenge", {}) if isinstance(projection, dict) else {}
    if not isinstance(metadata, dict):
        metadata = {}
    if not isinstance(challenge, dict):
        challenge = {}
    if kind == "game":
        return str(
            projection.get("gameBuild")
            or metadata.get("gameBuild")
            or metadata.get("gameVersion")
            or ""
        )
    return str(
        projection.get("challengeBuild")
        or challenge.get("build")
        or challenge.get("version")
        or ""
    )


def _entry_order_key(entry, ordering):
    primary = {
        "weighted_completion": entry["completion"],
        "kills": entry["kills"],
        "outposts": entry["outposts_completed"],
        "skills": entry["maxed_skills"],
        "verified_at": entry["verified_at"],
    }[ordering]
    return (
        primary,
        entry["completion"],
        entry["kills"],
        entry["outposts_completed"],
        entry["maxed_skills"],
        entry["verified_at"],
        str(entry["run"].pk),
    )


def build_ranking_table(raw_config=None):
    config = validate_ranking_config(raw_config or default_ranking_config())
    if config["source"] in {"legacy_leaderboard", "legacy_hall_of_fame"}:
        return _build_legacy_ranking_table(config)
    runs = ChallengeRun.objects.filter(
        status=ChallengeRun.Status.OFFICIAL,
        participant__isnull=False,
        approved_submission__isnull=False,
    ).select_related(
        "participant",
        "participant__primary_streaming_account",
        "approved_submission",
        "challenge_mode",
    )
    if config["lifecycles"]:
        runs = runs.filter(lifecycle_status__in=config["lifecycles"])
    if config["challenge_modes"]:
        runs = runs.filter(challenge_mode_id__in=config["challenge_modes"])
    if config["participants"]:
        runs = runs.filter(participant_id__in=config["participants"])

    candidates = []
    for run in runs:
        projection = run.approved_submission.projection or {}
        if config["game_builds"] and _projection_build_value(projection, "game") not in config["game_builds"]:
            continue
        if config["challenge_builds"] and _projection_build_value(projection, "challenge") not in config["challenge_builds"]:
            continue
        presented = build_public_run_context(run)
        outposts = presented["outposts"]
        selected_traits = presented["selected_traits"]
        score = weighted_completion(projection)
        verified_at = (
            run.approved_submission.reviewed_at
            or run.approved_submission.generated_at
        )
        primary_channel = run.participant.primary_streaming_account
        if (
            primary_channel
            and primary_channel.status == primary_channel.Status.CONNECTED
            and primary_channel.provider in (
                primary_channel.Provider.TWITCH,
                primary_channel.Provider.YOUTUBE,
            )
        ):
            source_url = primary_channel.channel_url
            stream_provider = primary_channel.provider
        else:
            source_url = ""
            stream_provider = ""
        entry = {
            "run": run,
            "participant": run.participant,
            "racer": run.participant.nickname,
            "survivor": run.character_name or "Unnamed survivor",
            "completion": score,
            "kills": run.approved_submission.current_kills,
            "outposts_completed": sum(item["complete"] for item in outposts),
            "outposts_total": len(outposts),
            "maxed_skills": presented["mastered_skills"],
            "skills_total": presented["overall_skill_count"],
            "in_game_day": run.in_game_day,
            "verified_at": verified_at,
            "source_url": source_url,
            "stream_provider": stream_provider,
            "profession": presented["profession"],
            "profession_icon_url": presented["profession_icon_url"],
            "selected_traits": selected_traits,
            "negative_traits": [
                trait for trait in selected_traits if trait["is_negative"]
            ],
            "positive_traits": [
                trait for trait in selected_traits if not trait["is_negative"]
            ],
        }
        entry["sort_key"] = _entry_order_key(entry, config["ordering"])
        candidates.append(entry)

    if config["selection"] == "all":
        entries = candidates
    else:
        selected = {}
        for entry in candidates:
            previous = selected.get(entry["run"].participant_id)
            if config["selection"] == "latest_per_participant":
                candidate_key = (
                    entry["verified_at"], entry["run"].event_sequence, str(entry["run"].pk),
                )
                previous_key = (
                    previous["verified_at"], previous["run"].event_sequence, str(previous["run"].pk),
                ) if previous else None
            else:
                candidate_key = entry["sort_key"]
                previous_key = previous["sort_key"] if previous else None
            if previous is None or candidate_key > previous_key:
                selected[entry["run"].participant_id] = entry
        entries = list(selected.values())
    entries = sorted(entries, key=lambda entry: entry["sort_key"], reverse=True)[:config["limit"]]
    build_header_icon = (
        CatalogueAsset.objects.filter(
            entry__kind="item",
            entry__stable_id="Base.BallPeenHammer",
            role=CatalogueAsset.Role.ICON,
            availability=CatalogueAsset.Availability.IMPORTED,
        )
        .exclude(file="")
        .order_by("-entry__introduced_in", "entry__stable_id")
        .first()
    )
    build_header_icon_url = build_header_icon.file.url if build_header_icon else ""
    for rank, entry in enumerate(entries, start=1):
        entry["rank"] = rank
        entry["build_header_icon_url"] = build_header_icon_url
    return entries


def _build_legacy_ranking_table(config):
    entries = []
    submission_relation = (
        "current_submission" if config["source"] == "legacy_leaderboard" else "best_submission"
    )
    queryset = LegacyRun.objects.select_related(
        submission_relation,
        f"{submission_relation}__import_review",
        "claimed_participant",
        "claimed_participant__primary_streaming_account",
    ).filter(**{f"{submission_relation}__isnull": False})
    if config["source"] == "legacy_leaderboard":
        queryset = queryset.filter(lifecycle=LegacyRun.Lifecycle.ACTIVE)
    if config["participants"]:
        queryset = queryset.filter(claimed_participant_id__in=config["participants"])
    for record in queryset:
        submission = getattr(record, submission_relation)
        participant = record.claimed_participant
        primary_channel = participant.primary_streaming_account if participant else None
        if primary_channel and primary_channel.status == primary_channel.Status.CONNECTED:
            source_url = primary_channel.channel_url
            stream_provider = primary_channel.provider
        else:
            source_url = ""
            stream_provider = ""
        if submission.source == submission.Source.PARTICIPANT:
            approved_at = submission.reviewed_at
        else:
            approved_at = (
                submission.import_review.imported_at
                if submission.import_review_id and submission.import_review.imported_at
                else submission.reviewed_at
            )
        entries.append({
            "run": None,
            "legacy_run": record,
            "source_rank": submission.source_rank or 0,
            "racer": participant.nickname if participant else record.legacy_participant_name,
            "participant": participant,
            "survivor": submission.character_name or record.character_name,
            "completion": float(submission.challenge_progress),
            "kills": submission.zombie_kills,
            "outposts_completed": submission.outposts_cleared,
            "outposts_total": 13,
            "maxed_skills": submission.maxed_skills,
            "skills_total": 35,
            "in_game_day": max(1, int(submission.survival_days)),
            "verified_at": approved_at,
            "source_url": source_url,
            "stream_provider": stream_provider,
            "build_header_icon_url": "",
        })
    sort_keys = {
        "weighted_completion": lambda entry: (entry["completion"], entry["kills"]),
        "kills": lambda entry: (entry["kills"], entry["completion"]),
        "outposts": lambda entry: (entry["outposts_completed"], entry["completion"]),
        "skills": lambda entry: (entry["maxed_skills"], entry["completion"]),
        "verified_at": lambda entry: (
            entry["verified_at"].timestamp() if entry["verified_at"] else 0,
            entry["completion"],
        ),
    }
    if config["ordering"] == "source_rank":
        entries.sort(
            key=lambda entry: (
                entry["completion"], entry["kills"], entry["outposts_completed"],
                entry["maxed_skills"], entry["in_game_day"], entry["racer"].casefold(),
            ),
            reverse=True,
        )
    else:
        entries.sort(key=sort_keys[config["ordering"]], reverse=True)
    entries = entries[:config["limit"]]
    for displayed_rank, entry in enumerate(entries, start=1):
        entry["rank"] = displayed_rank
    return entries


def build_current_leaderboard():
    config = default_ranking_config()
    config["lifecycles"] = [ChallengeRun.Lifecycle.ACTIVE]
    return build_ranking_table(config)
