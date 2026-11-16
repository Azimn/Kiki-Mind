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
