#!/usr/bin/env python3
"""
Thailand Election Policy Extraction Script
Extracts Thai political party policies from PDF files using Google Gemini 3 Pro Preview
Uses Gemini Structured Output for reliable JSON extraction
Integrated with Datadog LLM Observability for tracing and monitoring
"""

import argparse
import base64
import json
import os
import sys
import time
from pathlib import Path
from typing import Optional, List, Dict, Any

# Check for required packages
try:
    from google import genai
    from google.genai import types
    from pydantic import BaseModel, Field
except ImportError as e:
    print(f"Error: Required package not installed: {e}", file=sys.stderr)
    print("Install with: pip install google-genai pydantic", file=sys.stderr)
    sys.exit(1)

# Optional: Datadog LLM Observability
LLMOBS_ENABLED = False
LLMOBS_AVAILABLE = False

try:
    from ddtrace.llmobs import LLMObs
    from ddtrace.llmobs.decorators import workflow, llm, agent, tool, task, embedding, retrieval
    LLMOBS_AVAILABLE = True
except ImportError:
    pass

# Don't use decorators - they cause span context issues
# Instead, we'll use LLMObs.annotate() within functions
def workflow(func):
    return func

def task(func):
    return func

def llm(*args, **kwargs):
    def decorator(func):
        return func
    return decorator


# Pydantic models for structured output
class Policy(BaseModel):
    """Represents a single policy from a political party document"""
    policy_seq: int = Field(description="Policy sequence number (convert Thai numerals to Arabic)")
    policy_category: str = Field(description="Policy category from predefined list")
    policy_name: str = Field(description="Policy name extracted word by word")
    budget_baht: int = Field(description="Budget amount in Baht as pure number (0 if no budget)")
    funding_source: str = Field(description="Funding source details, preserve Thai numerals in lists")
    cost_effectiveness: str = Field(description="Cost-effectiveness details, preserve Thai numerals in lists")
    benefits: str = Field(description="Benefits details, preserve Thai numerals in lists")
    impacts: str = Field(description="Impacts details, preserve Thai numerals in lists")
    risks: str = Field(description="Risks details, preserve Thai numerals in lists")


class PoliticalPartyPolicies(BaseModel):
    """Collection of policies from a political party document"""
    policies: List[Policy] = Field(description="List of all policies extracted from the document")


def load_env_file():
    """Load environment variables from .env file"""
    possible_paths = [
        Path(__file__).parent.parent.parent.parent.parent / ".env",
        Path.cwd() / ".env",
    ]
    
    for env_path in possible_paths:
        if env_path.exists():
            with open(env_path) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        # Remove quotes and export prefix
                        value = value.strip().strip('"').strip("'")
                        key = key.strip().replace('export ', '')
                        os.environ[key] = value
            print(f"Loaded environment from: {env_path}", file=sys.stderr)
            return
    
    print("Warning: .env file not found", file=sys.stderr)

def initialize_llmobs():
    """Initialize Datadog LLM Observability if DD_API_KEY is available"""
    global LLMOBS_ENABLED
    
    dd_api_key = os.environ.get('DD_API_KEY')
    print("Info: DD_API_KEY ***" + dd_api_key[0:5])
    
    if not dd_api_key:
        print("Info: DD_API_KEY not found - LLMObs disabled", file=sys.stderr)
        LLMOBS_ENABLED = False
        return False
    
    if not LLMOBS_AVAILABLE:
        print("Info: ddtrace not installed - LLMObs disabled", file=sys.stderr)
        LLMOBS_ENABLED = False
        return False
    
    try:
        LLMObs.enable(
            ml_app="thailand-election-policy-extractor",
            api_key=dd_api_key,
            site=os.environ.get('DD_SITE', 'datadoghq.com'),
            agentless_enabled=True,
            env=os.environ.get('DD_ENV', 'prod'),
            service=os.environ.get('DD_SERVICE', 'claude-skills')
        )
        print("✓ Datadog LLMObs enabled", file=sys.stderr)
        print(f"  ML App: thailand-election-policy-extractor", file=sys.stderr)
        print(f"  Environment: {os.environ.get('DD_ENV', 'prod')}", file=sys.stderr)
        LLMOBS_ENABLED = True
        return True
    except Exception as e:
        print(f"Warning: Failed to enable LLMObs: {e}", file=sys.stderr)
        LLMOBS_ENABLED = False
        return False


@task
def encode_pdf_to_base64(pdf_path: str) -> str:
    """Encode PDF file to base64 string"""
    with open(pdf_path, 'rb') as pdf_file:
        encoded = base64.b64encode(pdf_file.read()).decode('utf-8')
    
    # Annotate task with PDF info (only if there's an active span)
    if LLMOBS_ENABLED:
        try:
            pdf_size_mb = len(encoded) * 3 / 4 / 1024 / 1024
            LLMObs.annotate(
                input_data={"pdf_path": pdf_path},
                output_data={"encoded_size_mb": round(pdf_size_mb, 2)},
                metadata={"encoding": "base64"}
            )
        except Exception:
            # No active span - skip annotation
            pass
    
    return encoded


def parse_page_range(page_spec: Optional[str], total_pages: Optional[int] = None) -> Optional[list]:
    """Parse page specification like '1-5' or '1,3,5' into list of page numbers"""
    if not page_spec:
        return None
    
    pages = []
    for part in page_spec.split(','):
        if '-' in part:
            start, end = map(int, part.split('-'))
            pages.extend(range(start, end + 1))
        else:
            pages.append(int(part))
    
    return sorted(set(pages))


def build_prompt(instructions: str, output_format: str, pdf_filename: str) -> str:
    """Build the prompt for Gemini model"""
    
    format_instructions = {
        'csv': """
Output the extracted information as CSV format with proper escaping:
- Use comma as delimiter
- Escape fields containing commas, quotes, or newlines with double quotes
- Use double quotes ("") to escape quotes within fields
- Include a header row with column names
""",
        'json': """
Output the extracted information as valid JSON format:
- Use proper JSON structure with arrays and objects
- Ensure all strings are properly escaped
- Use meaningful key names
- Pretty-print with indentation for readability
""",
        'markdown': """
Output the extracted information as Markdown format:
- Use tables for structured data (| Column1 | Column2 |)
- Use headers (# ## ###) for sections
- Use lists for enumerated items
- Use code blocks for technical content
""",
        'text': """
Output the extracted information as plain text:
- Use clear formatting and spacing
- Organize content logically
- Preserve important structure and hierarchy
"""
    }
    
    format_instruction = format_instructions.get(output_format, format_instructions['text'])
    
    prompt = f"""Analyze the PDF document: {pdf_filename}

{instructions}

{format_instruction}

IMPORTANT: Extract all text word by word with high accuracy. Pay special attention to:
- Thai language characters and diacritics
- Numbers and dates
- Tables and structured data
- Headers and section titles

Begin your extraction now:"""
    
    return prompt


def analyze_pdf_with_gemini(
    pdf_path: str,
    instructions: str,
    output_format: str = 'json',
    pages: Optional[str] = None,
    output_file: Optional[str] = None,
    use_structured_output: bool = True,
    max_retries: int = 2
) -> str:
    """
    Analyze PDF using Gemini 3 Pro Preview model with structured output
    
    Args:
        pdf_path: Path to PDF file
        instructions: Custom instructions for extraction
        output_format: Output format (json for structured, text for legacy)
        pages: Page range specification (e.g., "1-5" or "1,3,5")
        output_file: Optional path to save output
        use_structured_output: Use Gemini structured output (recommended)
    
    Returns:
        Extracted content as JSON string
    """
    
    # Load environment variables
    load_env_file()
    
    # Initialize LLMObs if available
    initialize_llmobs()
    
    # Check for API key
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError(
            "GEMINI_API_KEY not found in environment variables.\n"
            "Please set it in .env file or export it in your shell."
        )
    
    # Use LLMObs workflow context manager if enabled
    if LLMOBS_ENABLED:
        with LLMObs.workflow(name="analyze_pdf_with_gemini"):
            # Annotate workflow with input metadata
            try:
                LLMObs.annotate(
                    input_data={
                        "pdf_path": pdf_path,
                        "output_format": output_format,
                        "use_structured_output": use_structured_output,
                        "max_retries": max_retries
                    },
                    metadata={
                        "instructions_length": len(instructions),
                        "pages": pages if pages else "all"
                    },
                    tags={
                        "extraction_type": "thailand_election_policy",
                        "output_format": output_format
                    }
                )
            except Exception as e:
                print(f"Warning: Could not annotate workflow: {e}", file=sys.stderr)
                # Continue without annotation
            
            # Validate PDF file
            pdf_path_obj = Path(pdf_path)
            if not pdf_path_obj.exists():
                raise FileNotFoundError(f"PDF file not found: {pdf_path}")
            
            print(f"Analyzing PDF: {pdf_path_obj.name}", file=sys.stderr)
            if pages:
                print(f"Pages: {pages}", file=sys.stderr)
            print(f"Output format: {output_format}", file=sys.stderr)
            print(f"Structured output: {use_structured_output}", file=sys.stderr)
            print("", file=sys.stderr)
            
            # Initialize Gemini client
            client = genai.Client(api_key=api_key)
            
            # Build prompt
            prompt = build_prompt(instructions, output_format, pdf_path_obj.name)
            
            # Encode PDF
            print("Encoding PDF...", file=sys.stderr)
            pdf_base64 = encode_pdf_to_base64(pdf_path)
            pdf_size_mb = len(pdf_base64) * 3 / 4 / 1024 / 1024  # Approximate original size
            print(f"PDF size: ~{pdf_size_mb:.1f} MB", file=sys.stderr)
            
            # Prepare content for Gemini
            parts = [
                types.Part.from_text(text=prompt),
                types.Part(
                    inline_data=types.Blob(
                        mime_type="application/pdf",
                        data=pdf_base64
                    )
                )
            ]
            
            contents = [
                types.Content(
                    role="user",
                    parts=parts
                )
            ]
            
            # Configure generation with structured output
            if use_structured_output and output_format == 'json':
                generate_content_config = types.GenerateContentConfig(
                    temperature=0.5,
                    response_mime_type="application/json",
                    response_schema=PoliticalPartyPolicies.model_json_schema(),
                    thinking_config=types.ThinkingConfig(
                        thinking_level="low",
                    )
                )
            else:
                generate_content_config = types.GenerateContentConfig(
                    temperature=0.5,
                    thinking_config=types.ThinkingConfig(
                        thinking_level="low",
                    )
                )
            
            # Generate content with retry logic
            result_text = ""
            retry_count = 0
            chunk_timeout = 180  # 3 minutes in seconds
            
            while retry_count <= max_retries:
                if retry_count > 0:
                    print(f"\n⚠ Retry attempt {retry_count}/{max_retries}...", file=sys.stderr)
                
                print(f"[{time.strftime('%H:%M:%S')}] Sending request to Gemini 3 Pro Preview...", file=sys.stderr)
                print("This may take a moment for large PDFs...", file=sys.stderr)
                print(f"Timeout detection: Will retry if no chunks for >{chunk_timeout}s", file=sys.stderr)
                print("", file=sys.stderr)
                
                result_text = ""
                last_chunk_time = time.time()
                chunk_count = 0
                
                try:
                    for chunk in client.models.generate_content_stream(
                        model="gemini-3-pro-preview",
                        contents=contents,
                        config=generate_content_config,
                    ):
                        if chunk.text:
                            current_time = time.time()
                            elapsed = current_time - last_chunk_time
                            
                            # Check if stalled
                            if elapsed > chunk_timeout and chunk_count > 0:
                                print(f"\n⚠ Stream stalled for {elapsed:.0f}s (>{chunk_timeout}s)", file=sys.stderr)
                                raise TimeoutError(f"Stream stalled for {elapsed:.0f} seconds")
                            
                            result_text += chunk.text
                            chunk_count += 1
                            last_chunk_time = current_time
                            
                            # Print progress with preview
                            if chunk_count % 10 == 0:
                                # Show preview every 10 chunks
                                preview = chunk.text[:50].replace('\n', ' ')
                                print(f"\n[Chunk {chunk_count}] {preview}...", end="", file=sys.stderr, flush=True)
                            else:
                                print(".", end="", file=sys.stderr, flush=True)
                    
                    # After all chunks received
                    print("\n", file=sys.stderr)
                    print(f"Extraction complete! ({chunk_count} chunks received)", file=sys.stderr)
                    
                    # Validate JSON if using structured output
                    if use_structured_output and output_format == 'json':
                        try:
                            policies = PoliticalPartyPolicies.model_validate_json(result_text)
                            print(f"✓ Validated: {len(policies.policies)} policies extracted", file=sys.stderr)
                            # Re-serialize for consistent formatting
                            result_text = policies.model_dump_json(indent=2)
                        except Exception as e:
                            print(f"⚠ Warning: JSON validation failed: {e}", file=sys.stderr)
                            # If validation fails with only 1 chunk, treat as incomplete and retry
                            if chunk_count == 1:
                                print(f"⚠ Only 1 chunk received with invalid JSON - likely incomplete response", file=sys.stderr)
                                raise ValueError("Incomplete JSON response - only 1 chunk received")
                    
                    # Success - break out of retry loop
                    break
                    
                except TimeoutError as e:
                    print(f"\n✗ Timeout: {e}", file=sys.stderr)
                    retry_count += 1
                    if retry_count > max_retries:
                        print(f"\n✗ Failed after {max_retries} retries", file=sys.stderr)
                        raise
                    # Continue to next retry attempt
                    
                except ValueError as e:
                    # Incomplete response
                    print(f"\n✗ Incomplete response: {e}", file=sys.stderr)
                    retry_count += 1
                    if retry_count > max_retries:
                        print(f"\n✗ Failed after {max_retries} retries", file=sys.stderr)
                        raise
                    # Continue to next retry attempt
                    
                except Exception as e:
                    print(f"\nError during generation: {e}", file=sys.stderr)
                    retry_count += 1
                    if retry_count > max_retries:
                        raise
                    # Continue to next retry attempt
            
            # Export span context for evaluation tracking
            span_context = None
            if LLMOBS_ENABLED:
                try:
                    span_context = LLMObs.export_span()
                except Exception as e:
                    print(f"Warning: Could not export span context: {e}", file=sys.stderr)
            
            # Add span context to result if available
            if span_context and use_structured_output and output_format == 'json':
                try:
                    result_dict = json.loads(result_text)
                    result_dict['_llmobs_span_context'] = span_context
                    result_text = json.dumps(result_dict, indent=2, ensure_ascii=False)
                except:
                    pass  # If can't add, continue without it
            
            # Save to file if specified
            if output_file:
                output_path = Path(output_file)
                output_path.parent.mkdir(parents=True, exist_ok=True)
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(result_text)
                print(f"Output saved to: {output_file}", file=sys.stderr)
            
            # Final workflow annotation
            if LLMOBS_ENABLED:
                try:
                    policies_count = 0
                    if use_structured_output and output_format == 'json':
                        result_dict = json.loads(result_text)
                        policies_count = len(result_dict.get('policies', []))
                    
                    LLMObs.annotate(
                        output_data={
                            "policies_extracted": policies_count,
                            "output_file": output_file,
                            "span_context_exported": span_context is not None
                        },
                        metrics={
                            "policies_count": policies_count,
                            "total_retries": retry_count
                        }
                    )
                except Exception as e:
                    print(f"Warning: Could not annotate final output: {e}", file=sys.stderr)
            
            return result_text
    else:
        # LLMObs disabled - run without context manager
        # Validate PDF file
        pdf_path_obj = Path(pdf_path)
        if not pdf_path_obj.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")
        
        print(f"Analyzing PDF: {pdf_path_obj.name}", file=sys.stderr)
        if pages:
            print(f"Pages: {pages}", file=sys.stderr)
        print(f"Output format: {output_format}", file=sys.stderr)
        print(f"Structured output: {use_structured_output}", file=sys.stderr)
        print("", file=sys.stderr)
        
        # Initialize Gemini client
        client = genai.Client(api_key=api_key)
        
        # Build prompt
        prompt = build_prompt(instructions, output_format, pdf_path_obj.name)
        
        # Encode PDF
        print("Encoding PDF...", file=sys.stderr)
        pdf_base64 = encode_pdf_to_base64(pdf_path)
        pdf_size_mb = len(pdf_base64) * 3 / 4 / 1024 / 1024  # Approximate original size
        print(f"PDF size: ~{pdf_size_mb:.1f} MB", file=sys.stderr)
        
        # Prepare content for Gemini
        parts = [
            types.Part.from_text(text=prompt),
            types.Part(
                inline_data=types.Blob(
                    mime_type="application/pdf",
                    data=pdf_base64
                )
            )
        ]
        
        contents = [
            types.Content(
                role="user",
                parts=parts
            )
        ]
        
        # Configure generation with structured output
        if use_structured_output and output_format == 'json':
            generate_content_config = types.GenerateContentConfig(
                temperature=0.5,
                response_mime_type="application/json",
                response_schema=PoliticalPartyPolicies.model_json_schema(),
                thinking_config=types.ThinkingConfig(
                    thinking_level="low",
                )
            )
        else:
            generate_content_config = types.GenerateContentConfig(
                temperature=0.5,
                thinking_config=types.ThinkingConfig(
                    thinking_level="low",
                )
            )
        
        # Generate content with retry logic
        result_text = ""
        retry_count = 0
        chunk_timeout = 180  # 3 minutes in seconds
        
        while retry_count <= max_retries:
            if retry_count > 0:
                print(f"\n⚠ Retry attempt {retry_count}/{max_retries}...", file=sys.stderr)
            
            print(f"[{time.strftime('%H:%M:%S')}] Sending request to Gemini 3 Pro Preview...", file=sys.stderr)
            print("This may take a moment for large PDFs...", file=sys.stderr)
            print(f"Timeout detection: Will retry if no chunks for >{chunk_timeout}s", file=sys.stderr)
            print("", file=sys.stderr)
            
            result_text = ""
            last_chunk_time = time.time()
            chunk_count = 0
            
            try:
                for chunk in client.models.generate_content_stream(
                    model="gemini-3-pro-preview",
                    contents=contents,
                    config=generate_content_config,
                ):
                    if chunk.text:
                        current_time = time.time()
                        elapsed = current_time - last_chunk_time
                        
                        # Check if stalled
                        if elapsed > chunk_timeout and chunk_count > 0:
                            print(f"\n⚠ Stream stalled for {elapsed:.0f}s (>{chunk_timeout}s)", file=sys.stderr)
                            raise TimeoutError(f"Stream stalled for {elapsed:.0f} seconds")
                        
                        result_text += chunk.text
                        chunk_count += 1
                        last_chunk_time = current_time
                        
                        # Print progress with preview
                        if chunk_count % 10 == 0:
                            # Show preview every 10 chunks
                            preview = chunk.text[:50].replace('\n', ' ')
                            print(f"\n[Chunk {chunk_count}] {preview}...", end="", file=sys.stderr, flush=True)
                        else:
                            print(".", end="", file=sys.stderr, flush=True)
                
                # After all chunks received
                print("\n", file=sys.stderr)
                print(f"Extraction complete! ({chunk_count} chunks received)", file=sys.stderr)
                
                # Validate JSON if using structured output
                if use_structured_output and output_format == 'json':
                    try:
                        policies = PoliticalPartyPolicies.model_validate_json(result_text)
                        print(f"✓ Validated: {len(policies.policies)} policies extracted", file=sys.stderr)
                        # Re-serialize for consistent formatting
                        result_text = policies.model_dump_json(indent=2)
                    except Exception as e:
                        print(f"⚠ Warning: JSON validation failed: {e}", file=sys.stderr)
                        # If validation fails with only 1 chunk, treat as incomplete and retry
                        if chunk_count == 1:
                            print(f"⚠ Only 1 chunk received with invalid JSON - likely incomplete response", file=sys.stderr)
                            raise ValueError("Incomplete JSON response - only 1 chunk received")
                
                # Success - break out of retry loop
                break
                
            except TimeoutError as e:
                print(f"\n✗ Timeout: {e}", file=sys.stderr)
                retry_count += 1
                if retry_count > max_retries:
                    print(f"\n✗ Failed after {max_retries} retries", file=sys.stderr)
                    raise
                # Continue to next retry attempt
                
            except ValueError as e:
                # Incomplete response
                print(f"\n✗ Incomplete response: {e}", file=sys.stderr)
                retry_count += 1
                if retry_count > max_retries:
                    print(f"\n✗ Failed after {max_retries} retries", file=sys.stderr)
                    raise
                # Continue to next retry attempt
                
            except Exception as e:
                print(f"\nError during generation: {e}", file=sys.stderr)
                retry_count += 1
                if retry_count > max_retries:
                    raise
                # Continue to next retry attempt
        
        # Save to file if specified
        if output_file:
            output_path = Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(result_text)
            print(f"Output saved to: {output_file}", file=sys.stderr)
        
        return result_text


def main():
    parser = argparse.ArgumentParser(
        description="Analyze PDF files using Google Gemini 3 Pro Preview",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Extract Thai political party policies to CSV
  analyze_pdf.py --pdf-path "พรรคเพื่อไทย.pdf" --output-format csv \\
    --instructions "Extract all policies into a table with columns: Category, Title, Details"
  
  # Extract specific pages to JSON
  analyze_pdf.py --pdf-path "document.pdf" --pages "1-10" --output-format json \\
    --output-file "output.json"
  
  # Batch process multiple PDFs
  for pdf in *.pdf; do
    analyze_pdf.py --pdf-path "$pdf" --output-file "$${pdf%.pdf}.txt"
  done
"""
    )
    
    parser.add_argument(
        '--pdf-path',
        required=True,
        help='Path to PDF file to analyze'
    )
    
    parser.add_argument(
        '--instructions',
        default='Extract all text content from this PDF document word by word.',
        help='Custom instructions for the extraction (default: extract all text)'
    )
    
    parser.add_argument(
        '--output-format',
        choices=['json', 'text'],
        default='json',
        help='Output format (default: json with structured output)'
    )
    
    parser.add_argument(
        '--pages',
        help='Page range to analyze (e.g., "1-5" or "1,3,5")'
    )
    
    parser.add_argument(
        '--output-file',
        help='Path to save output (default: print to stdout)'
    )
    
    parser.add_argument(
        '--no-structured-output',
        action='store_true',
        help='Disable Gemini structured output (use legacy text parsing)'
    )
    
    parser.add_argument(
        '--max-retries',
        type=int,
        default=2,
        help='Maximum retry attempts for stalled streams (default: 2)'
    )
    
    args = parser.parse_args()
    
    try:
        result = analyze_pdf_with_gemini(
            pdf_path=args.pdf_path,
            instructions=args.instructions,
            output_format=args.output_format,
            pages=args.pages,
            output_file=args.output_file,
            use_structured_output=not args.no_structured_output,
            max_retries=args.max_retries
        )
        
        # Print result to stdout (unless saved to file)
        if not args.output_file:
            print(result)
        
        # Flush LLMObs traces before exit
        if LLMOBS_ENABLED:
            LLMObs.flush()
            print("✓ LLMObs traces flushed", file=sys.stderr)
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        
        # Flush traces even on error
        if LLMOBS_ENABLED:
            LLMObs.flush()
        
        sys.exit(1)


if __name__ == "__main__":
    main()
