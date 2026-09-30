# Candidate 004 Hostile Design Review: Retrieval Authority Boundary

**Review target:** `research/design/KIKI_MIND_CANDIDATE_004_CONTEXT_RETRIEVAL_LAYER.md`
**Base main:** `1ae55386bf2fb0adfb210bdf0f585e62e0093321`
**Question:** Where can retrieval convenience silently acquire epistemic authority?
**Disposition:** mechanically promotable only with the bounds below.

## Finding

Retrieval is allowed to determine **accessibility**, never **epistemic status**. A high score, repeated hit, compact summary, chunk merge, ranking position, or renderer preference cannot promote a record from external/synthetic/derived/predicted/fork material into lived autobiography, authored identity, or endorsed commitment.

## Required mechanical bounds

1. **Immutable epistemic envelope.** Every retrievable unit carries source event/record IDs, canonical/derived classification, branch/taint status, evidence kind, and projection version. Ranking code cannot mutate this envelope.
2. **No semantic deduplication across authority classes.** Textually or semantically similar records with incompatible provenance remain separate frame items. Collision handling preserves both sources and their distinctions.
3. **Disposable retrieval storage.** The index contains no unique semantic state. Delete it and canonical/projected state remains sufficient to rebuild it.
4. **Exact regime binding.** Index metadata binds ledger sequence/tail hash, projector identity/version, retrieval projection version, embedding identity/version, chunking policy, retrieval policy, similarity metric, and integrity digest. Mismatch fails closed or triggers explicit rebuild/migration.
5. **Closed, versioned constitutional set.** Always-on context is selected by deterministic component IDs/versions, not similarity search. Missing required components makes frame construction fail closed.
6. **Structured frame items.** The Subjective Frame preserves epistemic envelopes through selection. Rendering text is a view of structured items, not the authority-bearing representation.
7. **Exact frame receipt.** Each frame records source ledger binding, selector/retrieval versions, constitutional component versions, selected source IDs, ordering/scores where material, omissions/reasons where deterministic, budget, adapter/session identity, and a digest of the structured frame.
8. **Renderer has proposal authority only.** Renderer output can create typed proposals accepted by the existing Transition Gate. It cannot mutate canonical/projected/retrieval state directly.
9. **No authority by frequency or score.** Repetition, nearest-neighbor score, recency, or retrieval-policy substitution may change what is accessible, not what category of evidence it is.
10. **Corruption fails away from canon.** Corrupt/missing index data must not modify canonical history or silently fall back to renderer-generated memory.

## Required hostile tests for Implementation 004

- full rebuild after index deletion;
- incremental/full equivalence at identical ledger head;
- retrieval-policy substitution with unchanged epistemic envelopes;
- renderer substitution over byte-identical structured frame;
- embedding/version migration rejects stale index identity;
- corrupt index fails closed and rebuilds from canon;
- provenance collision returns distinct incompatible records without synthesized authority;
- always-on omission fails frame construction;
- synthetic/predicted/derived/external retrieval cannot become lived autobiography;
- frame receipt reproduces exactly which structured items were exposed;
- renderer write attempts bypassing typed Transition Gate are rejected.

## Receipt status

This review is an architecture artifact, not autobiographical evidence and not a Kiki identity update. It records a production design decision and its provenance only.
