FROM python:3.12-slim

RUN useradd -m -u 1000 appuser

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/
COPY seed_data.py .

# Persistent dirs: DB + uploaded images
RUN mkdir -p /app/data \
             /app/app/static/uploads/avatars \
             /app/app/static/uploads/leagues \
             /app/app/static/uploads/markets \
    && chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

CMD ["sh", "-c", "python seed_data.py && uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1"]
