# Extract Thailand Election Policies

Specialized skill for extracting Thai political party policy data from PDF documents.

## Quick Start

### Setup (First Time)

```bash
# 1. Create virtual environment
python3 -m venv .venv

# 2. Activate venv
source .venv/bin/activate

# 3. Install requirements
pip install -r requirements.txt

# 4. Verify installation
python -c "import google.genai, pydantic, requests; print('✓ Core packages installed')"

# 5. Optional - Install ddtrace for LLMObs
pip install ddtrace
```

### Usage

```bash
# Activate venv (always do this first)
source .venv/bin/activate

# Extract single party
python scripts/extract_policy.py \
  --pdf-path "party.pdf" \
  --output-file "party.json"

# Extract all parties
bash scripts/batch_extract_all.sh

# Convert to CSV
python scripts/json_to_csv.py \
  --json-file "party.json" \
  --output-file "party.csv"

# Send to Datadog
python scripts/send_to_datadog.py \
  --csv-file "consolidated.csv"

# Deactivate when done
deactivate
```

## Features

- ✅ Thai language OCR
- ✅ Structured JSON output
- ✅ 9-field policy model
- ✅ Budget normalization
- ✅ Auto-retry logic
- ✅ Error logging
- ✅ Datadog integration

## Data Model

**9 Fields per Policy:**
1. policy_seq (int)
2. policy_category (str) - 15 categories
3. policy_name (str)
4. budget_baht (int)
5. funding_source (str)
6. cost_effectiveness (str)
7. benefits (str)
8. impacts (str)
9. risks (str)

## Real-World Results

**Thailand 2026 Election:**
- 51 parties extracted (100%)
- 587 policies total
- All data in Datadog
- Analysis notebook created

## Documentation

- `SKILL.md` - Complete documentation
- `WORKFLOW.md` - Step-by-step guide
- `examples/` - Sample outputs
- `scripts/` - All extraction tools

## Datadog

**Query:** `source:custom-log service:th-election-policy`

**Notebook:** https://app.datadoghq.com/notebook/13821543

## Requirements

- Python 3.x
- `google-genai` package
- `pydantic` package
- `requests` package (for Datadog)
- GEMINI_API_KEY in .env
- DD_API_KEY in .env (for Datadog)

## Installation

```bash
pip install google-genai pydantic requests
```

## See Also

- Analysis guide: `DATADOG_ANALYSIS_GUIDE.md`
- Project summary: `PROJECT_COMPLETE_SUMMARY.md`
