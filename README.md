# thailand-election-skills
SKILLS for AGENT related to Thailand Election data processing and extraction

Install Gemini CLI

```
npm install -g @google/gemini-cli
```

Set GEMINI API Key

go to https://aistudio.google.com/api-keys

copy and save .env.example to .env

```
cp .env.example .env
```

Set GEMINI_API_KEY then source .env file

```
source .env
```

---

## Extract Thailand Election Policies Skill

This skill uses the Gemini 3 Pro Preview model to extract policy information from PDF documents of Thai political parties. It's designed to handle Thai language and produces structured JSON output.

### Features

- **Thai Language OCR**: Accurately reads Thai text and numerals from PDFs.
- **Structured JSON Output**: Extracts data into a clean, validated JSON format.
- **Detailed Data Extraction**: Captures 9 distinct fields for each policy, including name, budget, funding source, and more.
- **Budget Normalization**: Converts Thai budget units (e.g., ล้าน, พันล้าน) into numerical Baht values.
- **Robust Error Handling**: Includes automatic retries and detailed logging for troubleshooting.

### Setup

Before running the extraction scripts, you need to set up a Python virtual environment and install the required dependencies.

1.  **Navigate to the skill directory:**
    ```bash
    cd .claude/skills/extract-thailand-election-policies
    ```

2.  **Create a Python virtual environment:**
    *(If the `.venv` directory doesn't already exist)*
    ```bash
    python3 -m venv .venv
    ```

3.  **Activate the virtual environment:**
    ```bash
    source .venv/bin/activate
    ```
    *You should see `(.venv)` at the beginning of your shell prompt.*

4.  **Install the required Python packages:**
    ```bash
    pip install -r requirements.txt
    ```

You are now ready to run the extraction scripts. Remember to activate the virtual environment (`source .venv/bin/activate`) in your terminal session each time you want to use the scripts.

### Usage

#### Extracting a Single PDF

To extract policies from a single PDF file, use the `extract_policy.py` script.

```bash
# Make sure your virtual environment is activated
python scripts/extract_policy.py \
  --pdf-path "/path/to/your/party_policy.pdf" \
  --output-file "/path/to/your/output.json"
```

Replace the paths with the actual location of your PDF file and the desired location for the output JSON file.

#### Batch Extracting All PDFs

To process all PDF files located in a directory, you can use the `batch_extract_all.sh` script. By default, it processes PDFs from the `assets/นโยบายพรรคการเมือง/` directory.

```bash
# Make sure your virtual environment is activated
bash scripts/batch_extract_all.sh
```

This script will:
- Process all PDFs in the directory.
- Skip files that have already been extracted.
- Automatically retry if an extraction fails.
- Place the output JSON files in an `all_parties_output` directory.

### Output Format

The script generates a JSON file containing a list of policies. Each policy is an object with the following fields:

- `policy_seq`: The sequence number of the policy.
- `policy_category`: The assigned category (e.g., "Public Health", "Education").
- `policy_name`: The name of the policy.
- `budget_baht`: The budget in Baht (as an integer).
- `funding_source`: Description of where the funding comes from.
- `cost_effectiveness`: Analysis of cost-effectiveness.
- `benefits`: The described benefits of the policy.
- `impacts`: The potential impacts of the policy.
- `risks`: The identified risks of the policy.

**Example JSON Structure:**
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