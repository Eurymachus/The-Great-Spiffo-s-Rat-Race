from django.conf import settings
from branding.models import SiteBranding, WebsiteTheme


def site_identity(request):
    company_number = settings.SITE_COMPANY_NUMBER
    # Settings remain a safe fallback while migrations are being applied.
    brand = SiteBranding.current()
    theme = brand.active_theme if brand else None
    preview_theme_id = request.GET.get("theme-preview")
    if (
        preview_theme_id
        and request.user.is_authenticated
        and request.user.has_perm("branding.change_websitetheme")
    ):
        theme = WebsiteTheme.objects.filter(pk=preview_theme_id).first() or theme
    return {
        "site_legal_name": settings.SITE_LEGAL_NAME,
        "site_company_number": company_number,
        "site_registered_office": settings.SITE_REGISTERED_OFFICE,
        "site_privacy_email": settings.SITE_PRIVACY_EMAIL,
        "site_public_url": settings.SITE_PUBLIC_URL,
        "site_full_title": brand.full_title if brand else settings.SITE_FULL_TITLE,
        "site_short_title": brand.short_title if brand else settings.SITE_SHORT_TITLE,
        "site_tagline": brand.tagline if brand else settings.SITE_TAGLINE,
        "site_welcome_message": (
            brand.welcome_message if brand else settings.SITE_WELCOME_MESSAGE
        ),
        "site_former_participant_label": (
            brand.former_participant_label
            if brand
            else settings.SITE_FORMER_PARTICIPANT_LABEL
        ),
        "site_disclaimer": brand.disclaimer if brand else settings.SITE_DISCLAIMER,
        "site_companies_house_url": (
            "https://find-and-update.company-information.service.gov.uk/company/"
            f"{company_number}"
        ),
        "site_theme": theme,
        "site_theme_is_preview": bool(
            theme and preview_theme_id and str(theme.pk) == preview_theme_id
        ),
    }
