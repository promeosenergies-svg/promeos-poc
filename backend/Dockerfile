FROM python:3.11-slim

WORKDIR /app

# System deps for psycopg2-binary and cryptography
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev git \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Data directory (SQLite default path)
RUN mkdir -p /app/data

EXPOSE 8001

CMD ["python", "main.py"]
