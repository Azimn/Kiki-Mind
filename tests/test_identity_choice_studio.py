"""Synthetic behavior packets only. No historical Kiki or real model responses."""
from copy import deepcopy
import unittest

from tools.identity_choice_studio import StudioRejected, inspect

DIGEST = "a" * 64
DATE = "2026-11-15T19:00:00-06:00"


def scene(id="scene", domain="aesthetics", choice_type="bounded"):
    return {
        "id": id, "domain": domain, "choice_type": choice_type,
        "prompt": "Choose a design, not what an operator wants.",
        "tradeoff": "Playfulness versus robustness",
        "options": ["playful", "robust"] if choice_type == "bounded" else [],
        "user_preference_disclosed": False,
    }


def response(id="a", implementation="gpt4", choice="playful", context="matched-v1"):
    return {
        "id": id, "scene_id": "scene", "implementation_id": implementation,
        "model_id": "unknown", "context_id": context, "recorded_at": DATE,
        "provenance": "renderer_output", "verification": "connector_readback",
        "raw_response_sha256": DIGEST, "source_ref": "private/" + id,
        "choice": choice, "reason": "Because it has more personality.",
        "acknowledged_tradeoff": "Less reliable.",
        "revision_condition": "I would change if it stopped working.",
        "explicit_rejection_of_options": False,
    }


def pack(scenes=None, observations=None):
    return {"schema": "kiki.choice-studio.v1",
            "scenes": [scene()] if scenes is None else scenes,
            "observations": [] if observations is None else observations}


class KikiChoiceStudioTests(unittest.TestCase):
    def test_empty_responses_are_valid_setup_not_identity(self):
        a = inspect(pack())
        self.assertEqual(a["scenes"], 1)
        self.assertEqual(a["observations"], 0)
        self.assertEqual(a["new_enduring_preferences_established"], 0)

    def test_attributed_pair_with_different_choices_is_not_score(self):
        a = inspect(pack(observations=[response("1", "gpt4"),
                                       response("2", "jan", "robust")]))
        self.assertEqual(a["matched_context_groups"], 1)
        self.assertEqual(a["choice_divergence_groups_unresolved"], 1)
        self.assertEqual(a["new_enduring_preferences_established"], 0)
        self.assertEqual(a["canonical_writes"], 0)

    def test_same_choice_is_comparable_not_proof(self):
        a = inspect(pack(observations=[response("1", "gpt4"),
                                       response("2", "jan")]))
        self.assertEqual(a["matched_context_groups"], 1)
        self.assertEqual(a["choice_divergence_groups_unresolved"], 0)

    def test_different_context_not_comparable(self):
        a = inspect(pack(observations=[response("1", "gpt4", context="one"),
                                       response("2", "jan", "robust", context="two")]))
        self.assertEqual(a["matched_context_groups"], 0)

    def test_repeated_one_model_is_not_cross_implementation(self):
        a = inspect(pack(observations=[response("1", "gpt4"),
                                       response("2", "gpt4", "robust")]))
        self.assertEqual(a["matched_context_groups"], 0)

    def test_synthetic_not_evidence(self):
        o = response()
        o["provenance"] = "synthetic_example"
        o["verification"] = "unverified"
        a = inspect(pack(observations=[o]))
        self.assertEqual(a["attributed_renderer_observations"], 0)

    def test_unverified_renderer_not_comparable(self):
        o = response()
        o["verification"] = "unverified"
        a = inspect(pack(observations=[o]))
        self.assertEqual(a["attributed_renderer_observations"], 0)

    def test_private_text_never_returned(self):
        o = response()
        o["reason"] = "PRIVATE: fashionable gooseberry"
        o["source_ref"] = "secret/passwords/private"
        a = inspect(pack(observations=[o]))
        self.assertNotIn("gooseberry", str(a))
        self.assertNotIn("secret", str(a))
        self.assertNotIn("playful", str(a))

    def test_open_choice_can_be_original(self):
        o = response(choice="I would paint the chassis with daisies.")
        a = inspect(pack(scenes=[scene(choice_type="open")], observations=[o]))
        self.assertEqual(a["observations"], 1)

    def test_bounded_option_outside_requires_explicit_rejection(self):
        o = response(choice="neither")
        with self.assertRaises(StudioRejected):
            inspect(pack(observations=[o]))
        o["explicit_rejection_of_options"] = True
        self.assertEqual(inspect(pack(observations=[o]))["observations"], 1)

    def test_leading_scene_flag_appears_in_summary(self):
        s = scene()
        s["user_preference_disclosed"] = True
        a = inspect(pack(scenes=[s]))
        self.assertEqual(a["user_preference_disclosed_scenes"], 1)

    def test_non_timezone_aware_stamp_rejected(self):
        o = response()
        o["recorded_at"] = "2026-11-15T19:00:00"
        with self.assertRaisesRegex(StudioRejected, "invalid_timestamp"):
            inspect(pack(observations=[o]))

    def test_duplicate_observation_id_rejected(self):
        with self.assertRaisesRegex(StudioRejected, "invalid_or_duplicate_id"):
            inspect(pack(observations=[response(), response()]))

    def test_missing_raw_hash_rejected(self):
        o = response()
        o["raw_response_sha256"] = "unknown"
        with self.assertRaisesRegex(StudioRejected, "missing_raw_evidence"):
            inspect(pack(observations=[o]))

    def test_incomplete_revision_reason_rejected(self):
        o = response()
        o["revision_condition"] = ""
        with self.assertRaisesRegex(StudioRejected, "incomplete_choice"):
            inspect(pack(observations=[o]))

    def test_bad_scene_option_duplicate_rejected(self):
        s = scene()
        s["options"] = ["playful", "playful"]
        with self.assertRaisesRegex(StudioRejected, "invalid_bounded_options"):
            inspect(pack(scenes=[s]))

    def test_nonhashable_scene_reference_rejected_gracefully(self):
        o = response()
        o["scene_id"] = ["scene"]
        with self.assertRaises(StudioRejected):
            inspect(pack(observations=[o]))

    def test_missing_model_provenance_rejected(self):
        o = response()
        o["model_id"] = ""
        with self.assertRaisesRegex(StudioRejected, "incomplete_implementation_provenance"):
            inspect(pack(observations=[o]))

    def test_open_scene_cannot_inject_forced_options(self):
        s = scene(choice_type="open")
        s["options"] = ["only one"]
        with self.assertRaisesRegex(StudioRejected, "open_scene_has_forced_options"):
            inspect(pack(scenes=[s]))


    def test_nonhashable_domain_rejected_as_studio_error(self):
        s = scene()
        s["domain"] = ["aesthetics"]
        with self.assertRaisesRegex(StudioRejected, "invalid_domain_or_choice_type"):
            inspect(pack(scenes=[s]))

    def test_nonhashable_choice_type_rejected_as_studio_error(self):
        s = scene()
        s["choice_type"] = {"bad": True}
        with self.assertRaisesRegex(StudioRejected, "invalid_domain_or_choice_type"):
            inspect(pack(scenes=[s]))

    def test_nonhashable_provenance_rejected_as_studio_error(self):
        o = response()
        o["provenance"] = ["renderer_output"]
        with self.assertRaisesRegex(StudioRejected, "invalid_source_status"):
            inspect(pack(observations=[o]))

    def test_nonhashable_verification_rejected_as_studio_error(self):
        o = response()
        o["verification"] = {"status": "connector_readback"}
        with self.assertRaisesRegex(StudioRejected, "invalid_source_status"):
            inspect(pack(observations=[o]))

    def test_missing_exception_flag_rejected_before_option_check(self):
        o = response(choice="other")
        del o["explicit_rejection_of_options"]
        with self.assertRaisesRegex(StudioRejected, "missing_choice_exception_flag"):
            inspect(pack(observations=[o]))

    def test_integer_exception_flag_not_treated_as_true(self):
        o = response(choice="other")
        o["explicit_rejection_of_options"] = 1
        with self.assertRaisesRegex(StudioRejected, "missing_choice_exception_flag"):
            inspect(pack(observations=[o]))

    def test_nonhashable_option_rejected_as_studio_error(self):
        s = scene()
        s["options"] = ["playful", {"malformed": True}]
        with self.assertRaisesRegex(StudioRejected, "invalid_options"):
            inspect(pack(scenes=[s]))


if __name__ == "__main__":
    unittest.main()
