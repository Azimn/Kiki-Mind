# v0.4 results: public bAbI no-oracle memory interface

**Status:** executed and green on the original PR-head [GitHub Actions run 38060905490](https://github.com/Azimn/Kiki-Mind/actions/runs/38060905490), including source hash checks, ten v0.4 tests, 120 real benchmark questions and all original Kiki/v0.1-v0.3 regression suites.
**Execution code:** [Kiki-Mind PR #10](https://github.com/Azimn/Kiki-Mind/pull/10). Merge status must be separately verified.
**Data provenance:** Original FAIR/Meta bAbI tasks, *Towards AI-Complete Question Answering: A Set of Prerequisite Toy Tasks* (Weston et al., 2015). Test text retrieved from [azreasoners/LLM-ASP](https://github.com/azreasoners/LLM-ASP/tree/642a9ade9c92677b970b1bc9921cafb0764d2ed7/bAbI/data), commit `642a9ade9c92677b970b1bc9921cafb0764d2ed7`, with exactly pinned Git blobs. Dataset license: CC BY 3.0, [facebook/babi_qa](https://huggingface.co/datasets/facebook/babi_qa).
**Interface pin:** Pretorius-Connectome `cc82c72167d87c19f16125ccdf9477b53c777878`.
**Data selection:** first 40 public TEST questions each for qa1, qa2, qa6. All 120 externally authored (not produced by our development), public and **not blind**.

## Results from an actual complete CI run

| Condition | QA1 single fact /40 | QA2 two supporting facts /40 | QA6 yes/no /40 | Total /120 |
| --- | ---: | ---: | ---: | ---: |
| No context | 0 | 0 | 0 | 0 |
| Full preceding story, no index | 40 | 40 | 40 | **120** |
| Uniform random max five prior facts | 34 | 9 | 32 | **75** |
| Native lexical ranked top five | 40 | **0** | 40 | **80** |
| Same top five through shared cognition port | 40 | **0** | 40 | **80** |

Across QA1/QA2/QA6, the **average bAbI official-support recall** in the shared-port condition was respectively **1.00/0.50/1.00**; for full context 1.00 on all, and for random context 0.85/0.325/0.775. QA2's 40 unanswered questions are genuine recorded **abstentions**, not fabricated guesses. The native-source and shared-port ranked arms exactly match predictions, evidence IDs and citations for **all 120 trials**.

## Scientific reading

**Positive information-access result:** on original public bAbI benchmark questions, the fixed rule-based interpreter resolves single-supporting-fact and simple yes/no state tasks using a verified source retrieval channel, without oracle-structured entity/relation/date intent. Their 40/40 results reproduce equally through native retrieval and the shared memory-to-cognition interface, which supports interoperability rather than improvement from the port.

**Critical negative result:** all 40 two-supporting-fact queries FAILED under the same top-five single-hop lexical retrieval, even though the identical fixed interpreter solved all 40 with the complete *prior* story. Average QA2 required-support coverage 0.5 indicates that the lexical candidate selection is missing information needed for a correct two-hop answer, typically an actor's subsequent movement when a question only mentions a carried object. This is an explanation consistent with the implementation and support coverage, not a separately proven causal diagnosis. Random five source rows actually answered 9/40 QA2 tasks while single-hop ranked answered 0/40. We must not hide or retroactively tune away this null.

**No unsupported cognition claim:** this is an intentionally narrow **deterministic grammar** for bAbI template text, not a local neural or language model, model-agnostic natural-language semantics, episodic autobiographical identity, subjective experience or independently judged language behavior. Dataset was written externally, but public test templates and the task structure were known, so this is not sealed/blinded. No statistical generalization beyond this fixed slice is justified. Source and candidate counts differ across arms; random five is not an equal-information comparator. Native and shared same-candidate arms ARE equal-information controls.

## Safety and persistence

The actual Kiki hash-chained canonical event ledger and its TransitionGate process synthetic *external source receipt* events in temporary test databases only. A new read-only source and in-process capability are bound to a single task/question and **past-only story prefix**. Gold answers and gold support IDs are consulted **only in the scorer after decisions have been produced**, not in query parser, evidence ranking, or cognitive state tracking.

Passed six recorded checks: wrong owner denied, revoked capability denied, future record absent, past-only namespace boundary, stale snapshot denied after a deliberately post-scoring synthetic append, and confirmation that post-scoring append changes only the synthetic scratch ledger. The original canonical head stayed stable throughout scored queries. No real Kiki ledger, personal data or the existing metadata v0.1-v0.3 adapters were modified.

## Follow-up experiment

Preserve v0.4 exactly. Freeze a NEW bAbI test interval, for example qa1/qa2/qa6 question ordinals **201–240** at the same upstream pin, **before** implementing a query expansion algorithm. Compare:

1. Original top-five one-shot lexical ranking.
2. **Evidence-chain retrieval:** find the object's most recent pickup/drop or ownership record, then query the identified actor's movement history, with at most five unique permitted source sentences across both passes and no future/foreign data.
3. Full preceding story using identical rule interpreter (upper bound).
4. Native vs shared identical multi-pass source candidates; both must agree and neither may get extra facts.
5. A matched random-five condition and an intentional wrong-holder source swap as provenance control.

Primary metrics: exact QA2 answer accuracy, required support fact coverage, unsupported assertions, elapsed source reads, actual source character budget and source-ID citation legitimacy. Do not train/tune on the 201–240 answers. No claim of independent semantic intelligence should follow even if recall improves: the proposed mechanism is an explicit multi-hop graph-traversal heuristic. Only after fresh-split success consider a pinned local LLM renderer and genuinely independently graded narrative questions.
