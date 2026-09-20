"""
URL configuration for telemetry app.
"""
from django.urls import path
from django.views.static import serve
from django.conf import settings
from . import views

urlpatterns = [
    # Dashboard HTML UI
    path('', views.dashboard_view, name='dashboard'),

    # Health & System Status
    path('health', views.health_check, name='health'),
    path('api/health', views.health_check, name='api_health'),
    path('api/status', views.health_check, name='api_status'),

    # Machines & Telemetry
    path('api/machines', views.list_machines, name='api_machines'),
    path('api/readings/latest', views.get_latest_readings, name='api_readings_latest'),
    path('api/readings/history', views.get_history, name='api_readings_history'),
    path('api/readings', views.create_sensor_reading, name='api_readings_create'),

    # Overview & Statistics
    path('api/overview', views.get_system_overview, name='api_overview'),

    # ML Inference
    path('api/predict', views.predict_endpoint, name='api_predict'),

    # Alerts & Notifications
    path('api/alerts/recent', views.get_recent_alerts, name='api_alerts_recent'),
    path('api/alerts/test', views.trigger_test_alert, name='api_alerts_test'),

    # Simulator & Controls
    path('api/simulator/tick', views.simulate_tick, name='api_simulator_tick'),
    path('api/simulator/normalize', views.normalize_machine_endpoint, name='api_simulator_normalize'),

    # Runtime Settings
    path('api/settings', views.get_settings, name='api_settings'),
    path('api/settings/email-toggle', views.toggle_email_alerts, name='api_settings_email_toggle'),

    # Direct root asset fallbacks (for index.html fetching /style.css, /config.js, /app.js directly)
    path('style.css', serve, {'document_root': settings.STATICFILES_DIRS[0], 'path': 'style.css'}),
    path('config.js', serve, {'document_root': settings.STATICFILES_DIRS[0], 'path': 'config.js'}),
    path('app.js', serve, {'document_root': settings.STATICFILES_DIRS[0], 'path': 'app.js'}),
]
