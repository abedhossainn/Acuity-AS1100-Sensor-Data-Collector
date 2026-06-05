# Acuity Sensor Program

AS1100 is a local-first sensor acquisition application for collecting, monitoring, and exporting measurement sessions from supported serial-connected devices.

It is designed for practical day-to-day acquisition workflows:

- Start a session and stream live sensor samples in the web UI
- Persist session data durably for later review
- Browse session history and download session exports (CSV/ZIP)
- Keep timestamps aligned with the host machine timezone in agent mode

In short: this app helps you move from **live sensor capture** to **structured, exportable session data** with a simple browser-based interface.

The system is composed of:

- **Backend**: FastAPI (`backend/`)
- **Frontend**: Next.js (`frontend/`)
- **Host agent**: FastAPI bridge to host serial ports (`host_agent/`)

The backend runs in Docker and talks to the host agent through `host.docker.internal`.

## Repository Structure

- `docker-compose.yml` — root development stack (backend + frontend)
- `backend/` — acquisition APIs, session persistence, export logic
- `frontend/` — web UI
- `host_agent/` — host-side serial/agent service on port `8010`
- `start_agent_session.ps1` — root helper script to start host agent

## Prerequisites

- Docker Desktop (with Compose)
- Windows PowerShell
- Python 3.10+ (for `host_agent`)

## Quick Start (Recommended)

### 1) Start the host agent (on the host machine)

From repo root:

`./start_agent_session.ps1`

What this script does:

- Checks `http://127.0.0.1:8010/health`
- Installs `host_agent` dependencies if needed
- Starts `uvicorn main:app --host 127.0.0.1 --port 8010`

Keep this terminal open while using the app.

### 2) Start backend + frontend with Docker

From repo root:

- Build images: `docker compose build backend frontend`
- Start services: `docker compose up -d`

### 3) Open the app

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- Backend docs: http://localhost:8000/docs

## Timezone Behavior

- Timestamps are emitted as **offset-aware ISO datetimes**.
- In `agent` mode, backend timezone info is sourced from host agent `/time-info`.
- Session times and export naming follow host-local timezone semantics.

## Persistence & Data

- Docker named volume: `acuitysensorprogram_sensor_data`
- Mounted in backend at `/data`
- `AS1100_PERSISTENCE_MODE=dual` is enabled by default in `docker-compose.yml`.

## Useful Operations

### View service status

`docker compose ps`

### View logs

- Backend: `docker compose logs -f backend`
- Frontend: `docker compose logs -f frontend`

### Stop services

`docker compose down`

### Fresh reset (destructive)

Removes containers, network, and the project data volume:

`docker compose down --volumes --remove-orphans`

Then rebuild and start fresh:

- `docker compose build --no-cache backend frontend`
- `docker compose up -d --force-recreate`

## Troubleshooting

### UI or API shows UTC unexpectedly

1. Confirm host agent is running: `http://127.0.0.1:8010/health`
2. Confirm time endpoint: `http://127.0.0.1:8010/time-info`
3. Restart host agent from repo root with `./start_agent_session.ps1`
4. Restart backend container: `docker compose restart backend`

### Backend cannot reach host agent

- Ensure backend env includes:
  - `SENSOR_PROVIDER=agent`
  - `AGENT_BASE_URL=http://host.docker.internal:8010`
- Ensure host agent is bound to `127.0.0.1:8010` and healthy.

## Notes

- For local development, use the root `docker-compose.yml` and root `start_agent_session.ps1`.