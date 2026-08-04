from django.apps import AppConfig
from django.db.models.signals import post_migrate


def install_code_managed_pages(sender, **kwargs):
    from .code_pages import synchronise_code_managed_pages
    from .models import CodeManagedPage

    synchronise_code_managed_pages(CodeManagedPage)


class PagesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "pages"
    verbose_name = "Website Content"

    def ready(self):
        post_migrate.connect(
            install_code_managed_pages,
            sender=self,
            dispatch_uid="pages.install_code_managed_pages",
        )
