from django.apps import AppConfig


class ApiConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "api"

    def ready(self):
        """
        Import signal handlers and tasks when Django starts.
        This ensures all signals are registered and tasks are registered with Huey.
        """
        import api.signals  # noqa: F401
        import api.tasks  # noqa: F401 - Register Huey tasks

