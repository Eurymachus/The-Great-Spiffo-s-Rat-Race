from django.apps import AppConfig


class RegistryConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'registry'
    verbose_name = "Participant Registry"

    def ready(self):
        from . import signals  # noqa: F401
