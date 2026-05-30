"""
Precompute analysis results from the full corpus TSV.

Reads the corpus locally (article text stays on your machine), runs the full
keyword analysis, and writes two public CSV files into data/ that the deployed
app loads directly — no upload needed.

Usage (from streamlit_app/):
    python scripts/precompute.py /path/to/corpus.tsv

Output:
    data/precomputed_results.csv  — one row per article, metadata + term counts
    data/corpus_meta.csv          — metadata only (url, title, date, author, source)

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
                  t0: float) -> list:
    CHUNK = 2000
    all_results = []
    total = len(df)
    for start in range(0, total, CHUNK):
        chunk_df = df.iloc[start:start + CHUNK]
        chunk_results = analyze_corpus(chunk_df, expressions, options, name_mapping)
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



if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    run(Path(sys.argv[1]))
