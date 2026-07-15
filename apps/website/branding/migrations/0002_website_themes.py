import django.db.models.deletion
from django.core.validators import RegexValidator
from django.db import migrations, models


hex_colour = RegexValidator(
    regex=r"^#[0-9A-Fa-f]{6}$",
    message="Enter a six-digit hexadecimal colour such as #F2A33A.",
)


PRESETS = {
    "survival-event": {
        "name": "Survival Event", "colour_scheme": "dark", "background_style": "radial",
        "heading_font": "condensed", "body_font": "system", "corner_style": "rounded",
        "shadow_style": "dramatic", "background_colour": "#151912",
        "background_highlight_colour": "#394628", "surface_colour": "#191F15",
        "surface_alt_colour": "#0F130D", "text_colour": "#F6F2DF",
        "muted_text_colour": "#C8CDBD", "accent_colour": "#F2A33A",
        "accent_hover_colour": "#F4AD53", "border_colour": "#586746",
        "accent_text_colour": "#17120A",
        "success_colour": "#A6D66D", "error_colour": "#FF9B91",
    },
    "retro-road-race": {
        "name": "Retro Road Race", "colour_scheme": "light", "background_style": "road",
        "heading_font": "slab", "body_font": "humanist", "corner_style": "subtle",
        "shadow_style": "soft", "background_colour": "#E4C991",
        "background_highlight_colour": "#A8442A", "surface_colour": "#FFF3D6",
        "surface_alt_colour": "#F0D9A9", "text_colour": "#2A1B16",
        "muted_text_colour": "#6F5548", "accent_colour": "#B53624",
        "accent_hover_colour": "#D1492E", "border_colour": "#805E45",
        "accent_text_colour": "#FFF8E8",
        "success_colour": "#39734A", "error_colour": "#A52323",
    },
    "clean-competition": {
        "name": "Clean Competition", "colour_scheme": "dark", "background_style": "flat",
        "heading_font": "system", "body_font": "system", "corner_style": "subtle",
        "shadow_style": "soft", "background_colour": "#0B1220",
        "background_highlight_colour": "#17233A", "surface_colour": "#111C2E",
        "surface_alt_colour": "#09101D", "text_colour": "#F5F7FB",
        "muted_text_colour": "#AEB9CC", "accent_colour": "#4DA3FF",
        "accent_hover_colour": "#78BAFF", "border_colour": "#31425F",
        "accent_text_colour": "#07111F",
        "success_colour": "#63D39A", "error_colour": "#FF8585",
    },
}


def create_presets(apps, schema_editor):
    website_theme = apps.get_model("branding", "WebsiteTheme")
    site_branding = apps.get_model("branding", "SiteBranding")
    themes = {}
    for key, values in PRESETS.items():
        themes[key], _ = website_theme.objects.get_or_create(
            preset_key=key, defaults=values
        )
    branding = site_branding.objects.filter(pk=1).first()
    if branding and not branding.active_theme_id:
        branding.active_theme = themes["survival-event"]
        branding.save(update_fields=("active_theme",))


class Migration(migrations.Migration):
    dependencies = [("branding", "0001_initial")]

    operations = [
        migrations.CreateModel(
            name="WebsiteTheme",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=80, unique=True)),
                ("preset_key", models.CharField(blank=True, editable=False, max_length=40)),
                ("colour_scheme", models.CharField(choices=[("dark", "Dark"), ("light", "Light")], default="dark", max_length=8)),
                ("background_style", models.CharField(choices=[("flat", "Flat"), ("radial", "Atmospheric radial"), ("road", "Road stripes")], default="radial", max_length=12)),
                ("heading_font", models.CharField(choices=[("system", "Modern system"), ("condensed", "Condensed poster"), ("slab", "Slab serif")], default="system", max_length=12)),
                ("body_font", models.CharField(choices=[("system", "Modern system"), ("humanist", "Humanist"), ("mono", "Technical monospace")], default="system", max_length=12)),
                ("corner_style", models.CharField(choices=[("square", "Square"), ("subtle", "Subtle"), ("rounded", "Rounded")], default="rounded", max_length=12)),
                ("shadow_style", models.CharField(choices=[("none", "None"), ("soft", "Soft"), ("dramatic", "Dramatic")], default="dramatic", max_length=12)),
                ("background_colour", models.CharField(default="#151912", max_length=7, validators=[hex_colour])),
                ("background_highlight_colour", models.CharField(default="#394628", max_length=7, validators=[hex_colour])),
                ("surface_colour", models.CharField(default="#191F15", max_length=7, validators=[hex_colour])),
                ("surface_alt_colour", models.CharField(default="#0F130D", max_length=7, validators=[hex_colour])),
                ("text_colour", models.CharField(default="#F6F2DF", max_length=7, validators=[hex_colour])),
                ("muted_text_colour", models.CharField(default="#C8CDBD", max_length=7, validators=[hex_colour])),
                ("accent_colour", models.CharField(default="#F2A33A", max_length=7, validators=[hex_colour])),
                ("accent_hover_colour", models.CharField(default="#F4AD53", max_length=7, validators=[hex_colour])),
                ("accent_text_colour", models.CharField(default="#17120A", max_length=7, validators=[hex_colour])),
                ("border_colour", models.CharField(default="#586746", max_length=7, validators=[hex_colour])),
                ("success_colour", models.CharField(default="#A6D66D", max_length=7, validators=[hex_colour])),
                ("error_colour", models.CharField(default="#FF9B91", max_length=7, validators=[hex_colour])),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"ordering": ("name",)},
        ),
        migrations.AddField(
            model_name="sitebranding",
            name="active_theme",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="active_branding_records", to="branding.websitetheme"),
        ),
        migrations.RunPython(create_presets, migrations.RunPython.noop),
    ]
