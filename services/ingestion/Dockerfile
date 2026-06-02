FROM python:3.11-slim

WORKDIR /app

# Install git
RUN apt-get update && apt-get install -y --no-install-recommends git && rm -rf /var/lib/apt/lists/*

# Copy shared libs first for layer caching
COPY libs/ /app/libs/
COPY services/ingestion/requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy service code
COPY services/ingestion/ /app/service/

ENV PYTHONPATH=/app
ENV SERVICE_NAME=ingestion-service

EXPOSE 8080

CMD ["python", "-m", "service.main"]
