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

# Expose port
EXPOSE 3003

# Run the application
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "3003"]
