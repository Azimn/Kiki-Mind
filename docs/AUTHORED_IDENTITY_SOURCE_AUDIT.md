# Authored identity source integrity audit

**Status:** isolated experimental utility. It does not change the Kiki-Mind
canonical event ledger, any projection, or a deployed renderer.

## Purpose

An authored character instruction is evidence of **intended identity**.
It is not a transcript, a self-report, proof of behavioral consistency, or
autobiographical memory. Keep the unmodified original in authorized private
storage. Use the read-only local tool to record its byte fingerprint and
check the sequential numbering of any explicitly numbered rules.

The real K1-K1 MyGPT instructions must not be copied into this public
repository, commit messages, workflow logs, or test fixtures. The six
repository tests use only synthetic samples.

## Local usage

From the repository root, with a private UTF-8 original source file:

```bash
python tools/identity_source_audit.py /private/path/original-source.txt --expect-rules 39 --out /private/path/source-manifest.json
python -m unittest discover -s tests -p "test_identity_source_audit.py" -v
```

The manifest records only the SHA-256 of the actual input bytes, byte length,
UTF-8 validity, ordered numbered-rule count, final-newline flag, and a
fixed epistemic classification. It contains **no source text**.

The byte hash is exact, not semantic. If a private document export or text
editor changes newline conventions, Unicode encoding, or whitespace, the
hash will change. Preserve the original byte sequence separately and retain
the capture/export transformation in a private provenance record. Never
silently replace the original with an export.

## Boundaries and failures

The checker rejects empty sources, invalid UTF-8, missing or duplicate
rule numbers, and unexpected rule counts. An unnumbered original is allowed
unless an expected count is explicitly supplied. Rule counting does not
prove instruction authenticity, historical obedience, character identity,
or psychological continuity.

Before any canonical ingestion, a separate authorized evidence-import
process must verify source ownership, original versus capture dates,
provenance, restricted access, content hash, and the precise epistemic
class. This script performs **no ingest, mutation, publication, model
comparison, or personality scoring**.

In later controlled evaluations, preserve differences between authored
instructions, recorded character behavior, model-produced interpretations,
and verified developmental choices. Treat unknowns as unknowns.
