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
    def each_context(self, request):
        context = super().each_context(request)
        if request.user.is_authenticated and request.user.is_staff:
            context["admin_notifications"] = request.user.notifications.all()[:10]
            context["admin_unread_count"] = request.user.notifications.filter(read_at__isnull=True).count()
        sections = {
            key: {"id": key, "title": title, "icon": icon, "items": []}
            for key, title, icon in (
                ("rr2", "Rat Race 2.0", "2"),
                ("rr1", "Rat Race 1.0", "1"),
                ("people", "Community", "people"),
                ("rules", "Rules and mods", "rules"),
                ("website", "Website", "website"),
                ("catalogue", "Game catalogue", "catalogue"),
                ("system", "System", "system"),
            )
        }
        destinations = {
            "ChallengeRun": ("rr2", "Challenge runs"),
            "ChallengeMode": ("rr2", "Challenge modes"),
            "LegacyRun": ("rr1", "Runs and results"),
            "LegacyRunClaim": ("rr1", "Ownership claims"),
            "LegacyRunSubmission": ("rr1", "Run updates"),
            "LegacyDataImport": ("rr1", "Data imports"),
            "Participant": ("people", "Participants"),
            "Notification": ("people", "Notifications"),
            "AccountClosureRecord": ("people", "Account closures"),
            "StreamingAccount": ("people", "Connected channels"),
            "StreamingMedia": ("people", "Stream recordings"),
            "WorkshopMod": ("rules", "Workshop mods"),
            "ExploitRuling": ("rules", "Exploit rulings"),
            "Group": ("system", "Roles and permissions"),
        }
        for app in context["available_apps"]:
            default = ("website" if app["app_label"] in {"branding", "pages", "administration"}
                       else "catalogue" if app["app_label"] == "zomboid_catalogue" else "system")
            for model in app["models"]:
                url = model.get("admin_url") or model.get("add_url")
                if not url:
                    continue
                section, title = destinations.get(model["object_name"], (default, model["name"]))
                sections[section]["items"].append({
                    "title": title, "url": url,
                    "current": request.path.startswith(url),
                })
        for section in sections.values():
            priority = {
                "rr2": ("Challenge runs", "Challenge modes"),
                "rr1": ("Run updates", "Runs and results", "Ownership claims", "Data imports"),
            }.get(section["id"])
            if priority:
                section["items"].sort(key=lambda item: priority.index(item["title"]))
            section["open"] = section["id"] in {"rr2", "rr1"} or any(
                item["current"] for item in section["items"]
            )
        context["admin_menu"] = [section for section in sections.values() if section["items"]]
        context["admin_home_current"] = request.path == reverse("admin:index")
        return context

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
                "section": "rr2" if label == "registry.RunSubmission" else (
                    "rr1" if label in {"registry.LegacyRunClaim", "registry.LegacyRunSubmission"}
                    else "shared"
                ),
                "title": title,
                "count": model_admin.get_queryset(request).filter(**filters).count(),
                "url": url + "?" + urlencode(query),
            })
        context = {**(extra_context or {}), "title": "Dashboard", "dashboard_queues": queues}
        context["dashboard_sections"] = [
            {"id": key, "title": title, "queues": section_queues}
            for key, title in (
                ("rr2", "Rat Race 2.0"),
                ("rr1", "Rat Race 1.0"),
                ("shared", "Accounts and operations"),
            )
            if (section_queues := [queue for queue in queues if queue["section"] == key])
        ]
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
