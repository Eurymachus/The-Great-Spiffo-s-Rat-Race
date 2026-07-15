from django.conf import settings


def site_identity(request):
    company_number = settings.SITE_COMPANY_NUMBER
    return {
        "site_legal_name": settings.SITE_LEGAL_NAME,
        "site_company_number": company_number,
        "site_registered_office": settings.SITE_REGISTERED_OFFICE,
        "site_privacy_email": settings.SITE_PRIVACY_EMAIL,
        "site_public_url": settings.SITE_PUBLIC_URL,
        "site_full_title": settings.SITE_FULL_TITLE,
        "site_short_title": settings.SITE_SHORT_TITLE,
        "site_tagline": settings.SITE_TAGLINE,
        "site_welcome_message": settings.SITE_WELCOME_MESSAGE,
        "site_former_participant_label": settings.SITE_FORMER_PARTICIPANT_LABEL,
        "site_disclaimer": settings.SITE_DISCLAIMER,
        "site_companies_house_url": (
            "https://find-and-update.company-information.service.gov.uk/company/"
            f"{company_number}"
        ),
    }
