#!/usr/bin/env python3
"""
JSON to CSV Converter
Converts structured JSON data to CSV format with flexible options

Features:
- Custom delimiters (pipe, comma, tab)
- Newline preservation for spreadsheet import
- Nested JSON field extraction
- Batch processing
- Metadata columns
"""

import argparse
import csv
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union


def add_newlines_to_numbered_items(text: str) -> str:
    """
    Add \\n before Thai and Arabic numbered items for better readability
    Also converts actual newlines to \\n for CSV compatibility
    
    Converts: "๑) Item one ๒) Item two" 
    To: "๑) Item one\\n๒) Item two"
    """
    if not text or not isinstance(text, str):
        return text
    
    # First, convert actual newlines to \\n for CSV compatibility
    text = text.replace('\n', '\\n')
    text = text.replace('\r', '')  # Remove carriage returns
    
    # Thai numerals: ๑) ๒) ๓) ๔) ๕) ๖) ๗) ๘) ๙)
    for thai_num in ['๑)', '๒)', '๓)', '๔)', '๕)', '๖)', '๗)', '๘)', '๙)']:
        # Add \n before each occurrence (except at start)
        text = re.sub(f'(?<!^)\\s*({re.escape(thai_num)})', r'\\n\1', text)
    
    # Arabic numerals: 1) 2) 3) etc
    text = re.sub(r'(?<!^)\s+(\d+\))', r'\\n\1', text)
    
    return text


def get_nested_value(data: Dict, path: str, default: Any = "") -> Any:
    """
    Get value from nested dictionary using dot notation
    
    Example: get_nested_value(data, "user.address.city")
    """
    keys = path.split('.')
    value = data
    
    for key in keys:
        if isinstance(value, dict):
            value = value.get(key, default)
        else:
            return default
    
    return value if value is not None else default


def extract_fields(data: Dict, fields: Optional[List[str]] = None) -> Dict:
    """
    Extract specified fields from JSON data
    
    Args:
        data: JSON data dictionary
        fields: List of field paths (e.g., ["name", "address.city"])
    
    Returns:
        Dictionary with extracted fields
    """
    if fields is None:
        return data
    
    result = {}
    for field in fields:
        if '.' in field:
            # Nested field
            result[field] = get_nested_value(data, field)
        else:
            # Top-level field
            result[field] = data.get(field, "")
    
    return result


def json_to_csv(
    json_file: str,
    output_file: str,
    delimiter: str = '|',
    preserve_newlines: bool = True,
    fields: Optional[List[str]] = None,
    add_metadata: bool = False,
    no_header: bool = False,
    root_key: Optional[str] = None
) -> None:
    """
    Convert JSON file to CSV
    
    Args:
        json_file: Path to input JSON file
        output_file: Path to output CSV file
        delimiter: CSV delimiter character
        preserve_newlines: Convert newlines to \\n
        fields: List of fields to extract (None = all fields)
        add_metadata: Add source file and timestamp columns
        no_header: Skip CSV header row
        root_key: JSON key containing array of records
    """
    
    # Load JSON
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Extract records array
    if root_key:
        records = data.get(root_key, [])
    elif isinstance(data, list):
        records = data
    elif isinstance(data, dict):
        # Try common keys
        for key in ['items', 'data', 'records', 'policies', 'results']:
            if key in data and isinstance(data[key], list):
                records = data[key]
                break
        else:
            # Use the first list value found
            for value in data.values():
                if isinstance(value, list):
                    records = value
                    break
            else:
                raise ValueError("No array found in JSON. Specify --root-key")
    else:
        raise ValueError("Invalid JSON structure")
    
    if not records:
        print(f"Warning: No records found in {json_file}", file=sys.stderr)
        return
    
    # Determine fields
    if fields is None:
        # Use all fields from first record
        if records:
            fields = list(records[0].keys())
    
    # Add metadata fields if requested
    if add_metadata:
        metadata_fields = ['_source_file', '_timestamp', '_row_number']
        fields = metadata_fields + fields
    
    # Write CSV
    with open(output_file, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(
            f,
            fieldnames=fields,
            delimiter=delimiter,
            quoting=csv.QUOTE_MINIMAL
        )
        
        # Write header
        if not no_header:
            writer.writeheader()
        
        # Write records
        for idx, record in enumerate(records, 1):
            row = {}
            
            # Add metadata
            if add_metadata:
                row['_source_file'] = Path(json_file).name
                row['_timestamp'] = datetime.now().isoformat()
                row['_row_number'] = idx
            
            # Extract fields
            for field in fields:
                if field.startswith('_'):
                    continue  # Skip metadata fields (already added)
                
                value = get_nested_value(record, field)
                
                # Convert to string
                if isinstance(value, (dict, list)):
                    value = json.dumps(value, ensure_ascii=False)
                elif value is None:
                    value = ""
                else:
                    value = str(value)
                
                # Preserve newlines as \n
                if preserve_newlines:
                    value = add_newlines_to_numbered_items(value)
                
                row[field] = value
            
            writer.writerow(row)
    
    print(f"✓ Converted {len(records)} records to {output_file}", file=sys.stderr)


def batch_convert(
    batch_dir: str,
    output_dir: Optional[str] = None,
    output_file: Optional[str] = None,
    delimiter: str = '|',
    preserve_newlines: bool = True,
    fields: Optional[List[str]] = None,
    add_metadata: bool = False,
    no_header: bool = False,
    root_key: Optional[str] = None
) -> None:
    """
    Batch convert multiple JSON files to CSV
    
    Args:
        batch_dir: Directory containing JSON files
        output_dir: Directory for individual CSV files (if not consolidating)
        output_file: Single consolidated CSV file (if consolidating)
        delimiter: CSV delimiter
        preserve_newlines: Convert newlines to \\n
        fields: List of fields to extract
        add_metadata: Add source file and timestamp columns
        no_header: Skip CSV header row
        root_key: JSON key containing array of records
    """
    
    batch_path = Path(batch_dir)
    if not batch_path.exists():
        raise FileNotFoundError(f"Batch directory not found: {batch_dir}")
    
    json_files = sorted(batch_path.glob("*.json"))
    
    if not json_files:
        print(f"No JSON files found in {batch_dir}", file=sys.stderr)
        return
    
    print(f"Found {len(json_files)} JSON files", file=sys.stderr)
    
    if output_file:
        # Consolidate mode
        consolidate_json_to_csv(
            json_files=json_files,
            output_file=output_file,
            delimiter=delimiter,
            preserve_newlines=preserve_newlines,
            fields=fields,
            add_metadata=True,  # Force metadata for consolidation
            no_header=no_header,
            root_key=root_key
        )
    elif output_dir:
        # Individual files mode
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        for json_file in json_files:
            csv_file = output_path / f"{json_file.stem}.csv"
            json_to_csv(
                json_file=str(json_file),
                output_file=str(csv_file),
                delimiter=delimiter,
                preserve_newlines=preserve_newlines,
                fields=fields,
                add_metadata=add_metadata,
                no_header=no_header,
                root_key=root_key
            )
    else:
        raise ValueError("Either --output-dir or --output-file required for batch mode")


def consolidate_json_to_csv(
    json_files: List[Path],
    output_file: str,
    delimiter: str = '|',
    preserve_newlines: bool = True,
    fields: Optional[List[str]] = None,
    add_metadata: bool = True,
    no_header: bool = False,
    root_key: Optional[str] = None
) -> None:
    """
    Consolidate multiple JSON files into a single CSV
    """
    
    all_records = []
    
    # Collect all records
    for json_file in json_files:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Extract records
        if root_key:
            records = data.get(root_key, [])
        elif isinstance(data, list):
            records = data
        elif isinstance(data, dict):
            for key in ['items', 'data', 'records', 'policies', 'results']:
                if key in data and isinstance(data[key], list):
                    records = data[key]
                    break
            else:
                for value in data.values():
                    if isinstance(value, list):
                        records = value
                        break
                else:
                    continue
        else:
            continue
        
        # Add source file to each record
        for record in records:
            if add_metadata:
                record['_source_file'] = json_file.name
        
        all_records.extend(records)
    
    if not all_records:
        print("No records found in any JSON files", file=sys.stderr)
        return
    
    # Determine fields
    if fields is None:
        # Collect all unique fields
        all_fields = set()
        for record in all_records:
            all_fields.update(record.keys())
        fields = sorted(all_fields)
    
    # Add metadata fields
    if add_metadata:
        metadata_fields = ['_source_file', '_timestamp', '_row_number']
        fields = [f for f in metadata_fields if f in fields or f == '_timestamp' or f == '_row_number'] + \
                 [f for f in fields if not f.startswith('_')]
    
    # Write consolidated CSV
    with open(output_file, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(
            f,
            fieldnames=fields,
            delimiter=delimiter,
            quoting=csv.QUOTE_MINIMAL
        )
        
        if not no_header:
            writer.writeheader()
        
        for idx, record in enumerate(all_records, 1):
            row = {}
            
            if add_metadata:
                row['_timestamp'] = datetime.now().isoformat()
                row['_row_number'] = idx
            
            for field in fields:
                if field in ['_timestamp', '_row_number']:
                    continue
                
                value = record.get(field, "")
                
                if isinstance(value, (dict, list)):
                    value = json.dumps(value, ensure_ascii=False)
                elif value is None:
                    value = ""
                else:
                    value = str(value)
                
                if preserve_newlines:
                    value = add_newlines_to_numbered_items(value)
                
                row[field] = value
            
            writer.writerow(row)
    
    print(f"✓ Consolidated {len(all_records)} records from {len(json_files)} files to {output_file}", 
          file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(
        description="Convert JSON data to CSV format",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic conversion
  python json_to_csv.py --json-file data.json --output-file data.csv
  
  # Pipe-delimited with newline preservation
  python json_to_csv.py --json-file data.json --output-file data.csv \\
    --delimiter "|" --preserve-newlines
  
  # Extract specific fields
  python json_to_csv.py --json-file data.json --output-file data.csv \\
    --fields "name,age,address.city"
  
  # Batch convert directory
  python json_to_csv.py --batch-dir json_files/ --output-dir csv_files/ \\
    --delimiter "|" --preserve-newlines
  
  # Consolidate multiple JSON files
  python json_to_csv.py --batch-dir json_files/ --output-file all_data.csv \\
    --delimiter "|" --preserve-newlines --add-metadata
"""
    )
    
    # Input/output
    parser.add_argument('--json-file', help='Input JSON file')
    parser.add_argument('--output-file', help='Output CSV file')
    parser.add_argument('--batch-dir', help='Directory with JSON files (batch mode)')
    parser.add_argument('--output-dir', help='Output directory for batch mode')
    
    # Options
    parser.add_argument('--delimiter', default='|', 
                       help='CSV delimiter (default: |)')
    parser.add_argument('--preserve-newlines', action='store_true',
                       help='Convert newlines to \\n for spreadsheet import')
    parser.add_argument('--fields', 
                       help='Comma-separated list of fields to extract')
    parser.add_argument('--add-metadata', action='store_true',
                       help='Add metadata columns (source file, timestamp)')
    parser.add_argument('--no-header', action='store_true',
                       help='Skip CSV header row')
    parser.add_argument('--root-key',
                       help='JSON key containing array of records')
    
    args = parser.parse_args()
    
    # Parse fields
    fields = None
    if args.fields:
        fields = [f.strip() for f in args.fields.split(',')]
    
    try:
        if args.batch_dir:
            # Batch mode
            batch_convert(
                batch_dir=args.batch_dir,
                output_dir=args.output_dir,
                output_file=args.output_file,
                delimiter=args.delimiter,
                preserve_newlines=args.preserve_newlines,
                fields=fields,
                add_metadata=args.add_metadata,
                no_header=args.no_header,
                root_key=args.root_key
            )
        elif args.json_file and args.output_file:
            # Single file mode
            json_to_csv(
                json_file=args.json_file,
                output_file=args.output_file,
                delimiter=args.delimiter,
                preserve_newlines=args.preserve_newlines,
                fields=fields,
                add_metadata=args.add_metadata,
                no_header=args.no_header,
                root_key=args.root_key
            )
        else:
            parser.error("Either --json-file + --output-file OR --batch-dir required")
    
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
