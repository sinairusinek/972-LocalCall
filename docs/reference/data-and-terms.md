# Reference: data, terms, and statuses

A precise lookup for the corpus, the tracked terms, and the author categorisation scheme.

## Corpus

| | |
|---|---|
| Sources | +972 Magazine (English), Local Call / Mekomit (Hebrew) |
| Articles | 19,744 total (8,440 from +972, 11,304 from Local Call) |
| Date range | 2009-05-04 → 2025-12-25 |
| Last refresh | 2026-05-30 |
| Matched at least one tracked term | 11,676 articles (59 %) |

## Tracked terms

The dashboard searches for 19 political expressions in both English and Hebrew. Each term has multiple surface variants — *Nakba* matches both *Nakba* and *Nakbah*, the Hebrew matcher handles morphological prefixes — so the counts reflect the concept, not a single spelling. The Hebrew patterns are also tuned to reject specific homonym traps (the *Massacre* root **טבח** vs. *kitchen* **מטבח**, for example); the reasoning is documented in [false positives and the road not taken](../explanation/false-positives-and-the-semantic-review.md).

| ID | Term |
|---|---|
| TERM_001 | Nakba |
| TERM_002 | Colonialism |
| TERM_003 | Apartheid |
| TERM_004 | Jewish supremacy |
| TERM_005 | Zionism |
| TERM_006 | Anti-Zionism |
| TERM_007 | BDS / Boycott |
| TERM_008 | Coresistance |
| TERM_009 | Joint struggle |
| TERM_010 | Occupation |
| TERM_011 | Peace |
| TERM_012 | Coexistence |
| TERM_013 | Genocide |
| TERM_014 | Massacre |
| TERM_015 | War Crimes |
| TERM_016 | Crimes against humanity |
| TERM_017 | Fascism |
| TERM_018 | Pogrom |
| TERM_019 | Ethnic Cleansing |

## Author statuses

Every article is attributed to one or more authors, and every author is assigned one of seven statuses. The rationale is described in [explanation: methodology](../explanation/methodology.md).

| Code | Status | Definition |
|---|---|---|
| 1 | Israeli Jew | Jewish, resident or citizen of Israel |
| 2 | Diaspora Jew | Jewish, resident outside Israel |
| 3 | Palestinian citizen of Israel | Palestinian, holds Israeli citizenship |
| 4 | West Bank Palestinian | Palestinian, resident in the West Bank (incl. East Jerusalem) |
| 5 | Gaza Palestinian | Palestinian, resident in Gaza |
| 6 | Diaspora Palestinian | Palestinian, resident outside historic Palestine |
| 7 | Other / not identified | Insufficient information to assign a category |

### Current counts (2026-05-30)

Of 962 +972 Magazine authors, **764** resolve to categories 1–6; the remainder fall into 7. All 1,742 Local Call authors are currently in category 7, pending researcher categorisation.

| Status | +972 Magazine |
|---|---|
| Israeli Jew | 459 |
| Diaspora Jew | 102 |
| Palestinian citizen of Israel | 76 |
| West Bank Palestinian (incl. East Jerusalem) | 56 |
| Diaspora Palestinian | 36 |
| Gaza Palestinian | 35 |
| Other / not identified | 198 |

## Glossary of source-data fields

These appear in the underlying spreadsheet and may be visible in some table views.

| Field | Meaning |
|---|---|
| ethnonational identity | Top-level category: `J` (Jewish), `A` (Arab/Palestinian), `X` / `O` (other / not applicable) |
| Precisions | Sub-category code: `IJ`, `DJ`, `IP`, `WBP`, `EJP`, `GP`, `DP`, `O` |
| place of residence | Free-text residence used as a fallback when Precisions is missing |
| country of citizenship | Free-text citizenship used as a fallback when residence is missing |
