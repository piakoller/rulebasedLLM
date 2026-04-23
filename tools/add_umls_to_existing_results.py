#!/usr/bin/env python3
"""Attach UMLS verification results to an existing pipeline output.

Reads `results/psma_run_results.json` (or `results/psma_benchmark.json`),
verifies extracted medical terms via `core.ontology_tool.verify_multiple_relationships`,
and writes `results/psma_run_with_umls.json` with added `umls_verification` per row.
"""
import json
from pathlib import Path
import sys

repo_root = Path(__file__).parent.parent
sys.path.insert(0, str(repo_root))
sys.path.insert(0, str(repo_root / "core"))

from core.umls_grounding import extract_medical_terms
import core.ontology_tool as ontology_tool

IN = Path("results/psma_run_results.json")
OUT = Path("results/psma_run_with_umls.json")


def main():
    if not IN.exists():
        print(f"Input not found: {IN}")
        return

    data = json.loads(IN.read_text(encoding="utf-8"))
    # Support files with top-level 'rows' or 'results' lists
    rows = data.get("rows") or data.get("results") or data
    out_rows = []

    for r in rows:
        q = r.get("question") or r.get("prompt") or r.get("user_message")
        if not q:
            out_rows.append(r)
            continue

        terms = extract_medical_terms(q, language="de", max_terms=6)
        try:
            verif = ontology_tool.verify_multiple_relationships(terms)
            r["umls_verification"] = {t: {"found": bool(res.found), "cui": res.cui, "summary": res.summary} for t, res in verif.items()}
        except Exception as e:
            r["umls_verification_error"] = str(e)

        out_rows.append(r)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8") as fh:
        json.dump({"source": str(IN), "rows": out_rows}, fh, ensure_ascii=False, indent=2)
    print(f"Wrote augmented results to {OUT}")


if __name__ == "__main__":
    main()
