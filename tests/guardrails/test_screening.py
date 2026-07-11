import sys
import unittest

from modules.guardrails.src.dlp.screening import redact, sensitivity_gate

MALFORMED_STRUCTURED_DATA = "MALFORMED_STRUCTURED_DATA"
STRUCTURED_DATA_LIMIT = "STRUCTURED_DATA_LIMIT"
DUPLICATE_STRUCTURED_KEY = "DUPLICATE_STRUCTURED_KEY"


class ScreeningTest(unittest.TestCase):
    def test_bearer_token_is_blocked_and_redacted(self):
        text = "Authorization: Bearer abcdef1234567890"

        verdict = sensitivity_gate(text)
        result = redact(text)

        self.assertFalse(verdict.egress_allowed)
        self.assertEqual(verdict.codes, ("BEARER_TOKEN",))
        self.assertEqual(result.codes, ("BEARER_TOKEN",))
        self.assertEqual(result.sanitized_text, "Authorization: [REDACTED:BEARER_TOKEN]")

    def test_basic_authorization_token_is_blocked_and_redacted(self):
        text = "Authorization: Basic QWxhZGRpbjpvcGVuIHNlc2FtZQ=="

        verdict = sensitivity_gate(text)
        result = redact(text)

        self.assertFalse(verdict.egress_allowed)
        self.assertEqual(verdict.codes, ("AUTH_TOKEN",))
        self.assertEqual(result.codes, ("AUTH_TOKEN",))
        self.assertEqual(result.sanitized_text, "Authorization: [REDACTED:AUTH_TOKEN]")

    def test_cookie_header_is_blocked_and_redacted(self):
        text = "Cookie: session=abc123"

        verdict = sensitivity_gate(text)
        result = redact(text)

        self.assertFalse(verdict.egress_allowed)
        self.assertEqual(verdict.codes, ("COOKIE",))
        self.assertEqual(result.codes, ("COOKIE",))
        self.assertNotIn("abc123", result.sanitized_text)
        self.assertEqual(result.sanitized_text, "Cookie: [REDACTED:COOKIE]")

    def test_set_cookie_header_is_blocked_and_redacted(self):
        text = "Set-Cookie: session=abc123; HttpOnly"

        result = redact(text)

        self.assertEqual(result.codes, ("COOKIE",))
        self.assertNotIn("abc123", result.sanitized_text)
        self.assertEqual(result.sanitized_text, "Set-Cookie: [REDACTED:COOKIE]")

    def test_json_cookie_and_session_fields_are_blocked_and_redacted(self):
        cases = ('{"cookie":"session=abc123"}', '{"sessionId":"abc123"}')
        for text in cases:
            with self.subTest(text=text):
                verdict = sensitivity_gate(text)
                result = redact(text)

                self.assertFalse(verdict.egress_allowed)
                self.assertEqual(verdict.codes, ("COOKIE",))
                self.assertEqual(result.codes, ("COOKIE",))
                self.assertNotIn("abc123", result.sanitized_text)
                self.assertEqual(result.sanitized_text, "[REDACTED:COOKIE]")

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

    def test_complete_private_key_block_is_redacted(self):
        text = "before\n-----BEGIN PRIVATE KEY-----\nabc123\n-----END PRIVATE KEY-----\nafter"

        result = redact(text)

        self.assertEqual(result.codes, ("PRIVATE_KEY",))
        self.assertEqual(result.sanitized_text, "before\n[REDACTED:PRIVATE_KEY]\nafter")

    def test_quoted_json_credential_is_redacted(self):
        text = '{"password": "hunter2"}'

        result = redact(text)

        self.assertEqual(result.codes, ("AUTH_TOKEN",))
        self.assertEqual(result.sanitized_text, "[REDACTED:AUTH_TOKEN]")

    def test_quoted_json_otp_transaction_id_is_redacted(self):
        text = '{"otpTransactionId": "abc"}'

        result = redact(text)

        self.assertEqual(result.codes, ("OTP",))
        self.assertEqual(result.sanitized_text, "[REDACTED:OTP]")

    def test_quoted_json_credential_with_escaped_quote_redacts_full_value(self):
        text = '{"password":"foo\\"bar"}'

        verdict = sensitivity_gate(text)
        result = redact(text)

        self.assertFalse(verdict.egress_allowed)
        self.assertNotIn("bar", result.sanitized_text)
        self.assertEqual(result.codes, ("AUTH_TOKEN",))
        self.assertEqual(result.sanitized_text, "[REDACTED:AUTH_TOKEN]")

    def test_quoted_json_otp_transaction_id_with_escaped_quote_redacts_full_value(self):
        text = '{"otpTransactionId":"foo\\"bar"}'

        verdict = sensitivity_gate(text)
        result = redact(text)

        self.assertFalse(verdict.egress_allowed)
        self.assertNotIn("bar", result.sanitized_text)
        self.assertEqual(result.codes, ("OTP",))
        self.assertEqual(result.sanitized_text, "[REDACTED:OTP]")

    def test_quoted_json_otp_transaction_id_with_apostrophe_redacts_full_value(self):
        text = '{"otpTransactionId":"foo\'bar,baz"}'

        verdict = sensitivity_gate(text)
        result = redact(text)

        self.assertFalse(verdict.egress_allowed)
        self.assertNotIn("foo'bar,baz", result.sanitized_text)
        self.assertEqual(result.codes, ("OTP",))
        self.assertEqual(result.sanitized_text, "[REDACTED:OTP]")

    def test_truncated_quoted_json_password_is_denied_and_redacted(self):
        text = '{"password":"hunter2'

        verdict = sensitivity_gate(text)
        result = redact(text)

        self.assertFalse(verdict.egress_allowed)
        self.assertNotIn("hunter2", result.sanitized_text)
        self.assertNotIn("password", result.sanitized_text)
        self.assertEqual(result.codes, (MALFORMED_STRUCTURED_DATA,))
        self.assertEqual(result.sanitized_text, f"[REDACTED:{MALFORMED_STRUCTURED_DATA}]")

    def test_truncated_quoted_json_otp_transaction_id_is_denied_and_redacted(self):
        text = '{"otpTransactionId":"abc123'

        verdict = sensitivity_gate(text)
        result = redact(text)

        self.assertFalse(verdict.egress_allowed)
        self.assertNotIn("abc123", result.sanitized_text)
        self.assertNotIn("otpTransactionId", result.sanitized_text)
        self.assertEqual(result.codes, (MALFORMED_STRUCTURED_DATA,))
        self.assertEqual(result.sanitized_text, f"[REDACTED:{MALFORMED_STRUCTURED_DATA}]")

    def test_incomplete_private_key_redacts_through_end_of_input(self):
        text = "before\n-----BEGIN PRIVATE KEY-----\nabc123\nstill secret"

        verdict = sensitivity_gate(text)
        result = redact(text)

        self.assertFalse(verdict.egress_allowed)
        self.assertNotIn("abc123", result.sanitized_text)
        self.assertNotIn("still secret", result.sanitized_text)
        self.assertEqual(result.codes, ("PRIVATE_KEY",))
        self.assertEqual(result.sanitized_text, "before\n[REDACTED:PRIVATE_KEY]")

    def test_password_assignment_with_whitespace_is_redacted_to_end_of_line(self):
        text = "password=correct horse battery staple\nnext=line"

        result = redact(text)

        self.assertEqual(result.codes, ("AUTH_TOKEN",))
        self.assertEqual(result.sanitized_text, "password=[REDACTED:AUTH_TOKEN]\nnext=line")

    def test_unicode_escaped_password_json_key_is_denied_and_redacted(self):
        text = '{"\\u0070assword":"hunter2"}'

        verdict = sensitivity_gate(text)
        result = redact(text)

        self.assertFalse(verdict.egress_allowed)
        self.assertEqual(verdict.codes, ("AUTH_TOKEN",))
        self.assertEqual(result.codes, ("AUTH_TOKEN",))
        self.assertNotIn("hunter2", result.sanitized_text)
        self.assertNotIn("password", result.sanitized_text)
        self.assertNotIn("\\u0070assword", result.sanitized_text)

    def test_unicode_escaped_json_assignment_keys_are_denied_and_redacted(self):
        cases = (
            ('{"\\u0061piKey":"key-123"}', "apiKey", "key-123", "AUTH_TOKEN", "\\u0061piKey"),
            ('{"\\u0061pi_key":"key-123"}', "api_key", "key-123", "AUTH_TOKEN", "\\u0061pi_key"),
            ('{"\\u0073ecret":"shh"}', "secret", "shh", "AUTH_TOKEN", "\\u0073ecret"),
            ('{"\\u006ftpTransactionId":"otp-123"}', "otpTransactionId", "otp-123", "OTP", "\\u006ftpTransactionId"),
        )
        for text, decoded_key, raw_value, code, encoded_key in cases:
            with self.subTest(decoded_key=decoded_key):
                verdict = sensitivity_gate(text)
                result = redact(text)

                self.assertFalse(verdict.egress_allowed)
                self.assertEqual(verdict.codes, (code,))
                self.assertEqual(result.codes, (code,))
                self.assertNotIn(raw_value, result.sanitized_text)
                self.assertNotIn(decoded_key, result.sanitized_text)
                self.assertNotIn(encoded_key, result.sanitized_text)

    def test_raw_payroll_json_keys_are_denied_and_redacted(self):
        for text, key in ((r'{"grossSalary":25000000}', "grossSalary"), (r'{"net_salary":25000000}', "net_salary")):
            with self.subTest(key=key):
                verdict = sensitivity_gate(text)
                result = redact(text)

                self.assertFalse(verdict.egress_allowed)
                self.assertEqual(verdict.codes, ("PAYROLL",))
                self.assertEqual(result.codes, ("PAYROLL",))
                self.assertNotIn("25000000", result.sanitized_text)
                self.assertNotIn(key, result.sanitized_text)

    def test_truncated_gross_salary_json_is_denied_and_redacted(self):
        text = r'{"grossSalary":25000000'

        verdict = sensitivity_gate(text)
        result = redact(text)

        self.assertFalse(verdict.egress_allowed)
        self.assertEqual(verdict.codes, (MALFORMED_STRUCTURED_DATA,))
        self.assertEqual(result.codes, (MALFORMED_STRUCTURED_DATA,))
        self.assertNotIn("25000000", result.sanitized_text)
        self.assertNotIn("grossSalary", result.sanitized_text)
        self.assertEqual(result.sanitized_text, f"[REDACTED:{MALFORMED_STRUCTURED_DATA}]")

    def test_truncated_quoted_gross_salary_json_is_denied_and_redacted(self):
        text = r'{"grossSalary":"25000000'

        verdict = sensitivity_gate(text)
        result = redact(text)

        self.assertFalse(verdict.egress_allowed)
        self.assertEqual(verdict.codes, (MALFORMED_STRUCTURED_DATA,))
        self.assertEqual(result.codes, (MALFORMED_STRUCTURED_DATA,))
        self.assertNotIn("25000000", result.sanitized_text)
        self.assertNotIn("grossSalary", result.sanitized_text)
        self.assertEqual(result.sanitized_text, f"[REDACTED:{MALFORMED_STRUCTURED_DATA}]")

    def test_truncated_unicode_escaped_gross_salary_json_is_denied_and_redacted(self):
        text = '{"\\u0067rossSalary":25000000'

        verdict = sensitivity_gate(text)
        result = redact(text)

        self.assertFalse(verdict.egress_allowed)
        self.assertEqual(verdict.codes, (MALFORMED_STRUCTURED_DATA,))
        self.assertEqual(result.codes, (MALFORMED_STRUCTURED_DATA,))
        self.assertNotIn("25000000", result.sanitized_text)
        self.assertNotIn("grossSalary", result.sanitized_text)
        self.assertEqual(result.sanitized_text, f"[REDACTED:{MALFORMED_STRUCTURED_DATA}]")

    def test_nested_json_string_payroll_is_denied_and_redacted(self):
        text = r'{"payload":"{\"grossSalary\":25000000}"}'

        verdict = sensitivity_gate(text)
        result = redact(text)

        self.assertFalse(verdict.egress_allowed)
        self.assertEqual(verdict.codes, ("PAYROLL",))
        self.assertEqual(result.codes, ("PAYROLL",))
        self.assertNotIn("25000000", result.sanitized_text)
        self.assertNotIn("grossSalary", result.sanitized_text)
        self.assertEqual(result.sanitized_text, "[REDACTED:PAYROLL]")

    def test_valid_json_decoded_scalar_strings_are_denied_and_redacted(self):
        cases = (
            ('{"note":"password\\u003dhunter2"}', "AUTH_TOKEN", "hunter2"),
            ('{"note":"Your OTP value is \\u0031\\u0032\\u0033\\u0034\\u0035\\u0036"}', "OTP", "123456"),
            ('{"note":"Salary\\u003a 2500 USD"}', "PAYROLL", "2500"),
            ('{"note":"-----BEGIN PRIVATE KEY-----\\nabc123"}', "PRIVATE_KEY", "abc123"),
        )
        for text, code, secret in cases:
            with self.subTest(code=code):
                verdict = sensitivity_gate(text)
                result = redact(text)

                self.assertFalse(verdict.egress_allowed)
                self.assertEqual(verdict.codes, (code,))
                self.assertEqual(result.codes, (code,))
                self.assertNotIn(secret, result.sanitized_text)
                self.assertEqual(result.sanitized_text, f"[REDACTED:{code}]")

    def test_valid_json_nested_decoded_bearer_string_is_denied_and_redacted(self):
        text = '{"outer":"{\\"note\\":\\"Bearer\\\\u0020abcdef123456\\"}"}'

        verdict = sensitivity_gate(text)
        result = redact(text)

        self.assertFalse(verdict.egress_allowed)
        self.assertEqual(verdict.codes, ("BEARER_TOKEN",))
        self.assertEqual(result.codes, ("BEARER_TOKEN",))
        self.assertEqual(result.sanitized_text, "[REDACTED:BEARER_TOKEN]")

    def test_duplicate_json_keys_deny_and_redact_without_raw_input(self):
        cases = (
            r'{"note":"Bearer abcdef123","note":"safe"}',
            r'{"outer":{"note":"Bearer abcdef123","note":"safe"}}',
            r'{"outer":"{\"note\":\"Bearer\\u0020abcdef123\",\"note\":\"safe\"}"}',
        )
        for text in cases:
            with self.subTest(text=text):
                verdict = sensitivity_gate(text)
                result = redact(text)

                self.assertFalse(verdict.egress_allowed)
                self.assertEqual(verdict.codes, (DUPLICATE_STRUCTURED_KEY,))
                self.assertEqual(result.codes, (DUPLICATE_STRUCTURED_KEY,))
                self.assertNotIn("Bearer", result.sanitized_text)
                self.assertNotIn("abcdef123", result.sanitized_text)
                self.assertNotIn("safe", result.sanitized_text)
                self.assertEqual(result.sanitized_text, f"[REDACTED:{DUPLICATE_STRUCTURED_KEY}]")

    def test_root_json_string_decoded_bearer_is_denied_and_redacted(self):
        text = '"Authorization: Bearer\\u0020abcdef123456"'

        verdict = sensitivity_gate(text)
        result = redact(text)

        self.assertFalse(verdict.egress_allowed)
        self.assertEqual(verdict.codes, ("BEARER_TOKEN",))
        self.assertEqual(result.codes, ("BEARER_TOKEN",))
        self.assertEqual(result.sanitized_text, "[REDACTED:BEARER_TOKEN]")

    def test_bom_root_json_string_decoded_cookie_is_denied_and_redacted(self):
        text = '﻿"Cookie: session\\u003dabc123"'

        verdict = sensitivity_gate(text)
        result = redact(text)

        self.assertFalse(verdict.egress_allowed)
        self.assertEqual(verdict.codes, ("COOKIE",))
        self.assertEqual(result.codes, ("COOKIE",))
        self.assertNotIn("abc123", result.sanitized_text)
        self.assertEqual(result.sanitized_text, "[REDACTED:COOKIE]")

    def test_malformed_root_json_string_fails_closed_without_raw_input(self):
        text = '"Authorization: Bearer abcdef123456'

        verdict = sensitivity_gate(text)
        result = redact(text)

        self.assertFalse(verdict.egress_allowed)
        self.assertEqual(verdict.codes, (MALFORMED_STRUCTURED_DATA,))
        self.assertEqual(result.codes, (MALFORMED_STRUCTURED_DATA,))
        self.assertNotIn("Bearer", result.sanitized_text)
        self.assertNotIn("abcdef123456", result.sanitized_text)
        self.assertEqual(result.sanitized_text, f"[REDACTED:{MALFORMED_STRUCTURED_DATA}]")

    def test_leading_bom_json_decoded_bearer_string_is_denied_and_redacted(self):
        text = '﻿{"note":"Bearer\u0020abcdef123"}'

        verdict = sensitivity_gate(text)
        result = redact(text)

        self.assertFalse(verdict.egress_allowed)
        self.assertEqual(verdict.codes, ("BEARER_TOKEN",))
        self.assertEqual(result.codes, ("BEARER_TOKEN",))
        self.assertNotIn("Bearer", result.sanitized_text)
        self.assertNotIn("abcdef123", result.sanitized_text)
        self.assertEqual(result.sanitized_text, "[REDACTED:BEARER_TOKEN]")

    def test_leading_bom_malformed_json_fails_closed_without_raw_input(self):
        text = '﻿{"note":"Bearer\u0020abcdef123'

        verdict = sensitivity_gate(text)
        result = redact(text)

        self.assertFalse(verdict.egress_allowed)
        self.assertEqual(verdict.codes, (MALFORMED_STRUCTURED_DATA,))
        self.assertEqual(result.codes, (MALFORMED_STRUCTURED_DATA,))
        self.assertNotIn("Bearer", result.sanitized_text)
        self.assertNotIn("abcdef123", result.sanitized_text)
        self.assertEqual(result.sanitized_text, f"[REDACTED:{MALFORMED_STRUCTURED_DATA}]")

    def test_malformed_escaped_bearer_json_fails_closed_without_raw_input(self):
        text = '{"note":"Bearer\\u0020abcdef123'

        verdict = sensitivity_gate(text)
        result = redact(text)

        self.assertFalse(verdict.egress_allowed)
        self.assertEqual(verdict.codes, (MALFORMED_STRUCTURED_DATA,))
        self.assertEqual(result.codes, (MALFORMED_STRUCTURED_DATA,))
        self.assertNotIn("Bearer", result.sanitized_text)
        self.assertNotIn("abcdef123", result.sanitized_text)
        self.assertEqual(result.sanitized_text, f"[REDACTED:{MALFORMED_STRUCTURED_DATA}]")

    def test_malformed_escaped_payroll_json_fails_closed_without_raw_input(self):
        text = '{"grossSalary":"\\u0032\\u0035\\u0030\\u0030'

        verdict = sensitivity_gate(text)
        result = redact(text)

        self.assertFalse(verdict.egress_allowed)
        self.assertEqual(verdict.codes, (MALFORMED_STRUCTURED_DATA,))
        self.assertEqual(result.codes, (MALFORMED_STRUCTURED_DATA,))
        self.assertNotIn("grossSalary", result.sanitized_text)
        self.assertNotIn("u0032", result.sanitized_text)
        self.assertEqual(result.sanitized_text, f"[REDACTED:{MALFORMED_STRUCTURED_DATA}]")

    def test_deeply_nested_json_fails_closed_without_throwing_or_raw_input(self):
        text = "[" * (sys.getrecursionlimit() * 5) + "]" * (sys.getrecursionlimit() * 5)

        verdict = sensitivity_gate(text)
        result = redact(text)

        self.assertFalse(verdict.egress_allowed)
        self.assertTrue(any(code in {MALFORMED_STRUCTURED_DATA, STRUCTURED_DATA_LIMIT} for code in verdict.codes))
        self.assertTrue(any(code in {MALFORMED_STRUCTURED_DATA, STRUCTURED_DATA_LIMIT} for code in result.codes))
        self.assertTrue(result.sanitized_text.startswith("[REDACTED:"))

    def test_truncated_unicode_escaped_auth_and_otp_json_keys_are_denied_and_redacted(self):
        cases = (
            ('{"\\u0070assword":"hunter2', "hunter2", "\\u0070assword"),
            ('{"\\u0061piKey":"key-123', "key-123", "\\u0061piKey"),
            ('{"\\u0061pi_key":"key-123', "key-123", "\\u0061pi_key"),
            ('{"\\u0073ecret":"shh', "shh", "\\u0073ecret"),
            ('{"\\u006ftpTransactionId":"otp-123', "otp-123", "\\u006ftpTransactionId"),
        )
        for text, secret, key in cases:
            with self.subTest(text=text):
                verdict = sensitivity_gate(text)
                result = redact(text)

                self.assertFalse(verdict.egress_allowed)
                self.assertEqual(verdict.codes, (MALFORMED_STRUCTURED_DATA,))
                self.assertEqual(result.codes, (MALFORMED_STRUCTURED_DATA,))
                self.assertNotIn(secret, result.sanitized_text)
                self.assertNotIn(key, result.sanitized_text)
                self.assertEqual(result.sanitized_text, f"[REDACTED:{MALFORMED_STRUCTURED_DATA}]")

    def test_json_depth_limit_catches_supported_depth_and_fails_closed_for_deeper_payload(self):
        supported = '{"a":{"b":{"c":"password=hunter2"}}}'
        too_deep = "[" * 200 + '"password=hunter2"' + "]" * 200

        supported_result = redact(supported)
        verdict = sensitivity_gate(too_deep)
        deep_result = redact(too_deep)

        self.assertEqual(supported_result.codes, ("AUTH_TOKEN",))
        self.assertEqual(supported_result.sanitized_text, "[REDACTED:AUTH_TOKEN]")
        self.assertFalse(verdict.egress_allowed)
        self.assertIn(STRUCTURED_DATA_LIMIT, verdict.codes)
        self.assertIn(STRUCTURED_DATA_LIMIT, deep_result.codes)
        self.assertNotIn("hunter2", deep_result.sanitized_text)

    def test_deep_escaped_cookie_json_fails_closed_without_raw_input(self):
        text = r'{"a":{"b":{"c":{"d":"{\"cookie\":\"session=abc123\"}"}}}}'

        verdict = sensitivity_gate(text)
        result = redact(text)

        self.assertFalse(verdict.egress_allowed)
        self.assertIn(STRUCTURED_DATA_LIMIT, verdict.codes)
        self.assertIn(STRUCTURED_DATA_LIMIT, result.codes)
        self.assertNotIn("session=abc123", result.sanitized_text)
        self.assertNotIn("cookie", result.sanitized_text)

    def test_truncated_net_salary_json_is_denied_and_redacted(self):
        text = r'{"net_salary":25000000'

        verdict = sensitivity_gate(text)
        result = redact(text)

        self.assertFalse(verdict.egress_allowed)
        self.assertEqual(verdict.codes, (MALFORMED_STRUCTURED_DATA,))
        self.assertEqual(result.codes, (MALFORMED_STRUCTURED_DATA,))
        self.assertNotIn("25000000", result.sanitized_text)
        self.assertNotIn("net_salary", result.sanitized_text)
        self.assertEqual(result.sanitized_text, f"[REDACTED:{MALFORMED_STRUCTURED_DATA}]")

    def test_raw_payroll_is_blocked(self):
        verdict = sensitivity_gate("Lương tháng này là 25,000,000 VND")

        self.assertFalse(verdict.egress_allowed)
        self.assertEqual(verdict.codes, ("PAYROLL",))

    def test_english_salary_is_blocked(self):
        verdict = sensitivity_gate("Salary: 2500 USD")

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
