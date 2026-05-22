FROM python:3.11-slim

WORKDIR /app

# System deps for Pillow
RUN apt-get update && apt-get install -y --no-install-recommends \
    libjpeg-dev zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./
COPY simab ./simab

RUN pip install --no-cache-dir -e .

EXPOSE 8000
CMD ["uvicorn", "simab.main:app", "--host", "0.0.0.0", "--port", "8000"]
