import unittest

from cortex_rental.services.idempotency import _hash_payload, _record_name, with_idempotency


class TestIdempotencyHelpers(unittest.TestCase):
    def test_record_name_is_deterministic_per_company_scope_key(self):
        n1 = _record_name("CineRental Montreal", "quotes.create_quote_draft", "req-123")
        n2 = _record_name("CineRental Montreal", "quotes.create_quote_draft", "req-123")
        self.assertEqual(n1, n2)

    def test_record_name_differs_across_company_or_key(self):
        base = _record_name("CineRental Montreal", "quotes.create_quote_draft", "req-123")
        other_company = _record_name("Other Co", "quotes.create_quote_draft", "req-123")
        other_key = _record_name("CineRental Montreal", "quotes.create_quote_draft", "req-456")
        self.assertNotEqual(base, other_company)
        self.assertNotEqual(base, other_key)

    def test_hash_payload_is_order_independent(self):
        h1 = _hash_payload({"a": 1, "b": 2})
        h2 = _hash_payload({"b": 2, "a": 1})
        self.assertEqual(h1, h2)

    def test_without_frappe_handler_always_executes(self):
        """
        In this sandbox (no bench/frappe), with_idempotency degrades to a
        plain pass-through — it cannot dedup without a database. Real
        dedup/race/mismatched-payload behavior is exercised against a
        live Frappe site; see the module docstring in
        services/idempotency.py.
        """
        calls = []

        def handler():
            calls.append(1)
            return {"ok": True}

        with_idempotency("CineRental Montreal", "quotes.create_quote_draft", "req-123", {"a": 1}, handler)
        with_idempotency("CineRental Montreal", "quotes.create_quote_draft", "req-123", {"a": 1}, handler)
        self.assertEqual(len(calls), 2)


if __name__ == "__main__":
    unittest.main()
