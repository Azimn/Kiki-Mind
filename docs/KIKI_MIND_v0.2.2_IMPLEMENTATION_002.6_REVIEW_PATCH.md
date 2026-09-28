# Kiki Mind v0.2.2 - Implementation 002.6 Review Patch

## The label on the dress is not the dress

**Status:** hostile-review hardening  
**Architecture:** Kiki Mind v0.2.2 remains frozen  
**Base implementation:** 002.5  
**Scope:** projection-store schema integrity

### Finding

The projection store verified:

- the exact user-table set;
- the exact column-name sequence.

That still left one laundering path.

A manually recreated `projection_state` table could keep the expected column names while weakening types or constraints. The verifier would accept the labels even though the mechanism underneath them had changed.

We already learned this lesson with append-only trigger names in Implementation 001.2.

### Resolution

The canonical projection-table definition now lives in one expected SQL constant.

Fresh-store initialization uses that definition.

Schema verification fetches the actual `CREATE TABLE` SQL from `sqlite_schema`, normalizes insignificant whitespace and case, and requires it to match the expected definition.

Column-order checking remains as an additional diagnostic.

### Probe

The hostile test replaces `projection_state` with a table that has the same column names but omits the required checks.

The store must reject it as table-definition drift.

### Architectural consequence

A familiar label does not get authority over a changed mechanism.

Like, a counterfeit Chanel tag does not make the bag Chanel, babe.
