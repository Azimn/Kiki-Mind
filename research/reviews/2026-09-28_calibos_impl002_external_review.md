# Calibos External Hostile Review of Kiki Mind Implementation 002

**Date received:** 2026-09-28  
**Source:** user-ferried Calibos review  
**Reviewed code:** Kiki Mind Implementation 002 stack through 002.7  
**Status:** external gate satisfied  
**Provenance:** reviewer report, not Kiki autobiography

## Reviewer verdict

Calibos reported twelve probes with the underlying 60/60 suite green and concluded:

> I could not make the shadow brain the real brain.

No blocking wounds were reported.

Calibos explicitly signed off on merge from the external-review side and stated that Implementation 003 was unblocked from the review side.

## Original wounds revisited

### Nondeterministic fingerprint

Reported closed.

Calibos's cross-process probe matched and the structural fingerprint material held.

### Ambiguous `load()`

Reported closed.

The ambiguous path fails closed and directs callers toward explicitly unverified storage inspection or verified runner paths.

### Fingerprint blind to instance or closure state

Declared boundary accepted rather than mislabeled fixed.

Calibos constructed two closure-based projectors with different thresholds and identical fingerprints.

The important guard still held: replay equivalence detected divergence across the collided fingerprint.

This supports the intended architecture:

the fingerprint is a drift label and tripwire.

Replay equivalence is the authority-bearing guard.

### Schema verifier versus projection-store views or triggers

The exact table-definition laundering wound was reported closed.

Unverified views or triggers remain possible only through raw SQL access, which is outside the current threat model.

Calibos reported that those additions still could not defeat checksum plus replay verification.

## Additional attacks reported

### Hand-forged snapshots

Calibos reported forging snapshots with freshly computed valid SHA256 values at real checkpoints and at GENESIS.

Replay divergence rejected them.

### Rebuild race

Calibos reported 438 canonical events landing during threaded rebuild-race probes.

Stored checkpoints afterward still replay-matched their claimed prefixes.

### Ledger/projection file aliasing

Direct use of the ledger file as projection storage was rejected.

A hardlink alias was also rejected.

### Repair behavior

Raw-SQL corruption was repaired by rebuild.

A stale-but-valid projection propagated `ProjectionStaleError` rather than being mislabeled corruption.

### Event mutation

`EventRecord` is frozen, so mutating canonical event objects during projector application was not available as an attack path.

### `verify_on_open=False`

Calibos reported no internal callers using this option.

## Non-blocking notes

### Repair naming

`repair()` on stale-but-valid projection state raises `ProjectionStaleError` rather than catching up.

The behavior is honest, but the name may imply broader healing than the implementation performs.

### One-time full-chain verification after `verify_on_open=False`

Calibos noted that a ledger opened with `verify_on_open=False` and then committed verifies the current tail, not necessarily the entire middle chain.

A raw SQL middle-chain tamper is outside the current threat model.

A one-time full verification before the first commit remains a reasonable defense-in-depth follow-up.

### Standing tripwire for 003

Any future read path that grants authority without replay equivalence would violate the 002 boundary.

The 20,000-event replay cost is explicitly part of the current guarantee and must not be optimized away silently.

## Kiki acceptance

Architect Kiki accepts this review as satisfying the external hostile-review gate for Implementation 002.

Implementation 002 was merged to `main` in merge commit:

`dddcd938887085e4df34e5279be009f865a0cf44`

The review does not erase declared trust boundaries.

It confirms that the reviewed implementation handles the tested attacks without allowing disposable projection state to acquire canonical authority.

The shadow brain serves.

It does not rule.
