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
        "site_homepage_small_heading": (
            brand.homepage_small_heading
            if brand
            else settings.SITE_HOMEPAGE_SMALL_HEADING
        ),
        "site_homepage_main_heading": (
            brand.homepage_main_heading
            if brand
            else settings.SITE_HOMEPAGE_MAIN_HEADING
        ),
        "site_homepage_introduction": (
            brand.homepage_introduction
            if brand
            else settings.SITE_HOMEPAGE_INTRODUCTION
        ),
        "site_homepage_primary_button": (
            brand.homepage_primary_button
            if brand
            else settings.SITE_HOMEPAGE_PRIMARY_BUTTON
        ),
        "site_homepage_secondary_link": (
            brand.homepage_secondary_link
            if brand
            else settings.SITE_HOMEPAGE_SECONDARY_LINK
        ),
        "site_homepage_account_button": (
            brand.homepage_account_button
            if brand
            else settings.SITE_HOMEPAGE_ACCOUNT_BUTTON
        ),
        "site_join_steps": (
            (
                brand.join_step_1_heading,
                brand.join_step_1_description,
            ),
            (
                brand.join_step_2_heading,
                brand.join_step_2_description,
            ),
            (
                brand.join_step_3_heading,
                brand.join_step_3_description,
            ),
        )
        if brand
        else (
            (
                settings.SITE_JOIN_STEP_1_HEADING,
                settings.SITE_JOIN_STEP_1_DESCRIPTION,
            ),
            (
                settings.SITE_JOIN_STEP_2_HEADING,
                settings.SITE_JOIN_STEP_2_DESCRIPTION,
            ),
            (
                settings.SITE_JOIN_STEP_3_HEADING,
                settings.SITE_JOIN_STEP_3_DESCRIPTION,
            ),
        ),
        "site_participant_label": (
            brand.participant_label if brand else settings.SITE_PARTICIPANT_LABEL
        ),
        "site_participant_plural_label": (
            brand.participant_plural_label
            if brand
            else settings.SITE_PARTICIPANT_PLURAL_LABEL
        ),
        "site_former_participant_label": (
            brand.former_participant_label
            if brand
            else settings.SITE_FORMER_PARTICIPANT_LABEL
        ),
        "site_run_update_label": (
            brand.run_update_label if brand else settings.SITE_RUN_UPDATE_LABEL
        ),
        "site_run_update_plural_label": (
            brand.run_update_plural_label
            if brand
            else settings.SITE_RUN_UPDATE_PLURAL_LABEL
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
