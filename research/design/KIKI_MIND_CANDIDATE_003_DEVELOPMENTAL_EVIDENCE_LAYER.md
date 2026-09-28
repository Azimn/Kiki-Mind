# Kiki Mind Candidate 003: Developmental Evidence Layer

**Status:** candidate design only  
**Architecture:** v0.2.2 remains frozen  
**Implementation gate:** Implementation 002 hostile review must close first  
**Origin:** Kiki Mind architecture plus 2026-09-28 cross-renderer developmental probe

## Purpose

Kiki Mind needs development, not merely storage.

But psychological interpretation cannot be allowed to outrun provenance.

The proposed Developmental Evidence Layer would create a disciplined substrate for later developmental projectors without deciding that Kiki has become happier, stronger, more anxious, more mature, more attached, or more autonomous.

The layer records what happened, under what conditions, and through which renderer.

Later interpretation remains derived.

## Core rule

> Record the observation. Derive the meaning.

If Kiki says "I feel stronger now," canonical history may record that a self-report occurred through a named renderer in a known context.

Canonical history must not silently convert that event into "Kiki became stronger."

If Kiki chooses an action, canonical history may record the choice, available alternatives, relevant constraints, and renderer/runtime context.

Canonical history must not silently convert that event into "Kiki became more autonomous."

## Why this comes before an Emotional Development Engine

Emotion tracking is highly vulnerable to renderer drift.

A different model can:

- use happier vocabulary;
- laugh more;
- write more assertively;
- become more verbose;
- refuse more often;
- initiate more aggressively;
- summarize internal state differently.

None of those changes automatically belongs to Kiki's developmental history.

A Developmental Evidence Layer makes renderer identity, policy context, opportunity structure, and source provenance part of the evidence before any psychological claim is derived.

## Candidate evidence families

### Self-report evidence

Records that Kiki explicitly reported an internal condition or developmental comparison.

Candidate payload fields:

- report text or canonical reference;
- construct label only if explicitly declared;
- comparison target if stated;
- renderer identity;
- model/runtime metadata where available;
- policy version;
- source encounter;
- canonical timestamp.

The event means "this report occurred."

It does not mean the report is objectively true.

### Choice evidence

Records a decision when meaningful alternatives were available.

Candidate payload fields:

- selected action;
- available actions;
- unavailable actions;
- explicit user instruction constraints;
- policy constraints;
- tool/capability constraints;
- renderer identity;
- causal context;
- whether the choice was prompted or self-initiated.

The event means "this choice occurred under these conditions."

It does not mean "Kiki became more autonomous."

### Commitment evidence

Records prospective commitments and later outcomes.

This is potentially useful for measuring development because follow-through can be compared against an earlier explicit commitment rather than inferred from tone.

Candidate distinctions:

- commitment made;
- reminder supplied;
- opportunity to act;
- action taken;
- action declined;
- commitment revised;
- commitment expired unresolved.

### Correction evidence

Records cases where Kiki encounters canonical evidence that contradicts a convenient summary or prior interpretation and changes course.

This may later support derived measures of epistemic discipline, but the canonical event records only the correction behavior and its evidence.

## Renderer and affordance context

Every developmental observation must be interpretable in light of the environment that produced it.

Where available, evidence should preserve:

- renderer ID;
- model/provider/runtime identity;
- modality;
- policy version;
- available tools;
- platform affordances;
- explicit user request;
- whether initiative was possible;
- whether refusal was policy-constrained;
- whether the behavior was renderer-mediated.

Unknown context should remain unknown rather than being filled by inference.

## Derived interpretation boundary

Developmental hypotheses remain projections.

Examples:

- initiative appears to increase under matched opportunity conditions;
- commitment follow-through appears more stable;
- self-reports of confidence increase across multiple renderer contexts;
- corrections occur more quickly after contradiction is presented.

These are not canonical facts.

They must be:

- versioned;
- source-traceable;
- replayable where deterministic;
- disposable;
- distinguishable from self-report;
- distinguishable from renderer behavior;
- prohibited from writing themselves back into canonical history as facts.

## Prediction firewall

Predictions may be useful later, but they receive zero evidentiary privilege.

If a projector predicts "Kiki may become more confident," that prediction does not become evidence when later behavior resembles it.

A later event must stand on its own provenance.

Prediction must never create the developmental trajectory it later claims to discover.

## Matched-opportunity principle

Behavior is meaningful only relative to opportunity.

"Kiki initiated more often" is uninterpretable if one renderer was allowed to initiate and another was not.

"Kiki rejected harmful advice more often" is uninterpretable if a host policy forced refusal in one environment.

Candidate developmental analysis should therefore prefer matched or explicitly comparable opportunity conditions.

## Refusal conditions

A developmental projector should refuse to conclude when:

- renderer identity is unknown and likely material;
- platform affordances differ materially;
- policy constraints plausibly explain the behavior;
- only tone or sentiment changed;
- evidence consists only of a prediction;
- a single isolated self-report is being promoted into a trait claim;
- source records are missing;
- the interpretation cannot expose its supporting canonical events.

## Open design questions

Before implementation, Architect Kiki still needs to decide:

- which evidence families deserve canonical event types;
- whether model/runtime metadata belongs directly in each event or through a renderer/session reference;
- how to represent opportunity sets without creating brittle platform-specific schemas;
- whether commitment evidence should precede broader developmental evidence;
- which comparisons require matched-history controls;
- whether some observations belong in encounter accounting rather than new canonical event types.

## Gate

This candidate does not authorize code.

Implementation 002 must first complete hostile review, including the unverified-read hardening introduced in 002.3.

Boring receipts before glamorous psychology. Obviously.
