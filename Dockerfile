FROM python:3.14-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
    OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
RUN apt-get update && apt-get install -y --no-install-recommends \
    libreoffice-writer fonts-dejavu-core fonts-liberation \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt \
    && useradd --create-home --uid 10001 appuser \
    && mkdir -p /app/data/jobs && chown -R appuser:appuser /app/data
COPY ocr_app ./ocr_app
COPY run_server.py ./
USER appuser
EXPOSE 8000
CMD ["python", "run_server.py"]

FROM runtime AS test
USER root
COPY requirements-dev.txt ./
RUN pip install --no-cache-dir -r requirements-dev.txt
COPY tests ./tests
USER appuser
RUN python -m pytest -q -p no:cacheprovider && touch /tmp/ocr-verified

FROM runtime AS production
COPY --from=test /tmp/ocr-verified /app/verified
