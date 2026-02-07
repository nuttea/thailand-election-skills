---
name: extract-thailand-election-policies
description: Extract Thai political party policy data from PDF documents for Thailand 2026 election analysis. Uses Gemini 3 Pro Preview with structured output to extract policy details including sequence, category, name, budget, funding, benefits, impacts, and risks. Outputs validated JSON with Pydantic schemas. Use when extracting Thai political party policies from PDF documents.
---

# Extract Thailand Election Policies

Specialized skill for extracting Thai political party policy data from PDF documents using Google Gemini 3 Pro Preview with structured output.

## Agent Instructions - CRITICAL Setup Steps

**BEFORE running ANY Python script in this skill, the agent MUST execute these commands IN ORDER:**

```bash
# Step 1: Navigate to skill directory
cd .claude/skills/extract-thailand-election-policies

# Step 2: Create virtual environment (skip if .venv/ exists)
python3 -m venv .venv

# Step 3: ACTIVATE virtual environment (CRITICAL - don't skip!)
source .venv/bin/activate

# Step 4: Install requirements (CRITICAL - must be in activated venv!)
pip install -r requirements.txt

# Step 5: Verify installation succeeded
python -c "import google.genai, pydantic, requests; print('✓ Core packages ready')"

# Step 6: Optional - Install ddtrace for Datadog LLMObs tracing
pip install ddtrace
```

**IMPORTANT NOTES:**
- The `source .venv/bin/activate` command MUST be run before pip install
- Each new terminal session needs `source .venv/bin/activate` again
- Check for `(.venv)` prefix in terminal prompt to confirm activation
- If installation fails, try without version constraints: `pip install google-genai pydantic requests`

**After setup, run Python scripts normally:**
```bash
python scripts/extract_policy.py --pdf-path party.pdf --output-file party.json
```

**When done, deactivate:**
```bash
deactivate
```

## Quick Start (After Venv Setup)

```bash
# Extract single party
python scripts/extract_policy.py \
  --pdf-path "เบอร์ 9 พรรคเพื่อไทย.pdf" \
  --output-file "party_9_policies.json"
```

## Features

- ✅ **Thai Language OCR** - Handles Thai text and numerals
- ✅ **Structured Output** - Pydantic validation with JSON Schema
- ✅ **9-Field Extraction** - Complete policy data model
- ✅ **Budget Normalization** - Converts Thai units to Baht
- ✅ **Category Assignment** - 15 predefined categories
- ✅ **Stream Monitoring** - Timeout detection and auto-retry
- ✅ **Error Logging** - Detailed debugging information

## Policy Data Model

### Fields Extracted

1. **policy_seq** (int) - Policy sequence number (Thai numerals → Arabic)
2. **policy_category** (str) - One of 15 predefined categories
3. **policy_name** (str) - Policy title/name
4. **budget_baht** (int) - Budget in Baht (pure integer, 0 if none)
5. **funding_source** (str) - Funding source details
6. **cost_effectiveness** (str) - Cost-effectiveness analysis
7. **benefits** (str) - Benefits description
8. **impacts** (str) - Impact analysis
9. **risks** (str) - Risk assessment

### Policy Categories (15)

1. เศรษฐกิจและการค้า (Economy & Trade)
2. เกษตรกรรมและประมง (Agriculture & Fisheries)
3. สาธารณสุข (Public Health)
4. การศึกษา (Education)
5. โครงสร้างพื้นฐาน (Infrastructure)
6. สิ่งแวดล้อมและพลังงาน (Environment & Energy)
7. สวัสดิการสังคม (Social Welfare)
8. ธรรมาภิบาลและการต่อต้านคอร์รัปชัน (Governance & Anti-Corruption)
9. กลาโหมและความมั่นคง (Defense & Security)
10. การท่องเที่ยวและวัฒนธรรม (Tourism & Culture)
11. ที่ดินและที่อยู่อาศัย (Land & Housing)
12. แรงงานและการจ้างงาน (Labor & Employment)
13. ยุติธรรม (Justice)
14. การต่างประเทศ (Foreign Affairs)
15. อื่นๆ (Others)

## Usage

### Extract Single Party

```bash
python scripts/extract_policy.py \
  --pdf-path "เบอร์ 27 พรรคประชาธิปัตย์.pdf" \
  --output-file "party_27_policies.json"
```

### Batch Extract All Parties

```bash
bash scripts/batch_extract_all.sh
```

**Features:**
- Processes all PDFs in directory
- Skips already-extracted files
- Auto-retry on failures (up to 3 times)
- Moves processed PDFs to `processed/` directory
- Creates consolidated CSV at end
- 3-second delays between extractions

### Convert to CSV

```bash
python scripts/json_to_csv.py \
  --json-file "party_9_policies.json" \
  --output-file "party_9_policies.csv"
```

### Send to Datadog

```bash
python scripts/send_to_datadog.py \
  --csv-file "consolidated_all_parties.csv"
```

## Script Arguments

### extract_policy.py

| Argument | Required | Description |
|----------|----------|-------------|
| `--pdf-path` | Yes | Path to PDF file |
| `--output-file` | Yes | Output JSON file path |
| `--max-retries` | No | Max retry attempts (default: 2) |

### batch_extract_all.sh

| Argument | Description |
|----------|-------------|
| (none) | Extract all PDFs, skip existing |
| `--force` | Re-extract all files |

### json_to_csv.py

| Argument | Required | Description |
|----------|----------|-------------|
| `--json-file` | Yes | Input JSON file |
| `--output-file` | Yes | Output CSV file |
| `--delimiter` | No | CSV delimiter (default: `\|`) |
| `--preserve-newlines` | No | Convert newlines to `\n` |

### send_to_datadog.py

| Argument | Required | Description |
|----------|----------|-------------|
| `--csv-file` | Yes | CSV file to send |
| `--batch-size` | No | Batch size (default: 50) |
| `--dry-run` | No | Test without sending |

## Extraction Rules

### Thai Numeral Conversion

**Convert to Arabic ONLY in policy_seq:**
- ๐ → 0, ๑ → 1, ๒ → 2, ๓ → 3, ๔ → 4
- ๕ → 5, ๖ → 6, ๗ → 7, ๘ → 8, ๙ → 9

**Preserve in all other fields:**
- ๑) ๒) ๓) in lists
- Thai numerals in text content

### Budget Normalization

**Convert to pure integer in Baht:**
- ล้าน = × 1,000,000
- พันล้าน = × 1,000,000,000
- แสนล้าน = × 100,000,000,000
- ล้านล้าน = × 1,000,000,000,000
- ไม่ใช้เงินงบประมาณ = 0

**Examples:**
- 40,000 ล้าน → 40,000,000,000
- 3.5 แสนล้าน → 350,000,000,000
- ไม่ระบุ → 0

### Text Extraction

- Extract word-by-word for accuracy
- Preserve Thai formatting
- Include all policies (no TOTAL rows)
- Maintain numbered lists (๑) ๒) ๓))

## Output Format

### JSON Structure

```json
{
  "policies": [
    {
      "policy_seq": 1,
      "policy_category": "โครงสร้างพื้นฐาน",
      "policy_name": "ระบบรางความเร็วสูง",
      "budget_baht": 350000000000,
      "funding_source": "๑) งบประมาณแผ่นดิน\n๒) PPP\n๓) พันธบัตร",
      "cost_effectiveness": "ลดต้นทุนโลจิสติกส์...",
      "benefits": "๑) เพิ่มการเชื่อมต่อ\n๒) กระตุ้นเศรษฐกิจ",
      "impacts": "ผลกระทบระยะยาว...",
      "risks": "ความเสี่ยงทางการเงิน..."
    }
  ]
}
```

### CSV Format

Pipe-delimited with columns:
```
party_number|party_name|policy_seq|policy_category|policy_name|budget_baht|funding_source|cost_effectiveness|benefits|impacts|risks
```

## Performance

- **Average extraction time:** 3-5 minutes per PDF
- **Large PDFs (50MB):** 5-8 minutes
- **Small PDFs (<5MB):** 2-3 minutes
- **Batch processing:** ~4 hours for 51 parties

## Error Handling

### Automatic Retry

- Detects incomplete responses (1-chunk with invalid JSON)
- Retries up to 3 times
- 3-second delay between retries
- Logs all errors to `.error.log` files

### Stream Monitoring

- Tracks time between chunks
- Timeout if no chunks for >3 minutes
- Auto-retry on timeout
- Shows chunk count and content preview

### Error Logs

Location: `output_dir/party_N_NAME.error.log`

Contains:
- Python exceptions
- API errors
- Validation failures
- Timeout information

## Workflow

### 1. Extract PDFs to JSON

```bash
cd /path/to/pdfs
bash /path/to/skills/extract-thailand-election-policies/scripts/batch_extract_all.sh
```

**Output:**
- 51 JSON files in `all_parties_output/`
- PDFs moved to `processed/` directory
- Error logs for any failures

### 2. Convert to CSV

```bash
# Individual CSVs created automatically during extraction

# Create consolidated CSV
python scripts/consolidate_csv.py \
  --input-dir "all_parties_output" \
  --output-file "consolidated_all_parties.csv"
```

### 3. Send to Datadog

```bash
python scripts/send_to_datadog.py \
  --csv-file "consolidated_all_parties.csv"
```

**Result:** All policies searchable in Datadog with tags:
- `source:custom-log`
- `service:th-election-policy`
- `version:YYYYMMDD-HHMM`
- `env:prod`

## Example: Complete Workflow

```bash
# 1. Set up
cd /Users/nuttee.jirattivongvibul/Projects/nuttee-se-gemini-cli/temp_working/OTHERS/THAILAND_ELECTION_2026

# 2. Extract all parties
bash scripts/batch_extract_all.sh

# 3. Check status
./CHECK_STATUS.sh

# 4. Generate consolidated CSV
# (automatically done by batch script)

# 5. Send to Datadog
python send_to_datadog.py \
  --csv-file "all_parties_output/consolidated_all_parties.csv"

# 6. Analyze in Datadog
# Go to: https://app.datadoghq.com/logs
# Query: source:custom-log service:th-election-policy
```

## Real-World Results

### Thailand 2026 Election Extraction

**Completed:** 2026-01-29  
**Results:**
- ✅ 51 parties extracted (100%)
- ✅ 587 policies total
- ✅ All data in Datadog
- ✅ Analysis notebook created

**Processing Time:** ~6-7 hours total

**Success Factors:**
- Stream timeout detection
- Incomplete response retry
- Proper error logging
- 3-second delays

## Troubleshooting

### Issue: Incomplete JSON (1 chunk)

**Symptom:** Only 1 chunk received, invalid JSON

**Solution:** Script automatically detects and retries (up to 3 times)

**Manual fix:**
```bash
python scripts/extract_policy.py \
  --pdf-path "problem.pdf" \
  --output-file "output.json" \
  --max-retries 5
```

### Issue: Stream Stalls

**Symptom:** No chunks for >3 minutes

**Solution:** Script automatically detects timeout and retries

**Check logs:**
```bash
cat all_parties_output/party_N_NAME.error.log
```

### Issue: API Rate Limits

**Symptom:** Multiple failures in a row

**Solution:**
- Increase delay in batch script (change `DELAY_BETWEEN_PDFS`)
- Wait 1 hour and retry
- Use different API key

## Advanced Usage

### Custom Extraction

For different policy document formats, modify:

1. **Pydantic Models** (lines 28-43 in `extract_policy.py`)
2. **Instructions** (in batch script or command line)
3. **Categories** (update predefined list)

### Batch Processing Options

**Skip existing files:**
```bash
./batch_extract_all.sh
```

**Force re-extract all:**
```bash
./batch_extract_all.sh --force
```

**Custom delays:**
Edit `DELAY_BETWEEN_PDFS` in script (default: 3 seconds)

## Integration

### With Google Sheets

1. Use comma-separated CSV
2. Import with UTF-8 encoding
3. Find & Replace: `\n` → `Ctrl+Enter`
4. Format budget column with thousands separator

### With Datadog

1. Send logs with `send_to_datadog.py`
2. Query: `source:custom-log service:th-election-policy`
3. Create dashboards and monitors
4. Export for further analysis

### With Other Tools

**Python/Pandas:**
```python
import pandas as pd
df = pd.read_csv('consolidated.csv', delimiter='|')
```

**Excel:**
- Open CSV with delimiter: `|`
- Convert text to columns if needed

## Files in This Skill

```
extract-thailand-election-policies/
├── SKILL.md                    # This file
├── README.md                   # Quick reference
├── WORKFLOW.md                 # Step-by-step guide
├── scripts/
│   ├── extract_policy.py       # Single PDF extraction
│   ├── batch_extract_all.sh    # Batch processing
│   ├── json_to_csv.py          # JSON to CSV conversion
│   ├── send_to_datadog.py      # Datadog integration
│   └── CHECK_STATUS.sh         # Progress monitoring
└── examples/
    ├── sample_output.json      # Example JSON
    ├── sample_output.csv       # Example CSV
    └── datadog_queries.md      # Query examples
```

## Success Metrics

### Thailand 2026 Project

- **Extraction:** 51/51 parties (100%)
- **Policies:** 587 total
- **Data Quality:** 100% valid JSON
- **Datadog:** 587 logs ingested
- **Analysis:** Notebook with 35 cells created

## See Also

- **Analysis Guide:** `DATADOG_ANALYSIS_GUIDE.md`
- **Project Summary:** `PROJECT_COMPLETE_SUMMARY.md`
- **Datadog Notebook:** https://app.datadoghq.com/notebook/13821543

## Agent Workflow

When user requests Thai election policy extraction:

1. ✅ Use `scripts/extract_policy.py` for single PDF
2. ✅ Use `scripts/batch_extract_all.sh` for multiple PDFs
3. ✅ Convert to CSV with `scripts/json_to_csv.py`
4. ✅ Send to Datadog with `scripts/send_to_datadog.py`
5. ✅ Analyze using Datadog notebook

**This skill is production-ready and battle-tested with 51 real political party PDFs.**
