import os
import sys
from django.apps import AppConfig


class TelemetryConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'telemetry'
    verbose_name = 'AI Predictive Telemetry'

    def ready(self):
        # Optional: Start the autonomous telemetry background worker if runserver is running
        # Only start in the child process to avoid duplicate threads during auto-reload
        if 'runserver' in sys.argv and (os.environ.get('RUN_MAIN') == 'true' or '--noreload' in sys.argv):
            from .simulator import start_background_telemetry_worker
            start_background_telemetry_worker()
