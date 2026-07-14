from django.urls import path
from django.contrib.auth import views as auth_views

from . import views

app_name = "registry"

urlpatterns = [
    path("", views.register, name="register"),
    path("thanks/", views.thanks, name="thanks"),
    path("resend/", views.resend_verification, name="resend"),
    path("verify/<str:token>/", views.verify, name="verify"),
    path("login/", auth_views.LoginView.as_view(template_name="registry/login.html"), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
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
]
