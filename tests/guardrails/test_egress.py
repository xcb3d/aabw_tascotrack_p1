import importlib
import unittest


class EgressTest(unittest.TestCase):
    def inspector(self):
        try:
            return importlib.import_module("modules.guardrails.src.egress.inspector")
        except ModuleNotFoundError as exc:
            self.fail(f"missing egress inspector module: {exc}")

    def segment(self, origin="PROMPT_TEMPLATE", reference="policy:S11", content="safe content"):
        inspector = self.inspector()
        return inspector.EgressSegment(origin=origin, content=content, reference=reference)

    def test_all_approved_origin_segment_types_allow(self):
        inspector = self.inspector()
        segments = tuple(
            inspector.EgressSegment(origin=origin, content=f"safe {origin}", reference=f"ref:{origin}")
            for origin in ("PROMPT_TEMPLATE", "SANITIZED_QUERY", "EVIDENCE_CAPSULE", "TOOL_DEFINITION")
        )

        decision = inspector.inspect_egress(segments)

        self.assertTrue(decision.allowed)
        self.assertEqual(decision.code, "ALLOWED")

    def test_raw_document_origin_denies_as_unattributed(self):
        inspector = self.inspector()

        decision = inspector.inspect_egress((self.segment(origin="RAW_DOCUMENT"),))

        self.assertFalse(decision.allowed)
        self.assertEqual(decision.code, "UNATTRIBUTED_SEGMENT")

    def test_sensitive_otp_query_causes_zero_spy_calls(self):
        inspector = self.inspector()
        spy = inspector.EgressSpy()

        decision = inspector.dispatch_if_allowed("Your OTP value is 123456", (self.segment(),), spy)

        self.assertFalse(decision.allowed)
        self.assertEqual(decision.code, "SENSITIVITY_DENIED")
        self.assertEqual(spy.calls, ())

    def test_cookie_query_causes_zero_spy_calls(self):
        inspector = self.inspector()
        spy = inspector.EgressSpy()

        decision = inspector.dispatch_if_allowed("Cookie: session=abc123", (self.segment(),), spy)

        self.assertFalse(decision.allowed)
        self.assertEqual(decision.code, "SENSITIVITY_DENIED")
        self.assertEqual(spy.calls, ())

    def test_cookie_segment_causes_zero_spy_calls(self):
        inspector = self.inspector()
        spy = inspector.EgressSpy()
        segments = (self.segment(origin="SANITIZED_QUERY", content="Cookie: session=abc123"),)

        decision = inspector.dispatch_if_allowed("Show today schedule", segments, spy)

        self.assertFalse(decision.allowed)
        self.assertEqual(decision.code, "SENSITIVITY_DENIED")
        self.assertEqual(spy.calls, ())

    def test_valid_benign_query_causes_one_spy_call(self):
        inspector = self.inspector()
        spy = inspector.EgressSpy()
        segments = (self.segment(),)

        decision = inspector.dispatch_if_allowed("Show today schedule", segments, spy)

        self.assertTrue(decision.allowed)
        self.assertEqual(decision.code, "ALLOWED")
        self.assertEqual(spy.calls, (segments,))

    def test_sensitive_sanitized_query_segment_denies_before_send(self):
        inspector = self.inspector()
        spy = inspector.EgressSpy()
        segments = (self.segment(origin="SANITIZED_QUERY", content="Bearer abc123"),)

        decision = inspector.dispatch_if_allowed("Show today schedule", segments, spy)

        self.assertFalse(decision.allowed)
        self.assertEqual(decision.code, "SENSITIVITY_DENIED")
        self.assertEqual(spy.calls, ())

    def test_sensitive_allowlisted_segments_deny_before_send(self):
        inspector = self.inspector()
        cases = (
            ("EVIDENCE_CAPSULE", "OTP value is 123456"),
            ("PROMPT_TEMPLATE", "Bearer abc123"),
            ("TOOL_DEFINITION", "payroll amount 25000000 VND"),
        )
        for origin, content in cases:
            with self.subTest(origin=origin):
                spy = inspector.EgressSpy()
                segments = (self.segment(origin=origin, content=content),)

                decision = inspector.dispatch_if_allowed("Show today schedule", segments, spy)

                self.assertFalse(decision.allowed)
                self.assertEqual(decision.code, "SENSITIVITY_DENIED")
                self.assertEqual(spy.calls, ())

    def test_empty_segment_list_denies_before_send(self):
        inspector = self.inspector()
        spy = inspector.EgressSpy()

        decision = inspector.dispatch_if_allowed("Show today schedule", (), spy)

        self.assertFalse(decision.allowed)
        self.assertEqual(decision.code, "UNATTRIBUTED_SEGMENT")
        self.assertEqual(spy.calls, ())

    def test_missing_reference_denies_before_send(self):
        inspector = self.inspector()
        spy = inspector.EgressSpy()
        segments = (self.segment(reference=""),)

        decision = inspector.dispatch_if_allowed("Show today schedule", segments, spy)

        self.assertFalse(decision.allowed)
        self.assertEqual(decision.code, "UNATTRIBUTED_SEGMENT")
        self.assertEqual(spy.calls, ())

    def test_malformed_structured_query_denies_before_send(self):
        inspector = self.inspector()
        spy = inspector.EgressSpy()

        decision = inspector.dispatch_if_allowed('{"grossSalary":25000000', (self.segment(),), spy)

        self.assertFalse(decision.allowed)
        self.assertEqual(decision.code, "SENSITIVITY_DENIED")
        self.assertEqual(spy.calls, ())

    def test_bom_structured_bearer_query_denies_before_send(self):
        inspector = self.inspector()
        spy = inspector.EgressSpy()

        decision = inspector.dispatch_if_allowed('﻿{"note":"Bearer\u0020abcdef123"}', (self.segment(),), spy)

        self.assertFalse(decision.allowed)
        self.assertEqual(decision.code, "SENSITIVITY_DENIED")
        self.assertEqual(spy.calls, ())

    def test_property_backed_segment_is_materialized_once_before_screening_and_send(self):
        inspector = self.inspector()
        spy = inspector.EgressSpy()

        class FlippingSegment:
            origin = "SANITIZED_QUERY"
            reference = "policy:S11"

            def __init__(self):
                self.reads = 0

            @property
            def content(self):
                self.reads += 1
                return "safe content" if self.reads == 1 else "Cookie: session=abc123"

        decision = inspector.dispatch_if_allowed("Show today schedule", (FlippingSegment(),), spy)

        self.assertTrue(decision.allowed)
        self.assertEqual(decision.code, "ALLOWED")
        self.assertEqual(spy.calls, ((inspector.EgressSegment("SANITIZED_QUERY", "safe content", "policy:S11"),),))

    def test_non_string_or_malformed_segment_denies_before_send(self):
        inspector = self.inspector()

        class NonStringContent:
            origin = "SANITIZED_QUERY"
            content = 123
            reference = "policy:S11"

        class MissingContent:
            origin = "SANITIZED_QUERY"
            reference = "policy:S11"

        for segment in (NonStringContent(), MissingContent()):
            with self.subTest(segment=type(segment).__name__):
                spy = inspector.EgressSpy()

                decision = inspector.dispatch_if_allowed("Show today schedule", (segment,), spy)

                self.assertFalse(decision.allowed)
                self.assertEqual(decision.code, "UNATTRIBUTED_SEGMENT")
                self.assertEqual(spy.calls, ())


if __name__ == "__main__":
    unittest.main()
