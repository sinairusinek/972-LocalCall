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
    SOURCE_TO_OUTLET,
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


CROSS_PUBLISHED_LABEL = "972 + Local Call"
CROSS_PUBLISHED_TSV = DATA_DIR / "972also-inLocalCall.tsv"


@st.cache_data(show_spinner=False)
def _load_cross_published_urls() -> frozenset:
    if not CROSS_PUBLISHED_TSV.exists():
        return frozenset()
    df = pd.read_csv(CROSS_PUBLISHED_TSV, sep="\t", dtype=str, keep_default_na=False)
    if "url" not in df.columns:
        return frozenset()
    return frozenset(df["url"].str.strip())


_cross_urls: frozenset = _load_cross_published_urls()

if precomputed_exists() and st.session_state.results is None:
    st.session_state.results = _load_precomputed_cached()
    st.session_state.preloaded = True
    for r in st.session_state.results:
        url = str(r.original_row.get("url", "") or "").strip()
        r.original_row["_cross_published"] = url in _cross_urls

# ---------------------------------------------------------------------------
# Sidebar — corpus stats (filters are added later inside the dashboard step)
# ---------------------------------------------------------------------------

with st.sidebar:
    st.title("🔍 Corpus Analyzer")
    results = st.session_state.results
    if results:
        n = len(results)
        matched = sum(1 for r in results if r.total_matches > 0)
        st.caption(f"Corpus: **{n:,}** articles · **{matched:,}** with matches")
    st.markdown("---")



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
        st.session_state.step = "dashboard"
        st.rerun()


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

PLOTLY_COLORS = px.colors.qualitative.Plotly

OUTLET_COLORS = {
    "972 Magazine":     "#E63946",
    "Local Call":       "#457B9D",
    "972 + Local Call": "#6A4C93",
    "unknown":          "#888888",
}

# Colors keyed by AUTHOR_STATUS_LABELS label strings
STATUS_COLORS = {
    "Israeli Jew":                "#2196F3",   # blue
    "Diaspora Jew":               "#64B5F6",   # light blue
    "Palestinian citizen of Israel": "#4CAF50", # green
    "West Bank Palestinian":      "#FF9800",   # orange
    "Gaza Palestinian":           "#F44336",   # red
    "Diaspora Palestinian":       "#FF7043",   # deep orange
    "Other / not identified":     "#888888",   # grey
    "unknown":                    "#888888",
}


def step_dashboard():
    # Enlarge and highlight the dashboard tab labels
    st.markdown(
        """
<style>
div[data-testid="stTabs"] button[data-baseweb="tab"] {
    font-size: 1.15rem;
    font-weight: 600;
    padding: 0.6rem 1.2rem;
}
div[data-testid="stTabs"] button[data-baseweb="tab"][aria-selected="true"] {
    color: #2c5282;
}
</style>
""",
        unsafe_allow_html=True,
    )

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

        cross_published_only = st.checkbox(
            "Cross-published only",
            value=False,
            help=(
                "Show only 972 Magazine articles that were also published on Local Call (in Hebrew). "
                "Note: the Local Call counterparts are not separately listed in this dataset."
            ),
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

        color_mode = st.radio(
            "Color by",
            ["Term / Author", "Outlet", "Author status"],
            index=0,
            horizontal=True,
            key="color_mode",
        )
        color_by_outlet = color_mode == "Outlet"
        color_by_status = color_mode == "Author status"

    # ---- Pre-filter results by selected authors/outlets ----
    # Determine which outlet names are selected (None means no outlet filter exists)
    selected_outlet_names: set[str] | None = (
        set(selected_outlets) if (not authors_df.empty and "outlet" in authors_df.columns) else None
    )

    def _article_outlet(r) -> str:
        if r.original_row.get("_cross_published"):
            return CROSS_PUBLISHED_LABEL
        return SOURCE_TO_OUTLET.get(str(r.original_row.get("Source", "") or ""), "unknown")

    def _include_authorless(r: "AnalysisRowResult") -> bool:
        """Authorless posts: respect include_unknown, status-7, and outlet filter."""
        if not include_unknown:
            return False
        if 7 not in selected_statuses:
            return False
        if selected_outlet_names is not None:
            article_outlet = _article_outlet(r)
            # Cross-published articles are 972 Magazine articles; treat them as
            # passing the outlet filter if "972 Magazine" is selected.
            effective_outlet = (
                "972 Magazine" if article_outlet == CROSS_PUBLISHED_LABEL else article_outlet
            )
            if effective_outlet not in selected_outlet_names:
                return False
        return True

    filtered_results = [
        r for r in results
        if (
            (r.authors and any(a in selected_authors for a in r.authors))
            or (not r.authors and _include_authorless(r))
        )
        and (not cross_published_only or r.original_row.get("_cross_published", False))
    ]

    # ---- Build grouping maps for coloring modes ----
    author_outlet_map = None
    if color_by_outlet:
        author_outlet_map = {}
        for r in filtered_results:
            outlet = _article_outlet(r)
            for a in r.authors:
                # Cross-published takes priority over plain 972 Magazine
                if author_outlet_map.get(a) != CROSS_PUBLISHED_LABEL:
                    author_outlet_map[a] = outlet

    # author_id → status label string (for status coloring)
    author_status_label_map: dict[str, str] = {
        a: AUTHOR_STATUS_LABELS.get(author_status_map.get(a, 7), "Other / not identified")
        for a in all_authors
    }

    def _article_status_label(r) -> str:
        """Best-effort status label for an article, using its first author."""
        if r.authors:
            return author_status_label_map.get(r.authors[0], "Other / not identified")
        return "Other / not identified"

    # ---- Tabs ----
    tab_linguistic, tab_author, tab_table, tab_docs = st.tabs(
        ["Linguistic timeline", "Author timeline", "Results table", "Documentation"]
    )

    # ---- Linguistic timeline ----
    with tab_linguistic:
        # ---- Term summary chart (respects current filters) ----
        active_terms_set = set(selected_terms) if selected_terms is not None else None
        term_counts: dict[str, int] = {}
        for res in filtered_results:
            for m in res.matches:
                if active_terms_set is not None and m.term_title not in active_terms_set:
                    continue
                term_counts[m.term_title] = term_counts.get(m.term_title, 0) + m.count

        if term_counts:
            summary_df = pd.DataFrame(
                sorted(term_counts.items(), key=lambda x: x[1], reverse=True),
                columns=["Term", "Count"],
            )
            st.subheader("Term summary")
            summary_fig = px.bar(
                summary_df, x="Term", y="Count", color="Term",
                color_discrete_sequence=px.colors.qualitative.Plotly,
            )
            summary_fig.update_layout(
                showlegend=False, height=350, xaxis_title="", yaxis_title="Hits",
            )
            st.plotly_chart(summary_fig, use_container_width=True)

        c_cm, c_norm, _ = st.columns([1, 2, 3])
        with c_cm:
            count_mode = st.radio(
                "Count mode",
                [CountMode.HITS, CountMode.ROWS],
                format_func=lambda m: "Hits" if m == CountMode.HITS else "Articles",
                index=0,
                horizontal=True,
            )
        with c_norm:
            normalize = st.checkbox(
                "Normalize (per 1,000 words)",
                value=False,
                help="Divides hit counts by the total number of words published in that time period "
                     "(day/month/year, depending on the aggregation setting). "
                     "Useful when some periods have more articles than others — normalization shows "
                     "how frequent the terms are relative to how much was written, not just how often they appear in absolute numbers.",
                disabled=(count_mode == CountMode.ROWS),
            )

        timeline_df = prepare_timeline_data(
            filtered_results,
            count_mode=count_mode,
            active_terms=selected_terms if selected_terms is not None else None,
            aggregation=aggregation,
            normalize=normalize,
            group_by_outlet=color_by_outlet,
            article_group_fn=(
                _article_outlet if color_by_outlet
                else (_article_status_label if color_by_status else None)
            ),
        )

        if timeline_df.empty or timeline_df.get("total", pd.Series([0])).sum() == 0:
            st.info("No term matches for the selected filters.")
        else:
            y_label = "Hits per 1,000 words" if normalize else (
                "Hits" if count_mode == CountMode.HITS else "Articles"
            )
            term_cols = [c for c in timeline_df.columns if c not in ("period", "total")]
            fig = go.Figure()
            for i, term in enumerate(term_cols):
                if color_by_outlet:
                    color = OUTLET_COLORS.get(term, OUTLET_COLORS["unknown"])
                elif color_by_status:
                    color = STATUS_COLORS.get(term, STATUS_COLORS["unknown"])
                else:
                    color = PLOTLY_COLORS[i % len(PLOTLY_COLORS)]
                fig.add_trace(go.Bar(
                    x=timeline_df["period"], y=timeline_df[term],
                    name=term, marker_color=color,
                ))
            legend_title = "Outlet" if color_by_outlet else ("Author status" if color_by_status else "Term")
            fig.update_layout(
                barmode="stack", height=450,
                title="Term occurrences over time"
                      + (" (per 1,000 words)" if normalize else ""),
                xaxis_title="Period", yaxis_title=y_label,
                legend_title=legend_title,
                annotations=[dict(
                    text="Drag to zoom · Double-click to reset",
                    xref="paper", yref="paper", x=1, y=1.07,
                    xanchor="right", yanchor="bottom",
                    showarrow=False,
                    font=dict(size=11, color="grey"),
                )],
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
                filtered_results,
                active_authors=None,
                active_terms=selected_terms if selected_terms is not None else None,
                metric=author_metric,
                aggregation=aggregation,
                include_unknown=include_unknown,
                author_outlet_map=author_outlet_map,
                author_grouping_map=author_status_label_map if color_by_status else None,
                authorless_group_fn=(
                    _article_outlet if color_by_outlet
                    else (_article_status_label if color_by_status else None)
                ),
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
                    if color_by_outlet:
                        color = OUTLET_COLORS.get(author, OUTLET_COLORS["unknown"])
                    elif color_by_status:
                        color = STATUS_COLORS.get(author, STATUS_COLORS["unknown"])
                    elif author == UNKNOWN_AUTHOR:
                        color = "#555555"
                    elif author == "(others)":
                        color = "#cccccc"
                    else:
                        color = PLOTLY_COLORS[color_idx % len(PLOTLY_COLORS)]
                        color_idx += 1
                    fig2.add_trace(go.Bar(
                        x=plot_df["period"], y=plot_df[author],
                        name=author, marker_color=color,
                    ))
                legend_title2 = "Outlet" if color_by_outlet else ("Author status" if color_by_status else "Author")
                fig2.update_layout(
                    barmode="stack", height=450,
                    title=f"Author {author_metric.lower()} over time"
                          + (f" (top {MAX_AUTHORS} + others)" if rest_cols else ""),
                    xaxis_title="Period", yaxis_title=author_metric.capitalize(),
                    legend_title=legend_title2,
                    annotations=[dict(
                        text="Drag to zoom · Double-click to reset",
                        xref="paper", yref="paper", x=1, y=1.07,
                        xanchor="right", yanchor="bottom",
                        showarrow=False,
                        font=dict(size=11, color="grey"),
                    )],
                )
                st.plotly_chart(fig2, use_container_width=True)
                if rest_cols:
                    st.caption(f"{len(rest_cols)} additional authors grouped into '(others)'. "
                               "Use the author status or outlet filters to narrow down.")

            # Author summary table
            st.subheader("Author summary")
            author_totals: dict = {}
            for res in filtered_results:
                authors_here = res.authors if res.authors else (
                    [UNKNOWN_AUTHOR] if include_unknown else []
                )
                for author in authors_here:
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

        # Apply term filter on top of already author/outlet-filtered results
        tbl_filtered = [
            r for r in filtered_results
            if not selected_terms or any(m.term_title in selected_terms for m in r.matches)
        ]

        tbl_df = results_to_dataframe(tbl_filtered, public=True)
        _TAIL_COLS = ["institutional author", "translators", "tags", "page_type", "filename"]
        _base = [c for c in tbl_df.columns
                 if not c.startswith("_term_") and c not in ("_cross_published",) and c not in _TAIL_COLS]
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

    # ---- Documentation (Diátaxis) ----
    with tab_docs:
        _render_documentation()


_DOCS_ROOT = Path(__file__).resolve().parent.parent / "docs"

_DOCS_MAIN = "explanation/methodology.md"
_DOCS_EXTRAS = [
    ("Read more — why an embedding-based false-positive filter was rejected",
     "explanation/false-positives-and-the-semantic-review.md"),
]


@st.cache_data(show_spinner=False)
def _load_doc(rel_path: str) -> str:
    path = _DOCS_ROOT / rel_path
    try:
        return path.read_text(encoding="utf-8")
    except OSError as e:
        return f"_Could not load `{rel_path}`: {e}_"


def _render_documentation():
    st.markdown(_load_doc(_DOCS_MAIN))
    for extra_title, extra_rel in _DOCS_EXTRAS:
        with st.expander(extra_title, expanded=False):
            st.markdown(_load_doc(extra_rel))


# ---------------------------------------------------------------------------
# Top band — always-visible project info
# ---------------------------------------------------------------------------

ABOUT_LONG = """
The **CHOICE project** (2022–2026) is a collective research project funded by the French National Research Agency (ANR) and coordinated by Karine Lamarche. It examines hegemonic and counter-hegemonic dynamics within Israeli society, with a particular focus on forms of political dissent, the actors who engage with them, and the reactions they encounter. It seeks to understand how opposition emerges, circulates, and is received in a context marked by deep power asymmetries.

**Karine Lamarche** is a political sociologist and research fellow at the French National Centre for Scientific Research (CNRS). Her research focuses on power relations, political engagement, and contentious mobilizations, with a long-standing interest in Israeli society and forms of solidarity with Palestinians.

**Nitzan Perelman Becker** holds a PhD in political sociology from Université Paris Cité and is a research engineer at the CNRS as part of the ANR project CHOICE. She is co-author of the documentary *Israel: Ministers of Chaos* (2024, Arte, 69 minutes) and co-founder of the research collective Yaani. Her book *Anatomy of the Israeli Right* (Amsterdam) will be published in September 2026.
"""

st.markdown(
    """
<div style="background:#f0f4f9;border-left:4px solid #2c5282;padding:0.6rem 1rem;
            margin:-0.5rem 0 1rem 0;font-size:0.92rem;line-height:1.4;">
<strong>CHOICE</strong> — researching political dissent in Israeli society ·
ANR-funded, coordinated by <strong>Karine Lamarche</strong> with
<strong>Nitzan Perelman Becker</strong> (CNRS).
</div>
""",
    unsafe_allow_html=True,
)
with st.expander("About the project", expanded=False):
    st.markdown(ABOUT_LONG)

# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

step = st.session_state.step

# In preloaded mode, upload/configure are not accessible
if st.session_state.preloaded and step in ("upload", "configure"):
    st.session_state.step = "dashboard"
    step = "dashboard"

# Legacy "results" state routes straight to the dashboard
if step == "results":
    st.session_state.step = "dashboard"
    step = "dashboard"

if step == "upload":
    step_upload()
elif step == "configure":
    step_configure()
elif step == "dashboard":
    step_dashboard()

# ---------------------------------------------------------------------------
# Footer — credits
# ---------------------------------------------------------------------------

st.markdown(
    """
<hr style="margin-top:2rem;margin-bottom:0.5rem;border:none;border-top:1px solid #e2e8f0;" />
<div style="text-align:center;font-size:0.82rem;color:#666;padding:0.4rem 0 1rem 0;line-height:1.5;">
Computational analysis and app design by
<strong>Sinai Rusinek</strong>
(<a href="https://www.dh-dev.com/" target="_blank" rel="noopener"><em>DH-Dev</em></a>)
for the CHOICE project.
</div>
""",
    unsafe_allow_html=True,
)
