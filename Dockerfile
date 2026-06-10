FROM python:3.11-slim

WORKDIR /app

# System deps:
#  - libjpeg/zlib for Pillow
#  - Node.js 20 because the Agent Builder layer's Arize Phoenix MCP toolset
#    spawns `npx @arizeai/phoenix-mcp` over stdio at runtime (see simab/agent.py).
#    Without Node, the agent loads but the partner MCP tools are unavailable.
RUN apt-get update && apt-get install -y --no-install-recommends \
        libjpeg-dev zlib1g-dev curl ca-certificates gnupg \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    # Pre-fetch the Phoenix MCP server so the first agent request doesn't
    # pay an npm-download cold start on Cloud Run.
    && npm install -g @arizeai/phoenix-mcp@latest \
    && apt-get purge -y curl gnupg && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./
COPY simab ./simab

# [phoenix] = OTLP tracing + calibration deps; [agent] = google-adk so the same
# image can also serve the ADK agent (see CMD note below).
RUN pip install --no-cache-dir -e ".[phoenix,agent]"

EXPOSE 8000

# Default: the FastAPI backend (REST + SSE + share page + A2A).
CMD ["uvicorn", "simab.main:app", "--host", "0.0.0.0", "--port", "8000"]

# To run the Agent Builder service from this same image instead, deploy it as a
# second Cloud Run service and override the command with:
#   adk api_server simab --host 0.0.0.0 --port 8000
# (requires GOOGLE_GENAI_USE_VERTEXAI=TRUE, GOOGLE_CLOUD_PROJECT/LOCATION, and
#  PHOENIX_BASE_URL/PHOENIX_API_KEY in the service env.)
