# Chronos Frame Agent

**Chronos Frame Agent** is an autonomous AI agent application that curates top global news, generates stylized 9:16 portrait artwork via Google GenAI / Gemini, and pushes real-time Server-Sent Events (SSE) to smart digital frame displays (specifically optimized for the **Lenovo Smart Frame** running **Fully Kiosk Browser** and Portainer on **Asustor NAS**).

---

## ✨ Features

- **Autonomous 15-Minute News Ingestion**: Fetches top 5 global headlines, applies content safety filters, and deduplicates stories using sliding-window Jaccard keyword memory (`HeadlineMemory`).
- **Dynamic 9:16 Portrait Generation**: Produces 1080x1920 portrait bulletin art using Nano Banana / Gemini image models with time-of-day responsive 3D figure styling (Sunrise Vinyl Pop, Electric Matte Figurine, Luminescent Cyber-Toy).
- **Synchronized 5-Minute Display Rotation**: Coordinates display slideshows via Server-Sent Events (SSE), eliminating client reload race conditions and image tearing.
- **Full-Screen Ambient Display**: Pure edge-to-edge canvas with hardware-accelerated dual-layer GPU crossfades and in-memory pre-rendering.
- **Resilient Fallback Architecture**: Seamlessly falls back to a curated offline news pool and procedural canvas rendering if network or API quotas are unavailable.
- **100% Keyless ADC Security**: Connects to Google Cloud Vertex AI using auto-refreshing Application Default Credentials (ADC) with zero static private keys on disk (or optional `GEMINI_API_KEY`).

---

## 🚀 Quick Start for Developers

### Prerequisites: Install `uv`

Before running `make setup`, you must have Astral's [**uv**](https://docs.astral.sh/uv/) installed. `uv` is an extremely fast Python package and virtual environment manager used across all project scripts, Makefile targets, and pre-commit tooling.

Sample installation commands:

- **macOS / Linux** (standalone installer):
  ```bash
  curl -LsSf https://astral.sh/uv/install.sh | sh
  ```
- **macOS** (via Homebrew):
  ```bash
  brew install uv
  ```
- **Windows** (PowerShell):
  ```powershell
  powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
  ```
- **Via Pip**:
  ```bash
  pip install uv
  ```

For more installation options and detailed instructions, visit the official [Astral uv Installation Guide](https://docs.astral.sh/uv/getting-started/installation/).

---

### Step-by-Step Setup

```bash
# 1. Run one-command setup (creates virtualenv, syncs dependencies via uv, and installs git pre-commit hooks)
make setup

# 2. Configure local environment
cp .env.example .env
# Edit .env to set your GOOGLE_CLOUD_PROJECT and local ADC credentials path,
# or authenticate using Google Cloud CLI:
gcloud auth application-default login

# 3. Run the autonomous agent and smart frame web server locally
make run
```

The smart frame display will be live at `http://localhost:8168` (or your configured `PORT`).

---

## 🛠️ Developer Makefile Commands

A developer `Makefile` is provided for standard workflows:

| Make Target | Description |
| :--- | :--- |
| `make help` | Show all available make targets and descriptions |
| `make setup` | **One-step setup**: installs dependencies via `uv sync` and activates git `pre-commit` hooks |
| `make install` | Install production, dev, lint, and eval dependencies using `uv sync` |
| `make pre-commit` | Run `pre-commit` hooks manually across all files in the repository |
| `make test` | Run the full unit and integration test suite with `pytest` |
| `make lint` | Run code quality checks (`ruff check`, `ruff format --check`, `codespell`) |
| `make lint-fix` / `make format` | Automatically fix formatting and lint errors |
| `make run` | Start the autonomous scheduler loop and SSE web server locally (`run_loop.py`) |
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

## 🌐 Web Server & SSE API Endpoints

The unified runner (`run_loop.py`) serves the static web assets from `smart_frame_web/` alongside real-time SSE coordination endpoints:

| Endpoint | Method | Description |
| :--- | :--- | :--- |
| `/` or `/index.html` | `GET` | Edge-to-edge, full-screen digital frame canvas for kiosk browsers |
| `/events` | `GET` | Server-Sent Events (SSE) stream for photo rotation and new bulletin notifications |
| `/api/state` | `GET` | Returns current playlist items, active photo index, and rotation interval |
| `/api/rotate` | `POST` | Advances display to next photo or jumps to a specific index (`{"index": <n>}`) |
| `/api/generate` | `POST` | Immediately triggers an asynchronous agent generation workflow cycle |

---

## 📁 Project Structure

```text
chronos-frame-agent/
├── app/
│   ├── agent.py               # ADK 2.0 Graph Workflow Agent definition
│   ├── app_utils/             # ADK/A2A runtime services, typing, and telemetry
│   ├── event_hub.py           # Real-time SSE event hub and photo rotation coordinator
│   ├── fast_api_app.py        # FastAPI A2A backend server & feedback endpoint
│   ├── memory.py              # Jaccard keyword deduplication & sliding window memory
│   ├── prompt_loader.py       # Time-of-day style engine and external prompt loader
│   └── tools.py               # NewsTool, ImagenTool, and PublisherTool (3-image FIFO)
├── prompts/                   # External Markdown prompt templates
│   ├── news_anchor.md         # News anchor prompt with category balance & safety
│   ├── photo_frame_image.md   # Visual bulletin layout and styling prompt
│   └── styles/                # Time-of-day Nano Banana 3D figure style templates
│       ├── morning_retro_pop.md      # Sunrise Vinyl Pop (00:00 - 10:00)
│       ├── midday_claymation.md      # Electric Matte Figurine (10:00 - 16:00)
│       └── evening_luminescent.md   # Luminescent Cyber-Toy (16:00 - 24:00)
├── run_loop.py                # Unified scheduler loop & aiohttp SSE web server
├── smart_frame_web/           # Web client assets (index.html, playlist.json, image_*.png)
├── tests/
│   ├── unit/                  # Unit tests (memory, tools, event hub)
│   ├── integration/           # Integration tests (agent workflow, web server E2E)
│   └── eval/                  # ADK eval scenarios and datasets
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
| `GOOGLE_CLOUD_LOCATION` | `global` | GCP region for Vertex AI endpoints. |
| `GOOGLE_GENAI_USE_VERTEXAI` | `true` | Enables Vertex AI mode in `google-genai`. |
| `GEMINI_API_KEY` | — | Optional API key for Google GenAI (alternative to ADC). |
| `TZ` | `Australia/Sydney` | Local timezone for time-of-day styling and bulletin timestamps. |

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
      - GOOGLE_CLOUD_LOCATION=global
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
