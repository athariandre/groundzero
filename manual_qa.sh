#!/bin/bash
# Manual QA script for PR5 Oracle Routing, Aggregation, and Fallback
# Run this script to manually test the /check_claim endpoints

set -e

echo "========================================="
echo "GroundZero PR5 Manual QA Test"
echo "========================================="
echo ""

# Start server in background
echo "Starting server..."
uvicorn server.main:app --host 127.0.0.1 --port 8000 --log-level info > /tmp/server.log 2>&1 &
SERVER_PID=$!
sleep 3

# Wait for server to be ready
echo "Waiting for server to be ready..."
for i in {1..10}; do
    if curl -s http://127.0.0.1:8000/health > /dev/null 2>&1; then
        echo "Server is ready!"
        break
    fi
    sleep 1
done

echo ""
echo "========================================="
echo "Test 1: Parse Endpoint"
echo "========================================="
echo ""
echo "Testing: /check_claim/parse"
echo "Claim: 'SOL jumped 8% after ETF approval this morning.'"
echo ""

curl -s -X POST http://127.0.0.1:8000/check_claim/parse \
  -H "Content-Type: application/json" \
  -d '{"claim_text":"SOL jumped 8% after ETF approval this morning."}' | jq

echo ""
echo "========================================="
echo "Test 2: Check Endpoint (Finance Domain)"
echo "========================================="
echo ""
echo "Testing: /check_claim/check"
echo "Claim: 'SOL jumped 8% after ETF approval this morning.'"
echo ""

RESPONSE=$(curl -s -X POST http://127.0.0.1:8000/check_claim/check \
  -H "Content-Type: application/json" \
  -d '{"claim_text":"SOL jumped 8% after ETF approval this morning."}')

echo "$RESPONSE" | jq

echo ""
echo "Validation Checks:"
echo "------------------"

# Extract values
ORACLE_COUNT=$(echo "$RESPONSE" | jq '.oracle_calls | length')
FIRST_ORACLE=$(echo "$RESPONSE" | jq -r '.oracle_calls[0].oracle_name')
DOMAIN=$(echo "$RESPONSE" | jq -r '.domain.domain')
CONFIDENCE=$(echo "$RESPONSE" | jq -r '.domain.confidence')

echo "✓ Domain: $DOMAIN (expected: finance)"
echo "✓ First oracle: $FIRST_ORACLE (expected: finance)"
echo "✓ Domain confidence: $CONFIDENCE"

# Check if fallback was used
if [ "$ORACLE_COUNT" -eq 2 ]; then
    SECOND_ORACLE=$(echo "$RESPONSE" | jq -r '.oracle_calls[1].oracle_name')
    echo "✓ Fallback oracle: $SECOND_ORACLE (expected: llm_oracle)"
    
    # Fallback should be triggered if confidence < 0.6 or primary verdict is uncertain
    if (( $(echo "$CONFIDENCE < 0.6" | bc -l) )); then
        echo "✓ Fallback triggered due to low domain confidence (< 0.6)"
    else
        FIRST_VERDICT=$(echo "$RESPONSE" | jq -r '.oracle_calls[0].verdict')
        if [ "$FIRST_VERDICT" = "uncertain" ]; then
            echo "✓ Fallback triggered due to uncertain primary verdict"
        fi
    fi
else
    echo "✓ No fallback used (oracle count: $ORACLE_COUNT)"
fi

echo ""
echo "========================================="
echo "Test 3: Empty Claim (Error Handling)"
echo "========================================="
echo ""
echo "Testing: Empty claim text (should return 400)"
echo ""

curl -s -X POST http://127.0.0.1:8000/check_claim/parse \
  -H "Content-Type: application/json" \
  -d '{"claim_text":""}' | jq

echo ""
echo "========================================="
echo "Test 4: Tech Release Claim"
echo "========================================="
echo ""
echo "Testing: Tech release domain"
echo "Claim: 'Apple announced new iPhone yesterday'"
echo ""

curl -s -X POST http://127.0.0.1:8000/check_claim/check \
  -H "Content-Type: application/json" \
  -d '{"claim_text":"Apple announced new iPhone yesterday"}' | jq

echo ""
echo "========================================="
echo "Test 5: General Domain Claim"
echo "========================================="
echo ""
echo "Testing: General domain (no financial or tech keywords)"
echo "Claim: 'The weather was nice yesterday'"
echo ""

curl -s -X POST http://127.0.0.1:8000/check_claim/check \
  -H "Content-Type: application/json" \
  -d '{"claim_text":"The weather was nice yesterday"}' | jq

echo ""
echo "========================================="
echo "Cleanup"
echo "========================================="
echo ""
echo "Stopping server (PID: $SERVER_PID)..."
kill $SERVER_PID 2>/dev/null || true
wait $SERVER_PID 2>/dev/null || true

echo "Manual QA complete!"
echo ""
