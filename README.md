# Chronos Frame Agent

**Chronos Frame Agent** is an autonomous AI agent application that curates top global news, generates stylized 9:16 portrait artwork via Google GenAI / Gemini, and pushes real-time Server-Sent Events (SSE) to smart digital frame displays (specifically optimized for the **Lenovo Smart Frame** running **Fully Kiosk Browser** and Portainer on **Asustor NAS**).

---

## ✨ Features

- **Autonomous 15-Minute News Ingestion**: Fetches top 5 global headlines, applies content safety filters, and deduplicates stories using sliding-window Jaccard keyword memory.
- **Dynamic 9:16 Portrait Generation**: Produces 1080x1920 portrait bulletin art using Nano Banana 2 / Gemini image models with dynamic time-of-day styling (Morning Retro-Pop, Midday Claymation, Evening Luminescent).
- **Synchronized 5-Minute Display Rotation**: Coordinates display slideshows via Server-Sent Events (SSE), eliminating client reload race conditions.
- **Full-Screen Ambient Display**: Pure edge-to-edge canvas with hardware-accelerated dual-layer GPU crossfades and memory pre-rendering.
- **100% Keyless ADC Security**: Connects to Google Cloud Vertex AI using auto-refreshing Application Default Credentials (ADC) with zero static private keys on disk.

---

## 🚀 Quick Start for Developers

```bash
# 1. Clone and run one-command setup (installs uv dependencies and pre-commit hooks)
make setup

# 2. Configure local environment (copy template)
cp .env.example .env
# Edit .env to set your GOOGLE_CLOUD_PROJECT and GOOGLE_APPLICATION_CREDENTIALS

# 3. Run the autonomous agent and smart frame web server locally
make run
```

The smart frame display will be live at `http://localhost:8080`.

---

## 🛠️ Developer Makefile Commands

A developer `Makefile` is provided for standard workflows:

| Make Target | Description |
| :--- | :--- |
| `make help` | Show all available make targets and descriptions |
| `make setup` | **One-step setup**: installs dependencies via `uv` and installs git `pre-commit` hooks |
| `make install` | Install production, dev, lint, and eval dependencies using `uv` |
| `make pre-commit` | Run `pre-commit` hooks manually across all files in the repository |
| `make test` | Run the full unit and integration test suite with `pytest` |
| `make lint` | Run code quality checks (`ruff check`, `ruff format --check`, `codespell`) |
| `make lint-fix` / `make format` | Automatically fix formatting and lint errors |
| `make run` | Start the autonomous scheduler loop and SSE web server locally |
| `make docker-build` | Build the optimized production Docker container image |
| `make clean` | Clean up Python bytecode, caches (`.pytest_cache`, `.ruff_cache`), and test artifacts |

---

## 🪝 Pre-commit Hooks

This project uses [pre-commit](https://pre-commit.com/) to automatically enforce code formatting, linting, and hygiene standards on every `git commit`.

```bash
# Run manually across all files anytime:
make pre-commit
# or
uv run pre-commit run --all-files
```

---

## 📁 Project Structure

```text
chronos-frame-agent/
├── app/
│   ├── agent.py               # ADK 2.0 Graph Workflow Agent definition
│   ├── event_hub.py           # Real-time SSE event hub and photo rotation coordinator
│   ├── memory.py              # Jaccard keyword deduplication & sliding window memory
│   ├── prompts.py             # Dynamic time-of-day style templates (Morning, Midday, Evening)
│   ├── tools.py               # NewsTool, ImagenTool, and PublisherTool (3-image FIFO)
│   └── fast_api_app.py        # FastAPI A2A backend server
├── smart_frame_web/           # Web client assets (index.html, playlist.json, image_*.png)
├── tests/
│   ├── unit/                  # Unit tests (memory, tools, event hub)
│   └── integration/           # Integration tests (agent workflow, web server E2E)
├── Dockerfile                 # Lean, cached production container
├── docker-compose.yml         # Portainer / NAS Compose stack specification
├── Makefile                   # Developer productivity commands
├── .pre-commit-config.yaml    # Pre-commit hooks configuration
├── pyproject.toml             # Project dependencies and tool configurations
└── DESIGN_SPEC.md             # Detailed architectural specification
```

---

## ⚙️ Environment Variables

| Variable | Default | Description |
| :--- | :--- | :--- |
| `PORT` | `8168` | HTTP port for the smart frame web server. |
| `SCHEDULE_INTERVAL_SECONDS` | `900` | Frequency (in seconds) to fetch news and generate new artwork (15 minutes). |
| `ROTATION_INTERVAL_SECONDS` | `300` | Frequency (in seconds) to cycle display through the 3-image queue (5 minutes). |
| `GOOGLE_APPLICATION_CREDENTIALS` | — | Path to the ADC JSON credentials file. |
| `GOOGLE_CLOUD_PROJECT` | — | Google Cloud project ID for Vertex AI. |
| `GOOGLE_CLOUD_LOCATION` | `us-central1` | GCP region for Vertex AI endpoints. |
| `GOOGLE_GENAI_USE_VERTEXAI` | `true` | Enables Vertex AI mode in `google-genai`. |

---

## 🐳 NAS & Portainer Deployment

Deploy on your Asustor NAS or any Docker host using [docker-compose.yml](docker-compose.yml):

```yaml
version: "3.8"

services:
  chronos-smart-frame:
    image: chronos-frame-agent:latest
    container_name: chronos-smart-frame
    restart: unless-stopped
    ports:
      - "8168:8168"
    volumes:
      # Read-only mount for your auto-refreshing ADC credentials
      - /volume1/docker/chronos-frame/secrets/application_default_credentials.json:/secrets/application_default_credentials.json:ro
      # Persist generated images and queue history across container restarts
      - /volume1/docker/chronos-frame/smart_frame_web:/app/smart_frame_web
    environment:
      - GOOGLE_APPLICATION_CREDENTIALS=/secrets/application_default_credentials.json
      - GOOGLE_CLOUD_PROJECT=<YOUR_GCP_PROJECT_ID>
      - GOOGLE_CLOUD_LOCATION=us-central1
      - GOOGLE_GENAI_USE_VERTEXAI=true
      - PORT=8168
      - SCHEDULE_INTERVAL_SECONDS=900
      - ROTATION_INTERVAL_SECONDS=300
      - TZ=Australia/Sydney

  # Automatic Nightly Shutdown (10 PM) & Morning Start (6 AM) - Australian Time
  nightly-scheduler:
    image: docker:cli
    container_name: chronos-scheduler
    restart: unless-stopped
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
      - /etc/localtime:/etc/localtime:ro
    environment:
      - TZ=Australia/Sydney
    entrypoint: ["/bin/sh", "-c"]
    command:
      - |
        apk add --no-cache tzdata > /dev/null 2>&1
        echo "0 22 * * * docker stop chronos-smart-frame" > /etc/crontabs/root
        echo "0 6 * * * docker start chronos-smart-frame" >> /etc/crontabs/root
        crond -f -l 2
```

---

## 🖼️ Lenovo Smart Frame (Fully Kiosk Browser) Setup

1. In Fully Kiosk Browser on the Smart Frame, set **Start URL** to `http://<YOUR_NAS_IP>:8168`.
2. Under **Display Settings**:
   - Enable **Fullscreen Mode** (hides navigation/status bars).
   - Enable **Keep Screen On**.
   - Enable **Hardware Acceleration** (for 60fps GPU crossfade transitions).
3. Enable **Autostart on Boot**.
