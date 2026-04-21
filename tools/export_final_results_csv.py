#!/usr/bin/env python3
import json
import csv
from pathlib import Path

def main():
    benchmark_path = Path("results/psma_benchmark.json")
    final_results_path = Path("results/psma_run_results_final.json")
    csv_path = Path("results/psma_final_comparison.csv")
    
    # Load baselines mapping question -> baseline_response
    baselines = {}
    if benchmark_path.exists():
        with open(benchmark_path, 'r', encoding='utf-8') as f:
            bm_data = json.load(f)
            for row in bm_data.get('rows', []):
                q = row.get('question', '')
                if q:
                    baselines[q] = row.get('baseline_response', '')

    # Load final results
    if not final_results_path.exists():
        print(f"Error: {final_results_path} not found.")
        return

    with open(final_results_path, 'r', encoding='utf-8') as f:
        final_data = json.load(f)

    # Write CSV
    with open(csv_path, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f, dialect='excel')
        writer.writerow([
            'Index', 'Category', 'Question', 
            'Baseline Response (Standard LLM)', 
            'Agentic Thinking (Dual-Pillar)',
            'Agentic Response (Dual-Pillar Final)'
        ])
        
        items = final_data.get('results', []) if isinstance(final_data, dict) else final_data
        for item in items:
            if not isinstance(item, dict):
                continue
            i = item.get('index', '')
            cat = item.get('category', '')
            q = item.get('question', '')
            base = baselines.get(q, 'N/A')
            
            agent_resp_block = item.get('agent_response', {})
            filled_slots = agent_resp_block.get('filled_slots', {})
            thinking = filled_slots.get('thinking', '')
            agent_response = agent_resp_block.get('agent_response', '')
            
            writer.writerow([i, cat, q, base, thinking, agent_response])

    print(f"Successfully created Final Comparison CSV at: {csv_path}")

if __name__ == "__main__":
    main()
