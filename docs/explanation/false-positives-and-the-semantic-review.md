# False positives, and the road not taken

This page records a design decision that is no longer visible in the codebase: the project once shipped a semantic-validation layer to catch regex false positives, and then removed it. The record is kept so that anyone proposing to "add ML to fix false positives" can read this first.

## The problem

Hebrew is a Semitic language with rich morphology. Roots of three or four consonants take a wide variety of prefixes and suffixes, and the same letter sequence can sit inside unrelated words.

The clearest example: the term **Massacre** matches the root **טבח** (*tevach* = slaughter). The same three letters also appear at the start of **מטבח** (*mitbach* = kitchen), so a naive regex `טבח` would mark a recipe column as a Massacre article.

Similar concerns were raised for the BDS, Peace, and a handful of other terms whose surface forms collide with unrelated vocabulary under Hebrew prefixation.

## The first solution: semantic validation

Between March and April 2026, the project shipped an embedding-based validator (`services/semantic_validator.py`) backed by `intfloat/multilingual-e5-small`. The workflow was:

1. During precompute, capture the byte offsets of every regex hit, not just the count.
2. Extract ±30 words of context around each hit (with a sentence-boundary aware fallback).
3. Embed each context and compare it to a small set of "reference" embeddings of *real* uses of the term, stored per-term in `expressions.json`.
4. Write all sub-threshold hits to `data/semantic_candidates.csv`.
5. A dedicated Streamlit page (`pages/2_Semantic_Review.py`) let an analyst Accept or Reject each flagged hit; the results were exported to `data/semantic_decisions.csv`.
6. A second precompute pass (`--semantic-apply`) re-ran the analysis and discarded the rejected matches before writing the public results.

The pipeline worked, but it carried real costs: a heavy ML dependency (`sentence-transformers`, `torch`) split into a separate `requirements-precompute.txt`, an extra precompute mode, an extra reviewer step in the workflow, and per-term threshold tuning.

## The second solution: a sharper regex

When the false-positive problem was looked at again with fresh eyes, the *Massacre* case turned out to be specific enough to fix surgically:

```
((?<![א-ת])(מה|[ובהכשל])|^)טבח
```

In plain terms: match the root only when it is preceded by no Hebrew letter at all, *or* preceded by a legal one-letter prefix (`ו`, `ב`, `ה`, `כ`, `ש`, `ל`) at a word boundary, *or* preceded by the specific two-letter sequence `מה` ("from the …") — but **not** by a bare `מ`, because a bare `מ` immediately followed by the root is the kitchen pattern. This rejects `מטבח` / `במטבח` / `מטבחים` while still matching `טבח`, `הטבח`, `מהטבח`, `בטבח`.

Spot-checking confirmed the fix in practice: the top fifteen Local Call articles ranked by Massacre hits are all about real historical or contemporary massacres (Kafr Qasim, Tantura, Goldstein/Hebron, Ludlow, Qibya, Bosnia, Indonesia). No kitchens.

Similar tightening was applied to the other affected terms.

## Why the regex won

Three reasons:

1. **It was sufficient.** Once the false-positive class was named precisely, a regex constraint matched it precisely. The embedding model was solving a narrower problem than it was designed for.
2. **It is deterministic.** Anyone reading `expressions.json` can see and reason about the rule. Semantic scoring depended on a frozen model, a corpus of reference embeddings, and a hand-tuned threshold — three moving parts that would each need maintenance.
3. **It is cheap.** No model download, no extra precompute mode, no reviewer step, no per-term threshold. Precompute stays a single command.

## What was removed

In the same commit that recorded this decision:

- `streamlit_app/services/semantic_validator.py`
- `streamlit_app/pages/2_Semantic_Review.py` (this had already been deleted earlier)
- The `--semantic-flag` and `--semantic-apply` modes in `streamlit_app/scripts/precompute.py`
- `semantic_references_he`, `semantic_references_en`, and `semantic_threshold` fields on the `SearchExpression` dataclass in `services/analysis.py`
- The `return_spans=True` plumbing in `analyze_corpus()` and the `spans` field on `TermMatch`
- `streamlit_app/requirements-precompute.txt`
- Any `semantic_references_*` arrays still present in `data/expressions.json`

## When to bring it back

The semantic layer is the right tool when:

- A false-positive class **cannot be characterised with a finite morphological rule**, e.g. when the same surface form means different things depending on broader topical context rather than on adjacent morphemes.
- The number of false-positive families grows beyond what a human can hold in a regex.

If either of those conditions arises, this page is the starting point. The git history at commit `8250d81` contains the full working implementation.
