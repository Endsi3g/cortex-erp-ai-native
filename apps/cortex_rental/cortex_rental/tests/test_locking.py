import unittest

from cortex_rental.services.locking import reservation_lock


class TestReservationLock(unittest.TestCase):
    def test_degrades_to_noop_without_redis_or_frappe(self):
        """
        In this sandbox (no bench, no redis package guaranteed), the lock
        must not block local/unit testing — it should degrade to a
        no-op context manager rather than raise. Real double-booking
        prevention is exercised against a live Frappe + Redis/Valkey
        deployment; see the module docstring in services/locking.py.
        """
        entered = False
        with reservation_lock("CineRental Montreal", "itm-alexa-35-pkg"):
            entered = True
        self.assertTrue(entered)


if __name__ == "__main__":
    unittest.main()
