# Kiki Mind: Memory-to-Cognition Port v0.1

**Status:** optional cross-repository adapter and synthetic-ledger test. No live Kiki database, private thought store, renderer prompt, production account or Calibos archive is imported or modified.

**Contract owner:** [Pretorius-Connectome, merged PR #31](https://github.com/Azimn/Pretorius-Connectome/pull/31), release code pinned at `cc82c72167d87c19f16125ccdf9477b53c777878`. Reuse its Python `MemoryCognitionPort` and typed `CognitionEvidence`; do not recreate a competing standard inside Kiki Mind.

**Kiki owner:** the existing `runtime.kiki_mind.ledger.EventLedger`, hash-chained canonical history with gate-validated writes. See [Kiki's canonical history and projection contract](KIKI_MIND_v0.2.2_IMPLEMENTATION_SPEC_002.md) and [developmental evidence restrictions](KIKI_MIND_v0.3.0_IMPLEMENTATION_SPEC_003.md).

## What is implemented

`runtime/kiki_mind/cognition_adapter.py` provides a `KikiLedgerCognitionSource` adapter to the shared read-only protocol. It receives an independently verified Kiki `EventLedger` instance, validates its full hash chain, snapshots a canonical head and emits a version-pinned descriptor for subject `kiki`, namespace `kiki.canonical.events`. Its source hash is the hash of the canonical chain head, not a made-up identity signature. After any append, the adapter refuses both searches and exact record lookups until a **new** temporary source is built. A restarted process reconstructs the same derived receipt index from the identical canonical head.

This first adapter deliberately indexes **event receipts only**: allowlisted types include external source ingestion, Kiki-authored interpretation, Kiki encounter recording and developmental observations. It produces fixed category labels such as `encounter recorded kind retrieval`. It never indexes raw payload titles, message bodies, self-report text, operator text, private thoughts or general autobiographical narrative. Any event carrying *any* content restriction is excluded entirely. An `observed_runtime` origin here refers to a ledger receipt having occurred, **not** confirmation of the truth of the underlying memory, self-report or psychological claim. Source evidence remains labeled `external_document`.

A metadata-token search gives deterministic relevance rankings only for those bounded event labels. This is **not** semantic retrieval, is not a replacement for Kiki's projectors and does not prove that Kiki has a lived autobiographical memory of the retrieved content. The interface cannot grant an event permission to become a lived experience. The shared envelope explicitly sets `epistemic_status=candidate_not_entailment`, `channel=external_memory_evidence`, and `eligible_for_lived_write=False`.

The adapter creates no SQLite database or file and adds no canonical ledger events. It does not import Pretorius's biographies, FlyWire neural weights, BioCircuit inputs or character state. It has no model calls, API charges, continuous background service, scheduler or automatic projection write.

## Reproducing safely

Existing Kiki Mind installation and tests are unchanged:

```sh
python -m unittest discover -s tests -v
```

To run the isolated cross-project integration, check out the [exact shared port source commit](https://github.com/Azimn/Pretorius-Connectome/commit/cc82c72167d87c19f16125ccdf9477b53c777878) beside Kiki Mind (never copy its biography). Add the upstream `src` directory and Kiki Mind root to `PYTHONPATH`, then run:

```sh
python -m unittest discover -s tests_integration -p test_memory_cognition_port.py -v
```

[The dedicated GitHub Actions integration workflow](../.github/workflows/memory-cognition-integration.yml) performs those steps with a pinned external checkout and runs both the original Kiki suite and synthetic ledger integration. It does not download a language model or operate on private Kiki data.

The synthetic integration tests cover Kiki's **real EventLedger schema and transition gate**, source-bound capabilities, rejected Pretorius owner/namespace substitution, external evidence not automatically admitted to autobiography, metadata-only content privacy, restricted source exclusion, append/rebuild invalidation, revocation, nonexistent event IDs, two different process hash seeds, and unchanged canonical head.

## Important security limits

The shared port's `grant_self` method is an **in-process trusted-host mechanism**, not remote/user authentication. Do not expose it to a renderer, untrusted caller or public Kiki bot service. Access to `EventLedger` itself remains governed by Kiki's host and source rules; this adapter does not implement per-event privacy levels or permission grants. In particular, a host should never attach an arbitrary user's `mind.db` to this metadata index. Do not put live private text into public GitHub CI or test fixtures.

The index is a deliberately minimal derived projection. It does not participate in `ProjectionRunner` state or bypass projection freshness verification. On future integration with a production cognitive workspace, a separate admission/permission policy must decide what metadata the subject can perceive. Neither retrieval nor rendering creates canonical developmental evidence without the existing `TransitionGate`.

## Next experimental gate

After green isolated integration CI, compare a fresh Kiki synthetic event ledger with and without the metadata index at identical canonical head/renderer settings. This will test whether reliable receipt retrieval changes attribution and task outcomes, not merely response wording. Then design a **new explicit content-visibility policy** for text retrieval over Kiki-authored experiences before considering production. The current adapter should remain metadata-only until independent false-memory, wrong-owner and restricted-record probes pass.

Cross-project research documentation: [Shared Memory Integration](https://github.com/Azimn/Artificial-Life-Research-Journal/blob/main/programs/CROSS_PROJECT_SHARED_MEMORY_INTEGRATION_2026-10-09.md).
