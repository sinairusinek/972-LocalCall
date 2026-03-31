"""
Precompute analysis results from the full corpus TSV.

Reads the corpus locally (article text stays on your machine), runs the full
keyword analysis, and writes two public CSV files into data/ that the deployed
app loads directly — no upload needed.

Usage (from streamlit_app/):
    python scripts/precompute.py /path/to/corpus.tsv
    python scripts/precompute.py /path/to/corpus.tsv --semantic-flag
    python scripts/precompute.py /path/to/corpus.tsv --semantic-apply

Modes:
    (default)          Run full analysis and write precomputed_results.csv
    --semantic-flag    Run semantic scoring; write semantic_candidates.csv
                       (does NOT update precomputed_results.csv)
    --semantic-apply   Read semantic_decisions.csv; re-run analysis discarding
                       rejected matches; write updated precomputed_results.csv

Output:
    data/precomputed_results.csv  — one row per article, metadata + term counts
    data/corpus_meta.csv          — metadata only (url, title, date, author, source)
    data/semantic_candidates.csv  — flagged matches for review (--semantic-flag)
    data/semantic_decisions.csv   — your decisions exported from the review app

Both results files contain NO article text and are safe to commit and deploy.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import pandas as pd

# Make services importable when running from streamlit_app/
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.analysis import (
    META_COLUMNS,
    TEXT_COLUMNS,
    AnalysisOptions,
    CountMode,
    SearchMode,
    analyze_corpus,
    load_expressions,
    load_name_mapping,
    results_to_dataframe,
    split_corpus_columns,
)

DATA_DIR = Path(__file__).parent.parent / "data"
RESULTS_PATH = DATA_DIR / "precomputed_results.csv"
META_PATH = DATA_DIR / "corpus_meta.csv"
CANDIDATES_PATH = DATA_DIR / "semantic_candidates.csv"
DECISIONS_PATH = DATA_DIR / "semantic_decisions.csv"

# Corpus-specific column names (adapt if your TSV uses different headers)
DATE_COLUMN = "Date"
AUTHOR_COLUMN = "Authors(Temp)"


def _load_corpus(corpus_path: Path) -> pd.DataFrame:
    print(f"Loading corpus: {corpus_path.name}")
    df = pd.read_csv(
        corpus_path,
        sep="\t",
        dtype=str,
        keep_default_na=False,
        on_bad_lines="skip",
    )
    print(f"  {len(df):,} rows × {len(df.columns)} columns")
    return df


def _build_options(df: pd.DataFrame, text_cols: list, meta_cols: list) -> tuple:
    date_col = DATE_COLUMN if DATE_COLUMN in df.columns else None
    author_col = AUTHOR_COLUMN if AUTHOR_COLUMN in df.columns else None
    if not date_col:
        print("  WARNING: date column not found — timeline features will be unavailable")
    if not author_col:
        print("  WARNING: author column not found — author features will be unavailable")
    options = AnalysisOptions(
        selected_columns=text_cols if text_cols else meta_cols,
        include_english=True,
        include_hebrew=True,
        mode=SearchMode.CONCATENATED,
        count_mode=CountMode.HITS,
        date_column=date_col,
        author_column=author_col,
    )
    return options, date_col, author_col


def _run_analysis(df: pd.DataFrame, expressions, options, name_mapping,
                  t0: float, return_spans: bool = False) -> list:
    CHUNK = 2000
    all_results = []
    total = len(df)
    for start in range(0, total, CHUNK):
        chunk_df = df.iloc[start:start + CHUNK]
        chunk_results = analyze_corpus(chunk_df, expressions, options, name_mapping,
                                       return_spans=return_spans)
        all_results.extend(chunk_results)
        pct = min(start + CHUNK, total) / total * 100
        elapsed = time.time() - t0
        print(f"  {min(start+CHUNK, total):>6,}/{total:,}  {pct:5.1f}%  {elapsed:5.1f}s", end="\r")
    print()
    return all_results


def _write_results(all_results, expressions, results_df=None):
    if results_df is None:
        results_df = results_to_dataframe(all_results, public=True)

    matched = (results_df["_total_matches"].astype(int) > 0).sum()
    print(f"  {matched:,} / {len(results_df):,} rows have at least one term match")

    results_df.to_csv(RESULTS_PATH, index=False, encoding="utf-8")
    size_mb = RESULTS_PATH.stat().st_size / 1_000_000
    print(f"  Written: {RESULTS_PATH.name}  ({size_mb:.1f} MB,  {len(results_df):,} rows)")

    meta_cols_present = [c for c in results_df.columns
                         if c in META_COLUMNS or not c.startswith("_")]
    meta_cols_present = [c for c in meta_cols_present
                         if not c.startswith("_term_") and c != "_total_matches"
                         and c != "_matched_terms" and c != "_word_count"
                         and c != "_date_parsed" and c != "_authors"]
    meta_df = results_df[[c for c in meta_cols_present if c in results_df.columns]].copy()
    meta_df.to_csv(META_PATH, index=False, encoding="utf-8")
    size_mb2 = META_PATH.stat().st_size / 1_000_000
    print(f"  Written: {META_PATH.name}  ({size_mb2:.1f} MB,  {len(meta_df):,} rows)")

    print("\nTerm hit summary:")
    exp_map = {e.id: e.title_en for e in expressions}
    term_cols = [c for c in results_df.columns
                 if c.startswith("_term_") and not c.endswith("_per1k")]
    for tc in sorted(term_cols):
        tid = tc.replace("_term_", "")
        title = exp_map.get(tid, tid)
        vals = pd.to_numeric(results_df[tc], errors="coerce").fillna(0)
        total_hits = int(vals.sum())
        rows_with = int((vals > 0).sum())
        per1k_col = f"{tc}_per1k"
        avg_per1k = pd.to_numeric(results_df.get(per1k_col, pd.Series()),
                                  errors="coerce").mean()
        avg_str = f"  avg {avg_per1k:.2f}/1k words" if not pd.isna(avg_per1k) else ""
        print(f"  {title:<30} {total_hits:>8,} hits  in {rows_with:>6,} rows{avg_str}")


def run(corpus_path: Path):
    """Default mode: full analysis and write precomputed_results.csv."""
    t0 = time.time()
    df = _load_corpus(corpus_path)
    text_cols, meta_cols = split_corpus_columns(df)
    print(f"  Text columns (searched, not exported): {text_cols}")
    print(f"  Meta columns (exported): {meta_cols}")

    expressions = load_expressions()
    active = [e for e in expressions if e.enabled]
    print(f"\nRunning analysis with {len(active)} active expressions…")
    name_mapping = load_name_mapping()
    print(f"  Name mapping: {len(name_mapping)} aliases")

    options, _, _ = _build_options(df, text_cols, meta_cols)
    all_results = _run_analysis(df, expressions, options, name_mapping, t0)

    print(f"  Done. {time.time()-t0:.1f}s total")
    print("\nBuilding public results export…")
    _write_results(all_results, expressions)

    print(f"\nAll done in {time.time()-t0:.1f}s")
    print("Commit these files to deploy the preloaded app:")
    print(f"  {RESULTS_PATH.relative_to(Path(__file__).parent.parent.parent)}")
    print(f"  {META_PATH.relative_to(Path(__file__).parent.parent.parent)}")


def run_semantic_flag(corpus_path: Path):
    """
    --semantic-flag mode: score all matches semantically; write semantic_candidates.csv.
    Does NOT update precomputed_results.csv.
    """
    from services.semantic_validator import SemanticValidator

    if not SemanticValidator.is_available():
        print("ERROR: sentence-transformers is not installed.")
        print("Install it with: pip install -r requirements-precompute.txt")
        sys.exit(1)

    t0 = time.time()
    df = _load_corpus(corpus_path)
    text_cols, meta_cols = split_corpus_columns(df)

    expressions = load_expressions()
    active = [e for e in expressions if e.enabled]
    terms_with_refs = [e for e in active if e.semantic_references_he or e.semantic_references_en]
    print(f"\n{len(terms_with_refs)} terms have semantic references: "
          f"{[e.title_en for e in terms_with_refs]}")
    if not terms_with_refs:
        print("No terms have semantic_references defined in expressions.json — nothing to flag.")
        sys.exit(0)

    name_mapping = load_name_mapping()
    options, _, _ = _build_options(df, text_cols, meta_cols)

    validator = SemanticValidator(active)

    print(f"\nRunning analysis with span tracking…")
    all_results = _run_analysis(df, expressions, options, name_mapping, t0, return_spans=True)
    print(f"  Done. {time.time()-t0:.1f}s")

    # Score spans and collect candidates below threshold
    print("\nScoring matches semantically…")
    candidates = []
    scored_articles = 0
    for row_result in all_results:
        if not row_result.matches:
            continue
        url = row_result.original_row.get("url", "")
        title = row_result.original_row.get("Title", "")
        col_texts = [str(row_result.original_row.get(col, "") or "")
                     for col in options.selected_columns]
        full_text = " ".join(col_texts)

        for match in row_result.matches:
            if not validator.has_refs_for(match.term_id):
                continue
            scored_articles += 1
            scored = validator.score_spans(full_text, match.term_id, match.spans)
            for s in scored:
                candidates.append({
                    "url": url,
                    "title": title,
                    "term_id": match.term_id,
                    "term_title": match.term_title,
                    "matched_text": s["matched_text"],
                    "context_sentence": s["context"],
                    "similarity": s["similarity"],
                    "threshold": s["threshold"],
                    "passes": s["passes"],
                    "decision": "",  # to be filled in by the review app
                })

    if not candidates:
        print("No candidates found below threshold.")
        sys.exit(0)

    cands_df = pd.DataFrame(candidates)
    below = (~cands_df["passes"]).sum()
    above = cands_df["passes"].sum()
    print(f"  {len(cands_df):,} total scored spans: "
          f"{below:,} below threshold (flagged), {above:,} above (passes)")

    cands_df.to_csv(CANDIDATES_PATH, index=False, encoding="utf-8")
    print(f"  Written: {CANDIDATES_PATH.name}  ({len(cands_df):,} rows)")
    print(f"\nOpen the Streamlit app → Semantic Review page to review and export decisions.")
    print(f"Then run: python scripts/precompute.py {corpus_path} --semantic-apply")


def run_semantic_apply(corpus_path: Path):
    """
    --semantic-apply mode: read semantic_decisions.csv; re-run analysis
    discarding rejected matches; write updated precomputed_results.csv.
    """
    if not DECISIONS_PATH.exists():
        print(f"ERROR: {DECISIONS_PATH} not found.")
        print("Export decisions from the Semantic Review page in the app first.")
        sys.exit(1)

    decisions_df = pd.read_csv(DECISIONS_PATH, dtype=str, keep_default_na=False)
    rejected = set(
        zip(
            decisions_df.loc[decisions_df["decision"] == "rejected", "url"],
            decisions_df.loc[decisions_df["decision"] == "rejected", "term_id"],
            decisions_df.loc[decisions_df["decision"] == "rejected", "matched_text"],
        )
    )
    print(f"Loaded {len(decisions_df):,} decisions — {len(rejected):,} rejections")

    t0 = time.time()
    df = _load_corpus(corpus_path)
    text_cols, meta_cols = split_corpus_columns(df)

    expressions = load_expressions()
    name_mapping = load_name_mapping()
    options, _, _ = _build_options(df, text_cols, meta_cols)

    print(f"\nRunning analysis…")
    all_results = _run_analysis(df, expressions, options, name_mapping, t0)
    print(f"  Done. {time.time()-t0:.1f}s")

    # Apply rejections
    rejected_count = 0
    for row_result in all_results:
        url = row_result.original_row.get("url", "")
        validated_matches = []
        for match in row_result.matches:
            # Check if any variants of this match were rejected for this article+term
            # A rejection key is (url, term_id, matched_text)
            original_count = match.count
            # We don't have per-span info here, so reject the whole term match
            # if ANY matched_text variant was rejected for this (url, term_id)
            is_rejected = any(
                (url, match.term_id, mv) in rejected
                for mv in match.variants_found
            ) or (url, match.term_id, match.variants_found[0] if match.variants_found else "") in rejected
            if not is_rejected:
                validated_matches.append(match)
            else:
                rejected_count += 1
        row_result.matches = validated_matches
        row_result.total_matches = sum(m.count for m in validated_matches)

    print(f"  Applied {rejected_count} rejections")
    print("\nBuilding public results export…")
    _write_results(all_results, expressions)

    print(f"\nAll done in {time.time()-t0:.1f}s")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    corpus_path = Path(sys.argv[1])
    mode_flags = sys.argv[2:]

    if "--semantic-flag" in mode_flags:
        run_semantic_flag(corpus_path)
    elif "--semantic-apply" in mode_flags:
        run_semantic_apply(corpus_path)
    else:
        run(corpus_path)
