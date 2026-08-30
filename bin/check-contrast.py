#!/usr/bin/env python3
"""
WCAG 2.2 contrast checker for the Cortex Operations System state tokens.

No JS test runner exists in this repo (no package.json/vitest anywhere),
so this is the real, dependency-free substitute for the design system
spec's "vérification que les couleurs texte importantes respectent
contraste AA" requirement — it parses the actual shipped CSS custom
properties (not a hand-copied palette that could drift from the file)
and fails loudly if any text/background pair falls under 4.5:1, or any
badge border falls under 3:1 against the page background it actually
sits on (WCAG 2.2 SC 1.4.11 non-text contrast: a border's job is to
make a component's *boundary* against its surroundings perceivable —
these badges use pale ~50-level tint fills that measure ~1.1:1 against
white on their own, so the border, not the fill, is what has to carry
that boundary; border-vs-own-fill is the wrong pair to test).

First run of this script (see CHANGELOG.md) found the design spec's
literal border hex values failed 3:1 against white on every single
state — none of the pastel border tints cleared it. Fixed by swapping
each state's border to its palette's 500/600-level shade (same hue
family, same intent), verified below rather than eyeballed.

Usage: python3 bin/check-contrast.py
Exit code 0 = every pair passes; 1 = at least one fails (prints why).
"""

import re
import sys
from pathlib import Path

TOKENS_CSS = Path(__file__).resolve().parent.parent / "apps/cortex_rental/cortex_rental/public/css/cortex-tokens.css"

TEXT_MIN_RATIO = 4.5  # WCAG 2.2 AA, normal text
GRAPHICAL_MIN_RATIO = 3.0  # WCAG 2.2 AA, graphical objects / component boundaries


def parse_tokens(css_text):
    tokens = {}
    for match in re.finditer(r"--([\w-]+):\s*(#[0-9a-fA-F]{6});", css_text):
        tokens[match.group(1)] = match.group(2)
    return tokens


def hex_to_srgb(hex_color):
    hex_color = hex_color.lstrip("#")
    return tuple(int(hex_color[i : i + 2], 16) / 255.0 for i in (0, 2, 4))


def relative_luminance(rgb):
    def channel(c):
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = (channel(c) for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast_ratio(hex_a, hex_b):
    l1 = relative_luminance(hex_to_srgb(hex_a))
    l2 = relative_luminance(hex_to_srgb(hex_b))
    lighter, darker = max(l1, l2), min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)


# Every business-state token triple defined in cortex-tokens.css.
STATE_KEYS = [
    "quote",
    "draft",
    "reservation",
    "contract",
    "checked-out",
    "partial-return",
    "returned",
    "invoice-prepared",
    "invoiced",
    "closed",
    "cancelled",
    "disputed",
    "conflict",
    "quarantine",
    "repair",
    "missing",
]


def main():
    css_text = TOKENS_CSS.read_text()
    tokens = parse_tokens(css_text)

    failures = []
    checked = 0

    for key in STATE_KEYS:
        bg = tokens.get(f"state-{key}-bg")
        text = tokens.get(f"state-{key}-text")
        border = tokens.get(f"state-{key}-border")
        if not (bg and text and border):
            failures.append(f"state-{key}: missing bg/text/border token(s) in {TOKENS_CSS.name}")
            continue

        checked += 1
        text_ratio = contrast_ratio(bg, text)
        if text_ratio < TEXT_MIN_RATIO:
            failures.append(
                f"state-{key}: text {text} on bg {bg} = {text_ratio:.2f}:1, "
                f"below WCAG 2.2 AA normal-text minimum {TEXT_MIN_RATIO}:1"
            )

        # The border's real job (see module docstring): stay perceivable
        # against the page background the badge is placed on, not its
        # own pale fill. Check both realistic surfaces.
        for page_key in ("cortex-surface", "cortex-surface-subtle"):
            page_bg = tokens[page_key]
            border_ratio = contrast_ratio(page_bg, border)
            checked += 1
            if border_ratio < GRAPHICAL_MIN_RATIO:
                failures.append(
                    f"state-{key}: border {border} on {page_key} {page_bg} = {border_ratio:.2f}:1, "
                    f"below WCAG 2.2 AA graphical-object minimum {GRAPHICAL_MIN_RATIO}:1"
                )

    # A handful of the other text/surface pairs components actually use.
    surface_pairs = [
        ("cortex-text", "cortex-bg", TEXT_MIN_RATIO),
        ("cortex-text", "cortex-surface", TEXT_MIN_RATIO),
        ("cortex-text-secondary", "cortex-surface", TEXT_MIN_RATIO),
        ("cortex-text-muted", "cortex-surface", TEXT_MIN_RATIO),
        ("cortex-inverse", "cortex-primary-600", TEXT_MIN_RATIO),  # primary button label
        ("cortex-danger-700", "cortex-danger-50", TEXT_MIN_RATIO),  # destructive button label hover (cortex-utilities.css)
    ]
    for text_key, bg_key, minimum in surface_pairs:
        text, bg = tokens.get(text_key), tokens.get(bg_key)
        if not (text and bg):
            failures.append(f"{text_key}/{bg_key}: missing token(s)")
            continue
        checked += 1
        ratio = contrast_ratio(bg, text)
        if ratio < minimum:
            failures.append(f"{text_key} on {bg_key} = {ratio:.2f}:1, below {minimum}:1")

    print(f"Checked {checked} token pairs against WCAG 2.2 AA.")
    if failures:
        print(f"\n{len(failures)} FAILURE(S):")
        for f in failures:
            print(f"  ✗ {f}")
        return 1

    print("✓ All token pairs meet WCAG 2.2 AA contrast minimums.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
