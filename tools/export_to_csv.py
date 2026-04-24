#!/usr/bin/env python3
import json
import csv
import argparse
from pathlib import Path

def export_json_to_csv(json_path: Path, csv_path: Path):
    if not json_path.exists():
        print(f"Error: {json_path} not found.")
        return

    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Flatten results if needed
    results = data.get('results', []) if isinstance(data, dict) else data
    
    if not results:
        print("No results found in the JSON file.")
        return

    # Determine headers
    headers = ['Index', 'Category', 'Question', 'Thinking', 'Response', 'Confidence Score', 'Confidence Explanation']
    
    with open(csv_path, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f, dialect='excel')
        writer.writerow(headers)
        
        for item in results:
            if not isinstance(item, dict):
                continue
                
            idx = item.get('index', '')
            cat = item.get('category', '')
            q = item.get('question', '')
            
            agent_resp = item.get('agent_response', {})
            # Handle both direct string and nested object
            if isinstance(agent_resp, str):
                thinking = ""
                response = agent_resp
                conf_score = ""
                conf_expl = ""
            else:
                filled_slots = agent_resp.get('filled_slots', {})
                thinking = filled_slots.get('thinking', '')
                response = agent_resp.get('agent_response', '')
                conf_score = agent_resp.get('confidence_score', '')
                conf_expl = agent_resp.get('confidence_explanation', '')
            
            writer.writerow([idx, cat, q, thinking, response, conf_score, conf_expl])

    print(f"Successfully exported {len(results)} rows to: {csv_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Export pipeline JSON results to CSV")
    parser.add_argument("input", help="Path to input JSON results")
    parser.add_argument("--out", "-o", help="Path to output CSV (optional)")
    args = parser.parse_args()
    
    json_path = Path(args.input)
    csv_path = Path(args.out) if args.out else json_path.with_suffix('.csv')
    
    export_json_to_csv(json_path, csv_path)
