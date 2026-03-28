# Linguist Corpus Analyzer — 972 Magazine & Local Call (Mekomit)

A bilingual (Hebrew/English) corpus analysis tool for political journalism published by [972 Magazine](https://972mag.com) and [Local Call (Mekomit)](https://mekomit.co.il).

Built with Python and Streamlit.

## What it does

- **Keyword search** — searches a corpus of ~20,000 articles for configurable terms and expressions in Hebrew and English, with support for Hebrew morphology (prefix handling)
- **Author categorization** — classifies authors by ethnonational identity and residence using a 7-category system (Israeli Jewish, Diaspora Jewish, Palestinian citizen of Israel, West Bank Palestinian, Gaza Palestinian, Diaspora Palestinian, Other)
- **Name matching** — links Hebrew and English author names across the two outlets using fuzzy matching and transliteration
- **Timeline charts** — visualizes term frequency and author activity over time, with per-1,000-word normalization
- **Results table** — filterable, downloadable table of article-level match counts with clickable links

## Repository structure

```
streamlit_app/
├── app.py                        # Main Streamlit app
├── requirements.txt
├── pages/
│   └── 1_Author_Matching.py      # Name-matching review UI
├── services/
│   └── analysis.py               # Core analysis logic
├── data/
│   ├── expressions.json          # Search terms (Hebrew + English)
│   ├── authors.csv               # Author metadata and categories
│   ├── name_mapping.csv          # Accepted EN↔HE name aliases
│   ├── name_candidates.csv       # Fuzzy match candidates for review
│   ├── precomputed_results.csv   # Precomputed term counts (no article text)
│   └── corpus_meta.csv           # Article metadata (no article text)
└── scripts/
    └── precompute.py             # Regenerates precomputed CSVs from corpus TSV
```

> **Note:** The corpus TSV (article text) and author spreadsheet (XLSX) are not in this repository — they are kept locally for copyright and privacy reasons.

## Running locally

**Prerequisites:** Python 3.9+

```bash
cd streamlit_app
pip install -r requirements.txt
streamlit run app.py
```

The app loads precomputed results automatically on startup — no corpus upload needed.

## Regenerating precomputed data

If the corpus or expressions change, re-run from `streamlit_app/`:

```bash
# Recompute term counts
python scripts/precompute.py /path/to/corpus.tsv

# Refresh author name matching (requires corpus for cross-outlet filtering)
python data/build_name_candidates.py /path/to/authors.xlsx /path/to/corpus.tsv

# Re-import author metadata from spreadsheet
python data/import_authors.py /path/to/authors.xlsx
```
