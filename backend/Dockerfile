# backend/Dockerfile

# Use Python 3.10 slim image
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install system dependencies (needed for psycopg2/postgres)
RUN apt-get update && apt-get install -y libpq-dev gcc

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the complete folder
COPY . .

# Set Python path so it finds 'src'
ENV PYTHONPATH=/app

# Expose port
EXPOSE 8000

# Command to run the API
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]