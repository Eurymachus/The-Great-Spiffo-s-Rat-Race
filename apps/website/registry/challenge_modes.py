from .models import ChallengeMode, ChallengeModeAlias


def resolve_challenge_mode(challenge_id, game_mode_name=""):
    if challenge_id:
        mode = ChallengeMode.objects.filter(key=challenge_id).first()
        if mode:
            return mode
        alias = (
            ChallengeModeAlias.objects.select_related("challenge_mode")
            .filter(key=challenge_id)
            .first()
        )
        if alias:
            return alias.challenge_mode
    if game_mode_name:
        return ChallengeMode.objects.filter(game_mode_name=game_mode_name).first()
    return None
