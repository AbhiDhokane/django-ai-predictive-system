import os
import sys
from django.apps import AppConfig


class TelemetryConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'telemetry'
    verbose_name = 'AI Predictive Telemetry'

    def ready(self):
        # Optional: Start the autonomous telemetry background worker if enabled
        enable_sim = os.environ.get('ENABLE_SIMULATOR', 'true').lower() in ('true', '1', 'yes')
        is_runserver = 'runserver' in sys.argv and (os.environ.get('RUN_MAIN') == 'true' or '--noreload' in sys.argv)
        is_gunicorn = any('gunicorn' in arg for arg in sys.argv) or 'gunicorn' in sys.modules

        if enable_sim and (is_runserver or is_gunicorn):
            from .simulator import start_background_telemetry_worker
            start_background_telemetry_worker()
