"""Contrôle de mise en production : jugement sur la configuration du site (sans bench)."""

import unittest

from cortex_rental.ops import predeploy

SAFE = {
    "developer_mode": 0,
    "host_name": "https://app.exemple.ca",
    "encryption_key": "abc",
    "max_file_size": 10485760,
}


def levels(conf):
    return {name: level for level, name, _detail in predeploy.evaluate_site_config(conf)}


class TestSiteConfig(unittest.TestCase):
    def test_a_safe_production_config_has_no_failure(self):
        results = levels(SAFE)
        self.assertNotIn(predeploy.FAIL, results.values())
        self.assertNotIn(predeploy.WARN, results.values())

    def test_developer_mode_is_blocking(self):
        self.assertEqual(levels({**SAFE, "developer_mode": 1})["developer_mode"], predeploy.FAIL)

    def test_load_test_rate_limit_factor_is_blocking(self):
        self.assertEqual(levels({**SAFE, "cortex_rate_limit_factor": 1000})["limites de débit"], predeploy.FAIL)
        self.assertEqual(levels({**SAFE, "cortex_rate_limit_factor": 1})["limites de débit"], predeploy.OK)

    def test_mock_ai_engine_is_blocking(self):
        self.assertEqual(levels({**SAFE, "cortex_chat_provider": "mock"})["moteur IA"], predeploy.FAIL)

    def test_missing_encryption_key_is_blocking(self):
        conf = {k: v for k, v in SAFE.items() if k != "encryption_key"}
        self.assertEqual(levels(conf)["clé de chiffrement"], predeploy.FAIL)

    def test_wildcard_cors_is_blocking(self):
        self.assertEqual(levels({**SAFE, "allow_cors": "*"})["CORS"], predeploy.FAIL)
        self.assertEqual(levels({**SAFE, "allow_cors": ["*"]})["CORS"], predeploy.FAIL)

    def test_plain_http_host_is_a_warning(self):
        self.assertEqual(levels({**SAFE, "host_name": "http://x"})["adresse publique"], predeploy.WARN)


if __name__ == "__main__":
    unittest.main()
