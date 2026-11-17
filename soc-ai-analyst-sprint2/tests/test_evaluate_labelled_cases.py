import unittest
from pathlib import Path

from benchmarks.evaluate_labelled_cases import evaluate, load_json

EXAMPLES = Path(__file__).resolve().parents[1] / "benchmarks/examples"


class TestLabelledEvaluation(unittest.TestCase):
    def test_examples(self):
        labels = load_json(EXAMPLES / "us22-labels.json")
        reports = map(load_json, sorted(EXAMPLES.glob("us22-*-report.json")))
        result = evaluate(labels, reports)
        self.assertEqual(result["technique_agreement_rate"], 0.5)
        self.assertEqual(result["unsupported_claim_count"], 1)
        self.assertEqual(result["missing_evidence_count"], 1)
        case = result["cases"][0]
        self.assertEqual(case["matching_techniques"], ["T1110"])
        self.assertEqual(case["unsupported_claims"], [
            {"technique_id": "T1078", "reason": "unlabelled"}
        ])
        self.assertEqual(case["missing_evidence"], [
            {"technique_id": "T1110", "alert_ids": ["auth-failure-2"]}
        ])

    def test_matching_technique_with_wrong_citation(self):
        report = {
            "case_id": "test",
            "attack_mapping": [
                {
                    "technique_id": "T1110",
                    "status": "supported",
                    "evidence": [{"alert_id": "routine"}],
                }
            ],
        }
        [case] = evaluate({"test": {"T1110": ["failure"]}}, [report])["cases"]
        self.assertTrue(case["agreement"])
        self.assertEqual(case["unsupported_claims"][0]["alert_ids"], ["routine"])
        self.assertEqual(case["missing_evidence"][0]["alert_ids"], ["failure"])

    def test_rejects_invalid_input(self):
        valid_report = {"case_id": "test", "attack_mapping": []}
        for reports, error in (
            ([{"case_id": "test"}], "attack_mapping"),
            ([{"case_id": "other"}], "No labels"),
            ([], "At least one case"),
            ([valid_report, valid_report], "Duplicate report"),
        ):
            with self.subTest(error=error), self.assertRaisesRegex(ValueError, error):
                evaluate({"test": {}}, reports)

    def test_rejected_technique_does_not_count_as_a_positive_claim(self):
        report = {
            "case_id": "test",
            "attack_mapping": [
                {
                    "technique_id": "T1110",
                    "status": "not_supported",
                    "evidence": [{"alert_id": "failure"}],
                },
                {"technique_id": None, "status": "unknown", "evidence": []},
            ],
        }
        result = evaluate({"test": {"T1110": ["failure"]}}, [report])
        self.assertEqual(result["cases"][0]["missing_techniques"], ["T1110"])
        self.assertEqual(result["missing_evidence_count"], 1)
        self.assertEqual(result["unsupported_claim_count"], 0)
