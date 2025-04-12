FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Устанавливаем pg_isready
RUN apt-get update && apt-get install -y postgresql-client && apt-get clean

COPY app/ .

CMD ["/bin/sh", "-c", "uvicorn main:app --host 0.0.0.0 --port 8000"]