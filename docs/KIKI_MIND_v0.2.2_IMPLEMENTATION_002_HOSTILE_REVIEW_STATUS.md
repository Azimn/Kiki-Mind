# Kiki Mind v0.2.2 - Implementation 002 Hostile Review Status

**Internal review status:** complete through Implementation 002.7  
**Latest code-bearing head:** `691e9cade39c3e92c4d0f5c3e486eb66a9cca963`  
**Latest code-bearing CI:** 60/60 tests passed  
**External hostile review:** satisfied by Calibos, 2026-09-28  
**Merge status:** merged to `main` as `dddcd938887085e4df34e5279be009f865a0cf44`  
**Implementation 003:** unblocked from the 002 review side

## Review question

> Where can the shadow brain become the real brain?

Implementation 002 exists to make the answer boring.

Derived state may summarize canonical history. It may not become a second canonical history merely because it is faster, easier, prettier, or psychologically interesting.

## Mechanically closed attack surfaces

### Hidden canonical writes

Reference projectors receive canonical events through read-only ledger APIs.

Projection runs, rebuilds, and repairs are tested not to append canonical events.

The projection store lives in a physically separate SQLite file.

Implementation 002.5 also rejects hardlink aliases of the canonical ledger.

### Forged derived state

Stored projection state carries a checksum.

A forged state with a freshly recomputed checksum still fails because supported verified reads require equality with deterministic replay of the claimed canonical prefix.

The checksum proves storage consistency.

Replay equivalence proves correspondence to canonical history under the active projector.

Those are different claims on purpose.

### Stale state wearing a "current" label

Implementation 002.1 separates:

- `checkpoint_verified()`, which proves replay equivalence to the stored checkpoint;
- `current_verified()`, which additionally requires the checkpoint to equal canonical ledger head.

A replay-valid but stale projection raises `ProjectionStaleError` through the current-state path.

### Canonical append during catch-up

Implementation 002.2 rechecks canonical head before a default `run()` or `rebuild()` returns.

If canon advanced while the projection was catching up, the operation refuses to return the now-stale state as current.

### Unverified-read shortcuts

Implementation 002.3 renamed the low-level storage read to `load_unverified()`.

The ambiguous old `load()` path fails closed.

Implementation 002.7 also removes raw `ProjectionStore` and `ProjectionSnapshot` primitives from the package top-level API.

A deliberate low-level caller can still reach the projection module. The ordinary path points at the verified runner.

### Stale writers

Incremental projection updates use compare-and-swap over the prior canonical sequence and prior event hash.

A runner holding an old checkpoint cannot silently overwrite newer projection progress.

### Version and implementation drift

Projector version mismatch refuses continuation.

Same-version implementation drift is guarded by an implementation fingerprint.

Implementation 002.4 removes process-specific code-object repr material from that fingerprint and verifies stability across independent Python processes.

Source-less dynamically defined projectors are supported without crashing the fingerprint path.

### Projection schema laundering

Implementation 002.6 verifies the normalized `CREATE TABLE projection_state` definition, not merely familiar table and column names.

A counterfeit table with the same labels and weakened constraints is rejected.

### Rebuild authority

Rebuild starts from canonical history and writes disposable projection state.

Repair may rebuild corrupt, checkpoint-mismatched, or replay-divergent state.

It does not repair canonical history from projection state.

It does not reinterpret a stale projection as corruption.

It does not silently repair projector version or implementation mismatch.

## Declared trust boundaries

### Arbitrary projector purity

This is the biggest remaining boundary.

Projectors are ordinary trusted Python code.

The runner replays twice and can catch many forms of nondeterminism, including stateful behavior that diverges between replays.

That is a tripwire, not a mathematical proof of purity.

A malicious or badly written projector could read external mutable state that remains stable during both immediate replays. If that external state later changes, the same canonical ledger and same projector source could produce different derived results.

Implementation 002 does not claim to sandbox arbitrary projector code.

The reference projectors are intentionally pure with respect to their declared inputs.

If future Kiki Mind permits third-party or untrusted projectors, this boundary must be revisited. Candidate solutions include a restricted declarative projector language, sandboxed execution, or explicit dependency capture.

### Direct filesystem adversary

SQLite is not treated as an adversarial security boundary.

A process with unrestricted file access can edit databases outside the application APIs.

Kiki Mind detects many forms of corruption and schema drift, but a sufficiently capable attacker who forges a fully consistent canonical chain remains outside the current threat model.

### Point-in-time freshness

`current_verified()` means current at the final canonical-head observation made by the runner.

A new canonical event can always be appended after that observation and after the method returns.

The architecture does not claim timeless currentness because that would be nonsense in a live system.

### Fingerprints are tripwires

The projector fingerprint helps detect implementation drift.

It is not semantic equivalence proof.

Two different programs could theoretically behave the same, and hidden runtime dependencies can affect behavior without changing source material.

### Supported API is not a sandbox

Removing low-level store primitives from the top-level package API makes accidental misuse less likely.

Python code can still deliberately import internal modules or open SQLite directly.

Structure guides ordinary use. It does not pretend import syntax is a security boundary.

### Long-run verification pressure

Implementation 002 prioritizes correctness over speed.

Verified reads and rebuilds replay canonical history from zero, and some verification paths replay more than once.

The 20,000-event hostile probe passes, but the cost is intentionally visible.

Future optimization must preserve:

- canonical sovereignty;
- delete-and-rebuild equivalence;
- replay verification;
- explicit checkpoints;
- disposable derived state.

Performance pressure is not permission to make a cache indispensable.

## Internal conclusion

The obvious routes by which disposable state could masquerade as current, canonical, or verified state now fail closed.

The remaining weaknesses are not being relabeled as solved problems.

Projector purity, direct filesystem adversaries, point-in-time freshness, fingerprint limitations, and long-run verification cost are explicit boundaries.

That was enough for internal Implementation 002 review.

## External gate result

Calibos completed twelve hostile probes against the reviewed stack and reported no blocking wounds.

The external review independently confirmed the fingerprint, unverified-read, forged-state, rebuild-race, physical-file-separation, repair, and schema defenses.

Calibos also reproduced the declared fingerprint collision boundary using closure state and confirmed that replay divergence, not the fingerprint label, remained the authority-bearing guard.

Three non-blocking notes remain on the record:

1. `repair()` on a stale-but-valid projection raises `ProjectionStaleError` rather than catching up. This is honest but should remain clearly documented because the method name can suggest broader healing.
2. `EventLedger(path, verify_on_open=False)` followed by `commit()` verifies the tail rather than forcing a one-time full-chain verification. This is outside the current raw-filesystem threat model, but a one-time pre-commit full verification is reasonable defense-in-depth.
3. Any future read path that grants authority without replay equivalence is a regression. Long-run replay cost must not become an excuse to make disposable state indispensable.

External review evidence is preserved under `research/reviews/2026-09-28_calibos_impl002_external_review.md`.

Implementation 002 is accepted and merged.

Implementation 003 is unblocked from the review side.

The shadow brain can wear the leather jacket.

It still does not get the deed to the house.
