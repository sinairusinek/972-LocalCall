"""
One-time import script: reads the researchers' Excel file and produces
a normalised authors.csv that the app consumes.

Usage (from streamlit_app/):
    python data/import_authors.py /path/to/authors.xlsx

The Excel file is expected to have two sheets:
  - '972Authors'       — English-named authors with partial categorisation
  - 'LocalCallAuthors' — Hebrew-named authors (frequency list only, no categories yet)
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Optional

import pandas as pd


# ---------------------------------------------------------------------------
# Author status: the 7-category system
# ---------------------------------------------------------------------------

STATUS_LABELS = {
    1: "Israeli Jew",
    2: "Diaspora Jew",
    3: "Palestinian citizen of Israel",
    4: "West Bank Palestinian",
    5: "Gaza Palestinian",
    6: "Diaspora Palestinian",
    7: "Other / not identified",
}

# Place-of-residence keywords → status (for Palestinian authors, ethnonational=A)
_GAZA_KEYWORDS = {"gaza"}
_WB_KEYWORDS = {"wb", "west bank", "ramallah", "nablus", "jenin", "hebron",
                 "bethlehem", "east jerusalem", "tulkarm", "qalqilya", "jericho",
                 "masafer", "susiya"}
_IL_KEYWORDS = {"israel", "tel aviv", "haifa", "nazareth", "jaffa", "acre",
                "jerusalem", "negev", "galilee", "lod", "ramleh"}


def _normalise(s: str | None) -> str:
    return (s or "").strip().lower()


def derive_status(ethnonational: Optional[str], precisions: Optional[str],
                  country: Optional[str], residence: Optional[str]) -> int:
    """Derive the 1–7 researcher status code from raw spreadsheet fields."""
    eth = _normalise(ethnonational)
    prec = _normalise(precisions)
    res = _normalise(residence)
    cit = _normalise(country)

    if eth == "j":
        # Jewish
        if prec == "ji":
            return 1   # Israeli Jew
        if prec == "jd":
            return 2   # Diaspora Jew
        # If precisions is missing, try to infer from country
        if "il" in cit or "israel" in cit:
            return 1
        if cit and cit not in ("", "nan"):
            return 2
        return 7  # can't determine

    if eth == "a":
        # Palestinian/Arab — use residence then citizenship to sub-categorise
        if any(k in res for k in _GAZA_KEYWORDS):
            return 5
        if any(k in res for k in _WB_KEYWORDS):
            return 4
        if any(k in res for k in _IL_KEYWORDS):
            return 3
        if "il" in cit or "israel" in cit:
            return 3
        if res and res not in ("", "nan"):
            return 6   # residence known but outside IL/WB/Gaza → diaspora
        return 7  # can't determine

    # X, Iran, blank
    return 7


def _make_slug(name: str) -> str:
    """Convert 'First Last' → 'first_last'."""
    return re.sub(r"[^\w]+", "_", name.strip().lower()).strip("_")


# ---------------------------------------------------------------------------
# Process 972Authors sheet
# ---------------------------------------------------------------------------

def process_972(df: pd.DataFrame) -> pd.DataFrame:
    out_rows = []
    for _, row in df.iterrows():
        name = str(row.get("Clustered Author") or "").strip()
        if not name:
            continue

        eth = str(row.get("ethnonational identity") or "").strip() or None
        prec = str(row.get("Precisions") or "").strip() or None
        country = str(row.get("country of citizenship") or "").strip() or None
        residence = str(row.get("place of residence") or "").strip() or None

        status = derive_status(eth, prec, country, residence)

        out_rows.append({
            "author_id": _make_slug(name),
            "display_name_en": name,
            "display_name_he": str(row.get("עברית") or "").strip() or None,
            "outlet": "972 Magazine",
            "frequency": row.get("972AuthorFrequency"),
            "gender": str(row.get("gender") or "").strip() or None,
            "country_of_citizenship": country,
            "place_of_residence": residence,
            "ethnonational_identity": eth,
            "author_status": status,
            "author_status_label": STATUS_LABELS[status],
            "institutional_author": str(row.get("institutional author") or "").strip() or None,
            "author_url": str(row.get("author_url") or "").strip() or None,
        })

    return pd.DataFrame(out_rows)


# ---------------------------------------------------------------------------
# Process LocalCallAuthors sheet
# ---------------------------------------------------------------------------

def process_localcall(df: pd.DataFrame) -> pd.DataFrame:
    """
    LocalCall sheet has no header row — just: Hebrew name | frequency | (empty).
    Categories not yet filled; everything gets status=7 until data arrives.
    """
    df = df.copy()
    df.columns = ["display_name_he", "frequency", "_unused"]

    out_rows = []
    for _, row in df.iterrows():
        name_he = str(row.get("display_name_he") or "").strip()
        if not name_he:
            continue

        out_rows.append({
            "author_id": _make_slug(name_he),
            "display_name_en": None,
            "display_name_he": name_he,
            "outlet": "Local Call",
            "frequency": row.get("frequency"),
            "gender": None,
            "country_of_citizenship": None,
            "place_of_residence": None,
            "ethnonational_identity": None,
            "author_status": 7,
            "author_status_label": STATUS_LABELS[7],
            "institutional_author": None,
            "author_url": None,
        })

    return pd.DataFrame(out_rows)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run(xlsx_path, out_path=None):
    xlsx_path = Path(xlsx_path)
    if out_path is None:
        out_path = Path(__file__).parent / "authors.csv"

    xl = pd.ExcelFile(xlsx_path)

    df_972 = xl.parse("972Authors")
    df_lc = xl.parse("LocalCallAuthors", header=None)

    authors_972 = process_972(df_972)
    authors_lc = process_localcall(df_lc)

    combined = pd.concat([authors_972, authors_lc], ignore_index=True)

    # De-duplicate: if same author_id appears in both outlets, keep both rows
    # but flag it. (An author can write for both publications.)

    combined.to_csv(out_path, index=False, encoding="utf-8")
    print(f"Written {len(combined)} author rows to {out_path}")
    print("\nStatus distribution:")
    print(combined["author_status_label"].value_counts().to_string())
    print("\nOutlet distribution:")
    print(combined["outlet"].value_counts().to_string())


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    run(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
