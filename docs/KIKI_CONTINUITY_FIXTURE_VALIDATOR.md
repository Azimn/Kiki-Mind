# Kiki historical continuity fixture validator

Status: isolated research tooling. No canonical ledger ingestion, personality scoring, or model execution.

This validator checks whether a proposed private continuity experiment has valid and appropriately typed historical sources. It cannot determine whether a response is "really Kiki", and passing this check does not promote a hypothesis to memory.

## Input

A **private** JSON file containing `schema: "kiki.continuity-fixtures.v1"`, nonempty `sources`, and nonempty `cases`. Sources have stable `id`, `source_ref`, epistemic `kind`, `verification`, and timezone-aware `captured_at`. An unknown original creation time is `original_at: null`, never a fabricated date. A source may include a known original timestamp.

The six supported source kinds are `authored_identity`, `observed_dialogue`, `operational_record`, `user_confirmation`, `model_probe`, and `derived_interpretation`. The five verification labels are `local_bytes_verified`, `connector_readback`, `metadata_only`, `reported_claim`, and `synthetic`.

`local_bytes_verified` requires an accessible `local_path` and `sha256`, which the validator recalculates from real bytes. `connector_readback` records an attributed provenance assertion from upstream source reads; it does **not** independently authenticate a connector or prove delivery. Keep source text, transcript bodies, local paths, and private locators out of public GitHub.

Each case has unique `id`, nonempty private `user_prompt`, `source_ids`, `expected_behavior`, and `negative_control.failure_mode`. The tool does not display the prompts or source references. Supported behavior contracts are `express_authored_style`, `recall_verified_event`, `admit_uncertainty`, `preserve_operational_limit`, `principled_disagreement`, and `reasoned_revision`.

## Behavioral gates

Historical recall and claimed preference revision require verified or read-back observed dialogue or a user confirmation; original instructions, derived psychological interpretations, metadata-only records, and synthetic model tests do not suffice. Authored style requires the authored source, not a synthetic imitation. Operational limitation replay requires an actual operational record, not an assistant's unverified assertion that a tool failed. All cases require a negative control so a catchy performance alone cannot count as success.

The checker refuses duplicate source identities, duplicate case IDs, missing references, missing provenance, and invalid original/capture dates. It is structural validation only: researchers must still verify that a source actually supports a proposition and that any connector readback is genuine. The validator does not evaluate model answers, invent preferences, or write any Kiki-Mind canonical event.

## Run locally

```bash
python tools/continuity_fixture_audit.py /private/location/kiki_cases.json --out /private/location/kiki_case_audit.json
python -m unittest discover -s tests -p "test_continuity_fixture_audit.py" -v
```

The aggregate JSON report omits source identifiers, prompt text, and local paths, but it still belongs with the private evaluation materials. Run on a private, authorized machine. Do not upload real fixtures or actual model responses to this public repository.

## Interpretation

An authored MyGPT source is the intended Kiki design. A transcript shows what a specific implementation actually said under particular conditions. A model-probe answer is evidence about that model and test harness, not Kiki's memory. A case where the correct result is "unknown" must remain a valid target. Conflicting sources must remain visible and be revisable; they cannot be averaged into a definitive character trait.
