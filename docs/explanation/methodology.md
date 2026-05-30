# Methodology and rationale

This page explains *why* the Linguist Corpus Analyzer is built the way it is. It is not a how-to, and it is not a precise reference — it is the reasoning behind the choices a careful reader will inevitably want to question.

## Why these two outlets

+972 Magazine and Local Call (Mekomit) form an unusual pair. They are editorially aligned and frequently cross-publish, but they write for different audiences in different languages: +972 reaches an international, English-reading audience; Local Call reaches a domestic, Hebrew-reading one. Comparing them lets us ask: **does the same writer, or the same political camp, frame an event differently when addressing the world versus when addressing Israeli society?**

Most existing corpora of Israeli political journalism are monolingual. Pairing these two outlets is the cheapest way to make the bilingual question tractable.

## Why these 19 terms

The terms were chosen because each is contested. *Apartheid*, *Genocide*, *Pogrom*, *Ethnic Cleansing* — these are not neutral descriptions; their use signals a political position. The same is true of softer-sounding terms like *Peace* and *Coexistence*, which carry assumptions about whose conflict is to be resolved and on whose terms.

The list is deliberately small. A larger list would dilute the signal: each additional term increases the chance of finding correlations that mean nothing. Nineteen is enough to cover the major axes of disagreement (violence framing, settler-colonial framing, resolution framing) without overfitting.

## Why the seven-category author system

A two-category split (Jewish / Palestinian) loses too much. A Jewish writer based in New York and one based in Jerusalem are not interchangeable; a Palestinian writer in Haifa, Ramallah, and Gaza face different censorship, mobility, and risk constraints, and those constraints shape what they can say.

Six lived-experience categories plus a residual *Other* lets the data speak about geography and citizenship without inventing finer distinctions than the source spreadsheets can support.

The categories are derived from a researcher-curated spreadsheet, not inferred from text. Two fields drive the assignment: a high-level ethnonational marker and a precision code. Place of residence and country of citizenship are used as fallbacks when the precision code is missing. The full derivation rules are in the [reference](../reference/data-and-terms.md).

## Why per-1,000-words instead of raw counts

The two outlets publish at different volumes, and an active writing month is not directly comparable to a quiet one. Normalising by word count turns frequency into rate, which is what almost every interesting question is actually asking: "how prominent was this term in what was being written?"

Raw counts are still available in the results table for readers who want them.

## What this project does *not* do

- **It does not measure sentiment or stance.** A high count of "Genocide" does not tell you whether the writer accepts the framing or rejects it. It only tells you the word entered the discourse.
- **It does not weight by reach.** A widely-read column and a niche op-ed count the same. Reader engagement data is not in the corpus.
- **It does not detect quotation.** A term inside a quoted source is counted the same as a term in the writer's own prose.
- **It does not eliminate every false positive.** Hebrew morphology is rich: the same letter sequence can sit inside unrelated words. The matchers are tuned to reject the worst-known traps (see [false positives and the road not taken](false-positives-and-the-semantic-review.md) for the details and how the current Massacre regex avoids matching the Hebrew word for *kitchen*), but no purely lexical filter is exhaustive.
- **It does not yet categorise Local Call's Hebrew-only authors.** Categorisation depends on a researcher-maintained spreadsheet that currently covers only +972's English-named writers. Until that gap is closed, status filters apply mainly to the +972 side of the corpus.

These limitations are not bugs. They define what the dashboard can and cannot answer.

## Methodological caution

Quantitative discourse analysis is good at finding patterns and bad at explaining them. A spike in one term, in one author group, in one month is the beginning of a question — never the end of one. The intended workflow is: notice a pattern here, then read the underlying articles.
