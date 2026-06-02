FROM python:3.11-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends git && rm -rf /var/lib/apt/lists/*
COPY libs/ /app/libs/
COPY services/approval/requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt
COPY services/approval/ /app/service/
ENV PYTHONPATH=/app
ENV SERVICE_NAME=approval-service
EXPOSE 8080
CMD ["python", "-m", "service.main"]
