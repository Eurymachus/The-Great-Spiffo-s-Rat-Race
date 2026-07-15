from django.conf import settings


def site_identity(request):
    company_number = settings.SITE_COMPANY_NUMBER
    return {
        "site_legal_name": settings.SITE_LEGAL_NAME,
        "site_company_number": company_number,
        "site_registered_office": settings.SITE_REGISTERED_OFFICE,
        "site_privacy_email": settings.SITE_PRIVACY_EMAIL,
        "site_public_url": settings.SITE_PUBLIC_URL,
        "site_companies_house_url": (
            "https://find-and-update.company-information.service.gov.uk/company/"
            f"{company_number}"
        ),
    }
