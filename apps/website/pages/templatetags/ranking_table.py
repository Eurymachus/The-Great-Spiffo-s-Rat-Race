from django import template

from pages.ranking_config import validate_ranking_config
from registry.leaderboard import build_ranking_table


register = template.Library()


@register.inclusion_tag("registry/blocks/ranking_table.html", takes_context=True)
def managed_ranking_table(context, block):
    config = validate_ranking_config(block.ranking_config)
    return {
        "request": context["request"],
        "block": block,
        "config": config,
        "entries": build_ranking_table(config),
    }
