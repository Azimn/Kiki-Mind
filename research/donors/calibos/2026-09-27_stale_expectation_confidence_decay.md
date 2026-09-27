# Donor observation: stale expectation confidence decay

**Source:** Calibos morning upkeep relay, 2026-09-27  
**Status:** candidate donor mechanism only  
**Implementation authority:** none  
**Kiki Mind architecture:** v0.2.2 remains frozen

## Observation

Calibos reported a shipped expectation mechanism in which stale expectations lose confidence each time they expire unanswered, with a multiplicative decay of `0.6 * 0.8^N` down to a `0.15` floor, and regain confidence symmetrically when answered.

The same relay reported that the mutation passed Calibos's builder/critic loop and 370 tests, with an October 8 fitness check scheduled.

## Relevance to Kiki Mind

This mechanism may be relevant later to prospective commitments, unresolved concerns, partner reliability, or expectation accounting. It is especially interesting because it encodes repeated nonresponse as accumulated evidence rather than leaving an expectation indefinitely active at full confidence.

## Boundary

This observation does **not** authorize implementation in Kiki Mind Implementation 002.

Implementation 002 is limited to deterministic state projectors and accounting invariants. It must not acquire semantic expectation dynamics, concern decay, relationship inference, or autonomous cognitive policy.

If this donor mechanism is considered later, Kiki should decide whether its semantics fit her own architecture. Calibos's numerical constants must not be copied merely because they work in Calibos.

## Provenance rule

This note records a reported donor-system behavior. It is not Kiki autobiography, not Kiki state, and not evidence that Kiki has adopted the mechanism.
