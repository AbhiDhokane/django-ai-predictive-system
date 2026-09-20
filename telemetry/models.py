from django.db import models
from django.utils import timezone


class SensorReading(models.Model):
    """Stores high-frequency IoT telemetry measurements per industrial machine."""
    machine_id = models.CharField(max_length=20, db_index=True, help_text="Machine identifier (e.g. M01, M02, M03)")
    temperature = models.FloatField(help_text="Temperature in Celsius")
    vibration = models.FloatField(help_text="Vibration speed in mm/s")
    current = models.FloatField(help_text="Operating current in Amperes")
    rpm = models.IntegerField(help_text="Rotational speed in RPM")
    recorded_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        db_table = 'sensor_readings'
        ordering = ['-recorded_at']
        indexes = [
            models.Index(fields=['machine_id', '-recorded_at'], name='idx_machine_time'),
        ]

    def __str__(self):
        return f"{self.machine_id} @ {self.recorded_at:%Y-%m-%d %H:%M:%S} | Temp: {self.temperature}°C, Vib: {self.vibration}"

    def to_dict(self):
        return {
            "id": self.id,
            "machine_id": self.machine_id,
            "temperature": round(float(self.temperature), 2),
            "vibration": round(float(self.vibration), 2),
            "current": round(float(self.current), 2),
            "rpm": int(self.rpm),
            "recorded_at": self.recorded_at.isoformat(),
        }


class AlertLog(models.Model):
    """Audit log of dispatched automated incident alerts."""
    machine_id = models.CharField(max_length=20, db_index=True)
    risk_percent = models.FloatField(help_text="Evaluated failure probability percentage")
    status = models.CharField(max_length=50, help_text="Operational status (WARNING, HIGH FAILURE RISK, etc.)")
    recipients = models.TextField(help_text="Comma-separated email recipients")
    email_status = models.CharField(max_length=30, help_text="Status: sent, failed, cooldown_skipped, disabled")
    error_message = models.TextField(null=True, blank=True)
    sent_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        db_table = 'alert_log'
        ordering = ['-sent_at']
        indexes = [
            models.Index(fields=['-sent_at'], name='idx_alert_time'),
        ]

    def __str__(self):
        return f"[{self.email_status.upper()}] {self.machine_id} ({self.risk_percent:.1f}%) @ {self.sent_at:%Y-%m-%d %H:%M}"

    def to_dict(self):
        recipients_list = [r.strip() for r in (self.recipients or '').split(',') if r.strip()]
        return {
            "id": self.id,
            "machine_id": self.machine_id,
            "risk_percent": round(float(self.risk_percent), 1),
            "status": self.status,
            "recipients": recipients_list,
            "email_status": self.email_status,
            "error_message": self.error_message,
            "sent_at": self.sent_at.isoformat(),
        }
