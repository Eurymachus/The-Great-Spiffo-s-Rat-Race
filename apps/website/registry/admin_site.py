from django.contrib.admin import AdminSite
from django.contrib.admin.apps import AdminConfig


class RatRaceAdminConfig(AdminConfig):
    default_site = "registry.admin_site.RatRaceAdminSite"


class RatRaceAdminSite(AdminSite):
    registry_groups = (
        (
            "Participant administration",
            ("Participant", "Notification", "AccountClosureRecord"),
        ),
        ("Challenge configuration", ("ChallengeMode",)),
        ("Run moderation", ("ChallengeRun", "RunSubmission")),
        ("Mod policy", ("WorkshopMod",)),
        (
            "Platform integrations",
            ("StreamingAccount", "StreamingMedia"),
        ),
        (
            "System operations",
            (
                "ReferenceSource",
                "ReferenceUpdateJob",
                "CatalogueImportReview",
                "PZWikiArtworkSyncJob",
                "RunDataDangerZone",
            ),
        ),
    )

    def get_app_list(self, request, app_label=None):
        app_list = super().get_app_list(request, app_label)
        if app_label is not None:
            return app_list

        grouped_apps = []
        for app in app_list:
            if app["app_label"] not in {"registry", "operations"}:
                grouped_apps.append(app)
                continue

            models_by_name = {
                model["object_name"]: model for model in app["models"]
            }
            for index, (name, object_names) in enumerate(self.registry_groups):
                models = [
                    models_by_name[object_name]
                    for object_name in object_names
                    if object_name in models_by_name
                ]
                if not models:
                    continue
                grouped_apps.append(
                    {
                        **app,
                        "name": name,
                        "app_label": f"registry_group_{index}",
                        "app_url": f"/admin/registry/__group_{index}__/",
                        "models": models,
                    }
                )
            if app["app_label"] == "operations":
                continue
        return grouped_apps
