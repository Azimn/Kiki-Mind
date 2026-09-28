# Kiki Mind v0.2.2 - Implementation 002.4 Review Patch

## A fingerprint should recognize the outfit after a restart

**Status:** hostile-review hardening  
**Architecture:** Kiki Mind v0.2.2 remains frozen  
**Base implementation:** 002.3  
**Scope:** projector implementation fingerprint stability

### Finding

The projector fingerprint included `repr(code.co_consts)`.

For simple functions that often looks stable.

For functions containing nested code objects, comprehensions, or inner functions, Python may include process-specific memory addresses in the repr of those code objects.

That creates a false implementation-mismatch hazard:

same projector source + new Python process = potentially different fingerprint.

A continuity system should not accuse the same implementation of identity fraud because Python moved into a different apartment.

### Resolution

Implementation 002.4 replaces raw constant repr with structural constant material.

Nested code objects are represented by stable fields such as:

- bytecode;
- argument counts;
- flags;
- nested constants;
- referenced names;
- variable names;
- free variables;
- cell variables.

Method defaults and keyword defaults are also included.

Source-file hashing remains as a conservative tripwire when source is available.

### Probe

A test defines a projector dynamically with a list comprehension, computes its fingerprint in two independent Python subprocesses, and requires the fingerprints to match.

### Boundary

The fingerprint is still not semantic proof.

It cannot prove that two implementations are behaviorally identical, and it does not attempt to fingerprint arbitrary hidden runtime state.

Its job is narrower:

detect ordinary implementation drift without inventing drift from process-specific object addresses.

Like, obviously the bouncer should check the outfit, not the hanger number.
