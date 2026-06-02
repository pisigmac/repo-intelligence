#!/bin/bash
set -e

echo "=== Repo Intelligence Phase 2 Integration Test ==="
API="http://localhost:8000"

# 1. Health check all services
echo "[1/8] Health checks..."
curl -sf $API/health > /dev/null && echo "  Gateway OK"

# 2. Ingest repo and wait for pipeline
echo "[2/8] Ingesting test repository..."
RESPONSE=$(curl -s -X POST $API/repos   -H "Content-Type: application/json"   -d '{"git_url": "file:///app/test-repo", "branch": "main"}')
REPO_ID=$(echo $RESPONSE | python3 -c "import sys,json; print(json.load(sys.stdin).get('repo_id',''))")
echo "  Repo ID: $REPO_ID"
echo "  Waiting 60s for pipeline..."
sleep 60

# 3. Query for a playbook
echo "[3/8] Querying for playbook..."
QUERY=$(curl -s -X POST $API/query   -H "Content-Type: application/json"   -d '{"query": "How do I add a new protected route?", "repo": "'$REPO_ID'"}')
PB_ID=$(echo $QUERY | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['playbooks'][0]['id'] if d.get('playbooks') else '')")
echo "  Playbook ID: $PB_ID"

if [ -z "$PB_ID" ]; then
  echo "ERROR: No playbook found"
  exit 1
fi

# 4. Execute playbook
echo "[4/8] Executing playbook..."
EXEC=$(curl -s -X POST $API/execute   -H "Content-Type: application/json"   -d '{"playbook_id": "'$PB_ID'", "context": {"new_route": "/api/test", "method": "get"}}')
EXEC_ID=$(echo $EXEC | python3 -c "import sys,json; print(json.load(sys.stdin).get('execution_id',''))")
echo "  Execution ID: $EXEC_ID"
echo "  Waiting 15s for execution..."
sleep 15

# 5. Check feedback metrics
echo "[5/8] Checking feedback metrics..."
METRICS=$(curl -s $API/feedback/$PB_ID/metrics)
echo "  Metrics: $METRICS"
EPISODES=$(echo $METRICS | python3 -c "import sys,json; print(json.load(sys.stdin).get('episodes',0))")

# 6. Multi-agent execution
echo "[6/8] Multi-agent execution..."
AGENT_RESULT=$(curl -s -X POST $API/agents/execute   -H "Content-Type: application/json"   -d '{"query": "Add a protected route for items", "repo": "'$REPO_ID'", "auto_approve": false}')
echo "  Agent result: $AGENT_RESULT"
AGENTS=$(echo $AGENT_RESULT | python3 -c "import sys,json; print(','.join(json.load(sys.stdin).get('agents_used',[])))")
echo "  Agents used: $AGENTS"

# 7. Check approvals (may be empty if no optimization triggered yet)
echo "[7/8] Checking approvals..."
APPROVALS=$(curl -s "$API/approvals?status=pending")
APPROVAL_COUNT=$(echo $APPROVALS | python3 -c 'import sys,json; print(len(json.load(sys.stdin)))')
echo "  Pending approvals: $APPROVAL_COUNT"

# 8. Knowledge search
echo "[8/8] Searching knowledge..."
KNOWLEDGE=$(curl -s -X POST $API/knowledge/search   -H "Content-Type: application/json"   -d '{"query": "authentication", "language": "javascript"}')
KNOWLEDGE_COUNT=$(echo $KNOWLEDGE | python3 -c 'import sys,json; print(len(json.load(sys.stdin)))')
echo "  Knowledge entries: $KNOWLEDGE_COUNT"

echo ""
echo "=== Phase 2 Integration Test Complete ==="
echo "Playbook: $PB_ID | Episodes: $EPISODES | Agents: $AGENTS | Approvals: $APPROVAL_COUNT"
