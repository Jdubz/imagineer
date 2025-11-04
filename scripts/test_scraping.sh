#!/bin/bash
#
# Test web scraping functionality
#

set -e

echo "===================================="
echo "Web Scraping Test Script"
echo "===================================="
echo ""

# Get API URL
API_URL="${1:-http://localhost:10050}"

echo "Testing API at: $API_URL"
echo ""

# 1. Check API health
echo "1. Checking API health..."
if curl -s -f "$API_URL/health" > /dev/null; then
    echo "   ✓ API is running"
else
    echo "   ✗ API is not responding"
    exit 1
fi
echo ""

# 2. Check scraping stats endpoint
echo "2. Checking scraping stats..."
STATS=$(curl -s "$API_URL/api/scraping/stats")
if echo "$STATS" | jq -e '.total_jobs' > /dev/null 2>&1; then
    echo "   ✓ Scraping stats endpoint working"
    echo "$STATS" | jq '{total_jobs, total_images_scraped, recent_jobs}'
else
    echo "   ✗ Scraping stats endpoint failed"
    echo "   Response: $STATS"
    exit 1
fi
echo ""

# 3. Check scraping queue endpoint
echo "3. Checking scraping queue..."
QUEUE=$(curl -s "$API_URL/api/scraping/queue")
if echo "$QUEUE" | jq -e '.queue_size' > /dev/null 2>&1; then
    echo "   ✓ Scraping queue endpoint working"
    echo "$QUEUE" | jq '.'
else
    echo "   ✗ Scraping queue endpoint failed"
    echo "   Response: $QUEUE"
fi
echo ""

# 4. Check training-data setup
echo "4. Checking training-data repository..."
TRAINING_DATA_PATH="/home/jdubz/Development/training-data"
if [ -d "$TRAINING_DATA_PATH" ]; then
    echo "   ✓ Training-data repo exists"
else
    echo "   ✗ Training-data repo not found at $TRAINING_DATA_PATH"
    exit 1
fi

TRAINING_PYTHON="$TRAINING_DATA_PATH/venv/bin/python"
if [ -x "$TRAINING_PYTHON" ]; then
    echo "   ✓ Training-data Python found"
else
    echo "   ✗ Training-data Python not found or not executable"
    exit 1
fi

if "$TRAINING_PYTHON" -m training_data --help > /dev/null 2>&1; then
    echo "   ✓ Training-data module installed"
else
    echo "   ✗ Training-data module not installed"
    echo "   Run: cd $TRAINING_DATA_PATH && source venv/bin/activate && pip install -e ."
    exit 1
fi
echo ""

# 5. Check Anthropic API key
echo "5. Checking Anthropic API key..."
ENV_FILE="$TRAINING_DATA_PATH/.env"
if [ -f "$ENV_FILE" ]; then
    if grep -q "ANTHROPIC_API_KEY" "$ENV_FILE"; then
        echo "   ✓ API key configured in $ENV_FILE"
    else
        echo "   ⚠ No API key found in $ENV_FILE"
        echo "   Add: ANTHROPIC_API_KEY=sk-ant-..."
    fi
else
    echo "   ⚠ No .env file at $ENV_FILE"
    echo "   Copy .env.example and add ANTHROPIC_API_KEY"
fi
echo ""

# 6. Test scraper CLI directly
echo "6. Testing scraper CLI..."
TEST_OUTPUT="/tmp/scraping-test-$$"
mkdir -p "$TEST_OUTPUT"

echo "   Running dry-run test..."
if "$TRAINING_PYTHON" -m training_data \
    --dry-run \
    --max-images 3 \
    https://example.com \
    "test" \
    "$TEST_OUTPUT" 2>&1 | grep -q "Dry run complete"; then
    echo "   ✓ Scraper CLI working"
else
    echo "   ⚠ Scraper CLI may have issues (check manually)"
fi

rm -rf "$TEST_OUTPUT"
echo ""

# 7. Offer to start a real test job
echo "===================================="
echo "Pre-flight checks complete!"
echo "===================================="
echo ""
echo "To test with a real scraping job (requires admin auth):"
echo ""
echo "curl -X POST $API_URL/api/scraping/start \\"
echo "  -H 'Content-Type: application/json' \\"
echo "  -d '{"
echo "    \"url\": \"https://picsum.photos\","
echo "    \"depth\": 1,"
echo "    \"max_images\": 5"
echo "  }'"
echo ""
echo "Then check status:"
echo "curl $API_URL/api/scraping/jobs | jq '.jobs[0]'"
echo ""
echo "Or use the web UI at: https://imagineer-generator.web.app"
echo ""
