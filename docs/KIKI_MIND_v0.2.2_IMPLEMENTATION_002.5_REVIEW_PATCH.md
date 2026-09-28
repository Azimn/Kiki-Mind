# Kiki Mind v0.2.2 - Implementation 002.5 Review Patch

## Two names do not make two brains

**Status:** hostile-review hardening  
**Architecture:** Kiki Mind v0.2.2 remains frozen  
**Base implementation:** 002.4  
**Scope:** physical ledger/projection separation

### Finding

The runner compared resolved path strings to keep the canonical ledger and disposable projection store separate.

That correctly catches identical paths and symlink aliases.

A hardlink is sneakier. Two different path strings can refer to the same physical SQLite file.

The old code would still fail later because the canonical ledger schema is not a projection schema, but that made physical separation an accidental consequence of another invariant.

Gross.

### Resolution

When both files exist, the runner now checks whether the ledger path and projection path refer to the same physical file.

If they do, construction fails immediately with `ProjectionStoreSeparationError`.

### Probe

The hostile test creates a hardlink alias of the live canonical ledger and attempts to use that alias as the projection store.

The runner must reject it before projection-store initialization.

### Architectural consequence

"Separate files" now means separate physical files when the operating system can establish identity.

The shadow brain does not get to move into the canonical apartment just because it printed a second name on the mailbox.
