"""
Core corpus analysis logic.
Ported from services/analysisService.ts
"""

from __future__ import annotations

import re
import json
import io
from dataclasses import dataclass, field
from datetime import datetime, date
from enum import Enum
from pathlib import Path
from typing import Optional

import pandas as pd


# ---------------------------------------------------------------------------
# Column classification: text (private) vs metadata (public)
# ---------------------------------------------------------------------------

# Full article text — copyrighted; never committed to git or shown in deployed app.
TEXT_COLUMNS = frozenset([
    "Content",
    "Description/Summary",
    "Headlines",
    "Blockquote",
    "Captions",
    "Concatenation",
])

# Factual metadata — safe to commit, display in deployed app, and share.
META_COLUMNS = frozenset([
    "url",
    "Source",
    "Authors(Temp)",
    "filename",
    "Date",
    "Title",
    "institutional author",
    "translators",
    "tags",
    "page_type",
])


def split_corpus_columns(df: pd.DataFrame) -> tuple[list[str], list[str]]:
    """
    Given a corpus DataFrame, return (text_cols, meta_cols) based on
    the known classification above. Unknown columns are treated as metadata.
    """
    cols = list(df.columns)
    text = [c for c in cols if c in TEXT_COLUMNS]
    meta = [c for c in cols if c not in TEXT_COLUMNS]
    return text, meta


def strip_text_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Return a copy of df with all text (private) columns removed."""
    drop = [c for c in df.columns if c in TEXT_COLUMNS]
    return df.drop(columns=drop)


# ---------------------------------------------------------------------------
# Enums & config
# ---------------------------------------------------------------------------

class SearchMode(str, Enum):
    CONCATENATED = "CONCATENATED"   # join all selected columns then search
    SEPARATE = "SEPARATE"           # search each column independently


class CountMode(str, Enum):
    HITS = "HITS"   # count every regex match
    ROWS = "ROWS"   # count rows that contain at least one match


class TimeAggregation(str, Enum):
    DAY = "DAY"
    MONTH = "MONTH"
    YEAR = "YEAR"


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class SearchExpression:
    id: str
    title_en: str
    variants_en: list[str]
    variants_he: list[str]
    regex_en: str
    regex_he: str
    enabled: bool = True

    @classmethod
    def from_dict(cls, d: dict) -> "SearchExpression":
        return cls(
            id=d["id"],
            title_en=d["title_en"],
            variants_en=d.get("variants_en", []),
            variants_he=d.get("variants_he", []),
            regex_en=d.get("regex_en", ""),
            regex_he=d.get("regex_he", ""),
            enabled=d.get("enabled", True),
        )


@dataclass
class TermMatch:
    term_id: str
    term_title: str
    count: int
    variants_found: list[str]


@dataclass
class AnalysisRowResult:
    original_row: dict
    matches: list[TermMatch]
    total_matches: int
    authors: list[str]
    word_count: int
    date: Optional[date] = None


@dataclass
class AnalysisOptions:
    selected_columns: list[str]
    include_english: bool = True
    include_hebrew: bool = True
    mode: SearchMode = SearchMode.CONCATENATED
    count_mode: CountMode = CountMode.HITS
    date_column: Optional[str] = None
    author_column: Optional[str] = None


@dataclass
class ColumnStats:
    non_empty_rows: int = 0
    word_count: int = 0


@dataclass
class CorpusStats:
    total_rows: int = 0
    total_words: int = 0
    column_stats: dict[str, ColumnStats] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

DATA_DIR = Path(__file__).parent.parent / "data"


def load_expressions() -> list[SearchExpression]:
    path = DATA_DIR / "expressions.json"
    with open(path, encoding="utf-8") as f:
        raw = json.load(f)
    return [SearchExpression.from_dict(d) for d in raw]


AUTHOR_STATUS_LABELS = {
    1: "Israeli Jew",
    2: "Diaspora Jew",
    3: "Palestinian citizen of Israel",
    4: "West Bank Palestinian",
    5: "Gaza Palestinian",
    6: "Diaspora Palestinian",
    7: "Other / not identified",
}

AUTHOR_STATUS_SHORT = {
    1: "Israeli Jew",
    2: "Diaspora Jew",
    3: "Pal. citizen of Israel",
    4: "West Bank Palestinian",
    5: "Gaza Palestinian",
    6: "Diaspora Palestinian",
    7: "Other / unidentified",
}


def load_authors() -> pd.DataFrame:
    path = DATA_DIR / "authors.csv"
    if not path.exists():
        return pd.DataFrame()
    df = pd.read_csv(path, dtype=str, keep_default_na=False)
    if "author_status" in df.columns:
        df["author_status"] = pd.to_numeric(df["author_status"], errors="coerce").fillna(7).astype(int)
    return df


def load_name_mapping() -> dict[str, str]:
    """
    Returns a dict: corpus_name (any script) → canonical_author_id.
    Only includes rows with status='accepted'.
    """
    path = DATA_DIR / "name_mapping.csv"
    if not path.exists():
        return {}
    df = pd.read_csv(path, dtype=str, keep_default_na=False)
    accepted = df[df["status"] == "accepted"]
    return dict(zip(accepted["corpus_name"].str.strip(), accepted["canonical_author_id"].str.strip()))


def resolve_author_id(corpus_name: str, name_mapping: dict[str, str]) -> str:
    """
    Given a name as it appears in the corpus, return the canonical author_id.
    Falls back to a slugified form of the name itself if not in the mapping.
    """
    resolved = name_mapping.get(corpus_name.strip())
    if resolved:
        return resolved
    # Fallback: slug the name directly (will match author_id for authors
    # whose name in the corpus exactly matches their display_name_en/he)
    import re as _re
    return _re.sub(r"[^\w]+", "_", corpus_name.strip().lower()).strip("_")


def get_author_metadata(corpus_name: str, authors_df: pd.DataFrame,
                        name_mapping: Optional[dict] = None) -> Optional[dict]:
    """
    Look up author metadata for a corpus name.
    Resolution order:
      1. name_mapping (corpus_name → canonical_author_id)
      2. Direct match on display_name_en, display_name_he, author_id
    """
    if authors_df.empty:
        return None

    # Try via name_mapping first
    if name_mapping:
        cid = name_mapping.get(corpus_name.strip())
        if cid and "author_id" in authors_df.columns:
            match = authors_df[authors_df["author_id"].str.strip() == cid]
            if not match.empty:
                return match.iloc[0].to_dict()

    # Direct field match
    for col in ("display_name_en", "display_name_he", "author_id"):
        if col not in authors_df.columns:
            continue
        match = authors_df[authors_df[col].str.strip() == corpus_name.strip()]
        if not match.empty:
            return match.iloc[0].to_dict()

    return None


def _compile(pattern: str, case_insensitive: bool) -> Optional[re.Pattern]:
    if not pattern or not pattern.strip():
        return None
    flags = re.IGNORECASE if case_insensitive else 0
    try:
        return re.compile(pattern, flags)
    except re.error:
        return None


def _count_words(text: str) -> int:
    return len(text.split()) if text.strip() else 0


def _parse_date(val: str) -> Optional[date]:
    if not val or not val.strip():
        return None
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%Y/%m/%d", "%d-%m-%Y"):
        try:
            return datetime.strptime(val.strip(), fmt).date()
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(val.strip()).date()
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# TSV parsing
# ---------------------------------------------------------------------------

def parse_tsv(text: str) -> pd.DataFrame:
    """Parse a TSV string into a DataFrame."""
    lines = [l for l in text.splitlines() if l.strip()]
    if not lines:
        return pd.DataFrame()
    return pd.read_csv(
        io.StringIO(text),
        sep="\t",
        dtype=str,
        keep_default_na=False,
        on_bad_lines="skip",
    )


# ---------------------------------------------------------------------------
# Corpus stats
# ---------------------------------------------------------------------------

def calculate_corpus_stats(df: pd.DataFrame, selected_columns: list[str]) -> CorpusStats:
    stats = CorpusStats(total_rows=len(df))
    for col in selected_columns:
        if col not in df.columns:
            continue
        col_series = df[col].fillna("")
        non_empty = col_series.str.strip().astype(bool).sum()
        words = col_series.apply(_count_words).sum()
        stats.column_stats[col] = ColumnStats(non_empty_rows=int(non_empty), word_count=int(words))
        stats.total_words += int(words)
    return stats


# ---------------------------------------------------------------------------
# Core analysis
# ---------------------------------------------------------------------------

def analyze_corpus(
    df: pd.DataFrame,
    expressions: list[SearchExpression],
    options: AnalysisOptions,
    name_mapping: Optional[dict] = None,
) -> list[AnalysisRowResult]:
    """Run regex matching over the corpus, returning one result per row.

    name_mapping: optional dict from load_name_mapping(), used to resolve
    author names in the corpus to canonical_author_ids.
    """
    if name_mapping is None:
        name_mapping = load_name_mapping()
    active = [e for e in expressions if e.enabled]

    # Pre-compile patterns
    compiled = []
    for exp in active:
        reg_en = _compile(exp.regex_en, case_insensitive=True) if options.include_english else None
        reg_he = _compile(exp.regex_he, case_insensitive=False) if options.include_hebrew else None
        compiled.append((exp.id, exp.title_en, reg_en, reg_he))

    results: list[AnalysisRowResult] = []

    for _, row in df.iterrows():
        row_dict = row.to_dict()

        # Collect text from selected columns
        col_texts = [str(row_dict.get(col, "") or "") for col in options.selected_columns]
        word_count = sum(_count_words(t) for t in col_texts)

        matches: list[TermMatch] = []
        total_matches = 0

        for term_id, term_title, reg_en, reg_he in compiled:
            term_count = 0
            variants_found: set[str] = set()

            def _search_text(text: str):
                nonlocal term_count
                for reg in (reg_en, reg_he):
                    if reg is None:
                        continue
                    found = reg.findall(text)
                    if found:
                        # findall may return tuples when there are groups
                        flat = []
                        for f in found:
                            if isinstance(f, tuple):
                                flat.append("".join(f))
                            else:
                                flat.append(f)
                        term_count += len(flat)
                        variants_found.update(v.strip() for v in flat if v.strip())

            if options.mode == SearchMode.CONCATENATED:
                _search_text(" ".join(col_texts))
            else:
                for t in col_texts:
                    _search_text(t)

            if term_count > 0:
                matches.append(TermMatch(
                    term_id=term_id,
                    term_title=term_title,
                    count=term_count,
                    variants_found=list(variants_found),
                ))
                total_matches += term_count

        # Date
        parsed_date = None
        if options.date_column and options.date_column in row_dict:
            parsed_date = _parse_date(str(row_dict[options.date_column]))

        # Authors (pipe-separated in source data)
        # Each raw name is resolved to a canonical_author_id via name_mapping,
        # but we store the *resolved* form so that dashboard lookups are consistent.
        authors: list[str] = []
        if options.author_column and options.author_column in row_dict:
            raw_authors = str(row_dict[options.author_column] or "")
            for raw in raw_authors.split("|"):
                raw = raw.strip()
                if raw:
                    authors.append(resolve_author_id(raw, name_mapping))

        results.append(AnalysisRowResult(
            original_row=row_dict,
            matches=matches,
            total_matches=total_matches,
            authors=authors,
            word_count=word_count,
            date=parsed_date,
        ))

    return results


# ---------------------------------------------------------------------------
# Timeline aggregation
# ---------------------------------------------------------------------------

def _agg_key(d: date, aggregation: TimeAggregation) -> str:
    if aggregation == TimeAggregation.YEAR:
        return str(d.year)
    if aggregation == TimeAggregation.MONTH:
        return f"{d.year}-{d.month:02d}"
    return d.isoformat()


def prepare_timeline_data(
    results: list[AnalysisRowResult],
    count_mode: CountMode = CountMode.HITS,
    active_terms: list[str] | None = None,
    aggregation: TimeAggregation = TimeAggregation.MONTH,
    normalize: bool = False,
) -> pd.DataFrame:
    """
    Returns a DataFrame with columns:
      period | <term1> | <term2> | ... | total

    normalize=True: values are hits per 1,000 words in that period instead of
    raw counts. Requires count_mode=HITS (ignored for ROWS mode).
    """
    hit_rows = []
    word_rows = []

    for res in results:
        if res.date is None:
            continue
        key = _agg_key(res.date, aggregation)
        if normalize:
            word_rows.append({"period": key, "words": res.word_count or 0})
        for m in res.matches:
            if active_terms and m.term_title not in active_terms:
                continue
            increment = m.count if count_mode == CountMode.HITS else 1
            hit_rows.append({"period": key, "term": m.term_title, "value": increment})

    if not hit_rows:
        return pd.DataFrame(columns=["period", "total"])

    df = pd.DataFrame(hit_rows)
    pivoted = df.pivot_table(index="period", columns="term", values="value",
                             aggfunc="sum", fill_value=0)
    pivoted["total"] = pivoted.sum(axis=1)
    pivoted = pivoted.reset_index().sort_values("period")

    if normalize and count_mode == CountMode.HITS and word_rows:
        words_df = pd.DataFrame(word_rows).groupby("period")["words"].sum().reset_index()
        pivoted = pivoted.merge(words_df, on="period", how="left")
        term_cols = [c for c in pivoted.columns if c not in ("period", "total", "words")]
        for tc in term_cols + ["total"]:
            pivoted[tc] = (pivoted[tc] / pivoted["words"].replace(0, float("nan")) * 1000).round(4)
        pivoted = pivoted.drop(columns=["words"])

    return pivoted


UNKNOWN_AUTHOR = "(unknown / no author)"


def prepare_author_timeline_data(
    results: list[AnalysisRowResult],
    active_authors: list[str] | None = None,
    metric: str = "POSTS",
    aggregation: TimeAggregation = TimeAggregation.MONTH,
    include_unknown: bool = True,
) -> pd.DataFrame:
    """
    Returns a DataFrame with columns:
      period | <author1> | <author2> | ... | total

    Articles with no author are grouped under UNKNOWN_AUTHOR when
    include_unknown=True. The caller can colour this entry grey.
    """
    rows = []
    for res in results:
        if res.date is None:
            continue
        key = _agg_key(res.date, aggregation)
        val = 1 if metric == "POSTS" else res.word_count

        if not res.authors:
            if include_unknown:
                if active_authors is None or UNKNOWN_AUTHOR in active_authors:
                    rows.append({"period": key, "author": UNKNOWN_AUTHOR, "value": val})
        else:
            for author in res.authors:
                if active_authors and author not in active_authors:
                    continue
                rows.append({"period": key, "author": author, "value": val})

    if not rows:
        return pd.DataFrame(columns=["period", "total"])

    df = pd.DataFrame(rows)
    pivoted = df.pivot_table(index="period", columns="author", values="value", aggfunc="sum", fill_value=0)
    pivoted["total"] = pivoted.sum(axis=1)
    pivoted = pivoted.reset_index().sort_values("period")
    return pivoted


# ---------------------------------------------------------------------------
# Precomputed results — load and reconstruct
# ---------------------------------------------------------------------------

PRECOMPUTED_PATH = DATA_DIR / "precomputed_results.csv"


def precomputed_exists() -> bool:
    return PRECOMPUTED_PATH.exists()


def load_precomputed() -> list[AnalysisRowResult]:
    """
    Read precomputed_results.csv (written by scripts/precompute.py) and
    reconstruct a list of AnalysisRowResult objects for the dashboard.
    """
    df = pd.read_csv(PRECOMPUTED_PATH, dtype=str, keep_default_na=False)
    expressions = load_expressions()
    exp_map = {e.id: e.title_en for e in expressions}

    results: list[AnalysisRowResult] = []
    term_cols = [c for c in df.columns if c.startswith("_term_") and not c.endswith("_per1k")]

    for _, row in df.iterrows():
        row_dict = row.to_dict()

        # Reconstruct matches from per-term count columns
        matches: list[TermMatch] = []
        total = 0
        for tc in term_cols:
            try:
                count = int(float(row_dict.get(tc, 0) or 0))
            except (ValueError, TypeError):
                count = 0
            if count > 0:
                tid = tc.replace("_term_", "")
                title = exp_map.get(tid, tid)
                matches.append(TermMatch(term_id=tid, term_title=title,
                                         count=count, variants_found=[]))
                total += count

        # Authors — stored as pipe-separated canonical IDs
        raw_authors = str(row_dict.get("_authors", "") or "")
        authors = [a.strip() for a in raw_authors.split("|") if a.strip()]

        # Date
        parsed_date = _parse_date(str(row_dict.get("_date_parsed", "") or ""))

        # Word count
        try:
            wc = int(float(row_dict.get("_word_count", 0) or 0))
        except (ValueError, TypeError):
            wc = 0

        # Original row: strip internal _ columns so only source columns remain
        original = {k: v for k, v in row_dict.items() if not k.startswith("_")}

        results.append(AnalysisRowResult(
            original_row=original,
            matches=matches,
            total_matches=total,
            authors=authors,
            word_count=wc,
            date=parsed_date,
        ))

    return results


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------

def results_to_dataframe(results: list[AnalysisRowResult],
                         public: bool = False) -> pd.DataFrame:
    """Flatten results into a DataFrame suitable for display or CSV export.

    public=True strips all TEXT_COLUMNS (article body, summaries, etc.) so the
    output contains only metadata + analysis results — safe for GitHub and the
    deployed app.

    Per-term columns produced:
      _term_TERM_001        raw hit count
      _term_TERM_001_per1k  hits per 1,000 words (NaN if word_count == 0)
    """
    if not results:
        return pd.DataFrame()

    rows = []
    for res in results:
        row = dict(res.original_row)
        if public:
            for col in list(row.keys()):
                if col in TEXT_COLUMNS:
                    del row[col]
        row["_date_parsed"] = res.date.isoformat() if res.date else ""
        row["_authors"] = " | ".join(res.authors)
        row["_word_count"] = res.word_count
        row["_total_matches"] = res.total_matches
        row["_matched_terms"] = ", ".join(
            f"{m.term_title} ({m.count})" for m in res.matches
        )
        wc = res.word_count or 0
        for m in res.matches:
            row[f"_term_{m.term_id}"] = m.count
            row[f"_term_{m.term_id}_per1k"] = (
                round(m.count / wc * 1000, 4) if wc > 0 else None
            )
        rows.append(row)

    return pd.DataFrame(rows)
