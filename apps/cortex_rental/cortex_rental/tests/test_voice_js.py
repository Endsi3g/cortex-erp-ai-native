"""Exécute les tests Node de la saisie vocale quand Node est disponible (sinon ignorés, jamais faussement verts)."""

import pathlib
import shutil
import subprocess
import unittest

JS_TESTS = pathlib.Path(__file__).resolve().parent / "js"


@unittest.skipUnless(shutil.which("node"), "Node est requis pour les tests JavaScript")
class TestVoiceInput(unittest.TestCase):
    def test_node_suite_passes(self):
        files = sorted(str(path) for path in JS_TESTS.glob("*.test.mjs"))
        self.assertTrue(files, "aucun test JavaScript trouvé")
        result = subprocess.run(["node", "--test", *files], capture_output=True, text=True, timeout=120)
        self.assertEqual(result.returncode, 0, result.stdout[-2000:] + result.stderr[-2000:])
