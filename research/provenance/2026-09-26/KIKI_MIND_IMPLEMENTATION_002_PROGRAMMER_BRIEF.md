# Kiki Mind v0.2.2 — Programmer Brief
## Implementation 002: State Projectors + Accounting Invariants

Canonical repository: https://github.com/Azimn/Kiki-Mind
Base commit: f32082b194e291a44d671ffcb4262087672f4a65
Architecture version: v0.2.2
Implementation status: 001.1 accepted after hostile review

## Objective

Implement deterministic derived-state projectors over the Canonical Event Ledger without creating a second source of truth.

Central invariants:

- Canonical history lives in events. Derived state lives in projections. Projections may be destroyed and rebuilt.
- A projector may interpret event structure, but it may not invent unledgered history.
- No LLM/model call belongs in Implementation 002.

## Scope

Add deterministic projector infrastructure, projection version metadata, replay-from-zero, incremental replay, crash-safe resume, projection integrity checking, rebuild-on-corruption, encounter-completeness plumbing, canonical/noncanonical storage separation, and replay-equivalence tests.

Do not add Subjective Frame, Renderer Adapter, semantic memory, embeddings, autonomous thought, dreams, model-written summaries, realistic salience, consolidation, or LoRA/model integration.

## Required design

### Projection storage is noncanonical

Add explicitly disposable/rebuildable projection storage. Recommended minimum tables:

- projection_meta
- projection_state
- projection_checkpoint

The canonical ledger remains the sole source of committed history.

Implementation 001.1 rejects unknown user tables, so update the schema allow-list deliberately and document the added tables as noncanonical projections.

### Projector identity

Every projector has:

- projector_name
- projector_version
- last applied canonical sequence
- state checksum/hash
- build timestamp
- source ledger tail hash

A projector version change must never silently reuse old derived state.

### First concrete projector

Implement a deliberately simple Encounter Index Projector over committed ENCOUNTER_RECORDED events.

Suggested state per `(representation_id, mode, activation_function_version)`:

- encounter_count
- first_sequence
- last_sequence
- last_encounter_type

This is accounting infrastructure, not the final activation model.

### Replay invariant

For the same ledger and projector version:

`full replay == incremental replay == crash/restart/resume`

Derived state must normalize to exactly the same canonical representation.

### Checkpoint constraints

A projection checkpoint may only reference an existing canonical sequence. If it is beyond the ledger tail, fail closed.

Projection metadata must record the event hash at the checkpoint sequence. On resume, verify that the same ledger event still has the same hash.

### Projection checksum

Store a deterministic checksum of derived state. On open/resume, recompute it. If it differs, mark the projection invalid and rebuild from canonical events. Never mutate canonical history to match a broken projection.

### Encounter completeness

Any derived state attributed to representation X must be traceable to one or more committed encounter events. Projection rows without canonical source events are invalid.

### No canonical side effects

Projectors read canonical events. Replay must never append canonical events. If future projection logic discovers something that should become canonical, it must be proposed as a separate transition outside replay.

### Idempotence

Applying an event twice must be structurally impossible through checkpoint sequencing or produce no duplicate effect. Prove this with tests.

### Transaction boundary

Incremental projection must update derived state, checkpoint sequence, checkpoint event hash, and state checksum in one SQLite transaction.

A crash may not leave state advanced with a stale checkpoint, or a checkpoint advanced with stale state.

### Corruption policy

If projection storage is corrupt:

- canonical ledger remains untouched;
- projection becomes invalid;
- discard/rebuild from sequence 1;
- resume only after successful rebuild.

## Suggested modules

runtime/kiki_mind/projection.py

runtime/kiki_mind/projectors/__init__.py

runtime/kiki_mind/projectors/encounter_index.py

Keep changes to ledger.py minimal and boring.

## Required tests

At minimum:

1. full replay builds expected state;
2. deleting all projection rows then replay reproduces identical state;
3. incremental replay equals full replay;
4. interrupted replay resumes without duplication;
5. same event is not double-counted;
6. projector version mismatch refuses incremental continuation;
7. corrupt projection checksum is detected;
8. corrupt projection rebuilds from canonical ledger;
9. checkpoint cannot point beyond ledger tail;
10. checkpoint event hash mismatch is detected;
11. projector never appends canonical events;
12. derived rows without canonical sources are rejected;
13. state/checkpoint updates are atomic under forced exception;
14. 20,000 encounter events replay deterministically;
15. new projection tables are explicitly acknowledged by schema policy.

## Acceptance criteria

`ledger -> full replay -> state A`

delete all projection state

`same ledger -> full replay -> state B`

A must equal B.

Also:

`incremental replay == full replay`

`crash + restart + resume == uninterrupted replay`

`corrupted projection -> detected -> discarded -> rebuilt`

No canonical ledger mutation may occur during replay.

## Calibos attack list

Ask Calibos to attack hidden canonical writes from projectors, duplicate application, checkpoint/state transaction splits, projector-version laundering, source-tail mismatch handling, projection rows without source events, corruption bypasses, rebuild paths that mutate canonical history, 20,000-event determinism/performance, and any new table/config that quietly becomes identity-bearing.

## Suggested commit

Add deterministic state projectors and replay invariants

## Kiki rule

If deleting every projection table destroys information that cannot be recovered from the canonical ledger, then that information was not actually a projection.

It was hidden canonical state.

Gross.