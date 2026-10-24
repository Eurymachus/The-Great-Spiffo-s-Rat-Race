from django.contrib.admin import AdminSite
from django.contrib.admin.apps import AdminConfig
from django.shortcuts import redirect
from django.apps import apps
from django.conf import settings
from django.urls import reverse
from urllib.parse import urlencode


class RatRaceAdminConfig(AdminConfig):
    default_site = "registry.admin_site.RatRaceAdminSite"


class RatRaceAdminSite(AdminSite):
    def index(self, request, extra_context=None):
        queues = []
        definitions = (
            ("registry.RunSubmission", "2.0 submissions", {"status": "received"}, {"status__exact": "received"}),
            ("registry.LegacyRunClaim", "1.0 claims", {"status": "pending"}, {"status__exact": "pending"}),
            ("registry.LegacyRunSubmission", "1.0 updates", {"status": "received", "source": "participant"}, {"status__exact": "received", "source__exact": "participant"}),
            ("registry.Participant", "Avatar reviews", {"avatar_status": "pending"}, {"avatar_status__exact": "pending"}),
            ("registry.Participant", "Account closure requests", {"deletion_requested_at__isnull": False}, {"deletion_requested_at__isnull": "False"}),
            ("operations.CatalogueImportReview", "Catalogue reviews", {"status": "ready"}, {"status__exact": "ready"}),
            ("operations.ReferenceUpdateJob", "Reference jobs needing attention", {"status__in": ["failed", "authentication_required"]}, {"status__in": "failed,authentication_required"}),
        )
        for label, title, filters, query in definitions:
            model = apps.get_model(label)
            model_admin = self._registry.get(model)
            if not model_admin or not model_admin.has_view_permission(request):
                continue
            opts = model._meta
            url = reverse(f"admin:{opts.app_label}_{opts.model_name}_changelist")
            if label == "registry.RunSubmission":
                from .run_saved_views import FILTERS

                url = reverse("admin:registry_challengerun_changelist")
                query = {**dict.fromkeys(FILTERS, ""), "work": "review"}
            elif label == "registry.Participant":
                query = {**query, "_filters": "1"}
            queues.append({
                "title": title,
                "count": model_admin.get_queryset(request).filter(**filters).count(),
                "url": url + "?" + urlencode(query),
            })
        context = {**(extra_context or {}), "title": "Dashboard", "dashboard_queues": queues}
        if request.user.has_perm("operations.view_referencesource"):
            from operations.runtime_state import get_worker_heartbeat_state

            heartbeat = get_worker_heartbeat_state()
            context["dashboard_runtime"] = {
                "release": settings.RELEASE_ID,
                "worker_ready": bool(heartbeat and heartbeat.get("release_id") == settings.RELEASE_ID),
            }
        return super().index(request, context)

    registry_groups = (
        (
            "Participant administration",
            ("Participant", "Notification", "AccountClosureRecord"),
        ),
        ("Challenge configuration", ("ChallengeMode",)),
        ("Run moderation", ("ChallengeRun",)),
        (
            "Rat Race 1.0 data",
            (
                "LegacyDataImport",
                "LegacyRun",
                "LegacyRunSubmission",
                "LegacyRunClaim",
            ),
        ),
        ("Mod policy", ("WorkshopMod",)),
        ("Exploit policy", ("ExploitRuling",)),
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

    def app_index(self, request, app_label, extra_context=None):
        if app_label in {"registry", "operations"}:
            app_list = super().get_app_list(request, app_label)
            models_by_name = {
                model["object_name"]: model
                for app in app_list
                for model in app["models"]
            }
            for _group_name, object_names in self.registry_groups:
                for object_name in object_names:
                    model = models_by_name.get(object_name)
                    if model and model.get("admin_url"):
                        return redirect(model["admin_url"])
        return super().app_index(request, app_label, extra_context)

    def get_app_list(self, request, app_label=None):
        app_list = super().get_app_list(request, app_label)
        for app in app_list:
            for model in app["models"]:
                if model["object_name"] == "ChallengeRun":
                    model["name"] = "Challenge Runs"
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
