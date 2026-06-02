#!/bin/bash
set -e

echo "Seeding test repository..."

# Wait for services
echo "Waiting for ingestion service..."
until curl -s http://localhost:8000/health > /dev/null; do
  sleep 2
done

# Ingest test repo
echo "Ingesting test-repo..."
curl -X POST http://localhost:8000/repos   -H "Content-Type: application/json"   -d '{"git_url": "file:///app/test-repo", "branch": "main"}'

echo ""
echo "Ingestion queued. Monitor with: docker-compose logs -f ingestion-service parser-service analysis-service capability-service playbook-service"
echo "After ~30 seconds, query with:"
echo "  curl -X POST http://localhost:8000/query -H 'Content-Type: application/json' -d '{"query": "How do I add a new protected route?"}'"
