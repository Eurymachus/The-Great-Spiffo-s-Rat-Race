import re
from decimal import Decimal, ROUND_HALF_UP

from django.core.exceptions import ValidationError


KILL_TARGET = Decimal("1000000")
OUTPOST_TARGET = Decimal("13")
SKILL_TARGET = Decimal("35")
HOURS_PER_DAY = 24
DAYS_PER_MONTH = 30
MONTHS_PER_YEAR = 12


def parse_survival_time(value):
    original = " ".join(str(value or "").strip().split())
    if not original:
        raise ValidationError("Enter the time survived.")

    colon_match = re.fullmatch(r"(\d+):(\d{1,2}):(\d{1,2}):(\d{1,2})", original)
    if colon_match:
        years, months, days, hours = (int(part) for part in colon_match.groups())
    else:
        unit_pattern = re.compile(
            r"(\d+)\s*(years?|yrs?|y|months?|mos?|mo|days?|d|hours?|hrs?|h)\b",
            re.IGNORECASE,
        )
        matches = list(unit_pattern.finditer(original))
        remainder = unit_pattern.sub("", original).replace(",", "").strip()
        if not matches or remainder:
            raise ValidationError(
                "Use YY:MM:DD:HH or words such as 1 year 5 months 20 days 6 hours."
            )
        values = {"years": 0, "months": 0, "days": 0, "hours": 0}
        seen = set()
        for match in matches:
            unit = match.group(2).casefold()
            if unit.startswith(("y",)):
                key = "years"
            elif unit.startswith(("mo",)):
                key = "months"
            elif unit.startswith(("d",)):
                key = "days"
            else:
                key = "hours"
            if key in seen:
                raise ValidationError(f"Enter {key} only once.")
            seen.add(key)
            values[key] = int(match.group(1))
        years, months, days, hours = (
            values["years"], values["months"], values["days"], values["hours"]
        )

    total_hours = (
        years * MONTHS_PER_YEAR * DAYS_PER_MONTH * HOURS_PER_DAY
        + months * DAYS_PER_MONTH * HOURS_PER_DAY
        + days * HOURS_PER_DAY
        + hours
    )
    if total_hours <= 0:
        raise ValidationError("Time survived must be greater than zero.")
    normalized_years, remainder = divmod(total_hours, MONTHS_PER_YEAR * DAYS_PER_MONTH * HOURS_PER_DAY)
    normalized_months, remainder = divmod(remainder, DAYS_PER_MONTH * HOURS_PER_DAY)
    normalized_days, normalized_hours = divmod(remainder, HOURS_PER_DAY)
    full = f"{normalized_years:02d}:{normalized_months:02d}:{normalized_days:02d}:{normalized_hours:02d}"
    decimal_days = (Decimal(total_hours) / Decimal(HOURS_PER_DAY)).quantize(
        Decimal("0.00001"), rounding=ROUND_HALF_UP
    )
    return original, full, decimal_days


def calculate_legacy_progress(kills, outposts, skills):
    kills_ratio = min(Decimal(kills) / KILL_TARGET, Decimal("1"))
    outposts_ratio = min(Decimal(outposts) / OUTPOST_TARGET, Decimal("1"))
    skills_ratio = min(Decimal(skills) / SKILL_TARGET, Decimal("1"))
    return (
        kills_ratio * Decimal("50")
        + outposts_ratio * Decimal("25")
        + skills_ratio * Decimal("25")
    ).quantize(Decimal("0.00001"), rounding=ROUND_HALF_UP)


def legacy_submission_strength(submission):
    return (
        submission.challenge_progress,
        submission.zombie_kills,
        submission.outposts_cleared,
        submission.maxed_skills,
        submission.survival_days,
    )
