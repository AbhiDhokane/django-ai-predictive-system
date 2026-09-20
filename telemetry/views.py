"""
Django Views & REST API endpoints for AI Predictive Maintenance System.
Preserves 100% compatibility with the original FastAPI contracts and frontends.
"""
import json
from datetime import datetime, timezone
from typing import Dict, Any

from django.conf import settings
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils import timezone as dj_timezone

from .models import SensorReading, AlertLog
from .ml_model import predict_risk
from .alerts import send_test_email
from .simulator import (
    RUNTIME_SETTINGS,
    MACHINE_CONTROLLERS,
    generate_autonomous_cycle,
    normalize_machine,
    process_telemetry_reading,
)


def dashboard_view(request):
    """Renders the main industrial telemetry dashboard."""
    return render(request, 'index.html', {
        'api_url': request.build_absolute_uri('/')[:-1],
    })


@require_http_methods(["GET"])
def health_check(request):
    """Health check endpoint."""
    return JsonResponse({
        "status": "healthy",
        "service": "AI Predictive Maintenance System (Django)",
        "version": "2.0.0",
        "timestamp": dj_timezone.now().isoformat(),
    })


@require_http_methods(["GET"])
def list_machines(request):
    """Returns list of monitored machine identifiers."""
    machines = getattr(settings, 'MONITORED_MACHINES', ['M01', 'M02', 'M03'])
    return JsonResponse(machines, safe=False)


def _fetch_latest_machine_readings():
    """Helper: fetches the latest reading and AI risk status for each monitored machine."""
    machines = getattr(settings, 'MONITORED_MACHINES', ['M01', 'M02', 'M03'])
    response_data = []

    for mid in machines:
        last_reading = SensorReading.objects.filter(machine_id=mid).order_by('-recorded_at').first()
        ctrl = MACHINE_CONTROLLERS.get(mid, {})
        op_state = ctrl.get("operational_state", "RUNNING")

        if last_reading:
            pred = predict_risk(
                last_reading.temperature,
                last_reading.vibration,
                last_reading.current,
                last_reading.rpm,
            )
            display_status = "EMERGENCY STOPPED" if (op_state == "TRIPPED_STOPPED" and last_reading.rpm == 0) else pred["status"]
            response_data.append({
                "machine_id": mid,
                "temperature": round(float(last_reading.temperature), 2),
                "vibration": round(float(last_reading.vibration), 2),
                "current": round(float(last_reading.current), 2),
                "rpm": int(last_reading.rpm),
                "recorded_at": last_reading.recorded_at.isoformat(),
                "status": display_status,
                "risk_percent": pred["risk_percent"],
                "operational_state": op_state,
                "alert_info": None,
            })
        else:
            # Fallback default baseline if no readings stored yet
            response_data.append({
                "machine_id": mid,
                "temperature": 60.0,
                "vibration": 1.5,
                "current": 4.8,
                "rpm": 1650,
                "recorded_at": dj_timezone.now().isoformat(),
                "status": "NORMAL",
                "risk_percent": 12.0,
                "operational_state": "RUNNING",
                "alert_info": None,
            })

    return response_data


@require_http_methods(["GET"])
def get_latest_readings(request):
    """Returns the latest reading and AI risk status for each machine."""
    return JsonResponse(_fetch_latest_machine_readings(), safe=False)


@require_http_methods(["GET"])
def get_history(request):
    """Returns historical readings for charting."""
    machine_id = request.GET.get('machine_id')
    try:
        limit = min(int(request.GET.get('limit', 50)), 500)
    except (TypeError, ValueError):
        limit = 50

    qs = SensorReading.objects.all()
    if machine_id:
        qs = qs.filter(machine_id=machine_id)
    qs = qs.order_by('-recorded_at')[:limit]

    # Convert to ascending chronological order for time-series charts
    readings = list(qs)[::-1]
    data = []
    for r in readings:
        pred = predict_risk(r.temperature, r.vibration, r.current, r.rpm)
        data.append({
            "temperature": round(float(r.temperature), 2),
            "vibration": round(float(r.vibration), 2),
            "current": round(float(r.current), 2),
            "rpm": int(r.rpm),
            "risk_percent": pred["risk_percent"],
            "recorded_at": r.recorded_at.isoformat(),
        })

    return JsonResponse(data, safe=False)


@csrf_exempt
@require_http_methods(["POST"])
def create_sensor_reading(request):
    """Ingests a new telemetry packet, runs ML prediction, saves reading, triggers alerts."""
    try:
        payload = json.loads(request.body)
        mid = str(payload['machine_id'])
        temp = float(payload['temperature'])
        vib = float(payload['vibration'])
        curr = float(payload['current'])
        rpm = int(payload['rpm'])
    except (KeyError, ValueError, json.JSONDecodeError) as exc:
        return JsonResponse({"detail": f"Invalid payload format: {str(exc)}"}, status=400)

    result = process_telemetry_reading(mid, temp, vib, curr, rpm)
    return JsonResponse(result, status=200)


@require_http_methods(["GET"])
def get_system_overview(request):
    """Returns high-level system metrics and active fleet statuses."""
    total_readings = SensorReading.objects.count()
    total_alerts_sent = AlertLog.objects.filter(email_status='sent').count()
    machines_list = getattr(settings, 'MONITORED_MACHINES', ['M01', 'M02', 'M03'])
    threshold = getattr(settings, 'ALERT_RISK_THRESHOLD', 75)

    # Latest readings response
    machines_data = _fetch_latest_machine_readings()

    return JsonResponse({
        "total_readings": total_readings,
        "total_alerts_sent": total_alerts_sent,
        "monitored_machines": machines_list,
        "alert_threshold": threshold,
        "email_alerts_enabled": RUNTIME_SETTINGS["email_alerts_enabled"],
        "machines": machines_data,
    })


@csrf_exempt
@require_http_methods(["POST"])
def predict_endpoint(request):
    """Direct ML inference endpoint for raw sensor values."""
    try:
        data = json.loads(request.body)
        temp = float(data['temperature'])
        vib = float(data['vibration'])
        curr = float(data['current'])
        rpm = int(data['rpm'])
    except (KeyError, ValueError, json.JSONDecodeError) as exc:
        return JsonResponse({"detail": f"Invalid parameters: {str(exc)}"}, status=400)

    try:
        result = predict_risk(temp, vib, curr, rpm)
        return JsonResponse(result)
    except Exception as exc:
        return JsonResponse({"detail": f"Inference failure: {str(exc)}"}, status=500)


@require_http_methods(["GET"])
def get_recent_alerts(request):
    """Returns latest alert incident records."""
    try:
        limit = min(int(request.GET.get('limit', 20)), 100)
    except (TypeError, ValueError):
        limit = 20

    alerts = AlertLog.objects.order_by('-sent_at')[:limit]
    data = [a.to_dict() for a in alerts]
    return JsonResponse(data, safe=False)


@csrf_exempt
@require_http_methods(["POST"])
def trigger_test_alert(request):
    """Dispatches a test incident email notification."""
    recipient = None
    if request.body:
        try:
            body = json.loads(request.body)
            recipient = body.get('recipient')
        except Exception:
            pass

    result = send_test_email(recipient)
    status_code = 200 if result.get("sent") else 400
    return JsonResponse(result, status=status_code)


@csrf_exempt
@require_http_methods(["POST"])
def simulate_tick(request):
    """Manual fast-forward simulation cycle across all machines."""
    generate_autonomous_cycle()
    readings = _fetch_latest_machine_readings()
    return JsonResponse({
        "message": "Continuous telemetry cycle generated",
        "readings": readings,
    })


@csrf_exempt
@require_http_methods(["POST"])
def normalize_machine_endpoint(request):
    """Operator Action: Inspect, repair, and restart an emergency stopped machine."""
    machine_id = request.GET.get('machine_id')
    if not machine_id and request.body:
        try:
            body = json.loads(request.body)
            machine_id = body.get('machine_id')
        except Exception:
            pass

    if not machine_id:
        return JsonResponse({"detail": "machine_id query parameter or body field required."}, status=400)

    try:
        result = normalize_machine(machine_id)
        return JsonResponse(result)
    except ValueError as exc:
        return JsonResponse({"detail": str(exc)}, status=400)
    except Exception as exc:
        return JsonResponse({"detail": str(exc)}, status=500)


@require_http_methods(["GET"])
def get_settings(request):
    """Get dynamic runtime configuration."""
    return JsonResponse({
        "email_alerts_enabled": RUNTIME_SETTINGS["email_alerts_enabled"],
        "alert_threshold": getattr(settings, 'ALERT_RISK_THRESHOLD', 75),
        "alert_cooldown_minutes": getattr(settings, 'ALERT_COOLDOWN_MINUTES', 30),
    })


@csrf_exempt
@require_http_methods(["POST"])
def toggle_email_alerts(request):
    """Toggle automated email alerts on or off dynamically."""
    enabled_param = request.GET.get('enabled')
    if enabled_param is not None:
        val = enabled_param.lower() in ('true', '1', 'yes')
        RUNTIME_SETTINGS["email_alerts_enabled"] = val
    else:
        RUNTIME_SETTINGS["email_alerts_enabled"] = not RUNTIME_SETTINGS["email_alerts_enabled"]

    is_on = RUNTIME_SETTINGS["email_alerts_enabled"]
    return JsonResponse({
        "email_alerts_enabled": is_on,
        "status": "ACTIVE" if is_on else "PAUSED",
        "message": f"Email alert notifications are now {'ENABLED (Active)' if is_on else 'DISABLED (Turned OFF)'}."
    })
