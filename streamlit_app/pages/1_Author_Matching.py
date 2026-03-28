"""
Author Name Matching Review

Researchers accept or reject fuzzy-matched name pairs proposed by
build_name_candidates.py. Accepted matches are immediately written to
name_mapping.csv and take effect in the next analysis run.
"""

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).parent.parent))

DATA_DIR = Path(__file__).parent.parent / "data"
CANDIDATES_PATH = DATA_DIR / "name_candidates.csv"
MAPPING_PATH = DATA_DIR / "name_mapping.csv"

st.set_page_config(page_title="Author Name Matching", layout="wide")
st.title("Author Name Matching Review")
st.markdown(
    "Review fuzzy-matched name pairs between the two outlets. "
    "**Accept** correct links, **Reject** incorrect ones. "
    "Changes are saved immediately and used in all future analyses."
)


# ---------------------------------------------------------------------------
# Load / save helpers
# ---------------------------------------------------------------------------

@st.cache_data(ttl=0)
def _load_candidates() -> pd.DataFrame:
    if not CANDIDATES_PATH.exists():
        return pd.DataFrame()
    return pd.read_csv(CANDIDATES_PATH, dtype=str, keep_default_na=False)


def save_candidates(df: pd.DataFrame):
    df.to_csv(CANDIDATES_PATH, index=False, encoding="utf-8")
    st.cache_data.clear()


def _load_mapping() -> pd.DataFrame:
    if not MAPPING_PATH.exists():
        return pd.DataFrame()
    return pd.read_csv(MAPPING_PATH, dtype=str, keep_default_na=False)


def save_mapping(df: pd.DataFrame):
    df.to_csv(MAPPING_PATH, index=False, encoding="utf-8")


def accept_candidate(cands_df: pd.DataFrame, idx: int) -> pd.DataFrame:
    """Accept a candidate: update candidates CSV and append to name_mapping."""
    cands_df.at[idx, "status"] = "accepted"
    save_candidates(cands_df)

    row = cands_df.loc[idx]
    mapping = _load_mapping()

    # Add corpus_name → canonical_author_id mapping (HE alias)
    new_he = pd.DataFrame([{
        "corpus_name": row["corpus_name"],
        "canonical_author_id": row["canonical_author_id"],
        "name_script": row.get("name_script", "HE"),
        "source": row.get("source", "fuzzy"),
        "confidence": row.get("confidence", ""),
        "status": "accepted",
    }])

    # Also add the matched HE name as an alias if it came from a transliteration match
    new_rows = [new_he]
    if row.get("source") == "transliteration" and row.get("matched_he_name"):
        new_rows.append(pd.DataFrame([{
            "corpus_name": row["matched_he_name"],
            "canonical_author_id": row["canonical_author_id"],
            "name_script": "HE",
            "source": "fuzzy_accepted",
            "confidence": row.get("confidence", ""),
            "status": "accepted",
        }]))

    combined = pd.concat([mapping] + new_rows, ignore_index=True)
    combined = combined.drop_duplicates(subset=["corpus_name"]).sort_values("corpus_name")
    save_mapping(combined)

    return cands_df


def reject_candidate(cands_df: pd.DataFrame, idx: int) -> pd.DataFrame:
    cands_df.at[idx, "status"] = "rejected"
    save_candidates(cands_df)
    return cands_df


# ---------------------------------------------------------------------------
# Stats header
# ---------------------------------------------------------------------------

cands = _load_candidates()

if cands.empty:
    st.info(
        "No candidate file found. Run the matching pipeline first:\n\n"
        "```bash\n"
        "cd streamlit_app\n"
        "python3 data/build_name_candidates.py /path/to/authors.xlsx\n"
        "```"
    )
    st.stop()

total = len(cands)
n_pending = (cands["status"] == "pending").sum()
n_accepted = (cands["status"] == "accepted").sum()
n_rejected = (cands["status"] == "rejected").sum()

c1, c2, c3, c4 = st.columns(4)
c1.metric("Total candidates", total)
c2.metric("Pending review", n_pending)
c3.metric("Accepted", n_accepted)
c4.metric("Rejected", n_rejected)

if n_pending == 0:
    st.success("All candidates have been reviewed.")

st.markdown("---")

# ---------------------------------------------------------------------------
# Filters
# ---------------------------------------------------------------------------

col_f1, col_f2, col_f3 = st.columns(3)
with col_f1:
    show_status = st.multiselect(
        "Show status",
        ["pending", "accepted", "rejected"],
        default=["pending"],
    )
with col_f2:
    show_source = st.multiselect(
        "Matching method",
        cands["source"].unique().tolist(),
        default=cands["source"].unique().tolist(),
    )
with col_f3:
    min_conf = st.slider("Min confidence", 0.0, 1.0, 0.70, 0.01)

view = cands[
    cands["status"].isin(show_status)
    & cands["source"].isin(show_source)
    & (pd.to_numeric(cands["confidence"], errors="coerce").fillna(0) >= min_conf)
].copy()

st.caption(f"Showing {len(view)} candidates")

# ---------------------------------------------------------------------------
# Review table — one row per candidate with Accept / Reject buttons
# ---------------------------------------------------------------------------

if view.empty:
    st.info("No candidates match the current filters.")
else:
    # Batch actions
    col_ba1, col_ba2, _ = st.columns([1, 1, 4])
    with col_ba1:
        if st.button("✅ Accept all visible", type="secondary"):
            for idx in view.index:
                if cands.at[idx, "status"] == "pending":
                    cands = accept_candidate(cands, idx)
            st.rerun()
    with col_ba2:
        if st.button("❌ Reject all visible", type="secondary"):
            for idx in view.index:
                if cands.at[idx, "status"] == "pending":
                    cands = reject_candidate(cands, idx)
            st.rerun()

    st.markdown("---")

    for idx, row in view.iterrows():
        conf = float(row.get("confidence", 0))
        conf_color = "🟢" if conf >= 0.90 else ("🟡" if conf >= 0.80 else "🔴")
        status_icon = {"pending": "⏳", "accepted": "✅", "rejected": "❌"}.get(
            row["status"], "⏳"
        )

        with st.container():
            cols = st.columns([3, 3, 1, 1, 1, 1])

            with cols[0]:
                st.markdown(
                    f"**{row['corpus_name']}**  \n"
                    f"<span style='font-size:0.8em;color:grey'>corpus name</span>",
                    unsafe_allow_html=True,
                )
            with cols[1]:
                en = row.get("matched_en_name", "")
                he = row.get("matched_he_name", "")
                st.markdown(
                    f"**{en}**  \n"
                    f"<span dir='rtl'>{he}</span>  \n"
                    f"<span style='font-size:0.8em;color:grey'>"
                    f"→ `{row['canonical_author_id']}`</span>",
                    unsafe_allow_html=True,
                )
            with cols[2]:
                st.markdown(
                    f"{conf_color} **{conf:.0%}**  \n"
                    f"<span style='font-size:0.75em;color:grey'>{row.get('source','')}</span>",
                    unsafe_allow_html=True,
                )
            with cols[3]:
                st.markdown(f"{status_icon} {row['status']}")
            with cols[4]:
                if row["status"] != "accepted":
                    if st.button("✅ Accept", key=f"acc_{idx}"):
                        cands = accept_candidate(cands, idx)
                        st.rerun()
            with cols[5]:
                if row["status"] != "rejected":
                    if st.button("❌ Reject", key=f"rej_{idx}"):
                        cands = reject_candidate(cands, idx)
                        st.rerun()

            # Notes field — editable
            current_note = row.get("notes", "")
            new_note = st.text_input(
                "Note (optional)", value=current_note,
                key=f"note_{idx}", label_visibility="collapsed",
                placeholder="Add a note…"
            )
            if new_note != current_note:
                cands.at[idx, "notes"] = new_note
                save_candidates(cands)

            st.divider()

# ---------------------------------------------------------------------------
# Manual link entry
# ---------------------------------------------------------------------------

st.markdown("## Add a manual link")
st.markdown(
    "Link any corpus name to a canonical author ID directly — "
    "useful for names the fuzzy matcher missed."
)

with st.form("manual_link"):
    col_m1, col_m2, col_m3 = st.columns(3)
    with col_m1:
        manual_corpus = st.text_input("Corpus name (as it appears in the TSV)")
    with col_m2:
        manual_cid = st.text_input("Canonical author_id (from authors.csv)")
    with col_m3:
        manual_script = st.selectbox("Script", ["EN", "HE", "AR", "other"])
    submitted = st.form_submit_button("Add link")

    if submitted and manual_corpus and manual_cid:
        mapping = _load_mapping()
        if manual_corpus in mapping["corpus_name"].values:
            st.warning(f"'{manual_corpus}' already exists in the mapping.")
        else:
            new_row = pd.DataFrame([{
                "corpus_name": manual_corpus,
                "canonical_author_id": manual_cid,
                "name_script": manual_script,
                "source": "manual",
                "confidence": "1.0",
                "status": "accepted",
            }])
            updated = pd.concat([mapping, new_row], ignore_index=True)
            updated = updated.drop_duplicates(subset=["corpus_name"]).sort_values("corpus_name")
            save_mapping(updated)
            st.success(f"Added: '{manual_corpus}' → `{manual_cid}`")

# ---------------------------------------------------------------------------
# Current mapping browser
# ---------------------------------------------------------------------------

with st.expander("Browse current name_mapping.csv"):
    mapping_view = _load_mapping()
    if mapping_view.empty:
        st.info("Mapping is empty.")
    else:
        search = st.text_input("Search mapping", "")
        if search:
            mask = mapping_view.apply(
                lambda c: c.astype(str).str.contains(search, case=False, na=False)
            ).any(axis=1)
            mapping_view = mapping_view[mask]
        st.dataframe(mapping_view, use_container_width=True, height=300)
        dl = mapping_view.to_csv(index=False).encode("utf-8")
        st.download_button("Download name_mapping.csv", dl,
                           "name_mapping.csv", "text/csv")
