FROM python:3.10-slim

WORKDIR /app

# Install system dependencies if any (e.g., for building some python libs)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements-kraft.txt .
# We use requirements-kraft because it has the compatible versions for slim environments
RUN pip install --no-cache-dir -r requirements-kraft.txt

# Copy application code
COPY . .

# Environment variables
ENV PORT=5000
ENV HOST=0.0.0.0
ENV FALKORDB_HOST=falkordb

EXPOSE 5000

CMD ["python", "main.py"]
