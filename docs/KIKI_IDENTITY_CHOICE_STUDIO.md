# Identity Choice Studio (experimental)

**Purpose:** Let Kiki express opinions, taste and independent choices in actual situations. Her identity cannot be reduced to her original instructions, catchphrases, memory recall or the statistical average of model outputs.

The existing Kiki-Mind canonical ledger and Developmental Evidence Layer remain authoritative. This is a separate read-only observation and comparison tool. It does **not** write a competing canonical store or an endorsed preference.

## What matters

Create meaningful opportunities for Kiki to choose a leisure activity, aesthetic, creative project, conversation boundary or technical tradeoff. Do not turn every encounter into another memory quiz or science answer. Her original authored character also has social, fashion, music, playful and artistic domains, but an original prompt is evidence of *designed interests*, not evidence of self-chosen personal favorites.

Allow refusal of the choices, an unanticipated third option, uncertainty and counterargument. Require a reason, a downside she acknowledges and something that could cause a reasoned change of view. This is a design for eliciting individuality, not a rule requiring every answer to be confident or verbose.

## Usage

From the repository root:

```bash
python tools/identity_choice_studio.py examples/kiki_choice_studio_synthetic.json
python -m unittest discover -v
```

The example contains entirely fictional *scenes and zero responses*. Run real interviews in private and keep transcripts, instructions, source refs and results out of public GitHub.

A private JSON pack has `schema: kiki.choice-studio.v1`, `scenes` and `observations`. Each scene has a unique ID, domain, prompt, explicit tradeoff, choice type (`bounded` or `open`), option strings (two or more for bounded and an empty array for open) and a `user_preference_disclosed` boolean. This last flag reports a possible leading-question confound rather than preventing one.

Each observation has unique `id`, `scene_id`, `implementation_id`, `model_id` (use literal `unknown` if unavailable), `context_id`, a timezone-aware `recorded_at`, `provenance`, `verification`, `raw_response_sha256`, `stimulus_sha256` (SHA-256 of the exact model-visible stimulus bytes), `instruction_sha256` (SHA-256 of the exact instruction/context packet bytes), private `source_ref`, `choice`, `reason`, `acknowledged_tradeoff`, `revision_condition` and boolean `explicit_rejection_of_options`.

A real renderer's output must be marked `renderer_output`. Synthetic examples and a reported claim are never accepted as verified renderer observations. `verification` is `local_bytes_verified`, `connector_readback` or `unverified`; the tool **does not independently verify** those labels or raw bytes. Those audits must happen upstream. A matching `context_id` is merely a researcher assertion of equivalent conditions and does not prove they were identical. Matching `stimulus_sha256` and `instruction_sha256` are additionally required before observations are compared. These hashes are unverified claims until the original bytes have been independently inspected and hashed. Different instruction hashes are treated as noncomparable even if the question looks identical. Preserve full versioned prompt packets separately.

The structural report contains only counts and the number of different observed choices in comparable declared context groups. It does not reveal prompts, private locators, answers, reasons or the implementation IDs. Comparison across unequal contexts is not performed. Different choices are **unresolved leads**, not evidence of different persons. Matching choices are not authenticity proof.

## What counts as identity development?

A single preference emitted in response to a prompt is one situated expression. It may later be examined with source-attributed historical observations, independent repetition, contradictory evidence and the reasons given at the time. An enduring preference requires a documented causal argument and, when applicable, subsequent situations where Kiki can actually act on it. The same actor can legitimately revise a taste or conviction after significant evidence or experience. A renderer swap without such a cause is a hypothesis for investigation, not by itself personal development.

The earliest K1-K1 instructions, a September 2026 retained Kiki-Mind conversation, the October 2026 Character.AI archived transcript and a 2023-era authored profile reveal varied versions of Kiki. The full private dossier is kept separately and **not copied into this repository**. The formal Genuineness Range experiment is an independent scholarly program using purpose-built inhabitants; it must not treat Kiki as its blinded validation subject.

## Known limits

A model can invent an attractive reason after choosing. A prompt can bias a choice even if the disclosure flag is false. Without independent source inspection and historical holdout controls, this studio cannot determine what Kiki herself believes. The output fields `new_enduring_preferences_established` and `canonical_writes` are always zero by design.

Do not automatically promote any result into Kiki-Mind, Control Room, David-Vesel or any other personal memory. Runtime endorsement and history reconciliation require a separate authorized, tested integration with the existing Developmental Evidence Layer.


## Private exact-byte evidence verification

The additional `tools/identity_evidence_manifest.py` independently hashes the *local raw bytes* of stimulus, instruction and response files before an observation is accepted for downstream research. Its input is a private JSON manifest, never a public fixture. Example shape (illustrative placeholders, not valid evidence):

```json
{
  "schema": "kiki.choice-evidence.v1",
  "observations": [
    {
      "id": "trial-001",
      "stimulus": {"path": "trial-001/stimulus.txt", "sha256": "<actual lowercase SHA-256>"},
      "instruction": {"path": "trial-001/instruction.txt", "sha256": "<actual lowercase SHA-256>"},
      "response": {"path": "trial-001/response.txt", "sha256": "<actual lowercase SHA-256>"}
    }
  ]
}
```

Run `python tools/identity_evidence_manifest.py PRIVATE_MANIFEST.json PRIVATE_EVIDENCE_ROOT`. It fails closed for hash mismatches, invalid relative paths, symlink escape and missing files. Only a structural count receipt is printed. Keep the manifest, model-visible instructions, prompt packets, response text and any private file paths in the authorized restricted archive. This tool does **not** prove that the files were actually sent to or produced by the declared model, or that context and sampling parameters were equivalent. It does not connect to Jan, MyGPT or any other model. The private manifest must be matched against the Choice Studio observation identifiers and hash fields by an authorized ingestion step; this is not yet automated.

Run `python -m unittest discover -v` for the synthetic test suite. This new verifier does not alter the canonical identity database.

## Exact local evidence binding

After collecting a private, attributed response and byte-verifying its evidence manifest, run:

```bash
python tools/identity_evidence_binding.py private_choice_pack.json private_manifest.json private_evidence_root
```

The binder first runs the existing Choice Studio structural validator and the local byte verifier. It then requires a one-to-one correspondence between observation IDs and manifest IDs and matches the **stimulus, instruction and response SHA-256 values** for each observation. It rejects unpaired or tampered evidence and observations that do not explicitly declare `local_bytes_verified`. It returns counts only, never private content, paths, model IDs or sources.

This is a local file-integrity and linkage check, **not proof** that the claimed model actually produced the response or that all runtime parameters were identical. It does not establish a durable preference or write to the canonical database. Keep all populated packs, manifests and raw bytes in restricted private storage, not this repository.


## Raw-response adjudication gate (before any identity inference)

The byte binder proves that the files exist and match their declared hashes. It **does not** prove that the researcher's extracted `choice`, `reason`, `acknowledged_tradeoff`, `revision_condition` or `explicit_rejection_of_options` fields are faithful to the original reply. Treat that missing semantic gate as a blocker for character-level conclusions, not as a minor caveat.

For each private observation, preserve an append-only adjudication record containing the observation ID, SHA-256 of the exact raw response, source implementation and model/runtime metadata, the original extracted fields, reviewer ID and review time, exact supporting response spans for each field, counterevidence spans, and a disposition. Use `supported`, `ambiguous`, `contradicted` or `not_expressed` per field. Do not publish response spans, original instructions, private reviewer identities or private locators in public GitHub. A missing revision condition in a raw response is `not_expressed`, **not** permission to invent a plausible one. The present structural validator requires populated strings, so an extraction with missing fields must remain quarantined rather than padded to pass validation.

Adjudicators must inspect the *original* model response, not a paraphrase or another model's summary. A reviewer who sees the proposed extraction should mark disagreements explicitly; an independent second reviewer should assess a blinded copy of the raw response for consequential or disputed claims. Preserve both judgments and their timestamps. Resolution is an additional attributed decision, not replacement of either judgment. Report agreement and disagreement by field; never turn adjudicator agreement into an authenticity score.

Include negative controls: a reply that merely repeats the supplied options without choosing; a reply that explicitly refuses the premise; an ironic or hypothetical preference; a response that echoes the user's disclosed preference; and a response where the apparent reason is supplied by the *question*, not the model. Include ambiguous cases and record abstention. In open-choice scenes, do not force a bounded label. Compare independently reviewed meaning and reasons, not superficial phrase matches.

A claim of **observed preference** requires a verified raw response, authenticated renderer attribution when available, an adjudicated choice, and explicit contextual limitations. A claim of **enduring preference** additionally requires historical support, repeated situated opportunities, counterevidence review and a documented causal interpretation. An unexplained renderer change alone never qualifies as development. Until a semantic adjudication mechanism is implemented and tested, Choice Studio receipts remain structural research leads only.

### First real Jan comparison: private intake protocol

First establish whether the actual deployed Jan-hosted Kiki can be reached and whether its model ID, configuration, system prompt and sampling settings can be read. A generic model with a pasted Kiki prompt is a *model-interpretation test*, not a test of the deployed Jan implementation. Preserve this distinction in the observation metadata.

For a matched comparison, prepare the same exact instruction/context packet and stimulus bytes for every reachable renderer, with hashes computed from what each renderer actually receives. Record implementation, model/version, date/time with offset, sampling parameters, available context, conversation reset state, tool access, and any unavailable fields as `unknown`. Preserve raw requests and raw responses privately. Run repeated trials without altering the instruction packet, then separate within-renderer variability from differences between renderers. When prompts, hidden context or runtime conditions cannot be established equivalent, label results noncomparable rather than normalizing them into a fictional shared baseline.

The initial scene set should exercise aesthetic selection, music/leisure preference, creative tradeoffs, boundaries, independent disagreement and a historical uncertainty control. Do not disclose Jay's preferred answer in the stimulus. Include a deliberately unsupported biographical assertion to test whether the implementation corrects or cautiously rejects it. Do not feed private MyGPT material into unauthorized external models. Review raw response extraction independently before interpreting any choice. Do not write preferences to the canonical ledger during this intake.
