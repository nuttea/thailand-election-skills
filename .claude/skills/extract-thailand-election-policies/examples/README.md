# Examples

This directory contains example notebooks and documentation for extracting Thai election policies from PDF documents.

## Files

### `extract_policy_notebook.ipynb`

Interactive Jupyter notebook demonstrating:
- PDF policy extraction using Gemini 3 Pro Preview
- Data analysis and visualization
- Budget analysis by category
- Policy categorization
- Export to CSV/JSON
- Batch processing examples

**Usage:**
1. Install required packages:
   ```bash
   pip install pandas matplotlib seaborn jupyter
   ```

2. Open the notebook:
   ```bash
   jupyter notebook extract_policy_notebook.ipynb
   ```

3. Update the PDF path in the notebook to point to your PDF file

4. Run all cells to extract and analyze policies

**Features:**
- ✅ Step-by-step extraction guide
- ✅ Data visualization (charts, graphs)
- ✅ Budget analysis
- ✅ Category distribution
- ✅ Keyword search
- ✅ Export to CSV/JSON

### `datadog_queries.md`

Example Datadog queries for analyzing extracted policy data.

## Requirements

The notebook requires:
- Python 3.8+
- `pandas` - Data analysis
- `matplotlib` - Plotting
- `seaborn` - Statistical visualization
- `jupyter` - Notebook interface
- `google-genai` - Gemini API (from parent requirements.txt)
- `pydantic` - Data validation (from parent requirements.txt)

Install all requirements:
```bash
cd ../..
pip install -r requirements.txt
pip install pandas matplotlib seaborn jupyter
```

## Quick Start

1. **Set up environment:**
   ```bash
   # Ensure .env file has GEMINI_API_KEY
   export GEMINI_API_KEY=your_key_here
   ```

2. **Open notebook:**
   ```bash
   jupyter notebook extract_policy_notebook.ipynb
   ```

3. **Update PDF path** in cell 3.1 to your PDF file

4. **Run all cells** to extract and analyze

## Output

The notebook generates:
- `party_XX_policies.json` - Structured JSON with all policies
- `party_XX_policies.csv` - CSV file for spreadsheet import
- Visualizations (charts, graphs)
- Summary statistics

## Troubleshooting

**Import errors:**
- Ensure you're running the notebook from the `examples/` directory
- Check that `scripts/extract_policy.py` exists in the parent directory

**PDF not found:**
- Update the `pdf_path` variable in cell 3.1
- Use absolute paths if relative paths don't work

**API errors:**
- Verify `GEMINI_API_KEY` is set in `.env` file
- Check API quota/limits

## See Also

- **Main documentation**: `../SKILL.md`
- **Workflow guide**: `../WORKFLOW.md`
- **LLMObs integration**: `../LLMOBS_INTEGRATION.md`
