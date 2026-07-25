FROM python:3.11-slim

WORKDIR /app

# System deps: curl for health probes
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
 && rm -rf /var/lib/apt/lists/*

# CPU-only torch FIRST. The default PyPI wheel bundles ~2.5 GB of nvidia-* CUDA
# libraries that are useless without a GPU. Installing from the CPU index here
# means the sentence-transformers install below sees torch as already satisfied
# and never resolves the CUDA variant.
RUN pip install --no-cache-dir --index-url https://download.pytorch.org/whl/cpu torch

# Runtime deps only — no PyMuPDF/pdfplumber/pytest. See requirements-serve.txt.
COPY requirements-serve.txt .
RUN pip install --no-cache-dir -r requirements-serve.txt

# Pre-download the cross-encoder model so cold start doesn't need internet
RUN python -c "from sentence_transformers import CrossEncoder; CrossEncoder('cross-encoder/ms-marco-MiniLM-L-2-v2')"

# Copy source — ui/ and data/raw/ are excluded via .dockerignore
COPY configs/ ./configs/
COPY src/ ./src/
COPY data/cache/ ./data/cache/

ENV PYTHONPATH=/app/src:/app \
    PYTHONDONTWRITEBYTECODE=1 \
    # Single-threaded torch/tokenizers: on a shared-CPU instance extra threads
    # cost memory and add contention without improving rerank latency.
    OMP_NUM_THREADS=1 \
    MKL_NUM_THREADS=1 \
    TOKENIZERS_PARALLELISM=false

EXPOSE 8080

CMD uvicorn serving.api:app --host 0.0.0.0 --port ${PORT:-8080} --workers 1
