"""
Name-matching pipeline: links Hebrew ↔ English author names across the two sheets
and produces:
  - data/name_mapping.csv    (auto-accepted exact matches + all EN/HE aliases)
  - data/name_candidates.csv (fuzzy candidates for human review)

Usage (from streamlit_app/):
    python3 data/build_name_candidates.py /path/to/authors.xlsx

Re-run any time the spreadsheet is updated. Previously accepted/rejected decisions
in name_candidates.csv are preserved.

Requires: rapidfuzz   (pip install rapidfuzz)
"""

from __future__ import annotations

import re
import sys
import unicodedata
from pathlib import Path
from typing import Optional

import pandas as pd
from rapidfuzz import fuzz, process

DATA_DIR = Path(__file__).parent


# ---------------------------------------------------------------------------
# Hebrew → rough Latin transliteration
# Used only to generate candidates — not authoritative.
# ---------------------------------------------------------------------------

_HE_TO_LATIN = {
    "א": "", "ב": "b", "ג": "g", "ד": "d", "ה": "h",
    "ו": "v", "ז": "z", "ח": "kh", "ט": "t", "י": "y",
    "כ": "k", "ך": "k", "ל": "l", "מ": "m", "ם": "m",
    "נ": "n", "ן": "n", "ס": "s", "ע": "", "פ": "p",
    "ף": "f", "צ": "ts", "ץ": "ts", "ק": "k", "ר": "r",
    "ש": "sh", "ת": "t",
    # final forms already handled above; vowel marks (nikud) stripped by NFD
}

_NIKUD = set("\u05b0\u05b1\u05b2\u05b3\u05b4\u05b5\u05b6\u05b7\u05b8\u05b9"
             "\u05ba\u05bb\u05bc\u05bd\u05be\u05bf\u05c0\u05c1\u05c2\u05c7")


def strip_nikud(text: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", text) if c not in _NIKUD)


def he_to_latin(text: str) -> str:
    text = strip_nikud(text)
    out = []
    for ch in text:
        if ch == " ":
            out.append(" ")
        elif ch in _HE_TO_LATIN:
            out.append(_HE_TO_LATIN[ch])
        elif "\u0590" <= ch <= "\u05ff":
            pass  # other Hebrew punctuation — skip
        else:
            out.append(ch)
    # Collapse repeated spaces
    return re.sub(r"\s+", " ", "".join(out)).strip()


def normalise(s: Optional[str]) -> str:
    if not s:
        return ""
    return strip_nikud(str(s)).strip().lower()


# ---------------------------------------------------------------------------
# Load source data
# ---------------------------------------------------------------------------

def load_sheets(xlsx_path: Path):
    xl = pd.ExcelFile(xlsx_path)
    df972 = xl.parse("972Authors")
    dflc = xl.parse("LocalCallAuthors", header=None)
    dflc.columns = ["display_name_he", "frequency", "_unused"]
    return df972, dflc


# ---------------------------------------------------------------------------
# Build the initial name_mapping from known EN↔HE pairs in 972Authors
# ---------------------------------------------------------------------------

def build_base_mapping(df972: pd.DataFrame) -> pd.DataFrame:
    """
    Every row in 972Authors that has both an English name and a Hebrew name
    gives us two aliases for the same canonical_author_id.
    Returns a DataFrame with columns:
      corpus_name | canonical_author_id | name_script | source | confidence
    """
    rows = []

    for _, row in df972.iterrows():
        en = str(row.get("Clustered Author") or "").strip()
        he = str(row.get("עברית") or "").strip()
        if not en:
            continue

        # slug
        cid = re.sub(r"[^\w]+", "_", en.lower()).strip("_")

        # English alias
        rows.append({
            "corpus_name": en,
            "canonical_author_id": cid,
            "name_script": "EN",
            "source": "spreadsheet_exact",
            "confidence": 1.0,
            "status": "accepted",
        })

        # Hebrew alias (if present)
        if he:
            rows.append({
                "corpus_name": he,
                "canonical_author_id": cid,
                "name_script": "HE",
                "source": "spreadsheet_exact",
                "confidence": 1.0,
                "status": "accepted",
            })

    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Fuzzy matching: LocalCall HE names → 972Authors HE names
# ---------------------------------------------------------------------------

FUZZY_ACCEPT_THRESHOLD = 92   # auto-accept above this score
FUZZY_REVIEW_THRESHOLD = 72   # show for review above this score


def fuzzy_match_localcall(df972: pd.DataFrame, dflc: pd.DataFrame,
                          base_mapping: pd.DataFrame,
                          cross_outlet_he: Optional[set] = None) -> pd.DataFrame:
    """
    For each LocalCall Hebrew name not already in base_mapping,
    find the best match among 972Authors Hebrew names.

    cross_outlet_he: if provided, only attempt matching for Hebrew names that
    actually appear in both outlets in the corpus — ignoring LocalCall-only authors
    who can have no English parallel.
    """
    already_mapped = set(base_mapping["corpus_name"].str.strip())

    # 972Authors Hebrew pool: he_name → (en_name, canonical_author_id)
    he_pool: dict[str, tuple[str, str]] = {}
    for _, row in df972.iterrows():
        he = str(row.get("עברית") or "").strip()
        en = str(row.get("Clustered Author") or "").strip()
        if he and en:
            cid = re.sub(r"[^\w]+", "_", en.lower()).strip("_")
            he_pool[he] = (en, cid)

    he_pool_keys = list(he_pool.keys())
    he_pool_norm = [normalise(k) for k in he_pool_keys]

    candidates = []

    for _, row in dflc.iterrows():
        lc_he = str(row.get("display_name_he") or "").strip()
        if not lc_he or lc_he in already_mapped:
            continue
        # Skip LocalCall-only authors — they have no English parallel
        if cross_outlet_he is not None and lc_he not in cross_outlet_he:
            continue

        lc_norm = normalise(lc_he)
        if not lc_norm:
            continue

        # rapidfuzz: find best match in the 972 HE pool
        result = process.extractOne(
            lc_norm,
            he_pool_norm,
            scorer=fuzz.token_sort_ratio,
        )
        if result is None:
            continue

        best_norm, score, idx = result
        best_he = he_pool_keys[idx]
        best_en, best_cid = he_pool[best_he]

        if score < FUZZY_REVIEW_THRESHOLD:
            continue

        status = "accepted" if score >= FUZZY_ACCEPT_THRESHOLD else "pending"

        candidates.append({
            "corpus_name": lc_he,
            "canonical_author_id": best_cid,
            "matched_en_name": best_en,
            "matched_he_name": best_he,
            "name_script": "HE",
            "source": "fuzzy_he",
            "confidence": round(score / 100, 3),
            "status": status,
            "notes": "",
        })

    return pd.DataFrame(candidates)


# ---------------------------------------------------------------------------
# Transliteration pass: 972Authors EN-only → LocalCall HE names
# (generates candidates where an author has no Hebrew in 972Authors)
# ---------------------------------------------------------------------------

def transliteration_match(df972: pd.DataFrame, dflc: pd.DataFrame,
                          base_mapping: pd.DataFrame,
                          cross_outlet_he: Optional[set] = None) -> pd.DataFrame:
    """
    For 972Authors rows with NO Hebrew name, transliterate their English name
    and fuzzy-match against LocalCall Hebrew names to surface candidates.
    Only attempts matching against LocalCall names that appear in both outlets.
    """
    already_mapped = set(base_mapping["corpus_name"].str.strip())

    # 972 authors without a Hebrew name
    no_he = df972[
        df972["עברית"].isna() | (df972["עברית"].str.strip() == "")
    ][["Clustered Author"]].dropna()

    # LocalCall HE names not yet matched — restrict to cross-outlet if provided
    lc_names = [
        str(r) for r in dflc["display_name_he"].dropna()
        if str(r).strip()
        and str(r).strip() not in already_mapped
        and (cross_outlet_he is None or str(r).strip() in cross_outlet_he)
    ]
    if not lc_names:
        return pd.DataFrame()

    lc_norms = [normalise(n) for n in lc_names]
    # Also build latin transliterations of LC names for comparison
    lc_latin = [he_to_latin(n).lower() for n in lc_names]

    candidates = []

    for _, row in no_he.iterrows():
        en = str(row["Clustered Author"]).strip()
        en_norm = en.lower()
        cid = re.sub(r"[^\w]+", "_", en_norm).strip("_")

        if en in already_mapped:
            continue

        # Compare en_norm against latin transliterations of HE names
        result = process.extractOne(
            en_norm,
            lc_latin,
            scorer=fuzz.token_sort_ratio,
        )
        if result is None:
            continue

        best_latin, score, idx = result
        best_he = lc_names[idx]

        if score < FUZZY_REVIEW_THRESHOLD:
            continue

        status = "accepted" if score >= FUZZY_ACCEPT_THRESHOLD else "pending"

        candidates.append({
            "corpus_name": en,
            "canonical_author_id": cid,
            "matched_en_name": en,
            "matched_he_name": best_he,
            "name_script": "EN",
            "source": "transliteration",
            "confidence": round(score / 100, 3),
            "status": status,
            "notes": f"transliteration of HE: '{he_to_latin(best_he)}'",
        })

    return pd.DataFrame(candidates)


# ---------------------------------------------------------------------------
# Merge with existing decisions
# ---------------------------------------------------------------------------

def merge_with_existing(new_candidates: pd.DataFrame,
                        existing_path: Path) -> pd.DataFrame:
    """
    Preserve any status='accepted' or status='rejected' decisions already made,
    so re-running doesn't overwrite human decisions.
    """
    if not existing_path.exists() or new_candidates.empty:
        return new_candidates

    existing = pd.read_csv(existing_path, dtype=str)
    decided = existing[existing["status"].isin(["accepted", "rejected"])][
        ["corpus_name", "canonical_author_id", "status"]
    ]

    # Merge on (corpus_name, canonical_author_id), preserving prior decisions
    merged = new_candidates.merge(
        decided, on=["corpus_name", "canonical_author_id"], how="left",
        suffixes=("", "_prior")
    )
    # Where a prior decision exists, use it
    prior_mask = merged["status_prior"].notna()
    merged.loc[prior_mask, "status"] = merged.loc[prior_mask, "status_prior"]
    merged.drop(columns=["status_prior"], inplace=True)

    return merged


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run(xlsx_path: Path, corpus_path: Optional[Path] = None):
    print(f"Loading {xlsx_path.name}…")
    df972, dflc = load_sheets(xlsx_path)

    # 0. Build cross-outlet author set from corpus (if available)
    # Only Hebrew names that appear alongside 972 articles are worth fuzzy-matching.
    cross_outlet_he: Optional[set] = None
    if corpus_path and corpus_path.exists():
        print(f"Loading corpus to identify cross-outlet authors: {corpus_path.name}…")
        corpus = pd.read_csv(corpus_path, sep="\t", dtype=str, keep_default_na=False,
                             usecols=["Authors(Temp)", "Source"], on_bad_lines="skip")
        # Authors per outlet (raw strings, pipe-split)
        authors_972: set[str] = set()
        authors_lc: set[str] = set()
        for _, row in corpus.iterrows():
            raw = str(row.get("Authors(Temp)", "") or "")
            source = str(row.get("Source", "") or "")
            for name in raw.split("|"):
                name = name.strip()
                if not name:
                    continue
                if source == "972":
                    authors_972.add(name)
                elif source == "LocalCall":
                    authors_lc.add(name)
        # Hebrew names in LocalCall that also have a match in 972
        # (proxy: any LocalCall author name that shares a slug with a 972 name)
        cross_outlet_he = authors_lc & authors_972   # exact overlap
        # Also include LocalCall HE names whose slug matches any 972 slug
        slugs_972 = {re.sub(r"[^\w]+", "_", n.lower()).strip("_") for n in authors_972}
        for lc_name in list(authors_lc):
            if re.sub(r"[^\w]+", "_", lc_name.lower()).strip("_") in slugs_972:
                cross_outlet_he.add(lc_name)
        print(f"  → {len(authors_lc):,} LocalCall authors, "
              f"{len(authors_972):,} 972 authors, "
              f"{len(cross_outlet_he):,} potential cross-outlet matches")
    else:
        print("  No corpus path provided — fuzzy matching will cover all LocalCall authors.")

    # 1. Base mapping: all known EN↔HE pairs from 972Authors
    print("Building base mapping from known EN↔HE pairs…")
    base_mapping = build_base_mapping(df972)
    print(f"  → {len(base_mapping)} alias rows "
          f"({base_mapping['canonical_author_id'].nunique()} unique authors)")

    # 2. Fuzzy: LocalCall HE → 972Authors HE (cross-outlet authors only)
    print("Fuzzy-matching LocalCall Hebrew names → 972Authors Hebrew names…")
    fuzzy_cands = fuzzy_match_localcall(df972, dflc, base_mapping, cross_outlet_he)
    auto = (fuzzy_cands["status"] == "accepted").sum() if not fuzzy_cands.empty else 0
    review = (fuzzy_cands["status"] == "pending").sum() if not fuzzy_cands.empty else 0
    print(f"  → {auto} auto-accepted, {review} pending review")

    # 3. Transliteration: 972Authors EN-only → LocalCall HE (cross-outlet only)
    print("Transliteration pass: EN names → LocalCall HE names…")
    translit_cands = transliteration_match(df972, dflc, base_mapping, cross_outlet_he)
    tauto = (translit_cands["status"] == "accepted").sum() if not translit_cands.empty else 0
    treview = (translit_cands["status"] == "pending").sum() if not translit_cands.empty else 0
    print(f"  → {tauto} auto-accepted, {treview} pending review")

    # 4. Combine candidates (non-base)
    all_candidates = pd.concat(
        [df for df in [fuzzy_cands, translit_cands] if not df.empty],
        ignore_index=True,
    )

    # 5. Preserve existing human decisions
    cands_path = DATA_DIR / "name_candidates.csv"
    if not all_candidates.empty:
        all_candidates = merge_with_existing(all_candidates, cands_path)

    # 6. Write name_mapping.csv (accepted entries from both base and candidates)
    mapping_path = DATA_DIR / "name_mapping.csv"
    accepted_cands = (
        all_candidates[all_candidates["status"] == "accepted"][
            ["corpus_name", "canonical_author_id", "name_script", "source", "confidence", "status"]
        ]
        if not all_candidates.empty
        else pd.DataFrame()
    )
    full_mapping = pd.concat([base_mapping, accepted_cands], ignore_index=True)
    full_mapping = full_mapping.drop_duplicates(subset=["corpus_name"]).sort_values("corpus_name")
    full_mapping.to_csv(mapping_path, index=False, encoding="utf-8")
    print(f"\nWrote {len(full_mapping)} entries to {mapping_path.name}")

    # 7. Write name_candidates.csv (pending only — for human review)
    if not all_candidates.empty:
        all_candidates = all_candidates.sort_values("confidence", ascending=False)
        all_candidates.to_csv(cands_path, index=False, encoding="utf-8")
        pending = (all_candidates["status"] == "pending").sum()
        print(f"Wrote {len(all_candidates)} candidates to {cands_path.name} "
              f"({pending} pending review)")
    else:
        print("No fuzzy candidates generated.")

    print("\nDone. Summary:")
    print(f"  name_mapping.csv : {len(full_mapping)} accepted aliases")
    if not all_candidates.empty:
        print(f"  name_candidates.csv : {(all_candidates['status']=='pending').sum()} pending | "
              f"{(all_candidates['status']=='accepted').sum()} auto-accepted | "
              f"{(all_candidates['status']=='rejected').sum()} rejected")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    corpus = Path(sys.argv[2]) if len(sys.argv) >= 3 else None
    run(Path(sys.argv[1]), corpus_path=corpus)
