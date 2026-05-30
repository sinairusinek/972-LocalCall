# How to use this app

A practical walk-through of the dashboard, with worked examples. Read top to bottom on your first visit; come back to specific sections later as a recipe book.

## What you are looking at

The dashboard analyses **19,744 articles** published between **May 2009 and December 2025** by two sister outlets:

- **+972 Magazine** — English-language, 8,440 articles
- **Local Call (Mekomit)** — Hebrew-language, 11,304 articles

For each article it counts how often each of 19 political terms appears, then lets you slice the data by date, author, outlet, and author status. Every figure on the dashboard is filtered by the choices in the sidebar.

## The sidebar — your control panel

Four controls drive everything you see:

- **Time aggregation** — day, month, or year. Use month for most exploration; switch to year for a long arc, day for a specific incident.
- **Terms to show** — defaults to all 19. Untick to focus.
- **Author status** — the seven-category breakdown (Israeli Jew, Diaspora Jew, Palestinian citizen of Israel, West Bank, Gaza, Diaspora Palestinian, Other / not identified).
- **Outlet** — +972, Local Call, or the cross-published subset.
- **Color by** — switch the chart palette between terms, outlets, and author statuses without changing the underlying data.

A **Pick specific authors** expander lets you narrow to a handful of writers when you want a closer reading.

## How the tabs work together

The sidebar is **global**: every change there updates the Linguistic timeline, the Author timeline, and the Results table at the same time. There is one underlying filtered set of articles, and the three data tabs are three views onto it.

Controls that live **inside** a tab are local to that tab. Count mode and Normalize affect only the Linguistic timeline; the POSTS / WORDS toggle only the Author timeline; the row-search box only the Results table. Switching tabs preserves the sidebar selection but resets these local controls' visual state where relevant (e.g. chart zoom).

A few practical consequences:

- **Chart zoom is visual only.** Dragging on a chart to narrow a date range does not narrow the data feeding the Results table or the export. To restrict by date for export, use the sidebar (and/or sort/filter in the downloaded TSV).
- **The Results table is the ground truth.** Any pattern you notice in the charts can be inspected article by article in the table under the same filters. If a chart spike looks wrong, the table will show you the rows behind it.
- **Filters compound silently.** A surprising chart is often a filter you forgot you set in another part of the sidebar. The corpus stats line in the sidebar shows the current effective sample size — watch it shrink as you add filters.

## The four tabs

### 1. Linguistic timeline

A stacked bar chart of term frequency over time, plus a **Term summary** bar on top that shows the totals for the current filter.

- **Count mode** — *Hits* counts every occurrence; *Articles* counts each article once regardless of how many times the term appears.
- **Normalize (per 1,000 words)** — turns counts into rates, which makes quiet months and busy months comparable.

> **Tip:** Drag horizontally on any chart to zoom into a date range. Double-click to reset.

### 2. Author timeline

The same time axis, but stacked by author instead of by term. Useful for asking *who* was driving a trend, not just *what* was being said. Pick **POSTS** to count articles, **WORDS** to count volume.

The top 30 authors are shown by name; the rest are bundled into an "(others)" band. Below the chart, an **Author summary** table lists every author in the current filter, ranked by article count, with their status label and per-1,000-word match rate.

### 3. Results table

The article-level view. One row per article, with date, author, outlet, title, URL, and per-term hit counts. Two things you can do here:

- **Search rows** — free-text filter across all visible columns.
- **Download filtered results (TSV)** — exports exactly what you see, for spreadsheets or further analysis.

### 4. Methodology

The reasoning behind the design choices: why these two outlets, why these 19 terms, why per-1,000-words, what the dashboard can and cannot answer.

## Worked examples

### Example A — How is *Nakba* used differently across outlets?

1. In the sidebar, clear the **Terms** picker and select only **Nakba**.
2. Set **Color by** → *Outlet*.
3. On the **Linguistic timeline**, watch the May spikes (Nakba Day) and any war-related months. Compare the +972 bar height to the Local Call bar height in the same month.
4. Turn **Normalize (per 1,000 words)** on. The picture often changes — one outlet may use the term more *per unit of writing* even while publishing fewer absolute mentions.

### Example B — Which authors most concentrate the term *Apartheid*?

1. In the sidebar, select only **Apartheid**.
2. Open the **Author timeline** tab.
3. Scroll to the **Author summary** table and sort by `matches_per1k` descending.
4. The top of the list is the authors with the highest *concentration*, not the highest *volume*. That distinction matters for any claim about who "owns" a framing.

### Example C — Did coverage shift after a specific event?

1. Pick the term and the outlet you care about.
2. On the timeline, drag to zoom into a window around the event date.
3. Eyeball the average bar height before and after. For a sharper read, open the **Period totals** table under the chart and compute the difference yourself, or download the TSV.

### Example D — Compare two author groups on the same term

1. Pick one term.
2. Set **Color by** → *Author status*.
3. In **Author status**, keep only *Israeli Jew* and *Palestinian citizen of Israel*.
4. Read the stacked bars: the same term can have very different temporal profiles across groups, even within the same outlet.

### Example E — Export a slice for a chart or write-up

1. Configure the sidebar to the exact slice you want (term, outlet, date window via zoom is *not* exported — apply filters in the sidebar instead).
2. Open the **Results table** tab.
3. Click **⬇ Download filtered results (TSV)**. The file contains metadata and per-term hit counts; safe to share.

## Reading tips

- **Rate beats raw count.** Whenever you are comparing two outlets, two periods, or two author groups with different sizes, turn on normalisation.
- **A spike is the start of a question, not the answer.** Use the **Results table** to read the underlying articles before you commit to an interpretation.
