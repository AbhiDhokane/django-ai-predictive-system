# 🏭 AI Predictive Maintenance System (Django Edition)

An enterprise-grade, cloud-ready Predictive Maintenance IoT & AI Telemetry System converted to **Python Django**. Monitors industrial machines (`M01`–`M03`), performs real-time Machine Learning failure risk classification using a trained Random Forest model, visualizes live telemetry graphs on a modern Tailwind + Chart.js dashboard, and dispatches automated **SMTP email alerts** with per-machine cooldowns when critical risk thresholds are crossed.

---

## 🌟 Key Features

- **Full Django Architecture:** Built with Django models, views, management commands, and Django Admin.
- **Unified Service:** Django serves both the **interactive dark-mode frontend dashboard** and the high-performance **REST API** (`/api/...`) from a single service on port 8000.
- **Machine Learning Inference:** Integrated Scikit-Learn `failure_model.pkl` Random Forest classifier evaluating temperature, vibration, current, and RPM in real time.
- **Autonomous IoT Telemetry Simulation:** Background simulator thread continuously streams multi-stage physical wear and emergency safety trip lockouts.
- **Incident Alerts & Cooldown:** Automated email notifications via SMTP with cooldown suppression to prevent email flooding.
- **Django Admin Interface:** Full operational oversight of raw sensor streams and alert audit logs at `/admin/`.
- **Database Flexibility:** Works instantly out-of-the-box with **SQLite** (`db.sqlite3`) for local development, or switches to **PostgreSQL** (Neon, Render, Supabase) simply by setting `DATABASE_URL` in `.env`.

---

## ⚡ Quickstart (Local Development)

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment

Copy `.env.example` to `.env` (already configured for local SQLite):

```bash
cp .env.example .env
```

### 3. Run Database Migrations & Seed Telemetry

```bash
python manage.py makemigrations
python manage.py migrate
python manage.py seed_data
```

*(Optional) Create a superuser to access the Django Admin:*
```bash
python manage.py createsuperuser
```

### 4. Start the Django Server

```bash
python manage.py runserver 8000
```

- **Dashboard UI:** [http://127.0.0.1:8000/](http://127.0.0.1:8000/)
- **Django Admin:** [http://127.0.0.1:8000/admin/](http://127.0.0.1:8000/admin/)
- **Health Check:** [http://127.0.0.1:8000/api/status](http://127.0.0.1:8000/api/status)

---

## 🛠️ Management Commands

| Command | Description |
| :--- | :--- |
| `python manage.py seed_data` | Seeds initial historical telemetry and sample alert logs. |
| `python manage.py run_simulator` | Runs the telemetry generator as a standalone continuous CLI process. |
| `python manage.py train_model` | Retrains the Random Forest classifier on synthetic sensor data and exports `model/failure_model.pkl`. |

---

## 📡 REST API Reference

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/status` | System health check and API version. |
| `GET` | `/api/machines` | List monitored machines (`["M01", "M02", "M03"]`). |
| `GET` | `/api/readings/latest` | Latest telemetry readings and AI risk classification for each machine. |
| `GET` | `/api/readings/history?machine_id=M01&limit=50` | Historical readings formatted for time-series charts. |
| `POST` | `/api/readings` | Ingest a new sensor packet (`{machine_id, temperature, vibration, current, rpm}`). |
| `GET` | `/api/overview` | Fleet-wide overview metrics, alert counts, and machine statuses. |
| `POST` | `/api/predict` | Direct ML inference endpoint. |
| `GET` | `/api/alerts/recent` | Recent incident logs audit trail. |
| `POST` | `/api/alerts/test` | Dispatch a test email notification. |
| `POST` | `/api/simulator/tick` | Manually advance telemetry cycle across all machines. |
| `POST` | `/api/simulator/normalize?machine_id=M03` | Operator action: repair/heal and restart a tripped machine. |
| `GET` | `/api/settings` | Retrieve runtime configuration. |
| `POST` | `/api/settings/email-toggle` | Dynamically enable/disable automated email notifications. |

---

## 🗄️ Database Models

- **`SensorReading` (`sensor_readings`):**
  - `machine_id`: Machine identifier (e.g. `M01`, `M02`, `M03`)
  - `temperature`: Temperature (°C)
  - `vibration`: Vibration velocity (mm/s)
  - `current`: Operating current (A)
  - `rpm`: Spindle speed (RPM)
  - `recorded_at`: Timestamp (UTC)
- **`AlertLog` (`alert_log`):**
  - `machine_id`: Incident target
  - `risk_percent`: Evaluated risk percentage
  - `status`: Machine status (`WARNING`, `HIGH FAILURE RISK`)
  - `recipients`: Comma-separated email recipients
  - `email_status`: Status (`sent`, `failed`, `cooldown`, etc.)
  - `error_message`: Error details if delivery failed
  - `sent_at`: Timestamp (UTC)
