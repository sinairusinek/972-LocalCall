"""
Semantic Match Review

Review flagged regex matches that the semantic validator found to be
potentially false positives. Accept correct matches or reject false ones.
Decisions are saved immediately and can be exported for use in the next
precompute run.

To generate the candidates file, run from streamlit_app/:
    python scripts/precompute.py /path/to/corpus.tsv --semantic-flag
"""

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).parent.parent))

DATA_DIR = Path(__file__).parent.parent / "data"
CANDIDATES_PATH = DATA_DIR / "semantic_candidates.csv"
DECISIONS_PATH = DATA_DIR / "semantic_decisions.csv"

st.set_page_config(page_title="Semantic Match Review", layout="wide")
st.title("Semantic Match Review")
st.markdown(
    "Review regex matches that may be false positives based on semantic context. "
    "**Accept** correct matches, **Reject** false ones. "
    "When done, export decisions for use in the next precompute run."
)


# ---------------------------------------------------------------------------
# Load / save helpers
# ---------------------------------------------------------------------------

@st.cache_data(ttl=0)
def _load_candidates() -> pd.DataFrame:
    if not CANDIDATES_PATH.exists():
        return pd.DataFrame()
    return pd.read_csv(CANDIDATES_PATH, dtype=str, keep_default_na=False)


def _save_candidates(df: pd.DataFrame):
    df.to_csv(CANDIDATES_PATH, index=False, encoding="utf-8")
    st.cache_data.clear()


# ---------------------------------------------------------------------------
# Load data
# ---------------------------------------------------------------------------

cands = _load_candidates()

if cands.empty:
    st.info(
        "No candidate file found. Generate it by running:\n\n"
        "```bash\n"
        "cd streamlit_app\n"
        "python scripts/precompute.py /path/to/corpus.tsv --semantic-flag\n"
        "```"
    )
    st.stop()

# Ensure decision column exists
if "decision" not in cands.columns:
    cands["decision"] = ""

# ---------------------------------------------------------------------------
# Stats header
# ---------------------------------------------------------------------------

total = len(cands)
n_flagged = (cands["passes"] == "False").sum()
n_passes = (cands["passes"] == "True").sum()
n_pending = (cands["decision"] == "").sum()
n_accepted = (cands["decision"] == "accepted").sum()
n_rejected = (cands["decision"] == "rejected").sum()

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Total scored", total)
c2.metric("Below threshold", n_flagged)
c3.metric("Pending review", n_pending)
c4.metric("Accepted", n_accepted)
c5.metric("Rejected", n_rejected)

if n_pending == 0:
    st.success("All candidates have been reviewed.")

st.markdown("---")

# ---------------------------------------------------------------------------
# Filters
# ---------------------------------------------------------------------------

col_f1, col_f2, col_f3 = st.columns(3)
with col_f1:
    all_terms = sorted(cands["term_title"].unique().tolist())
    show_terms = st.multiselect("Term", all_terms, default=all_terms)
with col_f2:
    show_decision = st.multiselect(
        "Decision status",
        ["pending", "accepted", "rejected"],
        default=["pending"],
    )
with col_f3:
    show_flagged_only = st.checkbox("Show below-threshold only", value=True)

# Apply filters
mask = cands["term_title"].isin(show_terms)
decision_map = {"pending": "", "accepted": "accepted", "rejected": "rejected"}
mask &= cands["decision"].isin([decision_map[s] for s in show_decision])
if show_flagged_only:
    mask &= cands["passes"] == "False"

view = cands[mask].copy()
st.caption(f"Showing {len(view)} candidates")

# ---------------------------------------------------------------------------
# Batch actions
# ---------------------------------------------------------------------------

if not view.empty:
    col_ba1, col_ba2, _ = st.columns([1, 1, 4])
    with col_ba1:
        if st.button("✅ Accept all visible", type="secondary"):
            cands.loc[view.index[cands.loc[view.index, "decision"] == ""], "decision"] = "accepted"
            _save_candidates(cands)
            st.rerun()
    with col_ba2:
        if st.button("❌ Reject all visible", type="secondary"):
            cands.loc[view.index[cands.loc[view.index, "decision"] == ""], "decision"] = "rejected"
            _save_candidates(cands)
            st.rerun()

    st.markdown("---")

# ---------------------------------------------------------------------------
# Per-candidate review
# ---------------------------------------------------------------------------

if view.empty:
    st.info("No candidates match the current filters.")
else:
    for idx, row in view.iterrows():
        sim = float(row.get("similarity", 0))
        thresh = float(row.get("threshold", 0))
        passes = row.get("passes", "True") == "True"

        if sim >= thresh * 0.95:
            sim_icon = "🟢"
        elif sim >= thresh * 0.75:
            sim_icon = "🟡"
        else:
            sim_icon = "🔴"

        decision = row.get("decision", "")
        status_icon = {"accepted": "✅", "rejected": "❌", "": "⏳"}.get(decision, "⏳")

        with st.container():
            cols = st.columns([3, 3, 1, 1, 1, 1])

            with cols[0]:
                url = row.get("url", "")
                title = row.get("title", url)
                if url:
                    st.markdown(f"**[{title}]({url})**")
                else:
                    st.markdown(f"**{title}**")
                st.markdown(
                    f"<span style='font-size:0.8em;color:grey'>Term: {row.get('term_title','')}</span>",
                    unsafe_allow_html=True,
                )

            with cols[1]:
                matched = row.get("matched_text", "")
                context = row.get("context_sentence", "")
                # Bold the matched text within context
                highlighted = context.replace(matched, f"**{matched}**") if matched else context
                st.markdown(f"…{highlighted}…")

            with cols[2]:
                st.markdown(
                    f"{sim_icon} **{sim:.2f}**  \n"
                    f"<span style='font-size:0.75em;color:grey'>threshold: {thresh:.2f}</span>",
                    unsafe_allow_html=True,
                )

            with cols[3]:
                st.markdown(f"{status_icon} {decision or 'pending'}")

            with cols[4]:
                if decision != "accepted":
                    if st.button("✅ Accept", key=f"acc_{idx}"):
                        cands.at[idx, "decision"] = "accepted"
                        _save_candidates(cands)
                        st.rerun()

            with cols[5]:
                if decision != "rejected":
                    if st.button("❌ Reject", key=f"rej_{idx}"):
                        cands.at[idx, "decision"] = "rejected"
                        _save_candidates(cands)
                        st.rerun()

            st.divider()

# ---------------------------------------------------------------------------
# Export decisions
# ---------------------------------------------------------------------------

st.markdown("## Export decisions")
st.markdown(
    "Export your decisions to `semantic_decisions.csv`, then run:\n\n"
    "```bash\n"
    "python scripts/precompute.py /path/to/corpus.tsv --semantic-apply\n"
    "```"
)

reviewed = cands[cands["decision"] != ""]
if reviewed.empty:
    st.info("No decisions made yet.")
else:
    export_df = reviewed[["url", "term_id", "term_title", "matched_text",
                           "context_sentence", "similarity", "threshold", "decision"]].copy()

    col_e1, col_e2 = st.columns(2)
    with col_e1:
        dl = export_df.to_csv(index=False, encoding="utf-8").encode("utf-8")
        st.download_button(
            "⬇ Download semantic_decisions.csv",
            data=dl,
            file_name="semantic_decisions.csv",
            mime="text/csv",
        )
    with col_e2:
        if st.button("💾 Save to data/ folder"):
            export_df.to_csv(DECISIONS_PATH, index=False, encoding="utf-8")
            st.success(f"Saved to {DECISIONS_PATH.name}")

    st.dataframe(export_df, use_container_width=True, height=300)
