import re
from urllib.parse import urlsplit

from django import template
from django.utils.html import conditional_escape, format_html
from django.utils.safestring import mark_safe

from pages.community_stats import build_community_stats
from pages.models import SectionItem


register = template.Library()
LINK_PATTERN = re.compile(r"\[([^\]\n]+)\]\(([^\s)]+)\)")


def safe_link_destination(destination):
    if destination.startswith("/") and not destination.startswith("//"):
        return True
    if destination.startswith("#"):
        return True
    return urlsplit(destination).scheme.lower() in {"http", "https", "mailto"}


def render_inline_links(value):
    rendered = []
    cursor = 0
    for match in LINK_PATTERN.finditer(value):
        rendered.append(str(conditional_escape(value[cursor:match.start()])))
        label, destination = match.groups()
        if safe_link_destination(destination):
            rendered.append(str(format_html('<a href="{}">{}</a>', destination, label)))
        else:
            rendered.append(str(conditional_escape(match.group(0))))
        cursor = match.end()
    rendered.append(str(conditional_escape(value[cursor:])))
    return "".join(rendered)


@register.filter
def safe_text(value):
    paragraphs = re.split(r"(?:\r?\n){2,}", str(value or ""))
    rendered = []
    for paragraph in paragraphs:
        content = render_inline_links(paragraph)
        content = re.sub(r"\r?\n", "<br>", content)
        rendered.append(f"<p>{content}</p>")
    return mark_safe("\n".join(rendered))


def audience_is_visible(audience, user):
    if audience == "everyone":
        return True
    if audience == "visitors":
        return not user.is_authenticated
    if audience == "signed_in":
        return user.is_authenticated
    return False


@register.simple_tag(takes_context=True)
def visible_managed_cards(context, block):
    user = context["request"].user
    visible = []
    for item in block.items.all():
        audience = block.audience if item.audience == SectionItem.Audience.INHERIT else item.audience
        if audience_is_visible(audience, user):
            visible.append(item)
    return visible


@register.inclusion_tag(
    "registry/blocks/community_stats.html", takes_context=True
)
def managed_community_stats(context, block):
    return {
        "request": context.get("request"),
        "stats": build_community_stats(block.community_stats_config),
    }
