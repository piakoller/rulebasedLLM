#!/usr/bin/env python3
import json
import csv
from pathlib import Path

def main():
    json_path = Path("results/psma_benchmark.json")
    csv_path = Path("results/psma_comparison.csv")
    
    if not json_path.exists():
        print(f"Error: {json_path} not found.")
        return

    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    with open(csv_path, 'w', newline='', encoding='utf-8-sig') as f:
        # Using utf-8-sig so Excel recognizes the encoding automatically
        writer = csv.writer(f, dialect='excel')
        writer.writerow(['Index', 'Category', 'Question', 'Baseline Response', 'Agentic Response'])
        
        for row in data.get('rows', []):
            i = row.get('index', '')
            cat = row.get('category', '')
            q = row.get('question', '')
            base = row.get('baseline_response', '')
            agent = row.get('pipeline_response', {}).get('agent_response', '')
            
            writer.writerow([i, cat, q, base, agent])

    print(f"Successfully created CSV for Excel at: {csv_path}")

if __name__ == "__main__":
    main()
