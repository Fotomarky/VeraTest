FROM python:3.11-slim

WORKDIR /app

# System deps for Pillow
RUN apt-get update && apt-get install -y --no-install-recommends \
    libjpeg-dev zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./
COPY simab ./simab

# Install with the [phoenix] extra so the calibration layer (FidelityAuditor,
# Phoenix client, OpenInference instrumentor) actually has its dependencies
# available at runtime. Without this the Arize-track code silently no-ops.
RUN pip install --no-cache-dir -e ".[phoenix]"

EXPOSE 8000
CMD ["uvicorn", "simab.main:app", "--host", "0.0.0.0", "--port", "8000"]
