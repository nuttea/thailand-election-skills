#!/usr/bin/env python3
"""
Send Thai Political Party Policy data to Datadog as logs
Each CSV row becomes a log entry with tags and attributes
"""

import csv
import json
import os
import sys
import requests
from datetime import datetime
from pathlib import Path

# Load environment variables
def load_env():
    # Try multiple locations
    possible_paths = [
        Path(__file__).parent.parent.parent.parent.parent / ".env",  # Project root
        Path.cwd() / ".env",  # Current directory
    ]
    
    for env_path in possible_paths:
        if env_path.exists():
            with open(env_path) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        value = value.strip().strip('"').strip("'").replace('export ', '')
                        key = key.strip().replace('export ', '')
                        os.environ[key] = value
            print(f"Loaded environment from: {env_path}", file=sys.stderr)
            return
    
    print("Warning: .env file not found", file=sys.stderr)

load_env()

# Configuration
DD_API_KEY = os.environ.get('DD_API_KEY')
DD_SITE = 'datadoghq.com'  # or datadoghq.eu, us3.datadoghq.com, etc.
DD_LOGS_ENDPOINT = f'https://http-intake.logs.{DD_SITE}/api/v2/logs'

if not DD_API_KEY:
    print("Error: DD_API_KEY not found in environment", file=sys.stderr)
    sys.exit(1)

# Generate version tag from current date-time
VERSION = datetime.now().strftime('%Y%m%d-%H%M')

# Tags
TAGS = {
    'source': 'custom-log',
    'version': VERSION,
    'service': 'th-election-policy',
    'env': 'prod'
}

def send_log_to_datadog(log_entry, batch_mode=False):
    """Send a single log entry to Datadog"""
    
    headers = {
        'DD-API-KEY': DD_API_KEY,
        'Content-Type': 'application/json'
    }
    
    # Build log payload
    payload = {
        'ddsource': TAGS['source'],
        'ddtags': ','.join([f'{k}:{v}' for k, v in TAGS.items()]),
        'hostname': 'policy-extractor',
        'service': TAGS['service'],
        'message': log_entry.get('policy_name', 'Policy'),
        'attributes': log_entry
    }
    
    if batch_mode:
        return payload
    
    try:
        response = requests.post(
            DD_LOGS_ENDPOINT,
            headers=headers,
            json=payload,
            timeout=10
        )
        response.raise_for_status()
        return True
    except Exception as e:
        print(f"Error sending log: {e}", file=sys.stderr)
        return False

def send_logs_batch(log_entries):
    """Send multiple logs in a single request"""
    
    headers = {
        'DD-API-KEY': DD_API_KEY,
        'Content-Type': 'application/json'
    }
    
    # Build batch payload
    payloads = []
    for entry in log_entries:
        payload = {
            'ddsource': TAGS['source'],
            'ddtags': ','.join([f'{k}:{v}' for k, v in TAGS.items()]),
            'hostname': 'policy-extractor',
            'service': TAGS['service'],
            'message': entry.get('policy_name', 'Policy'),
            'attributes': entry
        }
        payloads.append(payload)
    
    try:
        response = requests.post(
            DD_LOGS_ENDPOINT,
            headers=headers,
            json=payloads,
            timeout=30
        )
        response.raise_for_status()
        return True
    except Exception as e:
        print(f"Error sending batch: {e}", file=sys.stderr)
        return False

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Send CSV data to Datadog as logs')
    parser.add_argument('--csv-file', required=True, help='CSV file to send')
    parser.add_argument('--batch-size', type=int, default=100, help='Batch size (default: 100)')
    parser.add_argument('--dry-run', action='store_true', help='Print logs without sending')
    
    args = parser.parse_args()
    
    # Read CSV
    print(f"Reading CSV: {args.csv_file}")
    with open(args.csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter='|')
        rows = list(reader)
    
    print(f"Found {len(rows)} policies to send")
    print(f"Tags: {TAGS}")
    print()
    
    if args.dry_run:
        print("DRY RUN - Showing first 3 log entries:")
        for i, row in enumerate(rows[:3], 1):
            print(f"\n--- Log {i} ---")
            print(json.dumps({
                'tags': TAGS,
                'message': row.get('policy_name', 'Policy'),
                'attributes': row
            }, indent=2, ensure_ascii=False))
        print(f"\n... and {len(rows) - 3} more")
        return
    
    # Send in batches
    total_sent = 0
    total_failed = 0
    
    for i in range(0, len(rows), args.batch_size):
        batch = rows[i:i + args.batch_size]
        batch_num = i // args.batch_size + 1
        total_batches = (len(rows) + args.batch_size - 1) // args.batch_size
        
        print(f"Sending batch {batch_num}/{total_batches} ({len(batch)} logs)...", end=' ')
        
        if send_logs_batch(batch):
            total_sent += len(batch)
            print(f"✓ Sent")
        else:
            total_failed += len(batch)
            print(f"✗ Failed")
    
    print()
    print(f"Results:")
    print(f"  Sent: {total_sent}")
    print(f"  Failed: {total_failed}")
    print(f"  Success rate: {total_sent/len(rows)*100:.1f}%")
    print()
    
    if total_sent > 0:
        print(f"✅ Logs sent to Datadog!")
        print(f"   Query in Datadog: source:custom-log service:th-election-policy")
        print(f"   Version tag: version:{VERSION}")

if __name__ == '__main__':
    main()
