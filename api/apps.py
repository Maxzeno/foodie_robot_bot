from django.apps import AppConfig


class ApiConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "api"

    def ready(self):
        """
        Import signal handlers when Django starts.
        This ensures all signals are registered and active.
        """
        import api.signals  # noqa: F401

