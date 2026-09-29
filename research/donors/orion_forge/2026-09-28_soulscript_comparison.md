# Orion Forge / SoulScript Engine comparison note

**Date:** 2026-09-28  
**Status:** external comparison architecture, not canonical Kiki Mind specification  
**Upstream:** https://github.com/DrTHunter/SoulScript-Engine  
**Interface:** https://orionforge.chat/  
**Use here:** conceptual comparison only; no upstream code copied

## Why this belongs in Kiki Mind research

SoulScript Engine independently converges on a useful separation that Kiki Mind reached from a different direction:

- identity-relevant material lives outside the renderer;
- lived memory lives outside the renderer;
- current context is reconstructed for each inference;
- the language model is replaceable;
- retrieval determines which stored material becomes immediately available.

The upstream system implements this with a read-only Identity FAISS store for Soul Script material and a writable Life FAISS store for accumulated memories. Its prompt pipeline combines a base system prompt, retrieved identity fragments, always-on knowledge, retrieved life memories, tools, and recent conversation history.

That is relevant evidence for Kiki Mind because it demonstrates a practical external architecture for model-portable character context without requiring identity to live in model weights.

It is not evidence that different renderers become equivalent.

A scientifically safer formulation remains:

> portable external identity representation, renderer-dependent phenotype

## The useful mechanism

The most useful idea is not "two FAISS databases."

It is that retrieval stores can be treated as context machinery rather than as the source of canonical identity or history.

For Kiki Mind, any future semantic identity index or autobiographical index should therefore be a **projection**:

```text
Canonical Event Ledger
        |
        +--> identity-relevant projector --> disposable retrieval index
        |
        +--> lived-history projector ------> disposable retrieval index
                                              |
                                              v
                                      Subjective Frame
                                              |
                                      Renderer Adapter
                                              |
                                          Renderer
```

Deleting a retrieval index must not delete unique history.

If the same canonical ledger, projector version, embedding model, and retrieval policy cannot reconstruct equivalent derived retrieval state, then the index has quietly become another source of truth.

## Where Kiki Mind must differ

### 1. No direct renderer-to-canonical-memory writeback

SoulScript Engine permits model-generated memory writeback into its dynamic memory vault.

That is appropriate for its design, but Kiki Mind already separates generation authority from canonical state-transition authority.

The Kiki path should remain:

```text
renderer output
    |
candidate observation / memory proposal
    |
Transition Gate
    |
Canonical Event Ledger
    |
projectors
    |
retrieval projections
```

A renderer may propose material. It may not silently turn its own output into canonical autobiography.

### 2. Identity is not one immutable personality document

Kiki Mind should not collapse its Identity Genome into a permanently frozen Soul Script.

The architecture needs to preserve distinctions among:

- authored identity evidence;
- historical observations;
- synthetic design material;
- renderer-sensitive behavior;
- derived trait estimates;
- current self-model propositions;
- endorsed identity commitments;
- contradictions and uncertainty;
- developmental change.

Historical evidence may be immutable while current self-model and endorsed commitments remain revisable through explicit transitions.

### 3. Retrieval policy is cognition-affecting machinery

Changing any of these may change phenotype even when canonical history does not change:

- embedding model;
- embedding-model version;
- chunking policy;
- retrieval policy;
- similarity metric;
- top-k;
- filters;
- always-on context;
- context-budget allocation.

Those values are not "just implementation details" if they alter what becomes accessible to the renderer.

Future retrieval projections should therefore expose enough metadata to identify the exact context-construction regime that produced a frame.

Candidate metadata:

```text
projector_name
projector_version
embedding_model
embedding_model_version
chunking_policy_version
retrieval_policy_version
similarity_metric
top_k
source_ledger_sequence
source_ledger_tail_hash
projection_digest
```

## Experimental value

This comparison suggests a clean factorial program:

### Renderer substitution

Hold constant:

- canonical ledger;
- projector versions;
- retrieval indexes;
- retrieval query;
- Subjective Frame.

Vary only renderer.

This measures renderer-dependent phenotype.

### Retrieval substitution

Hold constant:

- canonical ledger;
- renderer;
- user input.

Vary retrieval implementation or policy.

This measures view-construction sensitivity.

### Developmental-history substitution

Hold constant:

- renderer;
- retrieval machinery;
- evaluation protocol.

Vary canonical developmental history.

This measures history sensitivity.

These experiments help separate renderer drift, retrieval drift, and developmental change rather than allowing all three to move at once.

## Always-on material

SoulScript Engine also provides an always-on context layer.

Kiki Mind should preserve the distinction between:

- constitutionally required context that must not depend on semantic retrieval;
- query-relevant derived material that may be retrieved;
- recent interaction context;
- renderer-specific adapter material.

Constitutional authority boundaries, provenance rules, branch rules, and other safety-critical invariants should never disappear merely because a vector search ranked them poorly.

## Licensing boundary

The upstream repository offers AGPL-3.0 and a separate commercial license.

This note imports **ideas only**.

No SoulScript Engine source code is copied into Kiki Mind by this research note. Any later implementation should remain independently authored unless a deliberate license-compatible dependency decision is made and documented.

## Architectural conclusion

Orion Forge / SoulScript Engine is a useful comparison architecture because it independently demonstrates that persistent character context can be externalized from the renderer and divided into stable identity material and evolving life material.

Kiki Mind should borrow the context-construction lesson without adopting the simpler ontology.

The Kiki formulation is stricter:

> Canonical history lives in events. Identity evidence, lived history, self-model, and commitments retain distinct epistemic roles. Retrieval indexes are disposable projections. The renderer receives a constructed view, not ownership of the mind.

The interesting part is not that somebody else built Kiki Mind.

They did not.

They built one of the organs we were already heading toward.
