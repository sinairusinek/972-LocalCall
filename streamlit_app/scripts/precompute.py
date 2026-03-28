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

Both files contain NO article text and are safe to commit and deploy.
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


def run(corpus_path: Path):
    print(f"Loading corpus: {corpus_path.name}")
    t0 = time.time()

    df = pd.read_csv(
        corpus_path,
        sep="\t",
        dtype=str,
        keep_default_na=False,
        on_bad_lines="skip",
    )
    print(f"  {len(df):,} rows × {len(df.columns)} columns  ({time.time()-t0:.1f}s)")

    # ---- Identify columns ----
    text_cols, meta_cols = split_corpus_columns(df)
    print(f"  Text columns (searched, not exported): {text_cols}")
    print(f"  Meta columns (exported): {meta_cols}")

    date_col = DATE_COLUMN if DATE_COLUMN in df.columns else None
    author_col = AUTHOR_COLUMN if AUTHOR_COLUMN in df.columns else None
    if not date_col:
        print("  WARNING: date column not found — timeline features will be unavailable")
    if not author_col:
        print("  WARNING: author column not found — author features will be unavailable")

    # ---- Load supporting data ----
    expressions = load_expressions()
    active = [e for e in expressions if e.enabled]
    print(f"\nRunning analysis with {len(active)} active expressions…")

    name_mapping = load_name_mapping()
    print(f"  Name mapping: {len(name_mapping)} aliases")

    options = AnalysisOptions(
        selected_columns=text_cols if text_cols else meta_cols,
        include_english=True,
        include_hebrew=True,
        mode=SearchMode.CONCATENATED,
        count_mode=CountMode.HITS,
        date_column=date_col,
        author_column=author_col,
    )

    # ---- Analyse in chunks for progress reporting ----
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

    print(f"\n  Done. {time.time()-t0:.1f}s total")

    # ---- Build public results dataframe ----
    print("\nBuilding public results export…")
    results_df = results_to_dataframe(all_results, public=True)

    matched = (results_df["_total_matches"].astype(int) > 0).sum()
    print(f"  {matched:,} / {len(results_df):,} rows have at least one term match")

    # ---- Write precomputed_results.csv ----
    results_df.to_csv(RESULTS_PATH, index=False, encoding="utf-8")
    size_mb = RESULTS_PATH.stat().st_size / 1_000_000
    print(f"  Written: {RESULTS_PATH.name}  ({size_mb:.1f} MB,  {len(results_df):,} rows)")

    # ---- Write corpus_meta.csv (metadata only, no term counts) ----
    meta_cols_present = [c for c in meta_cols if c in results_df.columns]
    meta_df = results_df[meta_cols_present].copy()
    meta_df.to_csv(META_PATH, index=False, encoding="utf-8")
    size_mb2 = META_PATH.stat().st_size / 1_000_000
    print(f"  Written: {META_PATH.name}  ({size_mb2:.1f} MB,  {len(meta_df):,} rows)")

    # ---- Summary ----
    print("\nTerm hit summary:")
    exp_map = {e.id: e.title_en for e in expressions}
    # Only raw count columns (skip _per1k)
    term_cols = [c for c in results_df.columns
                 if c.startswith("_term_") and not c.endswith("_per1k")]
    for tc in sorted(term_cols):
        tid = tc.replace("_term_", "")
        title = exp_map.get(tid, tid)
        vals = pd.to_numeric(results_df[tc], errors="coerce").fillna(0)
        total_hits = int(vals.sum())
        rows_with = int((vals > 0).sum())
        per1k_col = f"{tc}_per1k"
        avg_per1k = pd.to_numeric(results_df.get(per1k_col, pd.Series()), errors="coerce").mean()
        avg_str = f"  avg {avg_per1k:.2f}/1k words" if not pd.isna(avg_per1k) else ""
        print(f"  {title:<30} {total_hits:>8,} hits  in {rows_with:>6,} rows{avg_str}")

    print(f"\nAll done in {time.time()-t0:.1f}s")
    print(f"Commit these files to deploy the preloaded app:")
    print(f"  {RESULTS_PATH.relative_to(Path(__file__).parent.parent.parent)}")
    print(f"  {META_PATH.relative_to(Path(__file__).parent.parent.parent)}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    run(Path(sys.argv[1]))
