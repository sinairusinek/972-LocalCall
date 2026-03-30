"""
Linguist Corpus Analyzer — Streamlit App
"""

import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

sys.path.insert(0, str(Path(__file__).parent))

from services.analysis import (
    AUTHOR_STATUS_LABELS,
    TEXT_COLUMNS,
    UNKNOWN_AUTHOR,
    AnalysisOptions,
    CountMode,
    SearchMode,
    TimeAggregation,
    analyze_corpus,
    calculate_corpus_stats,
    load_authors,
    load_expressions,
    load_name_mapping,
    load_precomputed,
    parse_tsv,
    precomputed_exists,
    prepare_author_timeline_data,
    prepare_timeline_data,
    results_to_dataframe,
    split_corpus_columns,
)

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="Linguist Corpus Analyzer",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)

DATA_DIR = Path(__file__).parent / "data"

# ---------------------------------------------------------------------------
# Session state init
# ---------------------------------------------------------------------------

def _init_state():
    defaults = {
        "corpus_df": None,
        "results": None,
        "expressions": None,
        "preloaded": False,
        "step": "dashboard" if precomputed_exists() else "upload",
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

_init_state()

# ---------------------------------------------------------------------------
# Load precomputed results once per session
# ---------------------------------------------------------------------------

@st.cache_data(show_spinner="Loading precomputed results…")
def _load_precomputed_cached():
    return load_precomputed()

if precomputed_exists() and st.session_state.results is None:
    st.session_state.results = _load_precomputed_cached()
    st.session_state.preloaded = True

# ---------------------------------------------------------------------------
# Sidebar — navigation
# ---------------------------------------------------------------------------

STEPS = ["upload", "configure", "results", "dashboard"]
STEP_LABELS = {
    "upload": "1 · Upload",
    "configure": "2 · Configure",
    "results": "3 · Results",
    "dashboard": "4 · Dashboard",
}

with st.sidebar:
    st.title("🔍 Corpus Analyzer")

    if st.session_state.preloaded:
        st.success("Preloaded corpus active")

    st.markdown("---")

    for s in STEPS:
        # In preloaded mode, upload/configure steps are hidden entirely
        if st.session_state.preloaded and s in ("upload", "configure"):
            continue

        active = st.session_state.step == s
        done = STEPS.index(s) < STEPS.index(st.session_state.step)
        icon = "✅" if done else ("▶" if active else "○")
        label = f"{icon} {STEP_LABELS[s]}"
        if done or active:
            if st.button(label, key=f"nav_{s}", use_container_width=True):
                st.session_state.step = s
                st.rerun()
        else:
            st.markdown(f"<span style='color:grey'>{label}</span>",
                        unsafe_allow_html=True)

    st.markdown("---")
    results = st.session_state.results
    if results:
        n = len(results)
        matched = sum(1 for r in results if r.total_matches > 0)
        st.caption(f"Corpus: **{n:,}** articles · **{matched:,}** with matches")


# ---------------------------------------------------------------------------
# Step 1 — Upload  (research / local mode)
# ---------------------------------------------------------------------------

def step_upload():
    st.header("Upload Corpus")

    if st.session_state.preloaded:
        st.info(
            "The app is running with precomputed results — no upload needed for the dashboard. "
            "Upload a corpus here only if you want to run a fresh local analysis."
        )

    st.markdown("Upload a **tab-separated (.tsv)** file. The first row must be headers.")

    uploaded = st.file_uploader("Choose a .tsv file", type=["tsv", "txt"])

    if uploaded is not None:
        text = uploaded.read().decode("utf-8", errors="replace")
        df = parse_tsv(text)
        if df.empty:
            st.error("Could not parse the file. Make sure it is tab-separated with a header row.")
            return

        st.session_state.corpus_df = df
        st.session_state.preloaded = False   # switch to live analysis mode
        st.success(f"Loaded **{len(df):,}** rows and **{len(df.columns)}** columns.")
        st.dataframe(df.head(5), use_container_width=True)

        if st.button("Continue to Configure →", type="primary"):
            if st.session_state.expressions is None:
                st.session_state.expressions = load_expressions()
            st.session_state.step = "configure"
            st.rerun()


# ---------------------------------------------------------------------------
# Step 2 — Configure  (research / local mode)
# ---------------------------------------------------------------------------

def step_configure():
    st.header("Configure Analysis")

    df = st.session_state.corpus_df
    if df is None:
        st.warning("Please upload a corpus first.")
        return

    cols = list(df.columns)
    expressions = st.session_state.expressions or load_expressions()
    authors_df = load_authors()

    # ---- Column selection ----
    st.subheader("Columns to search")
    known_text = [c for c in cols if c in TEXT_COLUMNS]
    default_search_cols = known_text if known_text else [c for c in cols if df[c].dtype == object][:4]

    selected_columns = st.multiselect(
        "Select columns whose text should be searched:",
        options=cols,
        default=default_search_cols,
        help="Text columns (article body, captions, etc.) are pre-selected.",
    )

    # ---- Date / Author columns ----
    _DATE_HINTS = ("date", "Date", "published", "Published", "timestamp")
    _AUTHOR_HINTS = ("author", "Author", "Authors(Temp)", "byline", "Byline", "writer")
    auto_date = next((c for c in cols if c in _DATE_HINTS), None)
    auto_author = next((c for c in cols if c in _AUTHOR_HINTS), None)

    col1, col2 = st.columns(2)
    with col1:
        date_col_options = ["(none)"] + cols
        default_date_idx = date_col_options.index(auto_date) if auto_date else 0
        date_col = st.selectbox("Date column", date_col_options, index=default_date_idx)
        date_column = None if date_col == "(none)" else date_col
    with col2:
        author_col_options = ["(none)"] + cols
        default_author_idx = author_col_options.index(auto_author) if auto_author else 0
        author_col = st.selectbox("Author column", author_col_options, index=default_author_idx)
        author_column = None if author_col == "(none)" else author_col

    # ---- Search options ----
    st.subheader("Search options")
    c1, c2, c3 = st.columns(3)
    with c1:
        include_en = st.checkbox("English patterns", value=True)
    with c2:
        include_he = st.checkbox("Hebrew patterns", value=True)
    with c3:
        search_mode = st.radio(
            "Search mode",
            [SearchMode.CONCATENATED, SearchMode.SEPARATE],
            format_func=lambda m: "Concatenated" if m == SearchMode.CONCATENATED else "Separate columns",
            horizontal=True,
        )

    count_mode = st.radio(
        "Count mode",
        [CountMode.HITS, CountMode.ROWS],
        format_func=lambda m: "Hits (every match)" if m == CountMode.HITS else "Rows (presence only)",
        horizontal=True,
    )

    # ---- Term library ----
    st.subheader("Term library")
    lang_filter = st.radio("Show terms:", ["All", "English only", "Hebrew only"], horizontal=True)

    term_data = []
    for exp in expressions:
        show = True
        if lang_filter == "English only" and not exp.regex_en:
            show = False
        if lang_filter == "Hebrew only" and not exp.regex_he:
            show = False
        if show:
            term_data.append({
                "enabled": exp.enabled,
                "ID": exp.id,
                "Term": exp.title_en,
                "EN pattern": exp.regex_en,
                "HE pattern": exp.regex_he,
            })

    term_df = pd.DataFrame(term_data)
    edited = st.data_editor(
        term_df,
        column_config={"enabled": st.column_config.CheckboxColumn("Active")},
        use_container_width=True,
        hide_index=True,
        key="term_editor",
    )
    for _, erow in edited.iterrows():
        for exp in expressions:
            if exp.id == erow["ID"]:
                exp.enabled = bool(erow["enabled"])
    st.session_state.expressions = expressions

    # ---- Run ----
    st.markdown("---")
    if not selected_columns:
        st.warning("Select at least one column to search.")
        return

    if st.button("Run Analysis ▶", type="primary"):
        name_mapping = load_name_mapping()
        options = AnalysisOptions(
            selected_columns=selected_columns,
            include_english=include_en,
            include_hebrew=include_he,
            mode=search_mode,
            count_mode=count_mode,
            date_column=date_column,
            author_column=author_column,
        )
        with st.spinner("Analysing corpus…"):
            results = analyze_corpus(df, expressions, options, name_mapping)

        st.session_state.results = results
        st.session_state.analysis_options = options
        st.session_state.step = "results"
        st.rerun()


# ---------------------------------------------------------------------------
# Step 3 — Results  (live analysis mode only)
# ---------------------------------------------------------------------------

def step_results():
    st.header("Results")

    results = st.session_state.get("results")
    if not results:
        st.warning("No results yet. Run the analysis first.")
        return

    if st.session_state.preloaded:
        st.info("Showing precomputed results. Use Upload → Configure to run a fresh analysis.")

    options = st.session_state.get("analysis_options")

    # ---- Stats ----
    c1, c2, c3 = st.columns(3)
    c1.metric("Total rows", f"{len(results):,}")
    matched_rows = sum(1 for r in results if r.total_matches > 0)
    c3.metric("Rows with matches", f"{matched_rows:,}")
    if options and st.session_state.corpus_df is not None:
        stats = calculate_corpus_stats(st.session_state.corpus_df, options.selected_columns)
        c2.metric("Total words", f"{stats.total_words:,}")

    # ---- Term summary chart ----
    term_counts: dict[str, int] = {}
    for res in results:
        for m in res.matches:
            term_counts[m.term_title] = term_counts.get(m.term_title, 0) + m.count

    if term_counts:
        summary_df = pd.DataFrame(
            sorted(term_counts.items(), key=lambda x: x[1], reverse=True),
            columns=["Term", "Count"],
        )
        st.subheader("Term summary")
        fig = px.bar(summary_df, x="Term", y="Count", color="Term",
                     color_discrete_sequence=px.colors.qualitative.Plotly)
        fig.update_layout(showlegend=False, height=350, xaxis_title="", yaxis_title="Hits")
        st.plotly_chart(fig, use_container_width=True)

    # ---- Row table — metadata + match columns only (no article text) ----
    st.subheader("Row-level results")
    filter_text = st.text_input("Filter rows:", "")

    result_df = results_to_dataframe(results, public=True)

    if filter_text:
        mask = result_df.apply(
            lambda col: col.astype(str).str.contains(filter_text, case=False, na=False)
        ).any(axis=1)
        result_df = result_df[mask]

    # Show a sensible subset of columns in a defined order
    _TAIL_COLS = ["institutional author", "translators", "tags", "page_type", "filename"]
    _base = [c for c in result_df.columns
             if not c.startswith("_term_") and c not in ("_word_count",) and c not in _TAIL_COLS]
    display_cols = _base + [c for c in _TAIL_COLS if c in result_df.columns]
    st.dataframe(
        result_df[display_cols],
        use_container_width=True,
        height=400,
        column_config={"url": st.column_config.LinkColumn("url", display_text="🔗 open")}
        if "url" in display_cols else None,
    )

    # ---- Downloads ----
    dl1, dl2 = st.columns(2)
    with dl1:
        pub_bytes = result_df.to_csv(index=False, sep="\t").encode("utf-8")
        st.download_button("⬇ Download public results (TSV)", data=pub_bytes,
                           file_name="corpus_results_public.tsv",
                           mime="text/tab-separated-values")
    with dl2:
        if not st.session_state.preloaded and st.session_state.corpus_df is not None:
            full_df = results_to_dataframe(results, public=False)
            full_bytes = full_df.to_csv(index=False, sep="\t").encode("utf-8")
            st.download_button("⬇ Download full results (local only)", data=full_bytes,
                               file_name="corpus_results_full.tsv",
                               mime="text/tab-separated-values",
                               help="Includes article text — do not share.")

    st.markdown("---")
    if st.button("Open Dashboard →", type="primary"):
        st.session_state.step = "dashboard"
        st.rerun()


# ---------------------------------------------------------------------------
# Step 4 — Dashboard
# ---------------------------------------------------------------------------

PLOTLY_COLORS = px.colors.qualitative.Plotly


def step_dashboard():
    st.header("Dashboard")

    results = st.session_state.get("results")
    if not results:
        if precomputed_exists():
            st.warning("Loading precomputed results…")
        else:
            st.warning("No results yet. Upload a corpus and run the analysis first.")
        return

    authors_df = load_authors()

    # ---- Build author → status lookup ----
    all_authors = sorted({a for r in results for a in r.authors})
    author_status_map: dict[str, int] = {}
    if not authors_df.empty:
        # Build a fast lookup dict from the authors table
        for col in ("author_id", "display_name_en", "display_name_he"):
            if col not in authors_df.columns:
                continue
            for _, arow in authors_df.iterrows():
                key = str(arow.get(col, "") or "").strip()
                if key and key not in author_status_map:
                    try:
                        author_status_map[key] = int(arow.get("author_status", 7))
                    except (ValueError, TypeError):
                        author_status_map[key] = 7

    # ---- Sidebar filters ----
    with st.sidebar:
        st.markdown("### Dashboard filters")

        aggregation = st.selectbox(
            "Time aggregation",
            [TimeAggregation.DAY, TimeAggregation.MONTH, TimeAggregation.YEAR],
            index=1,
            format_func=lambda a: a.value.capitalize(),
        )

        all_terms = sorted({m.term_title for r in results for m in r.matches})
        selected_terms = st.multiselect("Terms to show", all_terms, default=all_terms)

        st.markdown("#### Filter by author status")
        all_statuses = sorted(AUTHOR_STATUS_LABELS.keys())
        selected_statuses = st.multiselect(
            "Author status",
            options=all_statuses,
            default=all_statuses,
            format_func=lambda s: f"{s} — {AUTHOR_STATUS_LABELS[s]}",
        )

        # Outlet filter — builds a set of valid author keys; None means no outlet column
        outlet_valid_authors: set[str] | None = None
        if not authors_df.empty and "outlet" in authors_df.columns:
            all_outlets = sorted(authors_df["outlet"].dropna().unique().tolist())
            selected_outlets = st.multiselect("Outlet", all_outlets, default=all_outlets)
            outlet_valid_authors = set()
            for col in ("author_id", "display_name_en", "display_name_he"):
                if col in authors_df.columns:
                    outlet_valid_authors |= set(
                        authors_df.loc[authors_df["outlet"].isin(selected_outlets), col]
                        .dropna().tolist()
                    )

        # Upstream-filtered authors = status ∩ outlet (before the author picker)
        upstream_filtered = [
            a for a in all_authors
            if author_status_map.get(a, 7) in selected_statuses
            and (outlet_valid_authors is None or a in outlet_valid_authors)
        ]

        include_unknown = st.checkbox(
            "Show articles with no author",
            value=True,
            help="Articles where the author field is empty are grouped as '(unknown / no author)' in grey.",
        )

        # Reset the author picker whenever the upstream filters change so that
        # status and outlet filters always take effect (Streamlit would otherwise
        # keep the cached multiselect value across reruns).
        _upstream_key = (
            tuple(sorted(selected_statuses)),
            tuple(sorted(outlet_valid_authors or [])),
        )
        if st.session_state.get("_filter_upstream_key") != _upstream_key:
            st.session_state["author_picker"] = upstream_filtered
            st.session_state["_filter_upstream_key"] = _upstream_key

        with st.expander("Pick specific authors"):
            selected_authors = st.multiselect(
                "Authors", all_authors, default=upstream_filtered, key="author_picker"
            )

        count_mode = st.radio(
            "Count mode",
            [CountMode.HITS, CountMode.ROWS],
            format_func=lambda m: "Hits" if m == CountMode.HITS else "Rows",
            index=0,
            horizontal=True,
        )

        normalize = st.checkbox(
            "Normalize (per 1,000 words)",
            value=False,
            help="Divides hit counts by the total word count in each period. "
                 "Useful for comparing across outlets or time periods with different volumes.",
            disabled=(count_mode == CountMode.ROWS),
        )

    # ---- Tabs ----
    tab_linguistic, tab_author, tab_table = st.tabs(
        ["Linguistic timeline", "Author timeline", "Results table"]
    )

    # ---- Linguistic timeline ----
    with tab_linguistic:
        timeline_df = prepare_timeline_data(
            results,
            count_mode=count_mode,
            active_terms=selected_terms if selected_terms else None,
            aggregation=aggregation,
            normalize=normalize,
        )

        if timeline_df.empty or timeline_df.get("total", pd.Series([0])).sum() == 0:
            st.info("No term matches for the selected filters.")
        else:
            y_label = "Hits per 1,000 words" if normalize else (
                "Hits" if count_mode == CountMode.HITS else "Rows"
            )
            term_cols = [c for c in timeline_df.columns if c not in ("period", "total")]
            fig = go.Figure()
            for i, term in enumerate(term_cols):
                fig.add_trace(go.Bar(
                    x=timeline_df["period"], y=timeline_df[term],
                    name=term, marker_color=PLOTLY_COLORS[i % len(PLOTLY_COLORS)],
                ))
            fig.update_layout(
                barmode="stack", height=450,
                title="Term occurrences over time"
                      + (" (per 1,000 words)" if normalize else ""),
                xaxis_title="Period", yaxis_title=y_label, legend_title="Term",
            )
            st.plotly_chart(fig, use_container_width=True)

            with st.expander("Period totals table"):
                st.dataframe(timeline_df, use_container_width=True)

    # ---- Author timeline ----
    with tab_author:
        if not all_authors:
            st.info("No author data found. Make sure an author column was configured.")
        else:
            author_metric = st.radio("Metric", ["POSTS", "WORDS"], horizontal=True)
            author_tl = prepare_author_timeline_data(
                results,
                active_authors=selected_authors if selected_authors else None,
                metric=author_metric,
                aggregation=aggregation,
                include_unknown=include_unknown,
            )

            if author_tl.empty or author_tl.get("total", pd.Series([0])).sum() == 0:
                st.info("No author data for the selected filters.")
            else:
                MAX_AUTHORS = 30
                author_cols = [c for c in author_tl.columns if c not in ("period", "total")]

                # Sort by total contribution descending, keep unknown separate
                unknown_col = UNKNOWN_AUTHOR if UNKNOWN_AUTHOR in author_cols else None
                named_cols = [c for c in author_cols if c != UNKNOWN_AUTHOR]
                named_cols_sorted = sorted(
                    named_cols,
                    key=lambda c: author_tl[c].sum(),
                    reverse=True,
                )

                # Top N named authors; the rest go into "Others"
                top_cols = named_cols_sorted[:MAX_AUTHORS]
                rest_cols = named_cols_sorted[MAX_AUTHORS:]

                plot_df = author_tl[["period"] + top_cols].copy()
                if rest_cols:
                    plot_df["(others)"] = author_tl[rest_cols].sum(axis=1)
                if unknown_col:
                    plot_df[UNKNOWN_AUTHOR] = author_tl[UNKNOWN_AUTHOR]

                plot_cols = [c for c in plot_df.columns if c != "period"]

                fig2 = go.Figure()
                color_idx = 0
                for author in plot_cols:
                    if author == UNKNOWN_AUTHOR:
                        color = "lightgrey"
                    elif author == "(others)":
                        color = "#cccccc"
                    else:
                        color = PLOTLY_COLORS[color_idx % len(PLOTLY_COLORS)]
                        color_idx += 1
                    fig2.add_trace(go.Bar(
                        x=plot_df["period"], y=plot_df[author],
                        name=author, marker_color=color,
                    ))
                fig2.update_layout(
                    barmode="stack", height=450,
                    title=f"Author {author_metric.lower()} over time"
                          + (f" (top {MAX_AUTHORS} + others)" if rest_cols else ""),
                    xaxis_title="Period", yaxis_title=author_metric.capitalize(),
                    legend_title="Author",
                )
                st.plotly_chart(fig2, use_container_width=True)
                if rest_cols:
                    st.caption(f"{len(rest_cols)} additional authors grouped into '(others)'. "
                               "Use the author status or outlet filters to narrow down.")

            # Author summary table
            st.subheader("Author summary")
            author_totals: dict = {}
            for res in results:
                authors_here = res.authors if res.authors else (
                    [UNKNOWN_AUTHOR] if include_unknown else []
                )
                for author in authors_here:
                    if selected_authors and author not in selected_authors and author != UNKNOWN_AUTHOR:
                        continue
                    if author not in author_totals:
                        author_totals[author] = {"posts": 0, "words": 0, "matches": 0}
                    author_totals[author]["posts"] += 1
                    author_totals[author]["words"] += res.word_count
                    author_totals[author]["matches"] += res.total_matches

            if author_totals:
                summary_rows = []
                for a, v in author_totals.items():
                    status = author_status_map.get(a, 7)
                    wc = v["words"]
                    summary_rows.append({
                        "author": a,
                        "status": status,
                        "status_label": AUTHOR_STATUS_LABELS[status],
                        **v,
                        "matches_per1k": round(v["matches"] / wc * 1000, 2) if wc > 0 else None,
                    })
                summary = pd.DataFrame(summary_rows).sort_values("posts", ascending=False)

                if not authors_df.empty:
                    extra_cols = [c for c in
                                  ["display_name_he", "outlet", "gender"]
                                  if c in authors_df.columns]
                    for match_col in ("author_id", "display_name_en"):
                        if match_col not in authors_df.columns:
                            continue
                        meta_sub = authors_df[[match_col] + extra_cols].drop_duplicates(match_col)
                        summary = summary.merge(
                            meta_sub.rename(columns={match_col: "author"}),
                            on="author", how="left",
                        )
                        break

                st.dataframe(summary, use_container_width=True)

    # ---- Results table (metadata + matches, no article text) ----
    with tab_table:
        st.markdown("Filtered by current sidebar selections.")
        filter_text = st.text_input("Search rows:", "", key="dash_filter")

        # Filter results to selected authors/terms
        filtered = [
            r for r in results
            if (not selected_authors or any(a in selected_authors for a in r.authors))
            and (not selected_terms or any(m.term_title in selected_terms for m in r.matches))
        ]

        tbl_df = results_to_dataframe(filtered, public=True)
        _TAIL_COLS = ["institutional author", "translators", "tags", "page_type", "filename"]
        _base = [c for c in tbl_df.columns
                 if not c.startswith("_term_") and c not in _TAIL_COLS]
        display_cols = _base + [c for c in _TAIL_COLS if c in tbl_df.columns]

        if filter_text:
            mask = tbl_df[display_cols].apply(
                lambda col: col.astype(str).str.contains(filter_text, case=False, na=False)
            ).any(axis=1)
            tbl_df = tbl_df[mask]

        st.caption(f"{len(tbl_df):,} rows")
        st.dataframe(
            tbl_df[display_cols],
            use_container_width=True,
            height=450,
            column_config={"url": st.column_config.LinkColumn("url", display_text="🔗 open")}
            if "url" in display_cols else None,
        )

        dl_bytes = tbl_df.to_csv(index=False, sep="\t").encode("utf-8")
        st.download_button("⬇ Download filtered results (TSV)", data=dl_bytes,
                           file_name="filtered_results.tsv",
                           mime="text/tab-separated-values")


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

step = st.session_state.step

# In preloaded mode, upload/configure are not accessible
if st.session_state.preloaded and step in ("upload", "configure"):
    st.session_state.step = "dashboard"
    step = "dashboard"

if step == "upload":
    step_upload()
elif step == "configure":
    step_configure()
elif step == "results":
    step_results()
elif step == "dashboard":
    step_dashboard()
