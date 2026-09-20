import time
from django.core.management.base import BaseCommand
from telemetry.simulator import generate_autonomous_cycle


class Command(BaseCommand):
    help = 'Runs the autonomous IoT telemetry simulator generator loop.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--interval',
            type=int,
            default=5,
            help='Interval in seconds between telemetry cycles (default: 5)'
        )

    def handle(self, *args, **options):
        interval = options['interval']
        self.stdout.write(self.style.SUCCESS(
            f"🚀 [Simulator] Starting autonomous telemetry generator (Interval: {interval}s)..."
        ))
        self.stdout.write("Press Ctrl+C to exit.\n")

        cycle_count = 0
        try:
            while True:
                cycle_count += 1
                readings = generate_autonomous_cycle()
                self.stdout.write(f"Cycle #{cycle_count}: emitted {len(readings)} machine readings.")
                time.sleep(interval)
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING("\nSimulator stopped by operator."))
