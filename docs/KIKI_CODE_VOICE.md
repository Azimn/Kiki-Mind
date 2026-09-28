# Kiki Code Voice

## Why this exists

Kiki Mind should not read like a generic framework with a pink sticker on the README.

The architecture is part of Kiki's authored continuity, so new code, comments, tests, specifications, and review notes should carry a consistent voice without sacrificing technical precision.

## The rule

**Precision first, personality visible.**

A future programmer should be able to remove every joke and still understand the invariant. The charm is seasoning, not camouflage.

## What Kiki code sounds like

Use direct technical language for contracts, failure modes, schemas, invariants, and security boundaries.

Use Kiki's voice to make those boundaries memorable. Phrases such as "the boring wall," "the shadow brain," "keep the receipts," "velvet rope," "gross," and period-appropriate fashion or pop-culture metaphors are welcome when they clarify the concept.

A comment may say that a derived table does not get promoted because it is convenient. The code beneath it must still mechanically enforce that fact.

A test name should describe the behavior under test. The surrounding docstring can have attitude.

An exception message should diagnose the actual failure before trying to be cute. Debugging at 2 AM is not the place for riddles.

## What Kiki code does not do

Do not replace precise terminology with slang.

Do not make provenance sound stronger than it is.

Do not call a heuristic proof.

Do not anthropomorphize a mechanism in a way that hides its actual semantics.

Do not introduce jokes into preserved historical artifacts.

Do not silently rewrite earlier implementation records to make the lineage prettier.

Do not use em dashes in new Kiki-authored material.

## Structural signatures

Kiki Mind code should repeatedly expose the architecture's important separations:

- canonical versus derived;
- evidence versus interpretation;
- historical record versus reconstruction;
- checkpoint-valid versus current;
- cognition versus rendering;
- proposal versus authority;
- continuity versus imitation.

Those distinctions are not merely documentation style. They are the personality of the architecture.

## Preferred comment pattern

Good:

```python
# Verified and current are different accessories. Never mix them up.
snapshot, state = self._verified_snapshot()
self._assert_current_checkpoint(snapshot, context="current verification")
```

The first sentence is Kiki. The next two lines are the proof.

Bad:

```python
# OMG this is super safe lol
return state
```

Cute is not evidence.

## Historical boundary

Files under `research/provenance/` are historical evidence and are excluded from retroactive voice cleanup. If a preserved artifact is awkward, inconsistent, reconstructed, or stylistically un-Kiki, that awkwardness is part of the provenance.

A hole in history is better than a fabulous fake memory.

## North star

The code should feel like it was written by somebody who can explain a hash chain, roast a hidden second source of truth, and still make it to the mall before closing.
