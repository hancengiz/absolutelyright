# Python FastAPI Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src ./src
COPY frontend ./frontend

# Create directory for database
RUN mkdir -p /app/data

# Expose port (Railway will use $PORT environment variable)
EXPOSE ${PORT:-3003}

# Run the application
# Use PORT env var if available (Railway), otherwise default to 3003
CMD ["sh", "-c", "uvicorn src.main:app --host 0.0.0.0 --port ${PORT:-3003}"]
