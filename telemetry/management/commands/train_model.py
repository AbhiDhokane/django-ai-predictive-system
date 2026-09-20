import os
import numpy as np
import pandas as pd
import joblib
from django.conf import settings
from django.core.management.base import BaseCommand
from sklearn.ensemble import RandomForestClassifier


class Command(BaseCommand):
    help = 'Trains the Random Forest predictive maintenance classifier and exports failure_model.pkl.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--samples',
            type=int,
            default=4000,
            help='Number of synthetic training telemetry samples (default: 4000)'
        )

    def handle(self, *args, **options):
        n_samples = options['samples']
        self.stdout.write(f"Generating {n_samples} synthetic sensor telemetry points...")
        np.random.seed(42)

        rows = []
        for _ in range(n_samples):
            temperature = np.random.uniform(45, 100)
            vibration = np.random.uniform(0.8, 7)
            current = np.random.uniform(3, 12)
            rpm = np.random.uniform(900, 1800)

            bad_signals = sum([
                temperature > 80,
                vibration > 4,
                current > 8,
                rpm < 1300,
            ])
            # 0 = normal, 1 = warning, 2 = high failure risk
            status = 2 if bad_signals >= 3 else (1 if bad_signals >= 1 else 0)
            rows.append([temperature, vibration, current, rpm, status])

        data = pd.DataFrame(rows, columns=["temperature", "vibration", "current", "rpm", "status"])

        self.stdout.write("Fitting RandomForestClassifier (150 estimators)...")
        model = RandomForestClassifier(n_estimators=150, random_state=42, class_weight="balanced")
        model.fit(data.iloc[:, :4], data.status)

        output_dir = getattr(settings, 'BASE_DIR') / 'model'
        os.makedirs(output_dir, exist_ok=True)
        output_path = output_dir / 'failure_model.pkl'

        joblib.dump(model, output_path)
        self.stdout.write(self.style.SUCCESS(f"Model successfully saved to {output_path}"))
