FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 APP_HOST=0.0.0.0 APP_PORT=8000
WORKDIR /service
COPY requirements.lock ./
RUN pip install --no-cache-dir -r requirements.lock
COPY app/ ./app/
COPY scripts/ ./scripts/
COPY migrations/ ./migrations/
COPY knowledge-base/ ./knowledge-base/
COPY certs/ ./certs/
COPY alembic.ini ./
RUN useradd --create-home --uid 10001 appuser
USER appuser
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 CMD python -c "import os, urllib.request; urllib.request.urlopen('http://127.0.0.1:' + os.environ.get('APP_PORT', '8000') + '/health', timeout=3)"
CMD ["python", "-m", "scripts.run_server"]
