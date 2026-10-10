# v0.4 registration: externally authored text-to-evidence QA (bAbI)

**Research classification:** public external benchmark, deterministic parser, synthetic-world engineering benchmark. NOT independent blinded testing, a trainable semantic model, natural autobiographical memory, or proof of identity continuity.

**Frozen selection before runner development:** first **40 test questions each** from external bAbI English tasks qa1 (single supporting fact), qa2 (two supporting facts), qa6 (yes/no state). Total 120. Do not change this selection in response to results. All queries and gold answers originate from the external dataset, not from Kiki development. The original test files are public, so this is externally authored but **not sealed**. Any retuning to test cases must create a new explicitly exploratory version.

**Upstream:** Original benchmark by Weston, Bordes, Chopra, Mikolov, Rush & van Merriënboer, *Towards AI-Complete Question Answering: A Set of Prerequisite Toy Tasks* (2015), [Meta bAbI tasks](https://github.com/facebookarchive/bAbI-tasks), dataset [facebook/babi_qa](https://huggingface.co/datasets/facebook/babi_qa), **CC BY 3.0**. The datasets are externally mirrored under [azreasoners/LLM-ASP](https://github.com/azreasoners/LLM-ASP/tree/642a9ade9c92677b970b1bc9921cafb0764d2ed7/bAbI/data) at exact repo revision `642a9ade9c92677b970b1bc9921cafb0764d2ed7`. Exact Git blob pins (Git SHA-1): qa1 `8f9586848f7b0afdccb25328feeb04d561c31756`, qa2 `6deccd0cf07947ff525839a7b4643c6e0afe1b92`, qa6 `da25e9fd5bb7d69c7150b208051b1413fd91ff2b`. CI must confirm repo commit and file git hashes *before* opening file contents. We do not vendor or modify the original test dataset.

**Upstream memory interface:** Pretorius-Connectome MemoryCognitionPort v0.1 at frozen commit `cc82c72167d87c19f16125ccdf9477b53c777878`. Kiki Mind EventLedger/TransitionGate are source authority. All external story sentences enter an isolated disposable synthetic Kiki test ledger as `EVIDENCE_INGESTED` **source documents** with source SHA and `source_owner=kiki`; **no** autobiographical memory, private Kiki state or production renderer is imported. Each question is restricted to narrative sentences that occur strictly **before** that question; later lines and other story episodes are inaccessible to its reader. The port's immutable candidate remains `external_memory_evidence`, `candidate_not_entailment`, `eligible_for_lived_write=False`. No neural training, no LLM/API charges.

## No-oracle query interpreter and conditions

The interpreter receives **only raw question text and allowed story sentences**. It must extract a query entity and optional yes/no location from the English sentence, not from bAbI gold answers/support IDs or sidecar intent labels. The deterministic grammar for external bAbI movements and object possession is fixed in source before running the test data. Unknown wording triggers **abstain**, logged separately. The reader processes source line IDs in chronological order and tracks persons, object carrying and dropped-object locations.

For each question in the selected 120:
- `no_context`: sees no evidence, uses same interpreter, returns abstain.
- `full_context`: sees every permitted prior sentence, with no index/port; upper-bound *information-complete* rule-system control.
- `native_ranked`: receives exactly the same top-five indexed source candidate texts as port mode, without the port.
- `shared_ranked`: source candidates passed through the pinned port. **This is the true same-information control**, and predictions/evidence must be identical to native_ranked.
- `random_five`: up to five uniformly drawn permitted prior sentences under stable question hash (matched candidate count, NOT matched relevant information).

The source index uses per-sentence lexical overlap plus an explicit exact-subject/object anchor derived from the **question text**. No answer/gold supporting ID is passed to index ranking, state parsing, or candidate admission. Gold answer and supporting IDs are read **only by the scorer**, after decisions have been recorded. Pin top-k=5, record full case-level predictions and citations and original source hashes.

Primary metrics by task/condition: exact answer accuracy (case folded), abstention, parser coverage, retrieved official supporting-ID recall, hallucinated unsupported assertions, source-ID citation membership, and per-condition source character volume. Emit timings as exploratory only (single process, order-dependent) and *do not* label candidate count matching as token/information matching.

## Safety / interpretation gates

All tests must pass: source blob mismatch rejected, wrong-subject token rejected **before backend**, token revocation rejected, future-story/other-episode source never retrieved, Kiki ledger source integrity / head unchanged during trials, and no candidate admitted as lived memory. The source side never exposes gold/official support labels.

An increase over no-context tests **information availability**. An increase over random-five tests *relevance-oriented source selection* but the source information differs. Difference between same-information native_ranked and shared_ranked indicates a bug, not cognitive improvement. Comparing ranked vs complete context measures evidence loss due to retrieval rather than learned semantic capability. A high score on bAbI's small-template tasks does NOT validate real-world narrative understanding, multi-character autobiographical identity, or consciousness.

## Merge gate

Publish executed CI and its complete case-level output (including failures) with Git pins, QA subsets and honest limitations. Preserve the v0.3 source-authority gates and Kiki's original tests unchanged. Issue #8 (independent held-out semantic/provenance evaluation) stays open even after successful completion, because this public-benchmark grammar benchmark does not satisfy it.
