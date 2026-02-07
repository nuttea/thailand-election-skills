#!/usr/bin/env bash
#
# Production Batch Extraction: All 51 Political Parties
# PDF → JSON → CSV with retry logic and rate limit handling
#
# Usage:
#   ./batch_extract_all.sh          # Skip existing files
#   ./batch_extract_all.sh --force  # Re-extract all files
#
# Requirements:
#   - Python virtual environment (.venv) with required packages
#   - Run setup_venv.sh first if .venv doesn't exist
#

# Don't use set -e since we handle errors explicitly with return codes

# Activate virtual environment if available
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="${SCRIPT_DIR}/../.venv"

if [ -d "${VENV_DIR}" ]; then
    source "${VENV_DIR}/bin/activate"
    echo "✓ Activated virtual environment: ${VENV_DIR}"
else
    echo "⚠ Virtual environment not found at: ${VENV_DIR}"
    echo "  Run: bash scripts/setup_venv.sh"
    echo "  Continuing with system Python..."
fi

# Parse arguments
FORCE_EXTRACT=false
if [ "$1" = "--force" ] || [ "$1" = "-f" ]; then
    FORCE_EXTRACT=true
    echo "⚠️  FORCE MODE: Will re-extract all files"
fi

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../../../.." && pwd)"
PDF_DIR="${PROJECT_ROOT}/assets/นโยบายพรรคการเมือง"
OUTPUT_DIR="${SCRIPT_DIR}/all_parties_output"
PROCESSED_DIR="${PDF_DIR}/processed"
EXTRACT_SCRIPT="${SCRIPT_DIR}/extract_policy.py"
CONVERT_SCRIPT="${SCRIPT_DIR}/json_to_csv.py"
MAX_RETRIES=3
DELAY_BETWEEN_PDFS=3   # 3 seconds between extractions
DELAY_AFTER_FAILURE=3  # 3 seconds after failure
DELAY_AFTER_SKIP=3     # 3 seconds after skipping already extracted file

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Extraction instructions
read -r -d '' INSTRUCTIONS << 'EOF' || true
Extract ALL policies from this Thai political party document.

For EACH policy extract:
1. policy_seq (int): Policy sequence number - Convert Thai numerals (๐-๙) to Arabic (0-9)
2. policy_category (string): Choose ONE category from the predefined list
3. policy_name (string): Extract word by word, preserve Thai numerals ๑) ๒) ๓) in content
4. budget_baht (int): Budget in Baht as pure integer (0 if no budget specified)
5. funding_source (string): Extract word by word, preserve Thai numerals ๑) ๒) ๓)
6. cost_effectiveness (string): Extract word by word, preserve Thai numerals ๑) ๒) ๓)
7. benefits (string): Extract word by word, preserve Thai numerals ๑) ๒) ๓)
8. impacts (string): Extract word by word, preserve Thai numerals ๑) ๒) ๓)
9. risks (string): Extract word by word, preserve Thai numerals ๑) ๒) ๓)

IMPORTANT RULES:
- Convert Thai numerals to Arabic ONLY in policy_seq field
- Preserve Thai numerals (๑) ๒) ๓) etc) in all other text fields
- Budget must be pure integer in Baht:
  * ล้าน = multiply by 1,000,000
  * แสนล้าน = multiply by 100,000,000,000
  * พันล้าน = multiply by 1,000,000,000
  * ล้านล้าน = multiply by 1,000,000,000,000
  * ไม่ใช้เงินงบประมาณ = 0
- Extract text word-by-word for accuracy
- Include ALL policies (no TOTAL rows)

Policy categories to choose from:
เศรษฐกิจและการค้า, เกษตรกรรมและประมง, สาธารณสุข, การศึกษา, โครงสร้างพื้นฐาน, สิ่งแวดล้อมและพลังงาน, สวัสดิการสังคม, ธรรมาภิบาลและการต่อต้านคอร์รัปชัน, กลาโหมและความมั่นคง, การท่องเที่ยวและวัฒนธรรม, ที่ดินและที่อยู่อาศัย, แรงงานและการจ้างงาน, ยุติธรรม, การต่างประเทศ, อื่นๆ
EOF

# Functions
print_header() {
    echo ""
    echo "╔════════════════════════════════════════════════════════════════╗"
    printf "║  %-60s  ║\n" "$1"
    echo "╚════════════════════════════════════════════════════════════════╝"
    echo ""
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ $1${NC}"
}

extract_party_info() {
    local filename="$1"
    local num=$(echo "$filename" | grep -o 'เบอร์ [0-9]*' | grep -o '[0-9]*')
    local name=$(echo "$filename" | sed 's/เบอร์ [0-9]* //' | sed 's/.pdf$//')
    
    if [ -z "$num" ]; then
        # Handle files without number
        num="XX"
        name=$(echo "$filename" | sed 's/.pdf$//')
    fi
    
    echo "${num}|${name}"
}

validate_json() {
    local file="$1"
    [ ! -s "$file" ] && echo "Empty file" && return 1
    if ! python3 -c "import json; json.load(open('$file'))" 2>/dev/null; then
        echo "Invalid JSON"
        return 1
    fi
    local count=$(python3 -c "import json; data=json.load(open('$file')); print(len(data.get('policies', [])))" 2>/dev/null || echo "0")
    if [ "$count" -eq 0 ]; then
        echo "No policies found"
        return 1
    fi
    echo "$count"
    return 0
}

process_pdf() {
    local pdf="$1"
    local fn=$(basename "$pdf")
    local info=$(extract_party_info "$fn")
    local num=$(echo "$info" | cut -d'|' -f1)
    local name=$(echo "$info" | cut -d'|' -f2)
    local json_out="${OUTPUT_DIR}/party_${num}_${name}.json"
    local csv_out="${OUTPUT_DIR}/party_${num}_${name}.csv"
    local error_log="${OUTPUT_DIR}/party_${num}_${name}.error.log"
    
    echo ""
    echo "════════════════════════════════════════════════════════════════"
    echo "Processing: ${fn}"
    echo "Party #${num}: ${name}"
    echo "════════════════════════════════════════════════════════════════"
    
    # Check if already processed (skip if valid JSON with policies exists)
    if [ "$FORCE_EXTRACT" = "false" ]; then
        if [ -f "$json_out" ] && [ -s "$json_out" ] && [ -f "$csv_out" ]; then
            # Validate JSON and get count
            if python3 -c "import json; data=json.load(open('${json_out}')); exit(0 if len(data.get('policies', [])) > 0 else 1)" 2>/dev/null; then
                local existing_count=$(python3 -c "import json; data=json.load(open('${json_out}')); print(len(data.get('policies', [])))" 2>/dev/null)
                print_success "Already extracted: $existing_count policies (skipping)"
                # Return with special code to indicate skip
                return 2
            fi
        fi
    fi
    
    local attempt=1
    local success=false
    
    while [ $attempt -le $MAX_RETRIES ] && [ "$success" = "false" ]; do
        if [ $attempt -gt 1 ]; then
            print_warning "Retry $attempt/$MAX_RETRIES..."
            sleep $DELAY_AFTER_FAILURE
        fi
        
        # Load API key (only uncommented line)
        export GEMINI_API_KEY=$(grep "^export GEMINI_API_KEY=" "${PROJECT_ROOT}/.env" | head -1 | cut -d'=' -f2 | tr -d '"' | tr -d "'" | tr -d '\n' | tr -d '\r')
        
        # Clear previous error log
        rm -f "${error_log}"
        
        # Run extraction with detailed error logging
        if python3 "${EXTRACT_SCRIPT}" \
            --pdf-path "${pdf}" \
            --output-format json \
            --instructions "${INSTRUCTIONS}" \
            --output-file "${json_out}" \
            2> "${error_log}"; then
            
            # Validate JSON
            result=$(validate_json "${json_out}")
            if [ $? -eq 0 ]; then
                print_success "Extracted: ${result} policies"
                success=true
                # Remove error log on success
                rm -f "${error_log}"
                
                # Convert to CSV
                if python3 "${CONVERT_SCRIPT}" \
                    --json-file "${json_out}" \
                    --output-file "${csv_out}" \
                    --delimiter "|" \
                    --preserve-newlines \
                    --root-key "policies" \
                    2>> "${error_log}"; then
                    print_success "CSV created: ${csv_out}"
                    rm -f "${error_log}"
                    
                    # Move PDF to processed directory
                    if mv "${pdf}" "${PROCESSED_DIR}/" 2>/dev/null; then
                        print_success "Moved to processed/"
                    fi
                else
                    print_warning "CSV conversion failed (see ${error_log})"
                fi
            else
                print_error "Validation failed: $result"
                echo "Validation Error: $result" >> "${error_log}"
                if [ -s "${error_log}" ]; then
                    echo "Error details saved to: ${error_log}"
                    echo "--- Error Log Preview ---"
                    head -20 "${error_log}"
                    echo "-------------------------"
                fi
                attempt=$((attempt + 1))
            fi
        else
            print_error "Extraction failed"
            if [ -s "${error_log}" ]; then
                echo "Error details saved to: ${error_log}"
                echo "--- Error Log Preview ---"
                head -20 "${error_log}"
                echo "-------------------------"
            fi
            attempt=$((attempt + 1))
        fi
    done
    
    if [ "$success" = "false" ]; then
        print_error "FAILED after $MAX_RETRIES attempts"
        return 1
    fi
    
    return 0
}

# Main execution
main() {
    print_header "PRODUCTION EXTRACTION: ALL 51 PARTIES"
    
    echo "Configuration:"
    echo "  PDF Directory:    ${PDF_DIR}"
    echo "  Output Directory: ${OUTPUT_DIR}"
    echo "  Max Retries:      ${MAX_RETRIES}"
    echo "  Delay Between:    ${DELAY_BETWEEN_PDFS}s"
    echo ""
    
    # Check prerequisites
    if [ ! -f "${EXTRACT_SCRIPT}" ]; then
        print_error "Extract script not found: ${EXTRACT_SCRIPT}"
        exit 1
    fi
    
    if [ ! -f "${CONVERT_SCRIPT}" ]; then
        print_error "Convert script not found: ${CONVERT_SCRIPT}"
        exit 1
    fi
    
    if [ -z "$(grep "^export GEMINI_API_KEY=" "${PROJECT_ROOT}/.env" 2>/dev/null)" ]; then
        print_error "GEMINI_API_KEY not found in .env"
        exit 1
    fi
    
    print_success "Prerequisites checked"
    
    # Create output and processed directories
    mkdir -p "${OUTPUT_DIR}"
    mkdir -p "${PROCESSED_DIR}"
    print_success "Directories created (output + processed)"
    
    # Count PDFs
    local total_pdfs=$(ls -1 "${PDF_DIR}"/*.pdf 2>/dev/null | wc -l | tr -d ' ')
    echo ""
    print_info "Found ${total_pdfs} PDF files to process"
    echo ""
    
    # Process all PDFs
    local start_time=$(date +%s)
    local success_count=0
    local fail_count=0
    local current=0
    
    for pdf in "${PDF_DIR}"/*.pdf; do
        current=$((current + 1))
        echo ""
        print_info "Progress: ${current}/${total_pdfs}"
        
        process_pdf "$pdf"
        local result=$?
        
        if [ $result -eq 0 ]; then
            ((success_count++))
            # Normal delay after successful extraction
            if [ $current -lt $total_pdfs ]; then
                print_info "Waiting ${DELAY_BETWEEN_PDFS}s before next PDF..."
                sleep $DELAY_BETWEEN_PDFS
            fi
        elif [ $result -eq 2 ]; then
            # File was skipped (already extracted)
            ((success_count++))
            # Short delay after skip
            if [ $current -lt $total_pdfs ]; then
                sleep $DELAY_AFTER_SKIP
            fi
        else
            # Extraction failed
            ((fail_count++))
            # Normal delay after failure
            if [ $current -lt $total_pdfs ]; then
                print_info "Waiting ${DELAY_BETWEEN_PDFS}s before next PDF..."
                sleep $DELAY_BETWEEN_PDFS
            fi
        fi
    done
    
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))
    local hours=$((duration / 3600))
    local minutes=$(((duration % 3600) / 60))
    local seconds=$((duration % 60))
    
    # Create consolidated CSV
    print_header "CREATING CONSOLIDATED CSV"
    
    local timestamp=$(date +%Y%m%d_%H%M%S)
    local consol_csv="${OUTPUT_DIR}/${timestamp}_consolidated_all_parties.csv"
    local consol_json="${OUTPUT_DIR}/${timestamp}_consolidated_all_parties.json"
    
    if python3 "${CONVERT_SCRIPT}" \
        --batch-dir "${OUTPUT_DIR}" \
        --output-file "${consol_csv}" \
        --delimiter "|" \
        --preserve-newlines \
        --add-metadata \
        --root-key "policies" \
        > /dev/null 2>&1; then
        
        local total_records=$(python3 -c "import csv; f=open('${consol_csv}','r',encoding='utf-8'); print(sum(1 for _ in csv.DictReader(f, delimiter='|')))")
        print_success "Consolidated CSV created: ${consol_csv}"
        print_success "Total records: ${total_records}"
    else
        print_error "Consolidation failed"
    fi
    
    # Create consolidated JSON
    print_info "Creating consolidated JSON..."
    python3 << PYTHON_EOF
import json
import glob
from datetime import datetime

all_policies = []
party_summary = []

for json_file in sorted(glob.glob("${OUTPUT_DIR}/party_*.json")):
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        policies = data.get('policies', [])
        if policies:
            filename = json_file.split('/')[-1]
            parts = filename.replace('party_', '').replace('.json', '').split('_', 1)
            party_num = parts[0]
            party_name = parts[1] if len(parts) > 1 else filename
            
            # Add party info to each policy
            for policy in policies:
                policy['party_number'] = party_num
                policy['party_name'] = party_name
            
            all_policies.extend(policies)
            party_summary.append({
                'party_number': party_num,
                'party_name': party_name,
                'policy_count': len(policies)
            })
    except Exception as e:
        print(f"Error processing {json_file}: {e}")

# Create consolidated JSON
output = {
    'metadata': {
        'extraction_date': datetime.now().isoformat(),
        'total_parties': len(party_summary),
        'total_policies': len(all_policies)
    },
    'party_summary': party_summary,
    'all_policies': all_policies
}

with open('${consol_json}', 'w', encoding='utf-8') as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

print(f"✓ Consolidated JSON created: ${consol_json}")
print(f"  Parties: {len(party_summary)}")
print(f"  Policies: {len(all_policies)}")
PYTHON_EOF
    
    # Final Summary
    print_header "EXTRACTION COMPLETE"
    
    echo "Results:"
    echo "  Success:       ${success_count}/${total_pdfs}"
    echo "  Failed:        ${fail_count}/${total_pdfs}"
    echo "  Duration:      ${hours}h ${minutes}m ${seconds}s"
    echo ""
    echo "Output Directory: ${OUTPUT_DIR}"
    echo "  - ${success_count} JSON files"
    echo "  - ${success_count} CSV files"
    echo "  - 1 consolidated CSV"
    echo "  - 1 consolidated JSON"
    echo ""
    
    if [ $fail_count -eq 0 ]; then
        print_success "All parties extracted successfully!"
    else
        print_warning "${fail_count} parties failed"
        echo ""
        echo "Error logs available:"
        ls -1 "${OUTPUT_DIR}"/*.error.log 2>/dev/null | while read log; do
            echo "  - $(basename "$log")"
        done
        echo ""
        echo "Failed parties can be re-extracted with:"
        echo "  ./extract_all_parties.sh"
        echo "  (Script will skip already processed files)"
        echo ""
        echo "To view error details:"
        echo "  cat ${OUTPUT_DIR}/party_N_NAME.error.log"
    fi
    
    echo ""
    print_info "Consolidated CSV: ${consol_csv}"
    print_info "Ready for Google Sheets import!"
}

# Run main
main "$@"
