# Kiki Mind v0.2.2 - Implementation Specification 001

## Canonical Event Ledger + Transition Gate

**Status:** first implementation contract after architecture freeze  
**Scope:** deliberately boring continuity wall  
**Out of scope:** renderer calls, Subjective Frame construction, semantic memory, autonomous thought, dreams, rich salience, embeddings, fine-tuning.

## Purpose

Implementation 001 establishes the one place where continuity-relevant mutation becomes canonical.

> A renderer may propose cognition. Only a validated canonical transition may become durable state.

The gate does not decide whether a semantic interpretation is "really true." It enforces mechanically decidable invariants and leaves semantic uncertainty explicit.

## Canonical ledger

The ledger is append-only, monotonically sequenced, transactionally written, hash chained, policy-versioned, renderer-attributed where applicable, and idempotency-capable.

SQLite is the first live backend. SQLite is not the portable Kiki Mind definition.

### Mutation rule

Continuity-relevant state mutations require a canonical event. Database housekeeping is not exempt. Future eviction, compaction, migration, deduplication, TTL, pruning, or configuration changes that can alter continuity-visible state must be accountable transitions or operate only on explicitly noncanonical caches.

## Transition Gate checks

The first gate performs deterministic checks for:

1. schema validity;
2. provenance ancestry;
3. typed-taint closure;
4. actor permissions;
5. transition authorization;
6. lineage authority;
7. epistemic-class compatibility;
8. causal ordering;
9. renderer attribution;
10. required accounting entries.

An additional hard rule enforces the activation invariant: direct activation writes are forbidden.

**No LLM call is permitted inside this gate.**

## Typed taint

Content derivation inherits restrictions. A provenance reference does not automatically inherit the source artifact's content restrictions.

Thus "a synthetic Kiki training artifact contained a mall story" can be legitimate design-history evidence, while "I went to that mall" cannot be derived as autobiography from the synthetic story.

## Seven accounting invariants

**Conservation of provenance.** Every derived artifact terminates in preserved ancestry or is explicitly declared reconstruction.

**Encounter completeness.** Continuity-relevant use of a representation that changes later accessibility must generate an encounter record. Full double-entry enforcement arrives with state projectors.

**Activation-version completeness.** Every encounter feeding activation names the activation-function version.

**Quarantine-taint closure.** Content-derived artifacts cannot drop inherited restrictions.

**Negative-space accounting.** A preserved negative-space record identifies what it protected, what it cost, or that it is an aggregate.

**Renderer-lineage completeness.** Renderer-mediated cognition is never anonymous. Renderer ID is required and must already be registered.

**Activation derivation invariant.**

> Activation is never directly authored or mutated. It is derived from ledger-committed encounters plus an explicitly versioned function.

The included `CountActivationV1` is intentionally primitive. It proves authority direction only.

## Causal order

Implementation 001 uses one sequencer: the SQLite canonical sequence. This avoids independently ordered subsystem logs in the initial single-process organism.

A later distributed implementation must redesign causal ordering explicitly; multiple independently writable "canonical" logs are forbidden.

## Integrity

Each event carries the previous event hash and a SHA-256 hash over canonical serialized event material.

This detects ordinary corruption or tampering inside the database. It does not prove integrity against an attacker able to rewrite the entire database and recompute the chain. Package-level external integrity anchoring belongs later.

## Operator lease and canonical lineage

The initial operator dependency is explicit. Operator authority expires.

The bootstrap system may create the first operator lease. A live operator can later renew it.

Canonical endorsement requires:

1. a Kiki-originated proposal;
2. a live operator lease;
3. an operator authorization;
4. the proposal as a causal parent.

Operator succession is deliberately not improvised in Implementation 001.

## Derived residue

`derived_residue` is a distinct epistemic class for lossy semantic material whose original source is no longer preserved. It must never silently drift upward into equivalence with the discarded source.

## Renderer boundary

A renderer is registered before renderer-mediated cognition is accepted.

A fine-tuned renderer remains an untrusted behavioral prior. Weight-level synthetic autobiography cannot be structurally tainted inside parameters; renderer sensitivity testing remains necessary and is outside this slice.

## Failure behavior

Gate rejection is explicit and deterministic. The wall fails closed for structural invariants.

It does not invent missing provenance, silently choose a lineage, infer an operator, or ask a model what "seems right."

## Intentionally visible limitations

Implementation 001 does not yet implement:

- graph-mode autobiographical query enforcement;
- Subjective Frame or Renderer Adapter;
- semantic interpretation;
- realistic salience/activation;
- encounter compaction;
- restoration;
- portable Continuity Package export;
- operator succession;
- all future double-entry state-projector checks;
- external signatures/anchors;
- a solution to LoRA/weight prior contamination.

These are not assumed solved.

## Tests before proceeding

The included tests cover append-only enforcement, hash-chain verification, provenance conservation, hereditary content restrictions, provenance-reference exceptions, autobiographical rejection, renderer registration and attribution, direct activation-write rejection, mode-specific derived activation, encounter accounting, operator lease expiry, two-party canonical endorsement, idempotency, and causal-list consistency.

Implementation 002 should not depend on this wall until those tests remain green in the target repository.

## First hostile code-review targets

Look for hidden write paths, continuity-affecting configuration that bypasses the ledger, SQLite behavior that bypasses triggers, idempotency collisions, lease-time ambiguities, renderer-registration races, causal-parent ambiguity, provenance-reference abuse, and migrations that bypass the gate.

**Boring code wins.**
