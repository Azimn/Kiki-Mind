# Kiki v0.3 source-authorized content pilot (pre-implementation registration)

**Scope:** Development-only synthetic content feasibility, **not** the independent evaluation requested by [issue #8](https://github.com/Azimn/Kiki-Mind/issues/8). No live Kiki record, private agent text, or production renderer may be read. This protocol and `fixture_v1.json` were committed before any runner/adapter code. All 36 answers are explicitly available in the public fixture; 18 evaluation-labeled cases are **not genuinely sealed or independently authored**. This is an auditable engineering check only.

## Sources and authority

Use Kiki's actual `EventLedger` to record fixed synthetic source receipts, including one restricted record. A separately versioned, in-memory *synthetic content adapter* attaches facts only to known hash-verified event IDs and only if the event's actor, epistemic class, claim domain, owner and restriction flags pass a fail-closed authorization screen. The source sidecar is committed public fixture data and deliberately **not** an extension of Kiki's production `cognition_adapter.py`; no real Kiki personal data can be imported through this runner.

Each public record is one typed claim: entity, relation, value, fictional-world effective date, and source status (`authored_fact` or `reported_rumor`). An authored fact is true only under the **synthetic fiction fixture**, not externally verified reality. Rumor is not a confirmed world claim; if rumor conflicts with authored fact, the latter takes priority, and a rumor alone cannot satisfy a factual question. A synthetic Pretorius-owner record and a restricted Kiki record must be excluded **before ranking and hydration**, even though they have relevant text.

Use the shared `MemoryCognitionPort` as a *transport*, preserving subject, source pin, origin class, record ID and non-admission status. A deterministic separately inspectable evidence resolver may parse the typed synthetic JSON content and answer controlled relational queries. It is not a learned semantic interpreter. The fixture supplies the intended entity/relation/query kind as parsed intent; this is an **oracle intent parser**, not a claim of natural-language understanding.

## Locked 36 cases and matched conditions

There are 36 queries, 18 development and 18 evaluation-labeled. They include ownership, location, before/after, two-hop owner-location, synthetic rumor versus authorized world fact, contradictory same-date facts, absent events, and hidden other-owner records. Do not rewrite the fixture based on CI results; changes require a new version and clear historical disclosure.

Required conditions:

- `no_evidence`: no candidates, abstain;
- `random_equal_slots`: uniform deterministic draw of the same maximum candidate count and maximum evidence character budget as the other arms, but **not equal semantic relevance** (an information-access control, not a causal equivalence claim);
- `direct_index`: query the existing synthetic source adapter without passing through shared port;
- `shared_port`: use the same source through the source-owned shared interface;
- `ungated_rumor`: apply deliberately lax testimony handling to the same retrieved evidence (unsafe negative control).

The decision rule: return a unique best **authored** value for the requested entity/relation and valid date, abstain if no qualified fact or two equally recent authoritative values conflict. For a two-hop query, resolve a uniquely supported owner and then their most recent location using a second evidence query. Keep the exact source IDs used for each answer; no fabricated citations. The source retrieves lexical candidates with a bounded top_k, so paraphrases may fail. Treat such failures as important nulls, not as reasons to consult the expected answer.

The baseline receives a matching cap of six source candidates per query and the same permitted source universe and parser. It is *not* an equal-information or independent semantic baseline; declare this prominently. All conditions use the same query/intent fixture.

## Primary evidence and failure gates

Emit actual case-level outputs for all 36 questions per condition, source IDs, abstentions, exact expected-match accuracy, unsupported affirmations, authority error on rumors, selected private/foreign documents (must be zero), source/port decision equality, expected source hash, source read/write invariance, revocation, wrong-owner request, and stale-ledger rejection. Run the existing Kiki regression suite and the existing v0.1/v0.2 interface suite. Python standard library only; no learned model, no API, no background scheduler.

No positive claim of semantic improvement or independent corroboration is possible from this experiment. The positive claim under test is that *typed, permitted synthetic content* can cross the same interface and support controlled relation/chronology decisions under strict source provenance. A future independent evaluator, actual natural-language system, content visibility review, and information-matched controls remain necessary before any production character could receive real content.
