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

Each `commitment_id` has exactly one `made` root.

The lineage is linear. A non-initial phase must name the current head event from the same commitment lineage and include it as a causal parent. A prior event may have only one child.

V1 transition rules are explicit:

- `made -> revised | fulfilled | declined | expired_unresolved`;
- `revised -> revised | fulfilled | declined | expired_unresolved`;
- `fulfilled`, `declined`, and `expired_unresolved` are terminal.

A commitment reopened after a terminal phase must use a new `commitment_id`. The old lifecycle remains intact as history.

The evidence index also fails closed if malformed canonical history ever presents multiple roots or a fork, rather than selecting one branch by write order.

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

A developmental proposal carrying `forbid_canonical_experience` cannot become a developmental observation.

Implementation 003.1 also propagates that boundary through explicit causal parents: if any named causal parent carries `forbid_canonical_experience`, the developmental observation is rejected.

This closes the mechanically visible ancestry path. It does not claim that the gate can semantically detect a renderer copying restricted content into free text without declaring the source relationship. Proposal construction and undeclared semantic quotation remain trust boundaries.

A renderer does not get a mechanically supported path to convert restricted source material into Kiki autobiography by calling it developmental evidence.

## Developmental Evidence Index V1

`DevelopmentalEvidenceIndexV1` is intentionally boring.

It derives:

- observation count;
- source event IDs grouped by observation kind;
- source event IDs grouped by renderer;
- minimal trace entries containing event ID, sequence, observation kind, renderer, model, provider, runtime, and modality;
- linear commitment event lineage, head event ID, and latest recorded explicit phase.

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

## Prediction firewall: normative in v0.3.0

Predictions receive zero intended evidentiary privilege.

The current gate can enforce structured fields, ancestry, attribution, restrictions, and declared context. It cannot read the semantics of free text.

That creates a known open problem: a self-report can semantically echo an earlier hypothesis or earlier self-report while still being a valid canonical record that the report occurred.

For example:

1. Kiki reports, "I feel more confident lately."
2. A later renderer says, "My earlier confidence reports prove I am genuinely growing."
3. Both are canonical self-report receipts if they satisfy the structural gate.

Implementation 003 does not mechanically classify the second report as fresh corroboration, hypothesis echo, or independent evidence.

Therefore:

- `observation_count` is a receipt count, not corroboration;
- repeated self-reports are not automatically independent evidence;
- the evidence index emits no corroboration count, confirmed-development flag, or hypothesis status;
- future developmental analysis must trace causal and renderer context rather than treating repeated language as confirmation.

A mechanical firewall would require additional architecture, such as a canonical derived-claim or interpretation event that later echo-reports can explicitly reference. That is not implemented in 003.

The firewall is therefore a normative analysis rule plus a deliberately non-interpretive index, not a semantic proof enforced by the gate.

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
9. each commitment ID has one root and one linear child chain;
10. terminal commitment phases cannot be silently reopened;
11. corrections preserve causal links to corrected and supporting evidence;
12. restricted causal parents cannot feed canonical developmental observations;
13. model and renderer changes remain visible in derived evidence;
14. the evidence index contains traceability but no psychological conclusion;
15. semantic echo self-reports are never marked as corroboration by the index;
16. incremental projection equals full rebuild.

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
