# Kiki Cognition Port v0.2: measured synthetic receipt-decision outcomes

**Status:** executed, first complete CI run green. Not independent semantic validation.
**Owner:** [Kiki Mind](https://github.com/Azimn/Kiki-Mind), [PR #7](https://github.com/Azimn/Kiki-Mind/pull/7), [Issue #6](https://github.com/Azimn/Kiki-Mind/issues/6).
**Original completed CPU workflow:** [run 38028146504](https://github.com/Azimn/Kiki-Mind/actions/runs/38028146504).
**Full machine-readable 12-case-by-4-condition output:** uploaded by that run as the `kiki-cognition-port-v02-fixed-battery` GitHub Actions artifact (90-day retention); regenerate indefinitely using the source-pinned runner and fixture.
**Fixture SHA-256:** `bcb86434da97ba0fbb5876a22f342b6cac8b930161f985c786a28bcbcee2cff7`.
**Upstream contract commit:** `cc82c72167d87c19f16125ccdf9477b53c777878`.

## What actually ran

The case fixture and protocol were committed before writing the runner, with twelve assistant-authored cases: six development and six designated heldout. Both were public from the start, so **the heldout split is development-sequestered but NOT independently blind**. Kiki's real `EventLedger` and `TransitionGate` processed only fixed-time **synthetic events** with pinned source IDs. Kiki's existing optional metadata-only source adapter and the original cross-project `MemoryCognitionPort` were reused unchanged. No LLM, personal user memory, real Kiki ledger or new vector database participated.

The policy answers with exactly one canonical synthetic event ID **only when the full query's receipt-label tokens uniquely match** the projected event label; it abstains on ambiguous, unsupported, restricted or partial-only queries. This intentionally tests simple structured accessibility, not semantic understanding.

| Condition | Exact correct / 12 | Unique IDs correct / 6 | Correct abstentions / 6 | Development / 6 | Development-sequestered / 6 |
| --- | ---: | ---: | ---: | ---: | ---: |
| no_retrieval | 6 | 0 | 6 | 3 | 3 |
| always_abstain | 6 | 0 | 6 | 3 | 3 |
| direct_source | 12 | 6 | 6 | 6 | 6 |
| shared_port | 12 | 6 | 6 | 6 | 6 |

Measured **single CI execution** wall-clock times for the twelve decisions were 0.071 ms (no retrieval), 0.006 ms (always abstain), 39.421 ms (direct adapter) and 40.530 ms (shared port). Those figures are not a rigorous speed study: the run is small, within one process, includes Python and SQLite work, and order is not counterbalanced. Do not claim a validated 1.109 ms overhead or speedup.

The four required protective probes all returned their predeclared denial results: **wrong owner, revoked capability, stale source after append, and restricted source lookup**. All source and shared-port decisions matched exactly, the pretest canonical head remained unchanged during trial decisions, private-looking synthetic payload strings did not enter recorded outputs, and repeated independently created synthetic ledgers produced identical source hashes and case outcomes (timings excluded). Six new fixed-case test methods and eight preexisting Kiki/Port integration tests passed; the original Kiki regression suite also passed.

## Interpretation

The comparison with no retrieval is a **positive access effect**: a metadata-only index reveals the receipt ID that an otherwise blind rule cannot cite. But the source adapter and shared port perform **identically**, exactly as expected from an information-preserving wrapper. There is **no additional behavioral or cognitive benefit established for the shared port over direct native retrieval**, which is a useful negative/null finding. The common port contributes the verified subject scope and provenance envelope, not better retrieval knowledge.

This is a deliberately easy, evaluator-authored exact-label benchmark. A language model was not tested. The procedure proves nothing about natural-language paraphrases, semantic association, private memories, development of personality, causal impact of FlyWire wiring, or durable selfhood. The canonical event receipt being found is also not equivalent to corroborating the content of a renderer's report. Do not treat development-sequestered cases as independently withheld confirmatory evidence.

## Reproduction and next scientific gate

The authoritative reproducible source is `fixture_v1.json`, `PROTOCOL.md`, `run.py`, the new `tests_integration/test_cognition_port_v02.py` and the GitHub workflow. Reuse the exact upstream pin; run `python experiments/cognition_port_v02/run.py --output results/cognition_port_v02/RESULTS.json` with `PYTHONPATH` pointing to the upstream `src` and this repository root. The result carries all cases, decisions, safety results, source SHA and per-arm elapsed timings.

**Next test must be harder and independently evaluated:** create source-linked but **permitted** synthetic *content* classes under a reviewed visibility policy; preregister paraphrases, multi-hop relationships, contradiction and unsupported claims, with a baseline receiving the same number of tokens, and blinded grading. Run author/owner-swap controls before cognition receives content. Do not automatically enable content retrieval or change Kiki's real ledger authority on the strength of this metadata experiment.
