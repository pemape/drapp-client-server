FROM python:3.11-slim-bookworm

# Install system dependencies needed by psycopg2 and Pillow
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    curl \
    make \
    gcc \
    libjpeg-dev \
    zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copy the rest of the flask-app sources
COPY . .

# Ensure the uploads directory exists at runtime
RUN mkdir -p server/uploads

EXPOSE 8080

CMD ["python", "run.py"]
