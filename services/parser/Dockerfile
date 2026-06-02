FROM python:3.11-slim

WORKDIR /app

# Install git (for file ops) and build tools
RUN apt-get update && apt-get install -y --no-install-recommends git gcc && rm -rf /var/lib/apt/lists/*

COPY libs/ /app/libs/
COPY services/parser/requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

COPY services/parser/ /app/service/

ENV PYTHONPATH=/app
ENV SERVICE_NAME=parser-service

EXPOSE 8080

CMD ["python", "-m", "service.main"]
