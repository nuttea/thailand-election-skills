#!/bin/bash
#
# Check extraction status
#

OUTPUT_DIR="all_parties_output"

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║           EXTRACTION STATUS DASHBOARD                         ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

# Count files
json_count=$(ls -1 "${OUTPUT_DIR}"/party_*.json 2>/dev/null | wc -l | tr -d ' ')
csv_count=$(ls -1 "${OUTPUT_DIR}"/party_*.csv 2>/dev/null | wc -l | tr -d ' ')

echo "Files Generated:"
echo "  JSON files: ${json_count}/51"
echo "  CSV files:  ${csv_count}/51"
echo ""

# Count policies
if [ $json_count -gt 0 ]; then
    total_policies=$(python3 << 'EOF'
import json
import glob

total = 0
for f in sorted(glob.glob("all_parties_output/party_*.json")):
    try:
        data = json.load(open(f))
        count = len(data.get('policies', []))
        total += count
    except:
        pass
print(total)
EOF
)
    echo "Policies Extracted: ${total_policies}"
    echo ""
fi

# Show recent completions
echo "Recent Completions:"
ls -lt "${OUTPUT_DIR}"/party_*.json 2>/dev/null | head -5 | awk '{print "  " $9}' | sed 's|all_parties_output/||' | sed 's|.json||'
echo ""

# Check for failures
if [ -f "extraction_log.txt" ]; then
    fail_count=$(grep -c "✗.*FAILED" extraction_log.txt 2>/dev/null || echo "0")
    if [ "$fail_count" -gt 0 ]; then
        echo "⚠️  Failures detected: ${fail_count}"
        echo ""
        echo "Failed parties:"
        grep "✗.*FAILED" extraction_log.txt | tail -5
    else
        echo "✅ No failures so far"
    fi
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Progress: ${json_count}/51 parties ($(( json_count * 100 / 51 ))%)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
