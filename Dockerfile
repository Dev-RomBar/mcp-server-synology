# Dockerfile for Synology MCP Server
FROM python:3.13-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install the project and its dependencies from pyproject.toml (single source
# of truth). mcp>=2.0.0 ships starlette, uvicorn, and sse-starlette, so one
# install covers both stdio and Streamable HTTP transports.
COPY pyproject.toml ./
COPY src/ ./src/
RUN pip install --no-cache-dir .

# Copy entry point
COPY main.py .

# NOTE: .env is deliberately NOT copied. It is the file the README tells you to
# put SYNOLOGY_PASSWORD in, and baking it into a layer hands that password to
# anyone who can pull the image -- `docker history` is enough, and deleting the
# file in a later layer does not remove it.
#
# Configuration is supplied at RUN time instead, by one of:
#   - docker-compose.yml: `env_file: .env` (optional), or its `environment:`
#   - docker-compose.http.yml: `environment:`, with credentials listed there
#   - a plain `docker run -e SYNOLOGY_PASSWORD=...`
#   - the read-only ~/.config/synology-mcp mount, holding settings.json
# .dockerignore also excludes .env, so an accidental `COPY . .` cannot
# reintroduce it.

# Create logs directory
RUN mkdir -p logs

# Create non-root user for security
RUN useradd -m -u 1000 mcpuser && chown -R mcpuser:mcpuser /app
USER mcpuser

# Set environment variables for MCP
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# Fork: serve stateless Streamable HTTP on port 8000 (/mcp, /healthz). NAS units come from
# the environment (SYNOLOGY_NAS_NAMES), and are logged in to on first use.
ENV MCP_HTTP=true \
    MCP_HTTP_HOST=0.0.0.0 \
    MCP_HTTP_PORT=8000 \
    MCP_STATELESS=true \
    AUTO_LOGIN=false
EXPOSE 8000

CMD ["python", "main.py"] 