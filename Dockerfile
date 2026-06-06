FROM python:3.12-slim

# Non-root user for security
RUN useradd -m -u 1000 appuser

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ ./app/
COPY seed_data.py .

# Create data directory with correct ownership
RUN mkdir -p /app/data && chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

# Run seed + start server
CMD ["sh", "-c", "python seed_data.py && uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1"]
