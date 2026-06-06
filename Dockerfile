FROM python:3.12-slim

RUN useradd -m -u 1000 appuser

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/
COPY seed_data.py .

# Do NOT pre-create uploads/ — it must be replaced by a symlink at runtime.
# Pre-creating it causes ln -sfn to nest the symlink inside the dir instead of replacing it.
RUN chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

# /data is the Fly volume mount — DB lives there, uploads symlinked at startup
CMD ["sh", "-c", "\
  mkdir -p /data/uploads/avatars /data/uploads/leagues /data/uploads/markets /data/uploads/videos && \
  rm -rf /app/app/static/uploads && \
  ln -s /data/uploads /app/app/static/uploads && \
  python seed_data.py && \
  uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1"]
