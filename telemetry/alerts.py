"""
Email Alert Service for AI Predictive Maintenance in Django.
Supports SMTP (Gmail, Outlook) and HTTPS APIs, with automated cooldown suppression
and audit trail logging via Django ORM.
"""
import smtplib
import socket
import ssl
import json
import urllib.request
import urllib.error
from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Dict, Any, Optional, List

from django.conf import settings
from django.utils import timezone
from .models import AlertLog


class IPv4SMTP(smtplib.SMTP):
    """SMTP client forcing IPv4 socket resolution."""
    def _get_socket(self, host, port, timeout):
        try:
            res = socket.getaddrinfo(host, port, socket.AF_INET, socket.SOCK_STREAM)
            target = res[0][4]
        except Exception:
            target = (host, port)
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        sock.connect(target)
        return sock


class IPv4SMTP_SSL(smtplib.SMTP_SSL):
    """SMTP SSL client forcing IPv4 socket resolution."""
    def _get_socket(self, host, port, timeout):
        try:
            res = socket.getaddrinfo(host, port, socket.AF_INET, socket.SOCK_STREAM)
            target = res[0][4]
        except Exception:
            target = (host, port)
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        sock.connect(target)
        return self.context.wrap_socket(sock, server_hostname=self._host)


def _build_email_contents(machine_id: str, status: str, risk_percent: float, sensor: Dict[str, Any]):
    """Build formatted plain-text and HTML alert email bodies."""
    subject = f"🚨 [CRITICAL ALERT] {machine_id} - {status} ({risk_percent:.1f}% Failure Risk)"
    timestamp_str = timezone.now().strftime("%Y-%m-%d %H:%M:%S UTC")

    plain_text = f"""\
AI Predictive Maintenance Alert
=================================
Machine ID:    {machine_id}
Status:        {status}
Failure Risk:  {risk_percent:.1f}%
Detected At:   {timestamp_str}

Telemetry Readings:
- Temperature: {sensor.get('temperature', 0):.1f} °C
- Vibration:   {sensor.get('vibration', 0):.2f} mm/s
- Current:     {sensor.get('current', 0):.2f} A
- RPM:         {sensor.get('rpm', 0):.0f}

Recommended Action:
Schedule immediate mechanical and thermal inspection for Machine {machine_id}.
    """

    risk_color = "#ef4444" if risk_percent >= 80 else "#f59e0b"

    html_text = f"""\
<!DOCTYPE html>
<html>
<body style="margin:0;padding:24px;background-color:#0f172a;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;color:#f8fafc;">
  <div style="max-width:580px;margin:0 auto;background-color:#1e293b;border-radius:12px;border:1px solid #334155;overflow:hidden;box-shadow:0 10px 25px rgba(0,0,0,0.5);">
    <div style="background-color:{risk_color};padding:20px 24px;text-align:center;">
      <h1 style="margin:0;font-size:22px;color:#ffffff;font-weight:700;">🚨 Predictive Maintenance Incident</h1>
      <p style="margin:6px 0 0;font-size:14px;color:rgba(255,255,255,0.9);">{machine_id} Crossed Anomaly Threshold</p>
    </div>

    <div style="padding:28px 24px;">
      <div style="display:flex;justify-content:space-between;margin-bottom:20px;border-bottom:1px solid #334155;padding-bottom:16px;">
        <div>
          <span style="font-size:12px;color:#94a3b8;text-transform:uppercase;letter-spacing:0.05em;">Machine Target</span>
          <div style="font-size:20px;font-weight:bold;color:#38bdf8;">{machine_id}</div>
        </div>
        <div style="text-align:right;">
          <span style="font-size:12px;color:#94a3b8;text-transform:uppercase;letter-spacing:0.05em;">ML Failure Risk</span>
          <div style="font-size:22px;font-weight:bold;color:{risk_color};">{risk_percent:.1f}%</div>
        </div>
      </div>

      <h3 style="font-size:14px;color:#94a3b8;margin:0 0 12px;text-transform:uppercase;letter-spacing:0.05em;">Sensor Telemetry Snapshot</h3>
      <table style="width:100%;border-collapse:collapse;margin-bottom:24px;font-size:14px;">
        <tr style="background:#0f172a;">
          <td style="padding:10px 14px;border:1px solid #334155;color:#94a3b8;">Temperature</td>
          <td style="padding:10px 14px;border:1px solid #334155;font-weight:600;color:#f8fafc;">{sensor.get('temperature', 0):.1f} °C</td>
        </tr>
        <tr>
          <td style="padding:10px 14px;border:1px solid #334155;color:#94a3b8;">Vibration Velocity</td>
          <td style="padding:10px 14px;border:1px solid #334155;font-weight:600;color:#f8fafc;">{sensor.get('vibration', 0):.2f} mm/s</td>
        </tr>
        <tr style="background:#0f172a;">
          <td style="padding:10px 14px;border:1px solid #334155;color:#94a3b8;">Operating Current</td>
          <td style="padding:10px 14px;border:1px solid #334155;font-weight:600;color:#f8fafc;">{sensor.get('current', 0):.2f} A</td>
        </tr>
        <tr>
          <td style="padding:10px 14px;border:1px solid #334155;color:#94a3b8;">Spindle Speed</td>
          <td style="padding:10px 14px;border:1px solid #334155;font-weight:600;color:#f8fafc;">{sensor.get('rpm', 0):.0f} RPM</td>
        </tr>
      </table>

      <div style="background-color:#0f172a;border-left:4px solid {risk_color};padding:14px;border-radius:4px;font-size:13px;color:#cbd5e1;">
        <strong>Recommended Action:</strong> Inspect {machine_id} mechanical bearings, lubrication, and cooling systems immediately.
      </div>
    </div>

    <div style="background-color:#0f172a;padding:14px 24px;border-top:1px solid #334155;font-size:12px;color:#64748b;text-align:center;">
      Autonomous Alert dispatched by Django AI Predictive Maintenance System at {timestamp_str}
    </div>
  </div>
</body>
</html>
    """
    return subject, plain_text, html_text


def send_via_resend(
    api_key: str,
    from_addr: str,
    targets: List[str],
    subject: str,
    html_text: str,
    plain_text: str,
) -> Dict[str, Any]:
    """Dispatches alert email via Resend HTTPS REST API (Port 443 - works on Render Free)."""
    url = "https://api.resend.com/emails"
    # Resend default testing sender allows sending to the registered account email
    sender = from_addr if ("@" in from_addr and not from_addr.lower().endswith("@gmail.com")) else "AI Predictive Alert <onboarding@resend.dev>"
    
    payload = json.dumps({
        "from": sender,
        "to": targets,
        "subject": subject,
        "html": html_text,
        "text": plain_text,
    }).encode("utf-8")

    req = urllib.request.Request(
        url,
        data=payload,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": "Django-AI-Predictive-Maintenance/1.0",
        },
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=12) as response:
            res_data = json.loads(response.read().decode("utf-8"))
            return {"sent": True, "recipients": targets, "status": "sent", "resend_id": res_data.get("id")}
    except urllib.error.HTTPError as err:
        err_body = err.read().decode("utf-8")
        try:
            parsed = json.loads(err_body)
            msg = parsed.get("message", err_body)
        except Exception:
            msg = err_body
        print(f"[Resend API Error] Status {err.code}: {msg}")
        return {"sent": False, "reason": "api_error", "detail": f"Resend error ({err.code}): {msg}"}
    except Exception as exc:
        print(f"[Resend Error] {exc}")
        return {"sent": False, "reason": "api_error", "detail": str(exc)}


def send_alert_email(
    machine_id: str,
    status: str,
    risk_percent: float,
    sensor: Dict[str, Any],
    recipients: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Sends email alert via Resend HTTPS API (cloud-friendly) or SMTP fallback."""
    cfg = settings.EMAIL_CONFIG
    targets = recipients or cfg.get("recipients", [])

    if not targets:
        return {"sent": False, "reason": "no_recipients", "detail": "No recipients configured."}

    subject, plain_text, html_text = _build_email_contents(machine_id, status, risk_percent, sensor)

    # 1. Prefer Resend HTTPS API if configured (works seamlessly on Render Free & all cloud platforms)
    resend_key = cfg.get("resend_api_key")
    if resend_key:
        from_addr = cfg.get("from_email") or "onboarding@resend.dev"
        return send_via_resend(resend_key, from_addr, targets, subject, html_text, plain_text)

    # 2. Otherwise fall back to traditional SMTP
    user = cfg.get("smtp_user", "")
    password = cfg.get("smtp_password", "")
    from_addr = cfg.get("from_email") or user

    if not user or not password:
        return {
            "sent": False,
            "reason": "not_configured",
            "detail": "Neither RESEND_API_KEY nor SMTP credentials configured in environment variables."
        }

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = from_addr
    msg["To"] = ", ".join(targets)
    msg.attach(MIMEText(plain_text, "plain"))
    msg.attach(MIMEText(html_text, "html"))

    host = cfg.get("smtp_host", "smtp.gmail.com")
    port = int(cfg.get("smtp_port", 587))

    try:
        if port == 465:
            server = IPv4SMTP_SSL(host, port, timeout=12)
            server.login(user, password)
        else:
            server = IPv4SMTP(host, port, timeout=12)
            server.ehlo()
            server.starttls(context=ssl.create_default_context())
            server.ehlo()
            server.login(user, password)

        server.sendmail(from_addr, targets, msg.as_string())
        server.quit()
        return {"sent": True, "recipients": targets, "status": "sent"}
    except Exception as exc:
        print(f"[Email Error] Failed sending alert email for {machine_id}: {exc}")
        err_msg = str(exc)
        if "timed out" in err_msg.lower() or "10060" in err_msg or "refused" in err_msg.lower():
            err_msg += " (Note: Cloud hosts like Render Free block SMTP ports 25/465/587. Add RESEND_API_KEY in Render Environment Variables for HTTPS delivery)"
        return {"sent": False, "reason": "smtp_error", "detail": err_msg}


def maybe_send_alert(
    machine_id: str,
    status: str,
    risk_percent: float,
    sensor: Dict[str, Any],
    email_enabled: bool = True,
) -> Optional[Dict[str, Any]]:
    """Evaluates cooldown against DB and dispatches alert if applicable."""
    if not email_enabled:
        return {"sent": False, "reason": "disabled"}

    cooldown_min = getattr(settings, 'ALERT_COOLDOWN_MINUTES', 30)
    cooldown_cutoff = timezone.now() - timedelta(minutes=cooldown_min)

    recent_sent = AlertLog.objects.filter(
        machine_id=machine_id,
        email_status='sent',
        sent_at__gte=cooldown_cutoff
    ).first()

    if recent_sent:
        elapsed_seconds = (timezone.now() - recent_sent.sent_at).total_seconds()
        remaining = int(cooldown_min * 60 - elapsed_seconds)
        return {
            "sent": False,
            "reason": "cooldown",
            "remaining_seconds": max(0, remaining),
            "detail": f"In cooldown for next {max(0, remaining)}s"
        }

    # Dispatch email
    result = send_alert_email(machine_id, status, risk_percent, sensor)
    recipients_str = ", ".join(settings.EMAIL_CONFIG.get("recipients", []))

    if result.get("sent"):
        AlertLog.objects.create(
            machine_id=machine_id,
            risk_percent=risk_percent,
            status=status,
            recipients=recipients_str,
            email_status="sent",
            error_message=None,
        )
    else:
        # If not configured or failed, record reason in audit log
        AlertLog.objects.create(
            machine_id=machine_id,
            risk_percent=risk_percent,
            status=status,
            recipients=recipients_str,
            email_status=result.get("reason", "failed"),
            error_message=result.get("detail"),
        )

    return result


def send_test_email(recipient: Optional[str] = None) -> Dict[str, Any]:
    """Trigger a diagnostic email for operator testing."""
    targets = [recipient] if recipient else settings.EMAIL_CONFIG.get("recipients", [])
    if not targets:
        return {"sent": False, "reason": "no_recipients", "detail": "Please specify a recipient email."}

    dummy_sensor = {
        "temperature": 88.5,
        "vibration": 5.4,
        "current": 9.8,
        "rpm": 1210,
    }

    result = send_alert_email("M01-TEST", "HIGH FAILURE RISK (TEST)", 92.5, dummy_sensor, targets)
    
    AlertLog.objects.create(
        machine_id="M01-TEST",
        risk_percent=92.5,
        status="HIGH FAILURE RISK (TEST)",
        recipients=", ".join(targets),
        email_status="sent" if result.get("sent") else result.get("reason", "failed"),
        error_message=result.get("detail"),
    )
    return result
