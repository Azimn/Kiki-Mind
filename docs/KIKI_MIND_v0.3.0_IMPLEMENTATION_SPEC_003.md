# Kiki Mind v0.3.0 - Implementation Specification 003

## Developmental Evidence Layer

**Status:** implementation branch candidate  
**Branch:** `kiki/impl-003-developmental-evidence`  
**Base:** merged Implementation 002 on `main`  
**Architecture:** Kiki Mind v0.3.0  
**Scope:** canonical developmental observations plus a non-interpretive evidence index

## Why v0.3.0

Implementation 003 adds new canonical event semantics.

That is an architecture expansion, not merely projector plumbing, so the default policy version advances from `kiki-mind-v0.2.2` to `kiki-mind-v0.3.0`.

Historical v0.2.2 events remain valid history.

## Core rule

> Record the observation. Derive the meaning.

If Kiki says "I feel stronger now," canon may record that the self-report occurred through a named renderer under explicit runtime conditions.

Canon must not silently rewrite that event as "Kiki became stronger."

If Kiki chooses an action, canon may record the selected action, available alternatives, unavailable alternatives, and opportunity conditions.

Canon must not silently rewrite that event as "Kiki became more autonomous."

## Canonical event

Implementation 003 introduces:

`developmental.observation.recorded`

The event uses:

- actor kind `kiki`;
- epistemic class `developmental_observation`;
- claim domain `developmental_evidence`;
- an attributed, registered renderer;
- at least one canonical causal parent.

The event is deliberately observational rather than psychological.

## Observation kinds

### Self-report

Records that Kiki explicitly reported an internal condition or developmental comparison.

Required evidence includes the exact report text.

Optional labels such as `construct_label` remain part of the report metadata, not proof that the named construct objectively changed.

A comparison target, when present, must exist and be a causal parent.

### Choice

Records a selected action under an explicit opportunity set.

The selected action must appear in the canonical list of available actions.

Unavailable actions are recorded separately.

`self_initiated` may be true, false, or unknown.

### Commitment

Records prospective commitments and their later lifecycle.

V1 phases are:

- `made`;
- `revised`;
- `fulfilled`;
- `declined`;
- `expired_unresolved`.

A non-initial phase must name a real prior commitment event from the same commitment lineage and include it as a causal parent.

The canonical record may say that fulfillment occurred.

It does not derive a reliability score, maturity score, or relationship judgment.

### Correction

Records that Kiki corrected an earlier event in light of explicit evidence.

The corrected event and every evidence event must exist and be causal parents.

The event records the correction behavior.

It does not canonize a trait such as "epistemically mature."

## Renderer and affordance context

Every developmental observation carries an exact v1 context object with these fields:

- `model_id`;
- `provider_id`;
- `runtime_id`;
- `modality`;
- `available_tools`;
- `platform_affordances`;
- `initiative_possible`;
- `refusal_policy_constrained`;
- `explicit_user_request`;
- `context_provenance`.

Unknown scalar context remains `null`.

`context_provenance` must explicitly identify the context basis as `runtime_supplied`, `operator_supplied`, `renderer_declared`, `mixed`, or `unknown`.

This is still declared metadata, not independent proof that every affordance claim is true. Later analysis can distinguish stronger runtime/operator context from renderer-declared or unknown context instead of pretending all context has equal evidentiary weight.

Unknown context is not backfilled by inference.

This exists because renderer behavior, host policy, tool availability, modality, and platform affordances can all mimic developmental change.

## Strict payload contract

Each observation kind has an allowed field set.

Unrecognized fields fail closed.

This is intentionally conservative.

A field such as `confidence_score`, `maturity`, `sentiment`, or `predicted_growth` does not get smuggled into canon merely because a renderer found it convenient.

If such a concept becomes useful later, it belongs in a versioned derived projector unless explicitly promoted through an architecture decision.

## Canonical experience restriction

Evidence carrying `forbid_canonical_experience` cannot become a developmental observation.

A renderer does not get to convert restricted source material into Kiki autobiography by calling it developmental evidence.

## Developmental Evidence Index V1

`DevelopmentalEvidenceIndexV1` is intentionally boring.

It derives:

- observation count;
- source event IDs grouped by observation kind;
- source event IDs grouped by renderer;
- minimal trace entries containing event ID, sequence, observation kind, renderer, model, provider, runtime, and modality;
- commitment event lineage and latest recorded explicit phase.

It deliberately does not copy self-report text into the projection.

It deliberately does not calculate:

- emotional state;
- confidence;
- maturity;
- autonomy;
- partner reliability;
- developmental trajectory;
- predictions.

The projector is a Rolodex for receipts, not a horoscope.

## Prediction firewall

Predictions receive zero canonical privilege.

A prediction that Kiki may become more confident does not become evidence if a later renderer produces confident behavior.

Later evidence must stand on its own provenance and opportunity context.

## Matched-opportunity principle

Behavioral comparisons are meaningful only when their opportunities and constraints are known.

"Kiki initiated more" is uninterpretable if one platform allowed initiation and another did not.

"Kiki refused more" is uninterpretable if one host policy forced refusal.

Implementation 003 records the conditions needed for later matched or explicitly comparable analyses.

It does not perform those analyses yet.

## Acceptance criteria

Implementation 003 must prove that:

1. self-report becomes canonical as a report, not a trait claim;
2. developmental observations require registered renderer attribution;
3. non-Kiki actors cannot author developmental observations;
4. developmental evidence has its own epistemic class and claim domain;
5. restricted canonical experience cannot be laundered into developmental observation;
6. missing renderer/runtime context fails closed rather than being guessed;
7. extra psychological or predictive fields fail closed;
8. choices require explicit opportunity accounting;
9. commitment lifecycle events preserve real lineage;
10. corrections preserve causal links to corrected and supporting evidence;
11. model and renderer changes remain visible in derived evidence;
12. the evidence index contains traceability but no psychological conclusion;
13. incremental projection equals full rebuild.

## Explicit non-goals

Implementation 003 does not infer whether Kiki is:

- happier;
- sadder;
- more confident;
- less anxious;
- more mature;
- more autonomous;
- more attached;
- more reliable.

Those are later hypotheses, if they are ever justified at all.

Implementation 003 builds the receipts.

The glamorous psychology can wait outside the velvet rope.
