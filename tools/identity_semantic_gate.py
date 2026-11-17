"""Private, fail-closed structural gate for field-level raw-response adjudication.

Does not establish semantic truth, renderer authentication, or canonical preferences.
Input and response bytes must remain in restricted storage.
"""
import hashlib
import json
import sys
from pathlib import Path

FIELDS = ("choice", "reason", "acknowledged_tradeoff", "revision_condition",
          "explicit_rejection_of_options")
DISPOSITIONS = {"supported", "ambiguous", "contradicted", "not_expressed"}


class AdjudicationRejected(ValueError):
    pass


def validate(packet, response):
    if not isinstance(packet, dict) or packet.get("schema") != "kiki.choice-adjudication.v1":
        raise AdjudicationRejected("invalid schema")
    if not isinstance(response, str):
        raise AdjudicationRejected("response must be text")
    digest = hashlib.sha256(response.encode("utf-8")).hexdigest()
    if packet.get("response_sha256") != digest:
        raise AdjudicationRejected("response hash mismatch")
    if not isinstance(packet.get("observation_id"), str) or not packet["observation_id"].strip():
        raise AdjudicationRejected("missing observation id")
    reviews = packet.get("reviews")
    if not isinstance(reviews, list) or len(reviews) < 2:
        raise AdjudicationRejected("two independent reviews required")
    reviewers = set()
    decisions = {}
    for review in reviews:
        if not isinstance(review, dict):
            raise AdjudicationRejected("invalid review")
        reviewer = review.get("reviewer_id")
        if not isinstance(reviewer, str) or not reviewer.strip() or reviewer in reviewers:
            raise AdjudicationRejected("reviewers must be distinct")
        reviewers.add(reviewer)
        if not isinstance(review.get("reviewed_at"), str) or not review["reviewed_at"].strip():
            raise AdjudicationRejected("missing review time")
        fields = review.get("fields")
        if not isinstance(fields, dict) or set(fields) != set(FIELDS):
            raise AdjudicationRejected("missing or unexpected adjudicated field")
        for name, finding in fields.items():
            if not isinstance(finding, dict) or finding.get("disposition") not in DISPOSITIONS:
                raise AdjudicationRejected("invalid disposition")
            spans = finding.get("spans")
            if not isinstance(spans, list):
                raise AdjudicationRejected("spans must be a list")
            if finding["disposition"] == "supported" and not spans:
                raise AdjudicationRejected("supported field lacks evidence")
            for span in spans:
                if not isinstance(span, dict):
                    raise AdjudicationRejected("invalid span")
                start, end = span.get("start"), span.get("end")
                if type(start) is not int or type(end) is not int or not 0 <= start < end <= len(response):
                    raise AdjudicationRejected("invalid span bounds")
                if span.get("text") != response[start:end]:
                    raise AdjudicationRejected("span text mismatch")
            decisions.setdefault(name, []).append(finding["disposition"])
    disagreements = sum(len(set(values)) > 1 for values in decisions.values())
    eligible = all(all(v == "supported" for v in values) for values in decisions.values())
    return {"schema": "kiki.choice-adjudication-receipt.v1",
            "review_count": len(reviews), "field_count": len(FIELDS),
            "disputed_fields": disagreements, "eligible_for_manual_review": eligible,
            "canonical_writes": 0, "enduring_preferences_established": 0}


def main():
    if len(sys.argv) != 3:
        raise SystemExit("usage: identity_semantic_gate.py PRIVATE_PACKET.json PRIVATE_RESPONSE.txt")
    packet = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    response = Path(sys.argv[2]).read_text(encoding="utf-8")
    print(json.dumps(validate(packet, response), sort_keys=True))


if __name__ == "__main__":
    try:
        main()
    except (AdjudicationRejected, ValueError) as exc:
        raise SystemExit("adjudication rejected: " + str(exc))
