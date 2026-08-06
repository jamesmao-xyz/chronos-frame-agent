# Dockerfile for Chronos Frame Agent (Portainer / Asustor NAS / Local deployment)
FROM python:3.11-slim

# Install uv package manager
RUN pip install --no-cache-dir uv

WORKDIR /app

# Step 1: Copy dependency specifications for layer caching
COPY pyproject.toml README.md uv.lock* ./

# Step 2: Install ONLY production dependencies (excludes 'dev', 'eval', and 'lint' groups)
RUN uv sync --no-dev --no-install-project --default-index https://pypi.org/simple --python 3.11

# Step 3: Copy application source code, prompt templates, and web assets
COPY app ./app
COPY prompts ./prompts
COPY run_loop.py ./run_loop.py
COPY smart_frame_web ./smart_frame_web
COPY agents-cli-manifest.yaml ./agents-cli-manifest.yaml

# Step 4: Finalize sync for the project environment (strictly without dev dependencies)
RUN uv sync --no-dev --default-index https://pypi.org/simple --python 3.11

# Place virtual environment directly in PATH for faster execution
ENV PATH="/app/.venv/bin:$PATH"

# Expose HTTP port for smart frame web server
EXPOSE 8168

# Production environment variables
ENV PORT=8168
ENV SCHEDULE_INTERVAL_SECONDS=900
ENV ROTATION_INTERVAL_SECONDS=300

# Entrypoint directly executes run_loop.py in the production virtualenv
CMD ["python", "run_loop.py"]
