#!/bin/bash
set -e

echo "=== Repo Intelligence Integration Test ==="
API="http://localhost:8000"

# 1. Health check
echo "[1/6] Health check..."
curl -sf $API/health > /dev/null && echo "  Gateway OK" || exit 1

# 2. Ingest repo
echo "[2/6] Ingesting test repository..."
RESPONSE=$(curl -s -X POST $API/repos   -H "Content-Type: application/json"   -d '{"git_url": "file:///app/test-repo", "branch": "main"}')
echo "  Response: $RESPONSE"
REPO_ID=$(echo $RESPONSE | python3 -c "import sys,json; print(json.load(sys.stdin).get('repo_id',''))")

if [ -z "$REPO_ID" ]; then
  echo "ERROR: Failed to get repo_id"
  exit 1
fi

echo "  Repo ID: $REPO_ID"
echo "  Waiting 45s for pipeline to process..."
sleep 45

# 3. Check capabilities
echo "[3/6] Checking capabilities..."
CAPS=$(curl -s "$API/capabilities?repo=$REPO_ID")
echo "  Capabilities: $(echo $CAPS | python3 -c 'import sys,json; print(len(json.load(sys.stdin)))') found"

# 4. Query
echo "[4/6] Querying system..."
QUERY_RESP=$(curl -s -X POST $API/query   -H "Content-Type: application/json"   -d '{"query": "How do I add a new protected route?", "repo": "'$REPO_ID'"}')
echo "  Query response: $QUERY_RESP"
CONFIDENCE=$(echo $QUERY_RESP | python3 -c "import sys,json; print(json.load(sys.stdin).get('confidence',0))")

if (( $(echo "$CONFIDENCE > 0.5" | bc -l) )); then
  echo "  Confidence OK: $CONFIDENCE"
else
  echo "  WARNING: Low confidence: $CONFIDENCE"
fi

# 5. Get playbooks
echo "[5/6] Checking playbooks..."
PLAYBOOKS=$(curl -s "$API/playbooks")
PB_COUNT=$(echo $PLAYBOOKS | python3 -c 'import sys,json; print(len(json.load(sys.stdin)))')
echo "  Playbooks: $PB_COUNT found"

if [ "$PB_COUNT" -eq 0 ]; then
  echo "ERROR: No playbooks generated"
  exit 1
fi

# 6. Parse check
echo "[6/6] Checking parser output..."
PARSE=$(curl -s "$API/parse/$REPO_ID")
FILE_COUNT=$(echo $PARSE | python3 -c 'import sys,json; print(len(json.load(sys.stdin).get("files",[])))')
echo "  Parsed files: $FILE_COUNT"

echo ""
echo "=== Integration Test Complete ==="
