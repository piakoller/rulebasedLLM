#!/usr/bin/env python3
import json
import csv
from pathlib import Path

def main():
    agent_path = Path("results/psma_27b_verify.json")
    benchmark_path = Path("results/psma_benchmark.json")
    out_csv = Path("results/psma_27b_vs_baseline.csv")

    # Load agent results
    if not agent_path.exists():
        print(f"Error: {agent_path} not found.")
        return
    with open(agent_path, 'r', encoding='utf-8') as f:
        agent_data = json.load(f)
    agent_results = agent_data.get('results', [])

    # Load baseline from benchmark
    baseline_map = {}
    if benchmark_path.exists():
        with open(benchmark_path, 'r', encoding='utf-8') as f:
            bm_data = json.load(f)
            for row in bm_data.get('rows', []):
                q = row.get('question', '')
                if q:
                    baseline_map[q] = row.get('baseline_response', '')

    # Write CSV
    headers = [
        'Index', 
        'Category', 
        'Question', 
        'Baseline (Standard LLM)', 
        'Agentic Thinking (NURSE/Dual-Pillar)', 
        'Agentic Response (Final)'
    ]

    with open(out_csv, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f, dialect='excel')
        writer.writerow(headers)
        
        for item in agent_results:
            idx = item.get('index', '')
            cat = item.get('category', '')
            q = item.get('question', '')
            base = baseline_map.get(q, 'N/A')
            
            agent_resp_obj = item.get('agent_response', {})
            thinking = agent_resp_obj.get('filled_slots', {}).get('thinking', '')
            response = agent_resp_obj.get('agent_response', '')
            
            writer.writerow([idx, cat, q, base, thinking, response])

    print(f"Successfully created comparison CSV at: {out_csv}")

if __name__ == "__main__":
    main()
