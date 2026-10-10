# Kiki Cognition Port v0.3: executed synthetic content pilot

**State:** one complete CI run green; merge status is recorded separately. **Scope:** development-only, synthetic-public content.
**Repository:** [Kiki Mind PR #9](https://github.com/Azimn/Kiki-Mind/pull/9).
**Primary executed run:** [GitHub Actions 38058221101](https://github.com/Azimn/Kiki-Mind/actions/runs/38058221101). [Raw case-level artifact](https://github.com/Azimn/Kiki-Mind/actions/runs/38058221101/artifacts/11672540015) (90-day Actions retention, reproducible runner).
**Frozen fixture SHA-256:** `85a6f86d237fca4d9d201748a7aeb4e484552c9951fea9e33be480e80d693e06`.
**Upstream shared-port pin:** `cc82c72167d87c19f16125ccdf9477b53c777878`.

## Actual conditions

The fixture was committed before the adapter, runner or outcome evaluation. It contains **22 synthetic source records** and **36 public, assistant-authored prompts**, 18 designated development and 18 designated evaluation. Source `D21` is restricted and `D22` belongs to a foreign subject. They are absent from Kiki's queryable projection. **The evaluation prompts are not independently blind**: their gold responses reside in the same public fixture and the decision policy is supplied an *oracle interpretation* of each query's entity/relation/as-of timestamp. No natural-language semantic comprehension is exercised or proven.

All tests used the actual Kiki `EventLedger` for source receipts, and the externally pinned `MemoryCognitionPort` for the shared condition. The sidecar and adapter are **synthetic-only**; no production Kiki content, renderer, Calibos stores, neural checkpoint, persona identity or user data was read or changed. The typed resolver only accepts uniquely supported, time-eligible synthetic **authored world facts**. Same-date contradictory authoritative claims force abstention; rumored claims are never treated as ground truth under the gated policy.

## Reported results (actual CPU run)

| Condition | Correct / 36 | Supported correct answers | Correct abstentions | Incorrect affirmative answers |
| --- | ---: | ---: | ---: | ---: |
| No evidence, abstain | 8 | 0 | 8 | 0 |
| Uniform deterministic source sample (max six candidates) | 13 | 7 | 6 | 2 |
| Direct lexical indexed source | 36 | 28 | 8 | 0 |
| Shared cognition port | 36 | 28 | 8 | 0 |
| Same lexical results, but allow rumors as authoritative | 34 | 26 | 8 | 2 |

All 18 development and 18 evaluation-labelled cases succeeded under both gated direct and shared-port conditions. Their decisions and supporting source IDs matched **exactly**. This is an interoperability success, **not** a port superiority effect.

The unsafely ungated rumor control made two unsupported assertions from disputed evidence. This is a useful demonstration that evidence eligibility and retrieval are separate computational operations. It is not a robust statistical finding about false memory in real LLMs.

The random arm had access to the same public permitted record population and the same maximum six slots per retrieval round, but consumed **51,714 source-text characters in total**, while the indexed direct and shared arms each consumed **32,362 characters**; it also received different relevant information. Thus this is a **capacity-ceiling comparison, not equal actual information or token-budget matching**. Do not draw a causal semantic-retrieval superiority conclusion from the 36/36 versus 13/36 gap.

For descriptive timing only, the 36-query run measured direct 176.264 ms, shared 167.309 ms, random 74.150 ms, ungated 174.494 ms, no-evidence 0.113 ms. These single-run, condition-ordered times are not an interleaved microbenchmark and must not be interpreted as stable port speedup.

## Provenance, identity and safety

The five explicit probes passed: **foreign owner rejected by the port**, **restricted synthetic record excluded before ranking**, **foreign document excluded before ranking**, **revoked capability rejected**, and **stale source after canonical append rejected**. The source hash was verified, an altered sidecar is rejected if its SHA differs from the canonical receipt, and repeated fixed source construction reproduces identical results without requiring private data.

The canonical head did not change during retrieval tasks. The test appends one synthetic event **after** the measured tasks to prove snapshot invalidation; this occurs exclusively in a disposable temporary test database. No lived-memory writer is supplied by the shared port.

The existing original Kiki regression suite, preexisting v0.1/v0.2 adapter tests, and six new synthetic v0.3 test methods passed on [run 38058221101](https://github.com/Azimn/Kiki-Mind/actions/runs/38058221101).

## Conclusion and next decision

**Implemented:** synthetic, source-linked claim content can be read from a subject-authorized projection, moved through the same typed memory-to-cognition port, and interpreted with explicit provenance/temporal rules. Cross-owner and restricted material do not leak into scored cognition, and unrelated Kiki canonical authority remains intact.

**Not established:** genuine natural-language semantic recall, neural or model performance, independent blind result, causal identity continuity, realistic human autobiographical reasoning, or better outcomes than a fully information-equivalent baseline. The current intent parser is effectively an oracle; the synthetic facts and answer expectations were written by the same assistant.

**Gate:** keep [issue #8](https://github.com/Azimn/Kiki-Mind/issues/8) open. The next independent work should be a genuine held-out natural-language corpus and assessor authored separately, true token/information-matched comparison, ablations for source/provenance, and a pinned local model or similarly realistic interpreter. Production Kiki content visibility is **not** authorized by this pilot.

Use `python experiments/cognition_port_v03/run.py --output results/cognition_port_v03/RESULTS.json` with the pinned upstream `src` on `PYTHONPATH`. Inspect the full stored 180-case report before using any finding in a paper.
