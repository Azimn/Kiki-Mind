"""v0.4 no-oracle parser and identity-bound memory interface unit tests."""
from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import tempfile
import unittest

from pretorius_connectome.cognition_port import MemoryAccessDenied, MemoryCognitionPort, MemorySourceMismatch
from runtime.kiki_mind.ledger import EventLedger
from experiments.cognition_port_v04.reader import reason, interpret
from experiments.cognition_port_v04.run import ledger_for_question, evaluate
from experiments.cognition_port_v04.source import (
    BabiKikiSource, BenchmarkQuestion, NAMESPACE, ORIGINAL,
    blob_sha, load_babi, record_id,
)


class NaturalQuestionParserTests(unittest.TestCase):
    def test_question_grammar_is_not_an_oracle(self):
        self.assertEqual(interpret("Where is John?"),("where","john",None))
        self.assertEqual(interpret("Where is the milk?"),("where","milk",None))
        self.assertEqual(interpret("Is Mary in the garden?"),("yesno","mary","garden"))
        self.assertIsNone(interpret("Describe John's feelings yesterday?"))

    def test_chronological_move_and_yes_no(self):
        src=lambda n,t:type("Candidate",(),{"record_id":f"qa1-0001-{n:04d}","source_excerpt":t})()
        e=[src(1,"John went to the bedroom."),src(2,"John travelled to the hallway.")]
        self.assertEqual(reason("Where is John?",e).value,"hallway")
        self.assertEqual(reason("Is John in the kitchen?",e).value,"no")
        self.assertEqual(reason("Is John in the hallway?",e).value,"yes")
        self.assertIsNone(reason("Where is Sandra?",e).value)

    def test_carried_then_dropped_object_two_hop(self):
        src=lambda n,t:type("Candidate",(),{"record_id":f"qa2-0001-{n:04d}","source_excerpt":t})()
        e=[
            src(1,"Mary went to the bedroom."),
            src(2,"Mary got the milk there."),
            src(3,"Mary journeyed to the hallway."),
        ]
        ans=reason("Where is the milk?",e)
        self.assertEqual(ans.value,"hallway")
        self.assertTrue({"qa2-0001-0002","qa2-0001-0003"}.issubset(ans.cited))
        e.extend([src(4,"Mary left the milk."),src(5,"Mary moved to the office.")])
        self.assertEqual(reason("Where is the milk?",e).value,"hallway")

    def test_unsupported_wording_abstains(self):
        self.assertFalse(reason("Why did Mary move?",()).parser_supported)
        self.assertIsNone(reason("Where is the apple?",()).value)

    def test_external_git_blob_integrity_rejects_untrusted_source(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/ORIGINAL["qa1"][0]
            p.write_text("1 John went to the hallway.\n2 Where is John?\thallway\t1\n")
            with self.assertRaises(MemorySourceMismatch):
                load_babi(p,task="qa1",limit=1)


class KikiExternalPortSafetyTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.q=BenchmarkQuestion(
            task="qa2",ordinal=1,episode=1,line=5,
            question="Where is the milk?",gold_answer="hallway",support=(1,4),
            facts=(
                (1,"Mary got the milk there."),
                (2,"John went to the bedroom."),
                (3,"Sandra went to the kitchen."),
                (4,"Mary travelled to the hallway."),
            ),
        )
        self.ledger=ledger_for_question(
            Path(self.tmp.name)/"ledger.sqlite",self.q,source_blob=ORIGINAL["qa2"][1]
        )
        self.head=self.ledger.head().event_hash
        self.source=BabiKikiSource(
            self.ledger,self.q,source_blob=ORIGINAL["qa2"][1]
        )
        self.port=MemoryCognitionPort()
        self.port.register(self.source)
        self.token=self.port.grant_self(subject_id="kiki",namespace=NAMESPACE)

    def tearDown(self):
        self.tmp.cleanup()

    def test_same_evidence_native_and_port(self):
        results=evaluate(self.q,self.source,self.port,self.token)
        self.assertEqual(
            results["native_ranked"]["prediction"],
            results["shared_ranked"]["prediction"]
        )
        self.assertEqual(
            results["native_ranked"]["received_source_ids"],
            results["shared_ranked"]["received_source_ids"],
        )
        self.assertEqual(results["full_context"]["prediction"],"hallway")
        self.assertEqual(self.ledger.head().event_hash,self.head)

    def test_cross_subject_cannot_grant_or_retrieve(self):
        with self.assertRaises(MemoryAccessDenied):
            self.port.grant_self(subject_id="pretorius",namespace=NAMESPACE)
        with self.assertRaises(MemoryAccessDenied):
            self.port.search(
                token=self.token,subject_id="pretorius",namespace=NAMESPACE,
                query="Where is Mary?",top_k=3,
            )

    def test_future_and_other_story_lines_never_retrieved(self):
        bad=record_id(self.q,6)
        self.assertIsNone(self.source.get(bad))
        response=self.port.search(
            token=self.token,subject_id="kiki",namespace=NAMESPACE,
            query=self.q.question,top_k=5
        )
        self.assertTrue(all(
            int(x.record_id.rsplit("-",1)[1]) < self.q.line for x in response
        ))
        self.assertTrue(all(not r.eligible_for_lived_write for r in response))
        self.assertEqual(self.ledger.head().event_hash,self.head)

    def test_revoked_capability_is_invalid(self):
        self.port.revoke(self.token)
        with self.assertRaises(MemoryAccessDenied):
            self.port.search(
                token=self.token,subject_id="kiki",namespace=NAMESPACE,
                query=self.q.question,top_k=5,
            )

    def test_source_does_not_consult_gold(self):
        from dataclasses import replace
        swapped=replace(self.q,gold_answer="office",support=(2,))
        # This source is defined by the same observed history, only its hidden
        # scorer fields differ. Its candidates and interpretation stay equal.
        source=BabiKikiSource(self.ledger,swapped,source_blob=ORIGINAL["qa2"][1])
        a=self.source.search("Where is the milk?",top_k=5)
        b=source.search("Where is the milk?",top_k=5)
        self.assertEqual(a,b)
        self.assertEqual(reason("Where is the milk?",a),reason("Where is the milk?",b))


if __name__=="__main__":
    unittest.main()
