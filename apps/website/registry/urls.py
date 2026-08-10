from django.urls import path
from django.contrib.auth import views as auth_views
from django.urls import reverse_lazy

from . import views

app_name = "registry"

urlpatterns = [
    path("", views.home, name="home"),
    path("pages/<slug:slug>/", views.legacy_page, name="legacy_page"),
    path("signup/", views.register, name="register"),
    path(
        "signup/validate/",
        views.validate_registration_field,
        name="validate_registration_field",
    ),
    path("thanks/", views.thanks, name="thanks"),
    path("resend/", views.resend_verification, name="resend"),
    path("verify/<str:token>/", views.verify, name="verify"),
    path("login/", views.sign_in, name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path(
        "password-change/",
        auth_views.PasswordChangeView.as_view(
            template_name="registry/password_change.html",
            success_url=reverse_lazy("registry:password_change_done"),
        ),
        name="password_change",
    ),
    path(
        "password-change/done/",
        auth_views.PasswordChangeDoneView.as_view(
            template_name="registry/password_change_done.html"
        ),
        name="password_change_done",
    ),
    path("password-reset/", views.password_reset_request, name="password_reset"),
    path(
        "password-reset/<str:uidb64>/<str:token>/",
        views.password_reset_confirm,
        name="password_reset_confirm",
    ),
    path(
        "password-reset-complete/",
        views.password_reset_complete,
        name="password_reset_complete",
    ),
    path("account/", views.account, name="account"),
    path(
        "participants/<uuid:participant_id>/",
        views.participant_profile,
        name="participant_profile",
    ),
    path("leaderboard/", views.leaderboard, name="leaderboard"),
    path("mods/", views.mods_catalogue, name="mods"),
    path("exploits/", views.exploits_catalogue, name="exploits"),
    path("mods/workshop-lookup/", views.workshop_mod_lookup, name="workshop_mod_lookup"),
    path("runs/<uuid:run_id>/", views.public_run_detail, name="public_run_detail"),
    path(
        "legacy-runs/<int:run_id>/claim/",
        views.claim_legacy_run,
        name="claim_legacy_run",
    ),
    path(
        "account/dashboard/fragment/",
        views.account_dashboard_fragment,
        name="account_dashboard_fragment",
    ),
    path("account/submit/", views.submit_run, name="submit_run"),
    path("account/legacy/submit/", views.submit_legacy_run, name="submit_legacy_run"),
    path(
        "account/runs/<uuid:run_id>/deactivate/",
        views.deactivate_run,
        name="deactivate_run",
    ),
    path("account/settings/", views.account_settings, name="account_settings"),
    path(
        "account/streaming/twitch/connect/",
        views.connect_twitch,
        name="connect_twitch",
    ),
    path(
        "account/streaming/twitch/callback/",
        views.twitch_callback,
        name="twitch_callback",
    ),
    path(
        "account/streaming/twitch/disconnect/",
        views.disconnect_twitch,
        name="disconnect_twitch",
    ),
    path(
        "account/streaming/twitch/media/refresh/",
        views.refresh_twitch_media_view,
        name="refresh_twitch_media",
    ),
    path(
        "account/streaming/media/refresh/",
        views.refresh_streaming_media_view,
        name="refresh_streaming_media",
    ),
    path(
        "account/streaming/youtube/connect/",
        views.connect_youtube,
        name="connect_youtube",
    ),
    path(
        "account/streaming/youtube/callback/",
        views.youtube_callback,
        name="youtube_callback",
    ),
    path(
        "account/streaming/youtube/disconnect/",
        views.disconnect_youtube,
        name="disconnect_youtube",
    ),
    path(
        "account/streaming/primary/",
        views.set_primary_streaming_channel,
        name="set_primary_streaming_channel",
    ),
    path(
        "account/connections/discord/connect/",
        views.connect_discord,
        name="connect_discord",
    ),
    path(
        "account/connections/discord/callback/",
        views.discord_callback,
        name="discord_callback",
    ),
    path(
        "account/connections/discord/disconnect/",
        views.disconnect_discord,
        name="disconnect_discord",
    ),
    path("account/settings/avatar/", views.upload_avatar, name="upload_avatar"),
    path("account/settings/avatar/remove/", views.delete_avatar, name="delete_avatar"),
    path("account/notifications/", views.notifications, name="notifications"),
    path(
        "account/notifications/summary/",
        views.notification_summary,
        name="notification_summary",
    ),
    path(
        "account/notifications/stream/",
        views.notification_stream,
        name="notification_stream",
    ),
    path(
        "account/notifications/read/",
        views.mark_notifications_read,
        name="mark_notifications_read",
    ),
    path(
        "account/notifications/<uuid:notification_id>/",
        views.open_notification,
        name="open_notification",
    ),
    path("privacy/", views.privacy_notice, name="privacy"),
    path("account/data/", views.download_my_data, name="download_my_data"),
    path(
        "account/closure/",
        views.request_account_closure,
        name="account_closure",
    ),
    path(
        "account/closure/received/",
        views.account_closure_received,
        name="account_closure_received",
    ),
    # Managed page addresses are deliberately last so application routes win.
    path("<path:page_path>/", views.page_detail, name="page"),
]
