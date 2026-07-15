from django.urls import path
from django.contrib.auth import views as auth_views
from django.urls import reverse_lazy

from . import views

app_name = "registry"

urlpatterns = [
    path("", views.register, name="register"),
    path("thanks/", views.thanks, name="thanks"),
    path("resend/", views.resend_verification, name="resend"),
    path("verify/<str:token>/", views.verify, name="verify"),
    path(
        "login/",
        auth_views.LoginView.as_view(
            template_name="registry/login.html",
            redirect_authenticated_user=True,
        ),
        name="login",
    ),
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
]
