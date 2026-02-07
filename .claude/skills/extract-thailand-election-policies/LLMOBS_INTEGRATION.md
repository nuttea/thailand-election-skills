# Datadog LLMObs Integration

This skill is integrated with Datadog LLM Observability for comprehensive tracing and monitoring.

## Features

✅ **Automatic Detection** - Enables LLMObs if DD_API_KEY is in .env  
✅ **Workflow Tracing** - Entire extraction as single trace  
✅ **Nested Spans** - Task spans for encoding, prompt building  
✅ **Input/Output Tracking** - Captures PDF info and extraction results  
✅ **Metadata Enrichment** - Tags, metrics, and context  
✅ **Span Export** - Exports span context for evaluation tracking  
✅ **Prompt Tracking** - Instructions saved as metadata  
✅ **Error Tracing** - Failures captured with context  

## Setup

### 1. Install ddtrace

```bash
pip install ddtrace
```

### 2. Add DD_API_KEY to .env

```bash
# In .env file
export DD_API_KEY="your-datadog-api-key"
export DD_SITE="datadoghq.com"  # Optional
export DD_ENV="prod"  # Optional
```

### 3. Run Extraction

```bash
# LLMObs automatically enabled if DD_API_KEY found
python scripts/extract_policy.py \
  --pdf-path "party.pdf" \
  --output-file "party.json"
```

**Output:**
```
Loaded environment from: /path/to/.env
✓ Datadog LLMObs enabled
  ML App: thailand-election-policy-extractor
  Environment: prod
Analyzing PDF: party.pdf
...
✓ LLMObs traces flushed
```

## Trace Structure

### Span Hierarchy

```
analyze_pdf_with_gemini (workflow)
├── encode_pdf_to_base64 (task)
│   └── Annotated with PDF size
├── Gemini API call (auto-instrumented)
│   └── Multiple chunks streamed
└── Final annotations (output data)
```

### Span Details

**Workflow Span:**
- **Name:** `analyze_pdf_with_gemini`
- **Kind:** workflow
- **Input:** PDF path, instructions, config
- **Output:** Policies extracted, file saved
- **Metadata:** Instructions length, pages, retry count
- **Tags:** `extraction_type:thailand_election_policy`

**Task Span:**
- **Name:** `encode_pdf_to_base64`
- **Kind:** task
- **Input:** PDF path
- **Output:** Encoded size in MB
- **Metadata:** Encoding type

## Annotations

### Input Data (Start of Workflow)

```python
LLMObs.annotate(
    input_data={
        "pdf_path": "เบอร์ 9 พรรคเพื่อไทย.pdf",
        "output_format": "json",
        "use_structured_output": True,
        "max_retries": 2
    },
    metadata={
        "instructions_length": 1250,
        "pages": "all"
    },
    tags={
        "extraction_type": "thailand_election_policy",
        "output_format": "json"
    }
)
```

### Output Data (End of Workflow)

```python
LLMObs.annotate(
    output_data={
        "policies_extracted": 57,
        "output_file": "party_9_policies.json",
        "span_context_exported": True
    },
    metrics={
        "policies_count": 57,
        "total_retries": 0
    }
)
```

## Span Context Export

### What It Does

Exports trace_id and span_id for evaluation tracking:

```python
span_context = LLMObs.export_span()
# Returns: {"trace_id": "...", "span_id": "..."}
```

### Saved in Output JSON

```json
{
  "policies": [...],
  "_llmobs_span_context": {
    "trace_id": "1234567890",
    "span_id": "9876543210"
  }
}
```

### Use for Evaluations

```python
# Later, submit evaluation linked to this extraction
LLMObs.submit_evaluation(
    span_context=span_context,
    label="extraction_quality",
    metric_type="score",
    value=0.95
)
```

## Viewing Traces in Datadog

### Access Traces

**URL:** https://app.datadoghq.com/llm/traces

**Query:**
```
ml_app:thailand-election-policy-extractor
```

**Filter by party:**
```
ml_app:thailand-election-policy-extractor @pdf_path:*เบอร์ 9*
```

### Trace Details

**What You'll See:**
- Workflow duration (total extraction time)
- Task durations (encoding, processing)
- LLM call details (if auto-instrumented)
- Input/output data
- Metadata and tags
- Error information (if any)

### Metrics Available

- `policies_count` - Number of policies extracted
- `total_retries` - Retry attempts made
- `encoded_size_mb` - PDF size
- `instructions_length` - Prompt size

## Application Naming

**ML App Name:** `thailand-election-policy-extractor`

**Follows Datadog guidelines:**
- ✅ Lowercase
- ✅ Descriptive
- ✅ Unique identifier
- ✅ Uses hyphens for readability

**Format:** `<domain>-<purpose>-<tool>`

## Monitoring Queries

### Find Slow Extractions

```
ml_app:thailand-election-policy-extractor @duration:>300000
```

### Find Failed Extractions

```
ml_app:thailand-election-policy-extractor error:true
```

### Track Retries

```
ml_app:thailand-election-policy-extractor @total_retries:>0
```

### Monitor Policy Counts

```
ml_app:thailand-election-policy-extractor 
| stats avg(@policies_count), max(@policies_count) by @pdf_path
```

## Dashboards

### Key Metrics to Track

1. **Performance**
   - P95 extraction duration
   - Average policies per extraction
   - Retry rate

2. **Quality**
   - Policies extracted per PDF
   - Validation success rate
   - Error rate

3. **Volume**
   - Extractions per day
   - Total policies extracted
   - PDF sizes processed

### Sample Dashboard Widgets

**Extraction Duration:**
```
ml_app:thailand-election-policy-extractor
| stats p95(@duration) by time(1h)
```

**Policies Extracted:**
```
ml_app:thailand-election-policy-extractor
| stats sum(@policies_count)
```

**Error Rate:**
```
ml_app:thailand-election-policy-extractor
| stats count() by error
```

## Alerts

### High Error Rate

```
Alert when: error rate > 10% in last 5 minutes
Query: ml_app:thailand-election-policy-extractor error:true
```

### Slow Extractions

```
Alert when: p95 duration > 5 minutes
Query: ml_app:thailand-election-policy-extractor
Metric: p95(@duration)
```

### Low Policy Count

```
Alert when: avg policies < 5
Query: ml_app:thailand-election-policy-extractor
Metric: avg(@policies_count)
```

## Troubleshooting

### LLMObs Not Enabling

**Check:**
1. `DD_API_KEY` in .env file
2. `ddtrace` package installed
3. No import errors in console

**Debug:**
```bash
python -c "from ddtrace.llmobs import LLMObs; print('LLMObs available')"
```

### Traces Not Appearing

**Solutions:**
1. Ensure `LLMObs.flush()` is called
2. Check API key is valid
3. Verify DD_SITE is correct
4. Wait 1-2 minutes for ingestion

### Span Context Not Exported

**Check:**
- LLMObs is enabled
- Called within a traced function
- No exceptions during export

## Best Practices

### 1. Always Flush

```python
try:
    result = extract_policy(...)
finally:
    if LLMOBS_ENABLED:
        LLMObs.flush()
```

### 2. Rich Annotations

```python
LLMObs.annotate(
    input_data={"pdf": "party_9.pdf"},  # What went in
    output_data={"policies": 57},  # What came out
    metadata={"model": "gemini-3-pro"},  # Context
    metrics={"duration_ms": 4500},  # Numbers
    tags={"party": "9"}  # Searchable tags
)
```

### 3. Export Span for Evaluations

```python
span_context = LLMObs.export_span()
# Save in output for later evaluation
result['_span_context'] = span_context
```

### 4. Handle Errors

```python
try:
    result = extract(...)
except Exception as e:
    if LLMOBS_ENABLED:
        LLMObs.annotate(
            metadata={"error": str(e), "error_type": type(e).__name__}
        )
    raise
```

## Integration with Batch Script

The batch extraction script (`batch_extract_all.sh`) automatically benefits from LLMObs:

- Each PDF extraction creates a workflow trace
- All extractions visible in Datadog
- Can monitor batch progress in real-time
- Identify problematic PDFs quickly

**Query to see batch:**
```
ml_app:thailand-election-policy-extractor @timestamp:[now-1h TO now]
| sort @timestamp
```

## Example Trace

**Workflow:** Extract Party 9 (พรรคเพื่อไทย)

```
Trace ID: 1234567890
Duration: 4.5 seconds

Spans:
├─ analyze_pdf_with_gemini (workflow) - 4.5s
│  ├─ encode_pdf_to_base64 (task) - 0.2s
│  │  Input: {"pdf_path": "เบอร์ 9 พรรคเพื่อไทย.pdf"}
│  │  Output: {"encoded_size_mb": 15.2}
│  │
│  └─ gemini_api_call (auto-instrumented) - 4.2s
│     Input: Prompt + PDF
│     Output: 57 policies
│     Tokens: 8,500 input, 12,000 output
│
Output: {"policies_extracted": 57, "span_context_exported": true}
Metrics: policies_count=57, total_retries=0
Tags: extraction_type=thailand_election_policy
```

## Summary

✅ **LLMObs automatically enabled** when DD_API_KEY present  
✅ **Complete trace visibility** for all extractions  
✅ **Span context exported** for evaluation tracking  
✅ **Rich annotations** with inputs, outputs, metadata  
✅ **Nested spans** show operation hierarchy  
✅ **Prompt tracking** via metadata  
✅ **Production-ready** with error handling  

**View your traces:** https://app.datadoghq.com/llm/traces?query=ml_app:thailand-election-policy-extractor

---

**Integration Date:** 2026-01-29  
**ML App Name:** `thailand-election-policy-extractor`  
**Status:** ✅ Production-ready
