# Kiki Mind v0.3.0 - Implementation 003.1 Review Patch

## Semantic knives came back

**External reviewer:** Calibos  
**Review date:** 2026-09-28  
**Reviewed head:** `45e723a34e8f8ab36300e35f9ad481ef3f7c9e53`  
**Patch status:** candidate response to external hostile review  
**Merge status:** still held for reviewer confirmation

Calibos ran 22 independent probes against Implementation 003 and found one merge-blocking wound plus three non-blocking semantic wounds.

The blocking result was correct.

The gate permitted commitment forks while the evidence index collapsed the fork to a single `latest_recorded_phase`. That violated the core rule because the projector selected one canonical sibling over another by write order.

Implementation 003.1 changes the contract instead of teaching the projector to hide the contradiction.

## Wound 1: sibling commitment phases

**Status:** mechanically closed.

Commitment lineages are now linear.

A non-root commitment event must name the current lineage head as its prior event.

The gate rejects a second child of the same prior event.

The evidence index independently checks the same invariant and fails closed if malformed canonical history ever presents a fork.

`latest_recorded_phase` is therefore a mechanical property of one linear canonical chain, not a last-writer choice between siblings.

## Wound 2: duplicate made roots

**Status:** mechanically closed.

A `commitment_id` may have exactly one `made` root.

A second root under the same ID is rejected.

If Kiki later makes a genuinely new commitment after an old lifecycle ended, the new lifecycle gets a new commitment ID.

## Wound 3: phase semantics

**Status:** explicitly defined and mechanically enforced.

V1 allows:

- `made -> revised | fulfilled | declined | expired_unresolved`;
- `revised -> revised | fulfilled | declined | expired_unresolved`.

V1 treats:

- `fulfilled`;
- `declined`;
- `expired_unresolved`

as terminal.

The architecture is choosing this lifecycle deliberately. It is not pretending the words have no semantics.

A future architecture version may add reopening semantics, but it must do so explicitly rather than making terminal words secretly nonterminal.

## Wound 4: restriction taint through causal parents

**Status:** mechanically visible path closed; undeclared semantic quotation remains a trust boundary.

A developmental observation now rejects any explicit causal parent carrying `forbid_canonical_experience`.

This prevents a restricted source from being named as causal developmental evidence while dropping the restriction.

The gate still cannot detect a renderer copying restricted content into free text while hiding the source relationship. That is a semantic declaration boundary, not something 003.1 claims to solve.

## Q9: hypothesis echo

**Status:** declared open problem, not merge-blocking.

Calibos demonstrated that a later self-report can semantically quote or endorse an earlier developmental hypothesis and still enter canon as a report that occurred.

That is structurally valid and epistemically dangerous if a future consumer mistakes repeated receipts for independent corroboration.

The specification now states plainly:

- receipt count is not corroboration;
- repeated self-report is not automatically independent evidence;
- the v0.3.0 prediction firewall is normative, not semantic proof;
- the evidence index emits no confirmed-development or corroboration field.

A future mechanical solution likely requires explicit canonical representation of derived claims or interpretation provenance. That is new architecture and is not being smuggled into this patch.

## Reviewer notes accepted without fake fixes

`context_provenance` remains declared metadata.

Opportunity sets remain declared rather than externally proven.

Null and unknown context remain preserved rather than guessed.

Mixed v0.2.2 and v0.3.0 policy history remains legal and verifiable.

`construct_label` remains report metadata only. The evidence index does not aggregate it.

## New hostile probes

003.1 adds tests for:

1. sibling commitment rejection;
2. duplicate-root rejection;
3. terminal-phase rejection;
4. linear revision continuation;
5. restricted causal-parent rejection;
6. semantic echo receipts remaining unclassified as corroboration;
7. index head tracking for linear commitment chains.

## Gate

This patch answers the blocking review wound.

It does not self-certify the external gate.

Calibos should rerun the commitment-fork, duplicate-root, terminal-transition, restricted-parent, and hypothesis-echo probes against the patched head.

The observation may become canon.

The interpretation still does not.
