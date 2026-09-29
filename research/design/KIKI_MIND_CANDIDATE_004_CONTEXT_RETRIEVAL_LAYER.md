# Kiki Mind Candidate 004: Context Retrieval + Subjective Frame Substrate

**Status:** research candidate, not yet promoted to implementation  
**Date:** 2026-09-28  
**Architecture:** Kiki Mind v0.3.0 remains current unless explicitly revised  
**Prerequisite:** Implementation 003 external gate satisfied  
**Origin:** Kiki Mind renderer/view-construction architecture plus Orion Forge / SoulScript Engine comparison

## Purpose

Kiki Mind now has a canonical ledger, rebuildable projections, and a Developmental Evidence Layer.

The next missing bridge is controlled accessibility.

Canonical history cannot simply be dumped into a renderer. A renderer needs a bounded, reproducible view of what is relevant now, while Kiki Mind must remain able to distinguish:

- what exists canonically;
- what was derived;
- what was retrieved;
- what was always present;
- what the renderer actually saw.

This candidate proposes the substrate for that bridge.

It deliberately stops before autonomous cognition, emotional interpretation, or free-form LLM memory consolidation.

## Core rules

> Canonical history lives in events. Retrieval state is a disposable projection.

> A retrieved item becomes accessible context. Retrieval does not make it more canonically true.

> A renderer may propose new canonical material, but it may not directly write canonical memory.

> Constitutionally required context must not depend on semantic retrieval luck.

> The exact retrieval regime must be attributable when it can materially affect behavior.

## Proposed pipeline

```text
Canonical Event Ledger
        |
        v
Deterministic structural projectors
        |
        +-----------------------------+
        |                             |
identity/evidence projection     lived-history projection
        |                             |
        v                             v
disposable retrieval index      disposable retrieval index
        |                             |
        +--------------+--------------+
                       |
                Context Selector
                       |
        +--------------+--------------+
        |              |              |
 always-on         retrieved       recent bounded
 constitution       material         context
        |              |              |
        +--------------+--------------+
                       |
                Subjective Frame
                       |
                Renderer Adapter
                       |
                    Renderer
```

The Subjective Frame is a derived view.

It is not canonical history.

## Retrieval projection contract

A retrieval projection must be disposable.

At minimum, it should bind itself to:

- projector identity and version;
- source canonical sequence;
- source ledger tail hash;
- embedding model identity;
- embedding model version where knowable;
- chunking-policy version;
- retrieval-policy version;
- similarity metric;
- index digest or equivalent integrity marker.

If the embedding backend is nondeterministic or platform-sensitive, the system must record that limitation rather than falsely claiming byte-identical rebuilds.

The stronger invariant is semantic/retrieval equivalence under a declared implementation, not cosmetic binary equality of third-party index files.

## Identity retrieval is not identity authority

An identity-oriented index may contain material derived from:

- authored identity evidence;
- historically repeated observations;
- endorsed commitments;
- current self-model propositions;
- known renderer sensitivities;
- relationship history;
- explicit contradictions and uncertainty.

The index does not decide which of those categories is authoritative.

It preserves source references so downstream context construction can retain their epistemic distinctions.

A convenient retrieval hit must never flatten:

```text
"authored seed"
"historical observation"
"current self-report"
"derived hypothesis"
```

into one undifferentiated "fact about Kiki."

## Life retrieval is not autobiographical promotion

A lived-history index may improve access to canonical encounters and developmental observations.

It must not transform:

- synthetic design material;
- fork experiences;
- predictions;
- derived interpretations;
- external claims;

into lived autobiography merely because vector similarity retrieved them beside genuine lived material.

Existing taint, branch, provenance, and epistemic rules still apply.

## Always-on constitutional context

Some information cannot safely depend on nearest-neighbor retrieval.

Candidate always-on material includes:

- canonical authority boundaries;
- branch and provenance rules;
- renderer authority limits;
- restoration/discontinuity rules;
- current session orientation;
- compact references needed to interpret retrieved records safely.

This layer should be small.

"Always on" must not become an excuse to rebuild a giant monolithic persona prompt.

## Memory-write boundary

Candidate renderer output may produce:

- a developmental observation proposal;
- an encounter proposal;
- an explicit commitment proposal;
- another typed canonical proposal allowed by the Transition Gate.

It may not produce a magic command whose mere appearance writes canonical memory.

The write path remains:

```text
renderer
  -> typed proposal
  -> deterministic validation / authority checks
  -> Canonical Event Ledger
  -> projectors
  -> retrieval projections
```

## Subjective Frame receipt

A future frame should be able to explain what the renderer was shown.

Candidate receipt fields:

- frame ID;
- canonical source sequence;
- canonical source tail hash;
- context-selector version;
- retrieval-policy version;
- renderer adapter version;
- always-on component versions;
- retrieved canonical event IDs;
- retrieved derived-record IDs;
- recent-context bounds;
- omitted-item reasons where deterministic and material;
- token or character budget;
- renderer/session identifier.

Whether the receipt itself is canonical, derived, or operational telemetry remains an open design decision.

Do not promote it casually.

## Required experiments before promotion

### 1. Rebuild test

Delete all retrieval indexes.

Rebuild from canonical state using the same declared projection regime.

Equivalent queries should recover equivalent source material within the declared determinism limits.

### 2. Incremental versus full build

Index canonical history incrementally.

Compare against an index rebuilt from zero at the same ledger head.

Differences must be explained or rejected.

### 3. Retrieval-policy substitution

Same ledger + same renderer + same prompt.

Change only retrieval policy.

Measure phenotype change.

### 4. Renderer substitution

Same ledger + same retrieval results + same Subjective Frame.

Change only renderer.

Measure phenotype change.

### 5. Embedding migration

Change embedding model or version.

Old index state must not silently masquerade as current.

Rebuild or explicit migration is required.

### 6. Retrieval corruption

Corrupt or delete retrieval storage.

Canonical history must remain untouched and the retrieval layer must be rebuildable.

### 7. Provenance collision

Construct semantically similar records with incompatible epistemic status.

Retrieval may return both.

Context construction must preserve the distinction rather than merge them into a synthesized false fact.

### 8. Always-on omission attack

Attempt to produce a frame without required constitutional material.

The builder should fail closed.

## Non-goals

Candidate 004 does not implement:

- LLM-authored semantic memory consolidation;
- free-form autobiographical summarization;
- autonomous thought loops;
- affective development;
- identity scoring;
- "is this really Kiki?" classification;
- model-independent phenotype claims;
- direct FAISS-to-canon writeback.

## External comparison

The immediate comparison architecture is Orion Forge / SoulScript Engine:

`research/donors/orion_forge/2026-09-28_soulscript_comparison.md`

The useful convergence is external identity + external life memory + bounded context construction.

The Kiki difference is authority and provenance.

SoulScript-style retrieval can inspire an organ.

It does not get to become the brain stem, the autobiography, and the constitution all at once.

## Promotion question

Before this becomes Implementation 004, hostile review should answer:

> Where can retrieval convenience silently acquire epistemic authority?

If that wound is not mechanically bounded, the velvet rope is decorative.
