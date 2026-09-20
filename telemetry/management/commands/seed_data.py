from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from telemetry.models import SensorReading, AlertLog


class Command(BaseCommand):
    help = 'Seeds initial telemetry streams and sample alert audit logs.'

    def handle(self, *args, **options):
        if SensorReading.objects.exists():
            self.stdout.write(self.style.WARNING("Sensor readings already exist. Skipping seed."))
            return

        now = timezone.now()
        readings = [
            # M01 (Normal Operating State)
            SensorReading(machine_id='M01', temperature=58.4, vibration=1.85, current=4.80, rpm=1620, recorded_at=now - timedelta(minutes=15)),
            SensorReading(machine_id='M01', temperature=59.1, vibration=1.90, current=4.95, rpm=1610, recorded_at=now - timedelta(minutes=12)),
            SensorReading(machine_id='M01', temperature=60.3, vibration=1.82, current=5.10, rpm=1630, recorded_at=now - timedelta(minutes=9)),
            SensorReading(machine_id='M01', temperature=58.9, vibration=1.88, current=4.90, rpm=1625, recorded_at=now - timedelta(minutes=6)),
            SensorReading(machine_id='M01', temperature=61.2, vibration=1.95, current=5.20, rpm=1615, recorded_at=now - timedelta(minutes=3)),
            SensorReading(machine_id='M01', temperature=59.8, vibration=1.87, current=5.05, rpm=1640, recorded_at=now),

            # M02 (Elevated Warning State)
            SensorReading(machine_id='M02', temperature=68.5, vibration=2.80, current=6.20, rpm=1520, recorded_at=now - timedelta(minutes=15)),
            SensorReading(machine_id='M02', temperature=72.1, vibration=3.10, current=6.80, rpm=1490, recorded_at=now - timedelta(minutes=12)),
            SensorReading(machine_id='M02', temperature=75.4, vibration=3.45, current=7.10, rpm=1470, recorded_at=now - timedelta(minutes=9)),
            SensorReading(machine_id='M02', temperature=78.2, vibration=3.60, current=7.40, rpm=1450, recorded_at=now - timedelta(minutes=6)),
            SensorReading(machine_id='M02', temperature=81.0, vibration=3.90, current=7.80, rpm=1420, recorded_at=now - timedelta(minutes=3)),
            SensorReading(machine_id='M02', temperature=82.5, vibration=4.10, current=8.10, rpm=1390, recorded_at=now),

            # M03 (High Failure Risk Anomaly)
            SensorReading(machine_id='M03', temperature=75.0, vibration=3.20, current=6.90, rpm=1500, recorded_at=now - timedelta(minutes=15)),
            SensorReading(machine_id='M03', temperature=82.3, vibration=4.50, current=8.40, rpm=1380, recorded_at=now - timedelta(minutes=12)),
            SensorReading(machine_id='M03', temperature=88.7, vibration=5.20, current=9.60, rpm=1250, recorded_at=now - timedelta(minutes=9)),
            SensorReading(machine_id='M03', temperature=92.4, vibration=5.80, current=10.30, rpm=1120, recorded_at=now - timedelta(minutes=6)),
            SensorReading(machine_id='M03', temperature=95.1, vibration=6.40, current=11.10, rpm=1040, recorded_at=now - timedelta(minutes=3)),
            SensorReading(machine_id='M03', temperature=96.8, vibration=6.75, current=11.80, rpm=980, recorded_at=now),
        ]
        SensorReading.objects.bulk_create(readings)

        alerts = [
            AlertLog(
                machine_id='M03',
                risk_percent=98.5,
                status='HIGH FAILURE RISK',
                recipients='maintenance-ops@example.com',
                email_status='sent',
                error_message=None,
                sent_at=now - timedelta(minutes=10)
            ),
            AlertLog(
                machine_id='M02',
                risk_percent=74.2,
                status='WARNING',
                recipients='maintenance-ops@example.com',
                email_status='sent',
                error_message=None,
                sent_at=now - timedelta(minutes=45)
            ),
        ]
        AlertLog.objects.bulk_create(alerts)

        self.stdout.write(self.style.SUCCESS(f"Successfully seeded {len(readings)} sensor readings and {len(alerts)} alert logs."))
