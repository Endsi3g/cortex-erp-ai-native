"""Phase 8 : mode sombre. Contraste de la palette (WCAG), couche générée sans effet en mode clair, choix par personne."""

import pathlib
import re
import unittest
from types import SimpleNamespace

from cortex_rental.services import account

ROOT = pathlib.Path(__file__).resolve().parents[1]
DARK = ROOT / "public" / "css" / "cortex-dark.css"


def channel(value: int) -> float:
    v = value / 255
    return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4


def luminance(hex_color: str) -> float:
    h = hex_color.lstrip("#")
    r, g, b = (int(h[i : i + 2], 16) for i in (0, 2, 4))
    return 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b)


def contrast(a: str, b: str) -> float:
    la, lb = luminance(a), luminance(b)
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)


def header_tokens() -> dict:
    css = DARK.read_text(encoding="utf-8")
    block = css.split('html[data-theme="dark"] {', 1)[1].split("}", 1)[0]
    return dict(re.findall(r"(--[\w-]+):\s*(#[0-9a-fA-F]{6})", block))


class TestDarkPalette(unittest.TestCase):
    def test_text_levels_are_readable_on_every_dark_surface(self):
        t = header_tokens()
        surfaces = [
            t["--cortex-bg"],
            t["--cortex-canvas"],
            t["--cortex-surface"],
            t["--cortex-surface-subtle"],
            t["--cortex-surface-hover"],
        ]
        for surface in surfaces:
            self.assertGreaterEqual(contrast(t["--cortex-text"], surface), 7.0, surface)
            self.assertGreaterEqual(contrast(t["--cortex-text-secondary"], surface), 7.0, surface)
            self.assertGreaterEqual(contrast(t["--cortex-text-muted"], surface), 4.5, surface)
            # `--cortex-border-strong` sert aussi de texte discret dans les composants.
            self.assertGreaterEqual(contrast(t["--cortex-border-strong"], surface), 4.5, surface)

    def test_semantic_text_is_readable_on_its_tint_and_on_the_surface(self):
        t = header_tokens()
        pairs = [
            ("--cortex-emerald-800", "--cortex-emerald-50"),
            ("--cortex-warning-800", "--cortex-warning-50"),
            ("--cortex-danger-800", "--cortex-danger-50"),
            ("--cortex-info-800", "--cortex-info-50"),
            ("--cortex-danger-700", "--cortex-danger-50"),
        ]
        for text, tint in pairs:
            self.assertGreaterEqual(contrast(t[text], t[tint]), 4.5, f"{text} sur {tint}")
            self.assertGreaterEqual(contrast(t[text], t["--cortex-surface"]), 4.5, f"{text} sur la surface")

    def test_inverse_button_pair_is_readable(self):
        css = DARK.read_text(encoding="utf-8")
        t = header_tokens()
        self.assertGreaterEqual(contrast(t["--cortex-inverse"], "#f4f4f5"), 7.0)
        self.assertIn("#f4f4f5", css)

    def test_color_scheme_is_declared_for_native_controls(self):
        self.assertIn("color-scheme: dark", DARK.read_text(encoding="utf-8"))


class TestGeneratedLayer(unittest.TestCase):
    def setUp(self):
        self.css = DARK.read_text(encoding="utf-8")

    def test_it_is_generated_and_never_touches_light_mode(self):
        self.assertIn("GÉNÉRÉ par bin/generate-dark-theme.mjs", self.css)
        self.assertNotIn("@import", self.css)
        # Chaque règle (hors @media et @keyframes) vise html[data-theme="dark"] : rien ne s'applique en mode clair.
        for selector_block in re.findall(r"(?m)^([^\s@/}{][^{]*)\{", self.css):
            for selector in selector_block.split(","):
                self.assertTrue(selector.strip().startswith('html[data-theme="dark"]'), selector.strip())
        self.assertNotIn("@keyframes", self.css)

    def test_media_blocks_are_nested_under_the_dark_selector(self):
        for inner in re.findall(r"@media[^{]*\{\n((?:.|\n)*?)\n\}\n", self.css):
            for selector in re.findall(r"(?m)^\t([^\s}{][^{]*)\{", inner):
                self.assertTrue(selector.strip().startswith('html[data-theme="dark"]'), selector.strip())

    def test_only_palette_colors_are_emitted(self):
        allowed = set(re.findall(r"#[0-9a-fA-F]{6}\b", self.css.split("}", 1)[0] + self.css.split("}", 2)[1]))
        palette = {
            "#111113",
            "#0c0c0e",
            "#18181b",
            "#1f1f23",
            "#27272a",
            "#2e2e33",
            "#52525b",
            "#f4f4f5",
            "#d4d4d8",
            "#a1a1aa",
            "#09090b",
            "#6ee7b7",
            "#fbbf24",
            "#fca5a5",
            "#93c5fd",
            "#0f2a1f",
            "#2e2210",
            "#2d1517",
            "#14233a",
            "#14532d",
            "#5c4310",
            "#5c2226",
            "#71717a",
            "#303036",
            "#9696a0",
            "#123524",
            "#3a2b12",
            "#3b1b1e",
            "#172b47",
            "#94a3b8",  # base du texte « shimmer » d'attente : gris moyen, 6,7:1 sur les surfaces sombres
        }
        used = set(c.lower() for c in re.findall(r"#[0-9a-fA-F]{6}\b", self.css))
        self.assertTrue(used <= palette | allowed, sorted(used - palette - allowed))

    def test_it_is_loaded_last_and_the_generator_is_documented(self):
        hooks = (ROOT / "hooks.py").read_text(encoding="utf-8")
        css_list = hooks.split("app_include_css = [", 1)[1].split("]", 1)[0]
        self.assertTrue(css_list.rstrip().rstrip(",").endswith('cortex-dark.css"'))
        generator_path = ROOT.parents[2] / "bin" / "generate-dark-theme.mjs"
        if not generator_path.exists():
            self.skipTest("le générateur est dans le dépôt, pas dans un bench (testé hors bench)")
        self.assertIn("jamais modifié", generator_path.read_text(encoding="utf-8"))


class TestThemeChoice(unittest.TestCase):
    def test_only_the_three_known_values_and_only_for_the_signed_in_person(self):
        saved = []
        original = account.frappe
        original_user = account._user
        try:

            def throw(message, exc=None):
                raise ValueError(message)

            account.frappe = SimpleNamespace(
                throw=throw,
                ValidationError=ValueError,
                db=SimpleNamespace(
                    set_value=lambda doctype, name, field, value: saved.append((doctype, name, field, value))
                ),
            )
            account._user = lambda: "moi@exemple.ca"
            for theme in ("Light", "Dark", "Automatic"):
                self.assertEqual(account.set_theme(theme), {"theme": theme})
            with self.assertRaises(ValueError):
                account.set_theme("Neon")
            with self.assertRaises(ValueError):
                account.set_theme("")
            self.assertEqual({row[1] for row in saved}, {"moi@exemple.ca"})
            self.assertEqual({row[2] for row in saved}, {"desk_theme"})
        finally:
            account.frappe, account._user = original, original_user

    def test_endpoint_is_a_limited_post_without_a_user_argument(self):
        api = (ROOT / "api" / "v1" / "account.py").read_text(encoding="utf-8")
        head = api.split("def set_theme", 1)[0].rsplit("@frappe.whitelist", 1)[1]
        self.assertTrue(head.startswith('(methods=["POST"])'))
        self.assertIn('limit_user("set_theme"', head)
        signature = api.split("def set_theme", 1)[1].split(":", 1)[0]
        self.assertNotIn("user", signature)

    def test_light_is_the_default_and_the_profile_offers_the_choice(self):
        self.assertEqual(account.THEMES[0], "Light")
        source = (ROOT / "services" / "account.py").read_text(encoding="utf-8")
        self.assertIn('doc.desk_theme if doc.desk_theme in THEMES else "Light"', source)
        page = (ROOT / "cortex_rental" / "page" / "cortex_account" / "cortex_account.js").read_text(encoding="utf-8")
        self.assertIn('"Light"', page)
        self.assertIn("cortex.applyTheme(value)", page)
        views = (ROOT / "public" / "js" / "cortex_views.js").read_text(encoding="utf-8")
        self.assertIn('data-theme", dark ? "dark" : "light"', views)


class TestFinishing(unittest.TestCase):
    def test_loading_and_reduced_motion_are_covered_for_the_new_surfaces(self):
        motion = (ROOT / "public" / "css" / "cortex-motion.css").read_text(encoding="utf-8")
        self.assertIn("prefers-reduced-motion: reduce", motion)
        home = (ROOT / "public" / "js" / "cortex_home" / "CortexHome.vue").read_text(encoding="utf-8")
        self.assertIn("prefers-reduced-motion: reduce", home)


if __name__ == "__main__":
    unittest.main()
