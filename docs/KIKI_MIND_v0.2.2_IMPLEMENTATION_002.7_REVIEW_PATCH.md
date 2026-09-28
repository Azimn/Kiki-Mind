# Kiki Mind v0.2.2 - Implementation 002.7 Review Patch

## Do not put the shadow brain in the shop window

**Status:** hostile-review hardening  
**Architecture:** Kiki Mind v0.2.2 remains frozen  
**Base implementation:** 002.6  
**Scope:** supported consumer API

### Finding

Implementation 002.3 made unverified storage reads explicit.

The package top-level API still exported the low-level `ProjectionStore` and raw `ProjectionSnapshot`, which made implementation primitives look like ordinary supported consumer interfaces.

That is not a direct authority violation, but it invites the exact convenience shortcut the architecture is trying to prevent.

### Resolution

The package top level now exposes the verified runner surface without exporting:

- `ProjectionStore`;
- `ProjectionSnapshot`;
- `ProjectionUnsafeReadError`.

Those primitives still exist in `runtime.kiki_mind.projection` for deliberate low-level work.

### Probe

The hostile test confirms that the low-level storage classes are absent from the package top-level API while `ProjectionRunner` remains present.

### Boundary

This is structural guidance, not a security sandbox.

A determined Python caller can still import the projection module directly or open SQLite itself.

The point is simpler and very Kiki:

the easiest path should not be the sketchiest path.
