FROM python:3.12-slim

RUN useradd -m -u 1000 appuser

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/
COPY seed_data.py .

# Static upload dirs (inside image, non-persistent)
RUN mkdir -p /app/app/static/uploads/avatars \
             /app/app/static/uploads/leagues \
             /app/app/static/uploads/markets \
    && chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

# /data is the Fly volume mount — DB lives there, uploads symlinked at startup
CMD ["sh", "-c", "\
  mkdir -p /data/uploads/avatars /data/uploads/leagues /data/uploads/markets /data/uploads/videos && \
  ln -sfn /data/uploads /app/app/static/uploads && \
  python seed_data.py && \
  uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1"]
