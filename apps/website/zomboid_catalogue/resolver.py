from django.db.models import Q

from .models import CatalogueAlias, CatalogueEntry, version_key


def applies_to_version(record, game_version):
    if not game_version:
        return True
    target = version_key(game_version)
    if record.introduced_in and target < version_key(record.introduced_in):
        return False
    if record.removed_in and target >= version_key(record.removed_in):
        return False
    return True


def resolve_identifier(kind, stable_id, game_version=""):
    entries = list(
        CatalogueEntry.objects.filter(
            kind=kind, stable_id=stable_id, is_active=True
        ).order_by("-introduced_in")
    )
    entries.extend(
        alias.entry
        for alias in CatalogueAlias.objects.select_related("entry").filter(
            Q(stable_id=stable_id),
            entry__kind=kind,
            entry__is_active=True,
        )
        if applies_to_version(alias, game_version)
    )
    matches = [
        entry for entry in entries if applies_to_version(entry, game_version)
    ]
    # Multiple versions of one identity are not competing identities. Prefer the
    # latest applicable definition, but do not guess between distinct alias targets.
    unique_matches = {}
    for entry in matches:
        identity = (entry.kind, entry.stable_id)
        previous = unique_matches.get(identity)
        if previous is None or version_key(entry.introduced_in) > version_key(previous.introduced_in):
            unique_matches[identity] = entry
    if len(unique_matches) == 1:
        return next(iter(unique_matches.values()))
    return None
