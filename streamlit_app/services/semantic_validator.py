"""
Semantic match validator.

Uses a multilingual sentence embedding model to check whether each regex
match occurs in a context that is semantically consistent with the intended
concept. Runs only at precompute time — never imported by the Streamlit app.

Model: intfloat/multilingual-e5-small
  - Requires "query: " prefix for reference phrases
  - Requires "passage: " prefix for context sentences
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from services.analysis import SearchExpression


def _cosine_similarity(a, b):
    """Numpy-free cosine similarity between two 1-D arrays."""
    import numpy as np
    a, b = np.array(a), np.array(b)
    denom = (np.linalg.norm(a) * np.linalg.norm(b))
    if denom == 0:
        return 0.0
    return float(np.dot(a, b) / denom)


def _extract_context(text: str, start: int, end: int, window_words: int = 30) -> str:
    """
    Return the sentence containing [start:end], or a ±window_words word window
    as fallback for very short sentences.
    """
    # Find sentence boundaries
    sentence_re = re.compile(r'[^.!?\n]{5,}[.!?\n]|[^.!?\n]+$')
    sentences = []
    for m in sentence_re.finditer(text):
        sentences.append((m.start(), m.end(), m.group()))

    # Find which sentence contains the span
    for s_start, s_end, sentence in sentences:
        if s_start <= start and end <= s_end:
            if len(sentence.split()) >= 5:
                return sentence.strip()

    # Fallback: ±window_words words around the match
    words = text.split()
    # Find approximate word index of match
    char_pos = 0
    match_word_idx = 0
    for i, w in enumerate(words):
        if char_pos >= start:
            match_word_idx = i
            break
        char_pos += len(w) + 1

    lo = max(0, match_word_idx - window_words)
    hi = min(len(words), match_word_idx + window_words)
    return " ".join(words[lo:hi]).strip()


class SemanticValidator:
    """
    Validates regex matches by embedding their context and comparing to
    reference phrases for the intended concept.

    Usage:
        validator = SemanticValidator(expressions)
        scored = validator.score_spans(text, "TERM_014", [(12, 15), (80, 83)])
        # scored is a list of dicts with keys:
        #   span, matched_text, context, similarity, threshold, passes
    """

    def __init__(self, expressions: list):
        from sentence_transformers import SentenceTransformer
        import numpy as np

        self._model = SentenceTransformer("intfloat/multilingual-e5-small")
        self._np = np

        # Build per-term reference embeddings (query prefix for E5)
        self._refs: dict[str, tuple[object, float]] = {}  # term_id → (embeddings, threshold)
        self._exp_map: dict[str, object] = {e.id: e for e in expressions}

        terms_with_refs = [
            e for e in expressions
            if e.semantic_references_he or e.semantic_references_en
        ]

        if not terms_with_refs:
            return

        print(f"  SemanticValidator: pre-encoding references for {len(terms_with_refs)} terms…")
        for exp in terms_with_refs:
            refs = (
                [f"query: {r}" for r in exp.semantic_references_he]
                + [f"query: {r}" for r in exp.semantic_references_en]
            )
            if not refs:
                continue
            emb = self._model.encode(refs, normalize_embeddings=True)
            self._refs[exp.id] = (emb, exp.semantic_threshold)

    @staticmethod
    def is_available() -> bool:
        try:
            import sentence_transformers  # noqa: F401
            return True
        except ImportError:
            return False

    def has_refs_for(self, term_id: str) -> bool:
        return term_id in self._refs

    def score_spans(
        self,
        text: str,
        term_id: str,
        spans: list[tuple[int, int]],
    ) -> list[dict]:
        """
        Score each span in the text for semantic relevance to term_id.

        Returns a list of dicts (one per span):
          span, matched_text, context, similarity, threshold, passes
        """
        if not spans or term_id not in self._refs:
            # No references for this term — treat all spans as passing
            return [
                {"span": s, "matched_text": text[s[0]:s[1]],
                 "context": "", "similarity": 1.0,
                 "threshold": 0.0, "passes": True}
                for s in spans
            ]

        ref_embs, threshold = self._refs[term_id]

        # Extract contexts for all spans
        contexts = [_extract_context(text, s[0], s[1]) for s in spans]
        passages = [f"passage: {c}" for c in contexts]

        # Batch encode all contexts
        ctx_embs = self._model.encode(passages, normalize_embeddings=True)

        results = []
        for i, (span, context, ctx_emb) in enumerate(zip(spans, contexts, ctx_embs)):
            # Max cosine similarity across all reference embeddings
            sims = [_cosine_similarity(ctx_emb, ref) for ref in ref_embs]
            max_sim = max(sims)
            results.append({
                "span": span,
                "matched_text": text[span[0]:span[1]],
                "context": context,
                "similarity": round(max_sim, 4),
                "threshold": threshold,
                "passes": max_sim >= threshold,
            })

        return results
