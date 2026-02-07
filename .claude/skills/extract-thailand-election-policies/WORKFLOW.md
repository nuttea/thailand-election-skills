# Thailand Election Policy Extraction - Complete Workflow

## Overview

Step-by-step guide for extracting Thai political party policies from PDF documents.

## Prerequisites

### 1. Environment Setup

```bash
# Install required packages
pip install google-genai pydantic requests

# Set up API keys in .env
export GEMINI_API_KEY="your-gemini-api-key"
export DD_API_KEY="your-datadog-api-key"  # Optional, for Datadog integration
```

### 2. Directory Structure

```
project/
├── นโยบายพรรคการเมือง/          # PDF files
│   ├── เบอร์ 1 พรรคA.pdf
│   ├── เบอร์ 2 พรรคB.pdf
│   └── ...
└── all_parties_output/           # Output directory (created automatically)
```

## Step-by-Step Workflow

### Step 1: Extract Single Party (Test)

```bash
python scripts/extract_policy.py \
  --pdf-path "นโยบายพรรคการเมือง/เบอร์ 9 พรรคเพื่อไทย.pdf" \
  --output-file "all_parties_output/party_9_test.json"
```

**Expected output:**
```
Analyzing PDF: เบอร์ 9 พรรคเพื่อไทย.pdf
PDF size: ~15.2 MB
[HH:MM:SS] Sending request to Gemini 3 Pro Preview...
Timeout detection: Will retry if no chunks for >180s

..........
[Chunk 10] {"policies": [{"policy_seq": 1...
..........
[Chunk 20] "funding_source": "งบประมาณ...
...

Extraction complete! (250 chunks received)
✓ Validated: 57 policies extracted
Output saved to: all_parties_output/party_9_test.json
```

**Verify:**
```bash
python -c "import json; data=json.load(open('all_parties_output/party_9_test.json')); print(f'{len(data[\"policies\"])} policies')"
```

### Step 2: Batch Extract All Parties

```bash
bash scripts/batch_extract_all.sh
```

**What it does:**
1. Finds all PDFs in `นโยบายพรรคการเมือง/`
2. Skips already-extracted files
3. Extracts each PDF to JSON
4. Converts JSON to CSV
5. Moves processed PDFs to `processed/`
6. Creates consolidated CSV at end

**Monitor progress:**
```bash
# In another terminal
./scripts/CHECK_STATUS.sh

# Or watch log
tail -f extraction_log_production_final.txt
```

**Expected output:**
```
╔════════════════════════════════════════════════════════════════╗
║  PRODUCTION EXTRACTION: ALL 51 PARTIES                         ║
╚════════════════════════════════════════════════════════════════╝

Configuration:
  PDF Directory:    .../นโยบายพรรคการเมือง
  Output Directory: .../all_parties_output
  Max Retries:      3
  Delay Between:    3s

✓ Prerequisites checked
✓ Directories created (output + processed)

ℹ Found 51 PDF files to process

ℹ Progress: 1/51
Processing: เบอร์ 1 พรรคไทยทรัพย์ทวี.pdf
✓ Extracted: 8 policies
✓ CSV created
✓ Moved to processed/
...
```

### Step 3: Verify Extraction

```bash
./scripts/CHECK_STATUS.sh
```

**Output:**
```
╔════════════════════════════════════════════════════════════════╗
║           EXTRACTION STATUS DASHBOARD                         ║
╚════════════════════════════════════════════════════════════════╝

Files Generated:
  JSON files: 51/51
  CSV files:  51/51

Policies Extracted: 587

Recent Completions:
  party_51_พรรคพร้อม
  party_50_พรรคประชาอาสาชาติ
  ...

✅ No failures

Progress: 51/51 parties (100%)
```

### Step 4: Generate Consolidated CSV

**Pipe-delimited (for technical use):**
```bash
python scripts/json_to_csv.py \
  --batch-dir "all_parties_output" \
  --output-file "all_parties_output/consolidated_pipe.csv" \
  --delimiter "|" \
  --preserve-newlines \
  --add-metadata \
  --root-key "policies"
```

**Comma-delimited (for Google Sheets):**
```bash
# Convert pipe CSV to comma CSV with budget in millions
python scripts/convert_to_comma.py \
  --input "all_parties_output/consolidated_pipe.csv" \
  --output "all_parties_output/consolidated_comma.csv"
```

### Step 5: Add Party Information

```bash
python scripts/add_party_columns.py \
  --input "all_parties_output/consolidated.csv" \
  --output "all_parties_output/consolidated_with_party_info.csv"
```

**Adds columns:**
- `party_number` (extracted from filename)
- `party_name` (extracted from filename)

### Step 6: Send to Datadog

**Dry run (test):**
```bash
python scripts/send_to_datadog.py \
  --csv-file "all_parties_output/consolidated_with_party_info.csv" \
  --dry-run
```

**Actual send:**
```bash
python scripts/send_to_datadog.py \
  --csv-file "all_parties_output/consolidated_with_party_info.csv" \
  --batch-size 50
```

**Output:**
```
Loaded environment from: /path/to/.env
Reading CSV: consolidated_with_party_info.csv
Found 587 policies to send
Tags: {'source': 'custom-log', 'version': '20260129-0945', ...}

Sending batch 1/12 (50 logs)... ✓ Sent
Sending batch 2/12 (50 logs)... ✓ Sent
...
Sending batch 12/12 (37 logs)... ✓ Sent

Results:
  Sent: 587
  Failed: 0
  Success rate: 100.0%

✅ Logs sent to Datadog!
   Query: source:custom-log service:th-election-policy
```

### Step 7: Analyze in Datadog

**Open notebook:**
https://app.datadoghq.com/notebook/13821543

**Or create custom queries:**

```
# All policies
source:custom-log service:th-election-policy

# Specific party
source:custom-log service:th-election-policy @party_number:9

# Budget analysis
source:custom-log service:th-election-policy 
| stats sum(@budget_baht) by @party_name
| sort -sum(@budget_baht)
```

## Handling Errors

### If Extraction Fails

**Check error log:**
```bash
cat all_parties_output/party_N_NAME.error.log
```

**Retry specific party:**
```bash
python scripts/extract_policy.py \
  --pdf-path "นโยบายพรรคการเมือง/เบอร์ N พรรคNAME.pdf" \
  --output-file "all_parties_output/party_N_NAME.json" \
  --max-retries 5
```

### If Stream Stalls

**Symptoms:**
- Processing for >5 minutes with no progress
- Only 1 chunk received
- Invalid JSON

**Solution:**
- Script automatically detects and retries
- If still fails after 3 retries, check error log
- May need to wait for API rate limit reset

### If CSV Conversion Fails

**Check JSON validity:**
```bash
python -m json.tool party_N_NAME.json > /dev/null && echo "Valid" || echo "Invalid"
```

**Regenerate CSV:**
```bash
python scripts/json_to_csv.py \
  --json-file "party_N_NAME.json" \
  --output-file "party_N_NAME.csv" \
  --delimiter "|" \
  --preserve-newlines \
  --root-key "policies"
```

## Resume After Interruption

The batch script automatically skips already-extracted files:

```bash
# Just run again - will skip completed files
bash scripts/batch_extract_all.sh
```

**Check what's remaining:**
```bash
ls นโยบายพรรคการเมือง/*.pdf
# Lists unprocessed PDFs
```

## Performance Tips

### For Faster Processing

1. **Reduce delays** (edit `batch_extract_all.sh`):
   ```bash
   DELAY_BETWEEN_PDFS=1  # Change from 3 to 1
   ```

2. **Parallel processing** (advanced):
   ```bash
   # Split PDFs into batches and run multiple instances
   ```

### For Large PDFs

- Allow more time (5-10 minutes)
- Monitor chunk progress
- Check for stream stalls

### For Many PDFs

- Use batch script (handles all automatically)
- Monitor with `CHECK_STATUS.sh`
- Resume if interrupted

## Output Files

### Individual Files

```
all_parties_output/
├── party_1_พรรคไทยทรัพย์ทวี.json
├── party_1_พรรคไทยทรัพย์ทวี.csv
├── party_2_พรรคเพื่อชาติไทย.json
├── party_2_พรรคเพื่อชาติไทย.csv
└── ...
```

### Consolidated Files

```
all_parties_output/
├── YYYYMMDD_HHMMSS_consolidated_all_parties.csv
├── YYYYMMDD_HHMMSS_consolidated_with_party_info.csv
└── YYYYMMDD_HHMMSS_consolidated_comma_separated.csv
```

### Processed PDFs

```
นโยบายพรรคการเมือง/processed/
├── เบอร์ 1 พรรคไทยทรัพย์ทวี.pdf
├── เบอร์ 2 พรรคเพื่อชาติไทย.pdf
└── ...
```

## Validation

### Check Data Quality

```bash
# Count valid JSON files
python scripts/validate_all.py

# Check CSV structure
python -c "import csv; f=open('consolidated.csv','r',encoding='utf-8'); print(f'{sum(1 for _ in csv.DictReader(f, delimiter=\"|\"))} records')"

# Verify in Datadog
# Query: source:custom-log service:th-election-policy
# Should show 587 logs
```

## Timeline

**For 51 parties:**
- Setup: 5 minutes
- Extraction: 4-6 hours
- Conversion: 2 minutes
- Datadog upload: 1 minute
- **Total: ~4-6 hours**

## Success Criteria

✅ All PDFs extracted (51/51)  
✅ All JSON files valid  
✅ All CSV files created  
✅ Consolidated CSV complete  
✅ Data in Datadog (if using)  
✅ No error logs remaining  

## Next Steps

1. ✅ Import CSV to Google Sheets
2. ✅ Analyze in Datadog
3. ✅ Generate insights
4. ✅ Create visualizations
5. ✅ Share findings

## Support

See `SKILL.md` for detailed documentation and troubleshooting.
