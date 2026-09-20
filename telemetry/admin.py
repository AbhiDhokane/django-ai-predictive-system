from django.contrib import admin
from .models import SensorReading, AlertLog


@admin.register(SensorReading)
class SensorReadingAdmin(admin.ModelAdmin):
    list_display = ('id', 'machine_id', 'temperature', 'vibration', 'current', 'rpm', 'recorded_at')
    list_filter = ('machine_id', 'recorded_at')
    search_fields = ('machine_id',)
    ordering = ('-recorded_at',)
    readonly_fields = ('recorded_at',)


@admin.register(AlertLog)
class AlertLogAdmin(admin.ModelAdmin):
    list_display = ('id', 'machine_id', 'risk_percent', 'status', 'email_status', 'sent_at')
    list_filter = ('machine_id', 'email_status', 'sent_at')
    search_fields = ('machine_id', 'recipients', 'status')
    ordering = ('-sent_at',)
    readonly_fields = ('sent_at',)
