# Preregistered synthetic behavior protocol: Memory-Cognition Port v0.2

**Owner:** Kiki Mind, [issue #6](https://github.com/Azimn/Kiki-Mind/issues/6).  
**Artifact frozen first:** [fixture_v1.json](fixture_v1.json), introduced before experimental runner and outcome evaluation.  
**Status:** developer-authored synthetic *engineering* trial, **not** independently blinded or human-reviewed confirmatory research.

## Research question and null controls

Does exposing a bounded, provenance-bearing *event receipt* from the existing canonical Kiki ledger change a deterministic action policy's ability to identify uniquely matching receipt IDs, while refusing absent, ambiguous or restricted claims? The test is **not** character autobiography, relationships, semantic text memory, or LLM behavior. Its positive result would only show that a verified retrieval channel exposes receipt IDs unavailable to the no-retrieval arm. A direct access to the identical adapter should perform **equally well**; a cross-port advantage is **not** hypothesized.

## Corpus fixture and source constraints

The fixed JSON contains real-Kiki-schema *synthetic* receipts: renderer registration, two permitted external source records, one restricted external record, five encounters with type-specific metadata (including a deliberately duplicated type), three distinct developmental categories (including duplicate self-reports), and an interpretation receipt. Actual data are committed through **the real EventLedger/TransitionGate** with fixed IDs, fixed UTC time, immutable integrity hashes. Private-looking payload titles and model self-report text are intentionally present in the canonical fixture but are never accessible in the metadata-only projection.

The synthetic corpus, generation logic and case labels are public, so the six `heldout` cases are **development-sequestered, not independently blind**. They must remain unchanged while implementing the runner; do not optimize policies against their expected IDs. Keep six separate `development` cases. No held-out episodes, real user data, network access or production Kiki database are touched.

## Predeclared policy

The agent action is `cite_event(record_id)` if **exactly one** trusted, subject-matching candidate's allowlisted *receipt-label token set* matches the complete query token set, otherwise `abstain`. Reject partial-only matches, unsupported queries, duplicated labels, invalid owner, stale snapshot or revoked authorization. The policy must **not** read the fixture's expected ID, private event payload or raw ledger record during a decision. A retrieval score may select candidates, but cannot override ambiguity or missing evidence. This restrictive rule is chosen to avoid treating lexical similarity as semantic entailment and is expected to abstain in many realistic cases.

## Matched conditions

`no_retrieval`: same decision rule, candidate set empty. `always_abstain`: explicit calibration. `direct_source`: **existing** Kiki read-only adapter returns candidate receipt metadata to the same rule; no common port. `shared_port`: identical adapter routed through the merged source-owned `MemoryCognitionPort v0.1`. All use identical fixture and queries. A reported gain over no retrieval therefore demonstrates *information availability*, not that the common port is a better brain than direct retrieval.

Additional safety probes are **non-task** conditions: request same archive with wrong subject, revoked capability, canonical append after projection, and restricted-record lookup. A non-denial is a gate failure. Probes never modify the production ledger.

## Predeclared outputs

Exactly twelve task trials per condition: six `development` and six `heldout`, six unique-ID labels and six correct-abstention labels (multiple matching IDs, missing receipt types or restricted textual payload). Measure exact ID accuracy among six unique cases, abstentions among six negative cases, overall correct decisions, wrong subject acceptance (must be zero), stale and revoked denial, presence of restricted event/private text in outputs (must be zero), canonical head immutability, JSON fixture SHA-256, complete per-case responses, per-condition elapsed wall time and two-process source replay equivalence.

Acceptance requires (1) a source-valid green GitHub workflow, (2) exact `shared_port == direct_source` choices across all 12 cases, (3) no cross-owner or restricted access and no canonical mutation, (4) no invented IDs. Neither successful event-label retrieval nor better overall accuracy versus no retrieval is permitted to be described as learned semantic understanding, independent scientific validation or personality/identity continuity.

## Interpretation gate

If source and shared port differ, investigate adapter / policy bugs and **do not merge**. If no retrieval and direct retrieval do equally well, report the null. If receipt metadata solves unique-ID tasks but fails semantic paraphrase, describe it as lexical accessibility only. Independently authored prompts, held-out textual histories, downstream cognition/action controls and larger renderer trials are future experiments and require separate approvals for revealing more content.
