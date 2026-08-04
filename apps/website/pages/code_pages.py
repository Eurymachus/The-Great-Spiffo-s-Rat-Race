from dataclasses import dataclass


@dataclass(frozen=True)
class CodeManagedPageDefinition:
    key: str
    title: str
    description: str
    audience: str
    availability: str
    route_name: str = ""
    address: str = ""


CODE_MANAGED_PAGES = (
    CodeManagedPageDefinition(
        key="top-ten",
        title="Top ten",
        description="Public summary of the ten leading Rat Race records.",
        audience="public",
        availability="planned",
        address="/top-ten/",
    ),
    CodeManagedPageDefinition(
        key="mods",
        title="Mods",
        description="Searchable public catalogue of Rat Race mod rulings.",
        audience="public",
        availability="available",
        route_name="registry:mods",
        address="/mods/",
    ),
    CodeManagedPageDefinition(
        key="run-history",
        title="Run history",
        description="Signed-in, filterable history of all Rat Race runs.",
        audience="participant",
        availability="planned",
        address="/runs/",
    ),
    CodeManagedPageDefinition(
        key="run-detail",
        title="Run details",
        description="Signed-in details and statistics for an individual run.",
        audience="participant",
        availability="available",
        address="/runs/<run-id>/",
    ),
    CodeManagedPageDefinition(
        key="account",
        title="Participant account",
        description="Signed-in participant dashboard and account summary.",
        audience="participant",
        availability="available",
        route_name="registry:account",
        address="/account/",
    ),
    CodeManagedPageDefinition(
        key="account-settings",
        title="Account settings",
        description="Signed-in participant settings and connected accounts.",
        audience="participant",
        availability="available",
        route_name="registry:account_settings",
        address="/account/settings/",
    ),
    CodeManagedPageDefinition(
        key="notifications",
        title="Notifications",
        description="Signed-in participant notification history.",
        audience="participant",
        availability="available",
        route_name="registry:notifications",
        address="/account/notifications/",
    ),
)


def synchronise_code_managed_pages(model):
    registered_keys = {definition.key for definition in CODE_MANAGED_PAGES}
    for definition in CODE_MANAGED_PAGES:
        model.objects.update_or_create(
            key=definition.key,
            defaults={
                "title": definition.title,
                "description": definition.description,
                "audience": definition.audience,
                "availability": definition.availability,
                "route_name": definition.route_name,
                "address": definition.address,
            },
        )
    model.objects.exclude(key__in=registered_keys).delete()
