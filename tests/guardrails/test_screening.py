import unittest

from modules.guardrails.src.dlp.screening import redact, sensitivity_gate


class ScreeningTest(unittest.TestCase):
    def test_bearer_token_is_blocked_and_redacted(self):
        text = "Authorization: Bearer abcdef1234567890"

        verdict = sensitivity_gate(text)
        result = redact(text)

        self.assertFalse(verdict.egress_allowed)
        self.assertEqual(verdict.codes, ("BEARER_TOKEN",))
        self.assertEqual(result.codes, ("BEARER_TOKEN",))
        self.assertEqual(result.sanitized_text, "Authorization: [REDACTED:BEARER_TOKEN]")

    def test_otp_is_blocked(self):
        text = "Your OTP value is 123456"

        verdict = sensitivity_gate(text)
        result = redact(text)

        self.assertFalse(verdict.egress_allowed)
        self.assertEqual(verdict.codes, ("OTP",))
        self.assertEqual(result.sanitized_text, "Your [REDACTED:OTP]")

    def test_private_key_is_blocked(self):
        verdict = sensitivity_gate("-----BEGIN PRIVATE KEY-----")

        self.assertFalse(verdict.egress_allowed)
        self.assertEqual(verdict.codes, ("PRIVATE_KEY",))

    def test_raw_payroll_is_blocked(self):
        verdict = sensitivity_gate("Lương tháng này là 25,000,000 VND")

        self.assertFalse(verdict.egress_allowed)
        self.assertEqual(verdict.codes, ("PAYROLL",))

    def test_benign_vietnamese_sentence_passes_unchanged(self):
        text = "Tôi cần xem lịch làm việc hôm nay."

        verdict = sensitivity_gate(text)
        result = redact(text)

        self.assertTrue(verdict.egress_allowed)
        self.assertEqual(verdict.codes, ())
        self.assertEqual(result.codes, ())
        self.assertEqual(result.sanitized_text, text)


if __name__ == "__main__":
    unittest.main()
