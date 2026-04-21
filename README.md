# Empathic LLM Pipeline — End-to-End Guide

This repository implements an empathy-aware clinical conversational pipeline with ontology and optional vector retrieval, a DPO study UI for collecting pairwise preferences, and analysis/export utilities to produce SFT/DPO training data.

This README explains the full pipeline from a clean clone through collecting preferences, analyzing results, and producing training-ready datasets.

## What this repo contains (high level)

- `core/` — agent orchestration, UMLS/ontology helpers, grounding and framing logic.
- `tools/` — ingestion, analysis, benchmarks, utilities for the pipeline.
- `ui/study_ui.py` — Streamlit-based UI for collecting human preferences (paired A/B).
- `data/` — sample questions, framing prompt, and de-identified context used for tests/examples.
- `tests/` — automation and pipeline runners used for batch experiments.

Always refer to the files under `core/` and `tools/` for implementation details.

## Quick setup

1. Clone and enter the repository:

```bash
git clone <repo-url>
cd rulebasedLLM
```

2. Install Python dependencies (recommend using a venv):

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements_study.txt
```

3. Optional: install `git-filter-repo` if you plan to purge large files from history:

```bash
pip install git-filter-repo
```

## Environment variables and runtime config

Set the following optionally in your shell or an env file:

- `OLLAMA_URL` — endpoint for local Ollama (if used).
- `OLLAMA_MODEL` — model name to use for generation.
- `GRAPH_RAG_DOCUMENT_ROOTS` — comma-separated folders to scan for documents (default: `data/,docs/,context/`).

The system will run with mock grounding for tests if real UMLS credentials are not available.

## Full pipeline (step-by-step)

Below are the commands and explanations for a full end-to-end run.

1) Prepare documents and sample inputs

- Put any PDFs / `.md` / `.txt` you want indexed into one of the document roots (for example `data/context` or `docs/`).
- If you want to use the sample clinical questions provided for batch runs, they are in `data/sample_questions.json`.

2) (Optional) Ingest PDFs into a local vector store

If you prefer vector-based retrieval, run the ingestion tool which produces embeddings and metadata in `data/vector_store`:

```bash
python tools/ingest_pdfs_vectorstore.py --docs docs/ --out data/vector_store
```

Notes:
- Vector stores are optional. The pipeline supports ontology/RAG-first modes without vectors.
- If you accidentally commit vector files, see "Removing large vector stores from git" below.

3) Build the document-driven ontology / RAG index

Run the ontology/RAG builder which extracts entities/relations and prepares the grounding index used by the agent:

```bash
python core/ontology_rag.py --build
```

This step may call your configured LLM for structured extraction; it can be executed once and the result cached.

4) Run the agentic or interactive chat loop (developer/debug)

Start the agent orchestrator to test interactive behavior. The agent uses grounding, empathy framing, and tool execution.

```bash
python core/agent_engine.py --interactive
```

Notes:
- The exact CLI flags vary by script; use `--help` on each `core/` script for details.

5) Run the automated empathy pipeline over a questions set (batch run)

Use the pipeline runner to generate pairs or single responses for a question set. The repo includes a pipeline runner under `tests/` used in experiments:

```bash
python tests/run_empathy_pipeline.py --questions data/psma_sample_questions.json --out results/psma_run_results.json
```

This creates a result JSON (or results folder) containing original/revised responses, grounding metadata, and scoring fields used later by analysis tools.

6) Collect human preferences with the Streamlit UI

Start the UI to collect preferences interactively (useful for small-scale studies or pilot runs):

```bash
streamlit run ui/study_ui.py
```

Workflow in the UI:
- Generate paired responses for a question.
- Present randomized A/B ordering to avoid position bias.
- The UI app appends logged preferences to an append-only `study_data.jsonl` (or configured path).

7) Analyze preferences and generate diagnostics

After collecting preferences (either from the UI or via a human evaluation run), run analysis to compute position bias, preference distributions, and quality metrics:

```bash
python tools/analyze_study_data.py --in study_data.jsonl --out results/analysis.json
```

Example benchmarking tools:

```bash
python tools/benchmark_psma.py
python tools/psma_diagnostics.py
```

8) Convert preferences to training datasets (SFT / DPO)

Use the prepare script to generate training-ready JSONL files for trl.DPOTrainer and standard SFT:

```bash
python tools/prepare_dpo_data.py --in study_data.jsonl --out-dir results/
```

Outputs:
- `dpo_training_data.jsonl` — chosen/rejected pairs for DPO training
- `sft_training_data.jsonl` — single-best responses for SFT training
- `preference_training_data.jsonl` — full metadata for auditing

9) Tests and CI

Run unit/integration tests locally with pytest or the top-level test scripts:

```bash
pytest tests/ -q
# or run individual scripts used in prior experiments
python tests/test_empathy_pipeline.py
```

## Removing large vector stores from git

The repository ignores `data/vector_store/` and `data/vector_store_psma/` in `.gitignore`.

If those folders were already committed you can either stop tracking them going forward or purge them from history:

- Stop tracking (safe, preserves history):

```bash
git rm -r --cached data/vector_store data/vector_store_psma
git commit -m "Stop tracking vector store binaries"
git push
```

- Purge from history (rewrites history; collaborate before force-pushing):

```bash
git filter-repo --invert-paths --path data/vector_store --path data/vector_store_psma
git reflog expire --expire=now --all
git gc --prune=now --aggressive
git push origin --force --all
git push origin --force --tags
```

Warning: history rewrites require all collaborators to re-clone the repository.

## Developer notes

- Many scripts accept `--help` with up-to-date flags; use that to adapt paths and outputs.
- The pipeline is modular: you can run grounding-only (ontology), vector-only, or both depending on available models and resources.
- For reproducible experiments, pin dependencies and record the `OLLAMA_MODEL` and extraction model names used during graph construction.

## Example quick commands (summary)

```bash
# clone + install
git clone <repo-url> && cd rulebasedLLM
pip install -r requirements_study.txt

# optional: ingest vectors
python tools/ingest_pdfs_vectorstore.py --docs docs/ --out data/vector_store

# build ontology / graph
python core/ontology_rag.py --build

# run batch pipeline over sample questions
python tests/run_empathy_pipeline.py --questions data/psma_sample_questions.json --out results/psma_run_results.json

# analyze and prepare training data
python tools/analyze_study_data.py --in results/psma_run_results.json
python tools/prepare_dpo_data.py --in study_data.jsonl --out-dir results/

# start UI for human preferences
streamlit run ui/study_ui.py
```

---

If you want, I can also:
- add concrete CLI flag docs for each `core/` and `tools/` script, or
- generate a minimal `Makefile` or `scripts/` wrappers to standardize runs.

Contact: open an issue or edit `docs/QUICKSTART.md` to add project-specific notes.
