import re
from urllib.parse import urlsplit

from django import template
from django.utils.html import conditional_escape, format_html
from django.utils.safestring import mark_safe


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
