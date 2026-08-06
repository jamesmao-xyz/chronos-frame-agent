# Design Specification: Chronos Frame Agent

## Executive Summary
**Chronos Frame Agent** is an autonomous ADK 2.0 agentic AI application designed to generate stylized 9:16 (1080x1920) news bulletin dashboard images and serve them over an asynchronous real-time web server for smart digital frame displays (specifically tailored for the **Lenovo Smart Frame** running **Fully Kiosk Browser**, smart portrait displays, and Portainer on Asustor NAS).

The agent operates on an autonomous **15-minute recurring generation schedule**, rotates active display photos every **5 minutes**, maintains a strict **3-image FIFO queue** (`image_1.png`, `image_2.png`, `image_3.png`), and pushes real-time Server-Sent Events (SSE) to deliver edge-to-edge, full-resolution artwork with hardware-accelerated crossfade transitions.

---

## 1. Requirements & User Intent

### Core Goals
1. **Autonomous News Ingestion & Deduplication**: Ingest top 5 global news headlines periodically, apply content safety filters, and utilize agent memory (`HeadlineMemory`) with sliding-window Jaccard keyword deduplication to prevent repetitive stories across photos.
2. **Portrait Graphic Generation**: Convert summary context into a stylized, high-contrast, visually appealing 9:16 (1080x1920 portrait) bulletin dashboard image using Google GenAI / Gemini image models with dynamic time-of-day styling (Morning Retro-Pop, Midday Claymation, Evening Luminescent).
3. **Race-Condition-Free FIFO Queue Publisher**: Manage `smart_frame_web/` queue lifecycle (`image_1.png` → `image_2.png` → `image_3.png`) while persisting an atomic `playlist.json` manifest with cache-busting version tags (`?v=...`) to eliminate image tearing, stale cache collisions, or repeated content.
4. **Full-Screen Ambient Smart Frame Display**: Deliver a pure edge-to-edge canvas taking 100% of the display viewport without intrusive overlays (no persistent clocks, borders, or thumbnail sidebars), using dual-layer GPU crossfades and pre-rendering.
5. **Real-Time Synchronized Coordination**: Synchronize generation and slideshow rotation via Server-Sent Events (SSE), eliminating uncoordinated client reload timers.
6. **Containerization & Local Deployment**: Support single-command local execution (`uv run python run_loop.py`) and Docker container packaging for deployment on home NAS hardware (Portainer on Asustor NAS).

### Target Environment & Tech Stack
- **Framework**: Google Agent Development Kit (ADK) 2.0 Graph Workflow Agent (`Workflow`, `START`, `InMemoryRunner`)
- **Runtime**: Python 3.11 managed via `uv` package manager
- **Web Server**: Asynchronous `aiohttp` web server with SSE event streaming
- **Frontend Engine**: Pure HTML5/CSS3/ES6 with dual-layer GPU compositing (`transform: translateZ(0)`) and `EventSource`
- **Target Hardware**: Lenovo Smart Frame (1080x1920 9:16 portrait) running Fully Kiosk Browser (Android WebView)
- **API Dependencies**: Google GenAI SDK (`google-genai`), ADK (`google-adk`), Pillow / PIL for image composition & layout rendering.

---

## 2. Architecture & Workflow

### ADK 2.0 Graph Workflow Pipeline

```
+-----------------------------------------------------------------------------------+
|                            Chronos Frame Agent Workflow                           |
+-----------------------------------------------------------------------------------+
                                          |
                                          v
                              +-----------------------+
                              |   1. NewsTool         |
                              | - Fetch global news   |
                              | - Safety check        |
                              | - Memory dedup (5x)   |
                              +-----------------------+
                                          |
                                          v
                              +-----------------------+
                              |   2. ImagenTool       |
                              | - Time-of-day styles  |
                              | - 9:16 portrait ratio |
                              | - 1080x1920 render    |
                              +-----------------------+
                                          |
                                          v
                              +-----------------------+
                              |   3. PublisherTool    |
                              | - FIFO shift (1->2->3)|
                              | - Atomic playlist.json|
                              | - Prune images > 3    |
                              | - Notify EventHub     |
                              +-----------------------+
                                          |
                                          v
                              +-----------------------+
                              |   4. EventHub (SSE)   |
                              | - Broadcast new_photo |
                              | - Push to Smart Frame |
                              +-----------------------+
```

---

## 3. Tool & Component Specifications

### Tool 1: `NewsTool` ([app/tools.py]
- **Purpose**: Fetch top global news headlines, apply safety filtering, format into structured bullet points, and eliminate story repetition.
- **Memory Integration**: Connects to `HeadlineMemory` ([app/memory.py] maintaining a bounded sliding window of the last 25 headlines. Prevents story reuse via Jaccard keyword overlap matching.
- **Fallback Pool**: Contains a curated pool of diverse science, tech, and global achievements to ensure robust offline operation without repeats.
- **Outputs**: Dictionary containing `headlines: list[str]`, `summary: str`, `timestamp: str`.

### Tool 2: `ImagenTool` ([app/tools.py]
- **Purpose**: Render a high-contrast 1080x1920 (9:16 portrait) bulletin dashboard graphic.
- **Dynamic Time-of-Day Styling**:
  - **Morning (05:00 - 11:59)**: *Vivid Retro-Pop* (warm apricot, teal, golden yellow accents).
  - **Midday (12:00 - 17:59)**: *Electric Claymation* (bold cobalt, sunset coral, citrus amber).
  - **Evening/Night (18:00 - 04:59)**: *Luminescent Lo-Fi Digital* (midnight navy, neon cyan, amethyst).
- **Outputs**: Dictionary containing `image_bytes: bytes`, dimensions (`1080x1920`), and style metadata.

### Tool 3: `PublisherTool` ([app/tools.py]
- **Purpose**: Maintain `smart_frame_web/` directory and manage 3-image FIFO lifecycle.
- **FIFO Logic**:
  1. Prunes 4th oldest image if present (`image_4.png`).
  2. Deletes `image_3.png` (if exists).
  3. Renames `image_2.png` → `image_3.png`.
  4. Renames `image_1.png` → `image_2.png`.
  5. Saves newly rendered image as `image_1.png`.
  6. Writes atomic `playlist.json` manifest with cache-busting timestamp version tags (`?v=...`).
  7. Invokes `event_hub.set_playlist(...)` to broadcast real-time `new_photo` SSE events.

### Component 4: `SmartFrameEventHub` ([app/event_hub.py]
- **Purpose**: Singleton broadcaster managing SSE subscriber queues and slideshow state.
- **Event Wire Types**:
  - `event: init`: Delivers the current playlist and active photo index upon initial client connection.
  - `event: new_photo`: Broadcasts newly generated bulletins and resets rotation index to 0.
  - `event: rotate`: Coordinates synchronized photo rotation across the FIFO queue ($0 \rightarrow 1 \rightarrow 2 \rightarrow 0$).
  - `: keepalive`: Heartbeat comments sent every 15 seconds to prevent TCP drops over Wi-Fi / kiosk proxies.

---

## 4. Web Server & Frontend Architecture

### Server Runner ([run_loop.py]
- High-performance asynchronous `aiohttp` web server running inside the asyncio event loop.
- **Concurrent Async Loops**:
  1. `scheduler_loop`: Triggers the ADK agent workflow every `SCHEDULE_INTERVAL_SECONDS` (default: 900s / 15 min).
  2. `photo_rotation_loop`: Advances the active photo every `ROTATION_INTERVAL_SECONDS` (default: 300s / 5 min) and emits `event: rotate`.
- **API Endpoints**:
  - `GET /`: Serves the full-screen smart frame client (`index.html`).
  - `GET /events`: Server-Sent Events (SSE) real-time stream.
  - `GET /api/state`: Returns the active playlist JSON snapshot.
  - `POST /api/rotate`: Manual rotation / jump to target photo index.
  - `POST /api/generate`: On-demand background bulletin generation trigger.

### Full-Screen Smart Display Frontend ([smart_frame_web/index.html]
- **Edge-to-Edge Canvas**: 100% screen estate utilization (`width: 100vw; height: 100vh; position: fixed; inset: 0; cursor: none; background: #000000;`). No persistent clock headers or thumbnail bars on the display.
- **Dual-Layer GPU Crossfade**:
  - Stacks `#layerA` and `#layerB` using `position: absolute; inset: 0; object-fit: cover;`.
  - CSS hardware acceleration: `transition: opacity 1.5s cubic-bezier(0.4, 0, 0.2, 1); will-change: opacity; transform: translateZ(0);`.
- **Preload-Before-Swap**: JavaScript downloads each incoming photo off-screen in memory (`new Image().src = ...`) and only flips active layers once `onload` confirms the image is in RAM, preventing any black flickers or tearing on Android WebView.
- **Touch / Tap Interaction**: Tap or click anywhere on the display to manually advance to the next photo in the queue.
- **Kiosk Resilience & Offline Fallback**:
  - `EventSource` automatically reconnects on Wi-Fi drops.
  - If the server is unreachable for $>45\text{s}$, the client automatically activates a local fallback rotation loop cycling through cached images.

---

## 5. Docker Packaging & Deployment

- **Base Image**: `python:3.11-slim` with `uv` package manager.
- **Port**: Exposes port `8080`.
- **Container Execution**:
  ```dockerfile
  CMD ["python", "run_loop.py"]
  ```
- **Environment Variables**:
  - `PORT`: Web server port (default: `8080`).
  - `SCHEDULE_INTERVAL_SECONDS`: News bulletin generation interval (default: `900` / 15 min).
  - `ROTATION_INTERVAL_SECONDS`: Slideshow photo rotation interval (default: `300` / 5 min).
  - `GOOGLE_APPLICATION_CREDENTIALS`: Path to Application Default Credentials JSON.
  - `GOOGLE_CLOUD_PROJECT`: Vertex AI GCP Project ID.

---

## 6. Testing & Quality Assurance

- **Unit Tests**:
  - `tests/unit/test_memory.py`: Sliding window bounds, deduplication matching, and persistence.
  - `tests/unit/test_tools.py`: Prompt loaders, dynamic style generation, ImagenTool dimensions (1080x1920), and 3-image FIFO pruning.
  - `tests/unit/test_event_hub.py`: SSE subscription queues, rotation cycles ($0 \rightarrow 1 \rightarrow 2 \rightarrow 0$), and message serialization.
- **Integration Tests**:
  - `tests/integration/test_agent.py`: End-to-end graph workflow agent execution.
  - `tests/integration/test_server_e2e.py`: SSE web server initialization, `/api/state`, `/api/rotate`, and static file delivery.
