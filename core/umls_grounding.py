"""UMLS grounding helpers.

Contains term extraction, translation helpers, and UMLS grounding with a simple
JSON cache. Intended to be the single source of truth for grounding used by
tests and the runtime pipeline.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import List

# Optional imports for improved NER and fuzzy matching
try:
    import spacy
    HAS_SPACY = True
except Exception:
    spacy = None
    HAS_SPACY = False

try:
    from rapidfuzz import fuzz
    HAS_RAPIDFUZZ = True
except Exception:
    fuzz = None
    HAS_RAPIDFUZZ = False

try:
    from .ontology_tool import verify_clinical_relationship
    UMLS_AVAILABLE = True
except Exception:
    # Fallback to top-level import for tests run from workspace root
    try:
        from ontology_tool import verify_clinical_relationship
        UMLS_AVAILABLE = True
    except Exception:
        UMLS_AVAILABLE = False

# Medical acronyms and abbreviations with English translations
MEDICAL_ACRONYMS = {
    "psma": "prostate specific membrane antigen",
    "car-t": "chimeric antigen receptor t-cell",
    "car": "chimeric antigen receptor",
    "psa": "prostate specific antigen",
    "ct": "computed tomography",
    "mrt": "magnetic resonance imaging",
    "mri": "magnetic resonance imaging",
    "pci": "percutaneous coronary intervention",
    "dna": "deoxyribonucleic acid",
    "rna": "ribonucleic acid",
    "hiv": "human immunodeficiency virus",
    "hcc": "hepatocellular carcinoma",
    "nsclc": "non-small-cell lung carcinoma",
    "sclc": "small-cell lung carcinoma",
    "cll": "chronic lymphocytic leukemia",
    "aml": "acute myeloid leukemia",
    "mm": "multiple myeloma",
    "ipi": "ipilimumab",
}

# German-to-English medical term translation map
GERMAN_TO_ENGLISH_MEDICAL = {
    "krebs": "cancer",
    "behandlung": "treatment",
    "therapie": "therapy",
    "nebenwirkung": "side effect",
    "symptom": "symptom",
    "diagnose": "diagnosis",
    "strahlentherapie": "radiation therapy",
    "chemotherapie": "chemotherapy",
    "immuntherapie": "immunotherapy",
    "prognose": "prognosis",
    "genesung": "recovery",
    "heilung": "healing",
    "medikament": "medication",
    "dosierung": "dosage",
    "klinisch": "clinical",
    "onkologie": "oncology",
    "bestrahlung": "radiation",
    "übelkeit": "nausea",
    "appetitlosigkeit": "loss of appetite",
    "haarausfall": "hair loss",
    "müdigkeit": "fatigue",
    "schmerz": "pain",
    "schmerzen": "pain",
    "fieber": "fever",
    "hautreaktion": "skin reaction",
    "blutbild": "blood count",
    "blutdruck": "blood pressure",
    "durchfall": "diarrhea",
    "verstopfung": "constipation",
    "gedächtnisverlust": "memory loss",
    "konzentrationsstörung": "concentration disorder",
}


def extract_medical_terms(text: str, language: str = "de", max_terms: int = 5) -> List[str]:
    """Extract concise candidate terms for UMLS grounding.

    Tries spaCy/scispaCy NER first (if installed) and falls back to
    rule-based heuristics. Optionally prioritizes candidates using
    fuzzy matching (rapidfuzz) against known medical keys.
    """
    STOPWORDS_DE = {
        "wie", "was", "ist", "sind", "werden", "wer", "wem", "mir", "mich",
        "ich", "du", "er", "sie", "es", "und", "oder", "im", "in", "auf",
        "der", "die", "das", "ein", "eine", "für", "fuer", "mit", "von",
        "zu", "den", "dem", "ist", "keine", "nicht", "haben", "hatte", "wurde",
    }

    extracted: List[str] = []

    # Try spaCy-based extraction for higher precision
    if HAS_SPACY:
        try:
            model_name = None
            if language and language.startswith("de"):
                for m in ("de_core_news_sm", "de_core_news_md"):
                    try:
                        nlp = spacy.load(m)
                        model_name = m
                        break
                    except Exception:
                        continue
            else:
                for m in ("en_core_sci_sm", "en_core_web_sm"):
                    try:
                        nlp = spacy.load(m)
                        model_name = m
                        break
                    except Exception:
                        continue

            if model_name:
                doc = nlp(text)
                for ent in doc.ents:
                    val = ent.text.strip()
                    if val and val.lower() not in STOPWORDS_DE and val not in extracted:
                        extracted.append(val)
                for np in getattr(doc, "noun_chunks", []):
                    val = np.text.strip()
                    if val and val.lower() not in STOPWORDS_DE and val not in extracted:
                        extracted.append(val)
        except Exception:
            extracted = []

    # Fallback to heuristics if NER not available or returned nothing
    if not extracted:
        text_clean = re.sub(r"[\n\r]+", " ", text)
        tokens = re.findall(r"\b[\w\-\/]+\b", text_clean)

        candidates: List[str] = []

        for tok in tokens:
            if re.fullmatch(r"[A-ZÄÖÜ]{2,}(?:-[A-ZÄÖÜ]+)?", tok):
                if tok not in candidates:
                    candidates.append(tok)

        text_lower = text.lower()
        for term in GERMAN_TO_ENGLISH_MEDICAL.keys():
            if term in text_lower and term not in candidates:
                candidates.append(term)

        for acr, expansion in MEDICAL_ACRONYMS.items():
            pattern = re.compile(re.escape(acr), re.IGNORECASE)
            if pattern.search(text) and acr.upper() not in candidates:
                found = None
                for tok in tokens:
                    if tok.lower() == acr:
                        found = tok if tok.isupper() else acr.upper()
                        break
                candidates.append(found or acr.upper())

        for tok in tokens:
            tok_lower = tok.lower()
            if tok_lower in STOPWORDS_DE:
                continue
            if len(tok_lower) < 3 and not re.fullmatch(r"[A-Z]{2,}", tok):
                continue
            if tok_lower.endswith("en") and tok_lower not in GERMAN_TO_ENGLISH_MEDICAL:
                continue
            if tok not in candidates:
                candidates.append(tok)

        extracted = []
        for term in candidates:
            t = term.strip()
            if not t:
                continue
            eng = GERMAN_TO_ENGLISH_MEDICAL.get(t.lower())
            if eng:
                extracted.append(t)
                extracted.append(eng)
                continue
            expansion = MEDICAL_ACRONYMS.get(t.lower())
            if expansion:
                extracted.append(t)
                extracted.append(expansion)
                continue
            extracted.append(t)

    # Optionally prioritize using fuzzy matching
    if HAS_RAPIDFUZZ and extracted:
        scored = []
        pool = list(GERMAN_TO_ENGLISH_MEDICAL.keys()) + list(MEDICAL_ACRONYMS.keys())
        for term in extracted:
            score = 0
            for known in pool:
                try:
                    s = fuzz.token_sort_ratio(term.lower(), known.lower())
                    if s > score:
                        score = s
                except Exception:
                    continue
            scored.append((score, term))
        scored.sort(reverse=True)
        prioritized = [t for _, t in scored]
    else:
        prioritized = extracted

    unique: List[str] = []
    for s in prioritized:
        if s not in unique:
            unique.append(s)
        if len(unique) >= max_terms:
            break

    return unique


def get_umls_grounding(question: str, language: str = "de") -> dict:
    """Get UMLS grounding for a question using verify_clinical_relationship.

    Returns a dict with grounding info and a formatted context string.
    """
    if not UMLS_AVAILABLE:
        return {
            "grounded": False,
            "context": "",
            "terms_verified": [],
            "all_search_results": [],
            "search_terms": []
        }

    medical_terms = extract_medical_terms(question, language=language)
    if not medical_terms:
        return {
            "grounded": False,
            "context": "",
            "terms_verified": [],
            "all_search_results": [],
            "search_terms": []
        }

    umls_context = []
    verified_terms = []
    all_search_results = []
    search_attempt = []

    cache_dir = Path(__file__).parent / ".cache"
    cache_dir.mkdir(exist_ok=True)
    cache_file = cache_dir / "umls_cache.json"
    try:
        if cache_file.exists():
            with open(cache_file, "r", encoding="utf-8") as cf:
                umls_cache = json.load(cf)
        else:
            umls_cache = {}
    except Exception:
        umls_cache = {}

    for term in medical_terms:
        try:
            search_attempt.append(term)
            term_key = term.lower()

            cached = umls_cache.get(term_key)
            if cached is not None:
                found = cached.get("found", False)
                cui = cached.get("cui")
                relationships_count = cached.get("relationships_count", 0)
                summary = cached.get("summary", "")
                error = cached.get("error")
            else:
                result = verify_clinical_relationship(term)
                found = bool(getattr(result, "found", False))
                cui = getattr(result, "cui", None)
                relationships_count = len(getattr(result, "relationships", []))
                summary = getattr(result, "summary", "") or ""
                error = None if found else getattr(result, "error", None)

                try:
                    umls_cache[term_key] = {
                        "found": found,
                        "cui": cui,
                        "relationships_count": relationships_count,
                        "summary": summary,
                        "error": error,
                    }
                except Exception:
                    pass

            is_translation = term in [GERMAN_TO_ENGLISH_MEDICAL.get(t.lower()) 
                                      for t in medical_terms if t.lower() in GERMAN_TO_ENGLISH_MEDICAL]

            search_record = {
                "term": term,
                "found": found,
                "cui": cui,
                "is_translated": is_translation,
                "relationships_count": relationships_count,
                "error": error if not found else None
            }
            all_search_results.append(search_record)

            if found:
                verified_terms.append({
                    "term": term,
                    "cui": cui,
                    "relationships_found": relationships_count,
                    "is_translated": is_translation,
                    "summary": summary[:200]
                })
                umls_context.append(f"• {term} (CUI: {cui}): {summary[:150]}")

        except Exception as e:
            all_search_results.append({
                "term": term,
                "found": False,
                "cui": None,
                "is_translated": False,
                "relationships_count": 0,
                "error": str(e)
            })

    try:
        with open(cache_file, "w", encoding="utf-8") as cf:
            json.dump(umls_cache, cf, ensure_ascii=False, indent=2)
    except Exception:
        pass

    grounded_text = "\n".join(umls_context) if umls_context else ""

    return {
        "grounded": len(verified_terms) > 0,
        "context": grounded_text,
        "terms_verified": verified_terms,
        "all_search_results": all_search_results,
        "num_verified": len(verified_terms),
        "search_terms": search_attempt,
        "num_searches": len(search_attempt),
        "hybrid_approach": "German + English translations"
    }
