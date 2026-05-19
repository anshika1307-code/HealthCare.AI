FROM python:3.11-slim

WORKDIR /app

# System deps: libgl1 for PyMuPDF, curl for health probes
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    curl \
 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download the cross-encoder model so cold start doesn't need internet
RUN python -c "from sentence_transformers import CrossEncoder; CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')"

# Copy source — ui/ and data/raw/ are excluded via .dockerignore
COPY configs/ ./configs/
COPY src/ ./src/
COPY data/cache/ ./data/cache/

ENV PYTHONPATH=/app/src:/app

EXPOSE 8000

CMD uvicorn serving.api:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1
