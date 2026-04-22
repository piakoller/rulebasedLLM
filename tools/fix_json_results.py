#!/usr/bin/env python3
import json
from pathlib import Path

def fix_results(json_path: Path):
    if not json_path.exists():
        print(f"Error: {json_path} not found.")
        return

    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    results = data.get('results', [])
    fixed_count = 0

    for item in results:
        agent_resp_block = item.get('agent_response', {})
        inner_content = agent_resp_block.get('agent_response', '')

        # Check if it looks like a stringified JSON
        if isinstance(inner_content, str) and inner_content.strip().startswith('{'):
            try:
                inner_json = json.loads(inner_content)
                if 'thinking' in inner_json and 'response' in inner_json:
                    # Fix the structure
                    thinking = inner_json['thinking']
                    # Convert list thinking to string if preferred, but dict[str, Any] supports list
                    if isinstance(thinking, list):
                        thinking = "\n".join(thinking)
                    
                    agent_resp_block['filled_slots']['thinking'] = thinking
                    agent_resp_block['agent_response'] = inner_json['response']
                    fixed_count += 1
                elif 'thinking' in inner_json:
                    # In some cases maybe only thinking exists or it's a different schema
                     agent_resp_block['filled_slots']['thinking'] = inner_json['thinking']
                     # If there's no 'response' key, maybe it's just 'agent_response'? 
                     # But the user specifically said "thinking in thinking and response in response"
                     fixed_count += 1
            except json.JSONDecodeError:
                continue

    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"Fixed {fixed_count} items in {json_path}")

if __name__ == "__main__":
    fix_results(Path("results/psma_fast_test.json"))
    fix_results(Path("results/psma_run_results_final.json"))
