FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python requirements
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy source code and data files
COPY . .

# Run initial pipeline execution or verification
RUN python -c "import config, os; os.makedirs(config.OUTPUT_DIR, exist_ok=True)"

# Expose port
EXPOSE 8000

# Start FastAPI server via Uvicorn
CMD ["sh", "-c", "uvicorn src.api:app --host 0.0.0.0 --port ${PORT:-8000}"]
