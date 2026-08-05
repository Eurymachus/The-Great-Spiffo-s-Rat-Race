from django import template

from pages.ranking_config import validate_ranking_config
from registry.leaderboard import build_ranking_table
from registry.models import LegacyRun, LegacyRunClaim


register = template.Library()


@register.inclusion_tag("registry/blocks/ranking_table.html", takes_context=True)
def managed_ranking_table(context, block):
    config = validate_ranking_config(block.ranking_config)
    request = context["request"]
    entries = build_ranking_table(config)
    is_legacy_source = config["source"] in {
        "legacy_leaderboard",
        "legacy_hall_of_fame",
    }
    claim_journey_complete = False
    if request.user.is_authenticated and is_legacy_source:
        claim_journey_complete = (
            LegacyRun.objects.filter(claimed_participant=request.user).exists()
            or LegacyRunClaim.objects.filter(
                participant=request.user,
                status=LegacyRunClaim.Status.APPROVED,
            ).exists()
        )
    show_legacy_claims = (
        request.user.is_authenticated
        and is_legacy_source
        and not claim_journey_complete
    )
    if show_legacy_claims:
        claims = {
            claim.run_id: claim
            for claim in LegacyRunClaim.objects.filter(participant=request.user)
        }
        has_other_link = LegacyRun.objects.filter(
            claimed_participant=request.user
        ).exists()
        has_other_open_claim = LegacyRunClaim.objects.filter(
            participant=request.user,
            status__in=(LegacyRunClaim.Status.PENDING, LegacyRunClaim.Status.APPROVED),
        ).exists()
        for entry in entries:
            legacy_run = entry["legacy_run"]
            claim = claims.get(legacy_run.pk)
            if legacy_run.claimed_participant_id == request.user.pk:
                entry["claim_state"] = "claimed"
            elif legacy_run.claimed_participant_id:
                entry["claim_state"] = "unavailable"
            elif claim and claim.status == LegacyRunClaim.Status.PENDING:
                entry["claim_state"] = "pending"
            elif claim and claim.status == LegacyRunClaim.Status.APPROVED:
                entry["claim_state"] = "claimed"
            elif claim and claim.status == LegacyRunClaim.Status.DECLINED:
                entry["claim_state"] = "declined"
            elif has_other_link or has_other_open_claim:
                entry["claim_state"] = "unavailable"
            else:
                entry["claim_state"] = "available"
    return {
        "request": request,
        "block": block,
        "config": config,
        "entries": entries,
        "show_legacy_claims": show_legacy_claims,
    }
