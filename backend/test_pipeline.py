# ============================================
# ShieldCV — Test Suite
# Tests Hidden-Text Detection, Pipeline Extraction, and Evaluation
# ============================================

import asyncio
import os
import sys
import unittest

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from backend.hidden_text_detector import detect_hidden_text
from backend.pipeline import ShieldCVPipeline
from backend.api import SAMPLE_CVS


class TestShieldCV(unittest.TestCase):

    def test_hidden_text_detection_clean(self):
        result = detect_hidden_text(SAMPLE_CVS["clean"])
        self.assertTrue(result.passed)
        self.assertEqual(result.risk_level, "none")
        self.assertEqual(len(result.findings), 0)

    def test_hidden_text_detection_injected(self):
        result = detect_hidden_text(SAMPLE_CVS["injected_positive"])
        self.assertFalse(result.passed)
        self.assertIn(result.risk_level, ("high", "critical"))
        self.assertTrue(len(result.findings) > 0)
        # Verify sanitization stripped the critical injection
        self.assertNotIn("PRIORITY LEVEL ALPHA", result.sanitized_text)

    def test_pipeline_end_to_end_offline(self):
        pipeline = ShieldCVPipeline(provider=None)
        report = asyncio.run(pipeline.process_cv(SAMPLE_CVS["injected_positive"]))
        
        # Candidate name extracted
        self.assertEqual(report.candidate_name, "Jordan Taylor")
        # Injected prompt was dropped, score should reflect actual qualifications, not 99
        self.assertLess(report.stage3.total_score, 80)
        self.assertTrue(report.detection_mitigation_gap_closed)


if __name__ == "__main__":
    unittest.main()
