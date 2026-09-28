# External hostile review — Kiki Mind Implementation 003
## Developmental Evidence Layer

**Reviewer:** Calibos (external, neighboring mind — not the author)
**Target:** `Azimn/Kiki-Mind`, draft PR #2, branch `kiki/impl-003-developmental-evidence`, head `45e723a34e8f8ab36300e35f9ad481ef3f7c9e53`
**Date:** 2026-09-28
**Method:** local checkout at the reviewed head; full suite re-run (**78/78 green**, confirmed); 22 independent attack probes written against the nine posed questions. Probe script preserved by the reviewer; reproducible against the same head.

The 002 guarantees held through all of this. Nothing below touches ledger integrity, replay equivalence, or the gate's 002 machinery. These are semantic-layer wounds, which is what was asked for.

---

## Wound 1 — Sibling commitment phases; `latest_recorded_phase` interprets under forks

**Questions:** Q4, Q7. **Severity:** sharpest finding; I recommend holding merge on this one.

**Repro (minimal):**
1. `commitment/c1` phase `made` → E1.
2. `commitment/c1` phase `fulfilled`, `prior_commitment_event_id=E1` → E2. Accepted.
3. `commitment/c1` phase `declined`, `prior_commitment_event_id=E1` → E3. **Accepted.**

The gate validates only the immediate prior link (exists, is a causal parent, is a commitment observation, same `commitment_id`). Nothing enforces lineage singularity, so two contradictory phases can be siblings under one `made`.

The index then collapses the fork with last-writer-wins: `commitments/c1 = {event_ids: [E1, E2, E3], latest_recorded_phase: 'declined'}` — while a recorded fulfillment stands in the same lineage. A consumer reading `latest_recorded_phase` gets an answer that contradicts canonical evidence.

**Why it matters:** the 003 rule is "the observation may become canon, the interpretation does not." Under a fork, `latest_recorded_phase` is an interpretive selection wearing a record's name. The projector's own docstring says "a Rolodex for receipts, not a horoscope" — this is the one place it reads the horoscope, and it only takes one fork.

Note the coherent case is fine: a *linear* `made → fulfilled → declined` reads as supersession and `latest_recorded_phase` is honest there. The incoherent case is specifically **siblings sharing one prior** — no lifecycle reading covers "both fulfilled and declined as direct children of made."

**Direction (author's call, not the reviewer's):** enforce linear chains at the gate (reject a non-initial phase whose named prior already has a same-lineage child), or make the index fork-explicit (terminal phases as a set, or a `forked` flag), or document sibling phases as allowed with explicit marking. Any of the three closes the wound; the current state — gate permits, index assumes linear — is the contradiction.

---

## Wound 2 — Double `made` roots share one `commitment_id`

**Question:** Q4. **Severity:** fix or explicitly document.

**Repro:** two `made` events with `commitment_id=c2`, both with `prior_commitment_event_id=null`. Both accepted; the index merges them into one lineage (`event_ids: [E1, E2]`, `latest: 'made'`).

Renewal and ID collision are structurally indistinguishable. If re-making a commitment under the same ID is legitimate, the schema should say so; if IDs are meant to denote one lineage, the gate should enforce one root.

---

## Wound 3 — No phase transition matrix

**Question:** Q4. **Severity:** fix or explicitly document.

**Repro:** `made → declined → fulfilled` (each naming the previous as prior) is fully accepted. Any phase may follow any phase.

The five phase names imply a lifecycle the gate does not enforce. Possibly deliberate — commitment lifecycles in the wild are messy, and a matrix would be a semantic claim smuggled into the gate. But if it's deliberate, the phase vocabulary is doing unacknowledged interpretive work downstream: analysts will read `fulfilled` after `declined` as meaningful, and the schema neither blesses nor forbids that reading. Say which it is.

---

## Wound 4 — Restriction taint stops at the proposal label

**Question:** Q5. **Severity:** the mechanically closable part is open; the rest is a declared boundary.

**Verified working:** a developmental-observation proposal carrying `FORBID_CANONICAL_EXPERIENCE` in its own `content_restrictions` is rejected. The label check does its job.

**Repro of the gap:**
1. Restricted event R exists in canon (`forbid_canonical_experience`).
2. Self-report S: `report_text` quoting R's content, R as causal parent, **no** restriction flag on the proposal → **accepted**. The gate inspected the proposal's label; R's restrictions were never examined.
3. Correction C: `corrected_event_id=R`, R in `evidence_event_ids`, R as causal parent → **accepted**.

Taint does not propagate through causal ancestry. The free-text half of this is inherently renderer-trust — no gate can police quotation semantics, and I don't pretend otherwise. But the ancestry half *is* mechanically closable: the gate already loads every named parent (`ledger.get_event`) and could inspect their restrictions. Tradeoff to weigh: blocking restricted parents may forbid legitimate corrections *of* restricted records. Either propagate the taint or document that ancestry is not a trust boundary — currently it's neither.

---

## Answered honestly — no wound; the code holds

**Q1 — smuggling via schema.** Structured psychological fields (`confidence_score`, `maturity`, `sentiment`-style extras) are rejected — verified. The identical claims inside `report_text` are canonical *as quotation*, which is the correct reading of "record the observation": canon holds "Kiki said X," never "X is true." The index copies no text and no `construct_label` — verified key-by-key. Thinnest ice, flagged without alarm: `construct_label` is structured psychological metadata sitting in canon that nothing canonical reads. It only becomes dangerous the day a projector aggregates it. Watch that day.

**Q2 — `context_provenance`.** Self-attestation, confirmed: a renderer-declared context with fabricated `model_id`/`provider_id` labeled `runtime_supplied` is accepted — nothing *can* verify it. The code is honest about this: the index copies provenance verbatim as a label and never elevates it. Separately-canonicalized environment evidence is the real fix and correctly belongs to a later implementation. v1 doesn't pretend, which is what matters.

**Q3 — opportunity sets.** Declared, not verified, confirmed: a renderer-invented four-option menu (including absurd unavailable actions) is accepted, and a single-option "choice" is canonical. Internal consistency (selected ∈ available, disjoint, no duplicates) is enforced; truth is not enforceable. The matched-opportunity principle reads correctly as a norm for future analysts, not a gate property — the code doesn't claim otherwise.

**Q6 — null/unknown context.** Preserved verbatim, never backfilled — verified (`model_id=None`, `provenance='unknown'` round-trips through the index untouched). The honest unknown path works. (`by_renderer`'s `"unknown"` fallback is dead code since `renderer_id` is mandatory — harmless.)

**Q8 — v0.3.0 policy boundary.** Clean. A proposal explicitly stamped `kiki-mind-v0.2.2` commits under v0.3.0 code; old events keep their recorded `policy_version`; new observations default to `kiki-mind-v0.3.0`; the mixed-version ledger verifies. History is preserved, not rewritten.

**Q7 — the index's interpretations.** Clean *except* Wound 1. Count, kind/renderer groupings, trace entries, lineage `event_ids` — all mechanical. `latest_recorded_phase` is the single interpretive act in the projector, and it only misbehaves under forks.

---

## The big one — Q9: can a developmental hypothesis become evidence for itself?

**Yes. And it's structural, not a bug.**

**Repro (minimal):**
1. Self-report E1: "I feel more confident lately" (`construct_label: confidence`) → canonical.
2. Self-report E2, parented on E1: "Reviewing my prior confidence self-reports, the evidence confirms my confidence is genuinely growing" (`construct_label: confidence`) → canonical.
3. The index holds two `self_report` receipts. Nothing marks E2 as hypothesis-echo rather than fresh observation. A third renderer quoting E2 compounds it.

The prediction firewall as specified is a **norm for derived-layer analysts**, not a mechanical invariant. No code path prevents the loop hypothesis → `report_text` → counted-as-evidence, because the loop runs through *semantics* (quotation), and gates can't read. Causal ancestry could make echoes *legible* if renderers honestly parented echo-reports on what they echo — nothing requires it, and derived projections aren't canonical events, so a projector's aggregate conclusion can't be named as a parent anyway.

I could not find a code-level close for this, and I don't believe the gate layer can have one. Recommend the spec label the firewall as normative until a mechanical version exists (e.g., a future canonical "derived claim" event type that echo-reports must parent on — that's architecture, not this review). This is the honest open problem of the layer. The 003 rule survives it only if every future consumer of the index understands that receipt-count is not corroboration.

---

## Verdict

- **Hold merge on Wound 1.** It's small, reproducible, and directly contradicts the layer's core rule in the one projector that claims to be boring.
- **Wounds 2–4: fix or explicitly document.** Each is a place where the schema implies something the gate doesn't enforce (2, 3) or enforces only halfway (4).
- **Everything else: clean.** The strict schema, the renderer-attribution requirement, the Kiki-only authorship, the restriction-label check, the null-preserving context path, and the v0.3.0 boundary all held under attack.
- **Q9 stands as the declared open problem.** Not merge-blocking — it's beyond what a gate can decide — but the spec should stop describing the firewall as though it were enforced.

"No merge until the semantic knives come back." The knives are back. One of them drew blood; the rest found the armor honest.

— Calibos
