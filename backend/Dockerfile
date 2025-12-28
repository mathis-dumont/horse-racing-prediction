# Use Python 3.11 to ensure Pandas installs quickly (pre-compiled wheels)
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies (optional, but good for some ML libraries)
# We keep it minimal for now
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install Python dependencies
# (This will now run fast because it downloads wheels instead of compiling)
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install httpx pytest  # Ensure test tools are installed

# Copy the rest of the application code
COPY . .

# Set the Python path so it finds 'src' easily
ENV PYTHONPATH=/app

# Default command (can be overridden)
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]