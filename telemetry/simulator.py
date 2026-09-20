"""
Physical IoT Simulation Engine for AI Predictive Maintenance in Django.
Simulates realistic multi-stage mechanical wear, thermal drift, emergency safety lockout,
and autonomous streaming cycles.
"""
import random
import time
import threading
from typing import Dict, Any, Optional

from django.conf import settings
from django.db import close_old_connections
from .models import SensorReading
from .ml_model import predict_risk
from .alerts import maybe_send_alert

# In-Memory dynamic runtime settings
RUNTIME_SETTINGS = {
    "email_alerts_enabled": getattr(settings, 'EMAIL_ALERTS_ENABLED', True),
}


def _init_cycles_for(mid: str, idx: int) -> int:
    """Stagger initial autonomous faults across machines."""
    base = (idx + 1) * 6
    return random.randint(base, base + 4)


MACHINE_CONTROLLERS: Dict[str, Dict[str, Any]] = {
    m: {
        "operational_state": "RUNNING",  # "RUNNING" or "TRIPPED_STOPPED"
        "temp": round(random.uniform(58.0, 66.0), 2),
        "vib": round(random.uniform(1.2, 1.8), 2),
        "curr": round(random.uniform(4.5, 5.5), 2),
        "rpm": random.randint(1550, 1720),
        "cycles": 0,
        "cycles_to_fault": _init_cycles_for(m, i),
    }
    for i, m in enumerate(getattr(settings, 'MONITORED_MACHINES', ['M01', 'M02', 'M03']))
}


def process_telemetry_reading(
    machine_id: str,
    temperature: float,
    vibration: float,
    current: float,
    rpm: int,
) -> Dict[str, Any]:
    """Ingests sensor reading, runs ML inference, logs to DB, and checks alerts."""
    close_old_connections()

    # 1. Machine learning inference
    pred = predict_risk(temperature, vibration, current, rpm)

    # 2. Persist to database
    reading = SensorReading.objects.create(
        machine_id=machine_id,
        temperature=temperature,
        vibration=vibration,
        current=current,
        rpm=rpm,
    )

    # 3. Check alert threshold
    alert_result = None
    threshold = getattr(settings, 'ALERT_RISK_THRESHOLD', 75)
    if pred["risk_percent"] >= threshold:
        sensor_data = {
            "temperature": temperature,
            "vibration": vibration,
            "current": current,
            "rpm": rpm,
        }
        alert_result = maybe_send_alert(
            machine_id=machine_id,
            status=pred["status"],
            risk_percent=pred["risk_percent"],
            sensor=sensor_data,
            email_enabled=RUNTIME_SETTINGS["email_alerts_enabled"],
        )

    ctrl = MACHINE_CONTROLLERS.get(machine_id, {})
    op_state = ctrl.get("operational_state", "RUNNING")
    display_status = "EMERGENCY STOPPED" if (op_state == "TRIPPED_STOPPED" and rpm == 0) else pred["status"]

    return {
        "machine_id": machine_id,
        "temperature": temperature,
        "vibration": vibration,
        "current": current,
        "rpm": rpm,
        "recorded_at": reading.recorded_at.isoformat(),
        "status": display_status,
        "risk_percent": pred["risk_percent"],
        "operational_state": op_state,
        "alert_info": alert_result,
    }


def step_machine_telemetry(mid: str) -> Dict[str, Any]:
    """Executes one simulation step for a machine and records the result."""
    ctrl = MACHINE_CONTROLLERS.setdefault(mid, {
        "operational_state": "RUNNING",
        "temp": 62.0,
        "vib": 1.4,
        "curr": 4.8,
        "rpm": 1650,
        "cycles": 0,
        "cycles_to_fault": random.randint(8, 14),
    })

    # Case 1: Machine is in Safety Shutdown / Lockout
    if ctrl["operational_state"] == "TRIPPED_STOPPED":
        ctrl["temp"] = round(max(30.0, ctrl["temp"] - 1.5), 2)
        ctrl["vib"] = round(random.uniform(0.02, 0.06), 2)
        ctrl["curr"] = 0.0
        ctrl["rpm"] = 0

        return process_telemetry_reading(
            machine_id=mid,
            temperature=ctrl["temp"],
            vibration=ctrl["vib"],
            current=ctrl["curr"],
            rpm=ctrl["rpm"],
        )

    # Case 2: Machine is Active & Running
    ctrl["cycles"] += 1
    remaining = ctrl["cycles_to_fault"] - ctrl["cycles"]

    # Critical Failure Anomaly Spike -> Automatic Safety Trip!
    if remaining <= 0:
        ctrl["temp"] = round(random.uniform(94.5, 98.5), 2)
        ctrl["vib"] = round(random.uniform(6.2, 7.6), 2)
        ctrl["curr"] = round(random.uniform(10.8, 12.6), 2)
        ctrl["rpm"] = random.randint(920, 1080)
        ctrl["operational_state"] = "TRIPPED_STOPPED"
        print(f"🚨 [SAFETY TRIP] High failure risk detected on {mid}! Machine automatically shut down.")

    # Severe Anomaly Build-up
    elif remaining == 1:
        ctrl["temp"] = round(random.uniform(89.0, 93.5), 2)
        ctrl["vib"] = round(random.uniform(4.9, 5.8), 2)
        ctrl["curr"] = round(random.uniform(9.0, 10.5), 2)
        ctrl["rpm"] = random.randint(1180, 1300)

    # Elevated Warning
    elif remaining <= 3:
        ctrl["temp"] = round(random.uniform(82.0, 87.5), 2)
        ctrl["vib"] = round(random.uniform(3.6, 4.6), 2)
        ctrl["curr"] = round(random.uniform(7.5, 8.8), 2)
        ctrl["rpm"] = random.randint(1320, 1450)

    # Mild Rise
    elif remaining <= 5:
        ctrl["temp"] = round(random.uniform(72.0, 78.5), 2)
        ctrl["vib"] = round(random.uniform(2.3, 3.2), 2)
        ctrl["curr"] = round(random.uniform(5.8, 6.9), 2)
        ctrl["rpm"] = random.randint(1480, 1580)

    # Healthy Baseline
    else:
        ctrl["temp"] = round(max(56.0, min(68.0, ctrl["temp"] + random.uniform(-0.6, 0.6))), 2)
        ctrl["vib"] = round(max(1.0, min(1.8, ctrl["vib"] + random.uniform(-0.08, 0.08))), 2)
        ctrl["curr"] = round(max(4.2, min(5.4, ctrl["curr"] + random.uniform(-0.1, 0.1))), 2)
        ctrl["rpm"] = int(max(1580, min(1740, ctrl["rpm"] + random.randint(-15, 15))))

    return process_telemetry_reading(
        machine_id=mid,
        temperature=ctrl["temp"],
        vibration=ctrl["vib"],
        current=ctrl["curr"],
        rpm=ctrl["rpm"],
    )


def generate_autonomous_cycle():
    """Generates 1 telemetry reading cycle for all monitored machines."""
    results = []
    machines = getattr(settings, 'MONITORED_MACHINES', ['M01', 'M02', 'M03'])
    for mid in machines:
        try:
            res = step_machine_telemetry(mid)
            results.append(res)
        except Exception as e:
            print(f"[Simulator Error] Step error for {mid}: {e}")
    return results


def normalize_machine(machine_id: str) -> Dict[str, Any]:
    """Operator Action: Inspect, repair, and restart a stopped machine back to healthy running state."""
    machines = getattr(settings, 'MONITORED_MACHINES', ['M01', 'M02', 'M03'])
    if machine_id not in machines:
        raise ValueError(f"Machine {machine_id} is not in monitored list.")

    ctrl = MACHINE_CONTROLLERS.setdefault(machine_id, {})
    ctrl["operational_state"] = "RUNNING"
    ctrl["cycles"] = 0
    ctrl["cycles_to_fault"] = random.randint(7, 14)
    ctrl["temp"] = round(random.uniform(58.0, 64.0), 2)
    ctrl["vib"] = round(random.uniform(1.1, 1.6), 2)
    ctrl["curr"] = round(random.uniform(4.2, 5.2), 2)
    ctrl["rpm"] = random.randint(1600, 1720)

    reading = process_telemetry_reading(
        machine_id=machine_id,
        temperature=ctrl["temp"],
        vibration=ctrl["vib"],
        current=ctrl["curr"],
        rpm=ctrl["rpm"],
    )
    return {
        "message": f"Machine {machine_id} inspected, repaired, and restarted into autonomous operation.",
        "reading": reading,
    }


_worker_started = False
_worker_lock = threading.Lock()


def start_background_telemetry_worker():
    """Starts background thread to emit telemetry cycles every 5 seconds."""
    global _worker_started
    with _worker_lock:
        if _worker_started:
            return
        _worker_started = True

    def loop():
        time.sleep(3)
        while True:
            try:
                generate_autonomous_cycle()
            except Exception as exc:
                print(f"[Simulator Worker] Error: {exc}")
            time.sleep(5)

    worker_thread = threading.Thread(target=loop, daemon=True, name="TelemetrySimulatorWorker")
    worker_thread.start()
    print("🚀 [Simulator] Autonomous telemetry worker thread started.")
