"""Unit tests for build.py.  Run: python3 -m unittest discover -s src"""
from __future__ import annotations

import re
import struct
import tempfile
import unittest
from pathlib import Path

import build


def vp8(w: int, h: int) -> bytes:
    """Return a minimal lossy (VP8) WebP header for the given size."""
    payload = b"\x00" * 3 + b"\x9d\x01\x2a" + struct.pack("<HH", w, h)
    return b"RIFF" + struct.pack("<I", 4 + 8 + len(payload)) + b"WEBP" + b"VP8 " + struct.pack("<I", len(payload)) + payload


def vp8l(w: int, h: int) -> bytes:
    """Return a minimal lossless (VP8L) WebP header for the given size."""
    bits = (w - 1) | ((h - 1) << 14)
    payload = b"\x2f" + bits.to_bytes(4, "little")
    return b"RIFF" + struct.pack("<I", 4 + 8 + len(payload)) + b"WEBP" + b"VP8L" + struct.pack("<I", len(payload)) + payload


def vp8x(w: int, h: int) -> bytes:
    """Return a minimal extended (VP8X) WebP header for the given size."""
    payload = b"\x00" * 4 + (w - 1).to_bytes(3, "little") + (h - 1).to_bytes(3, "little")
    return b"RIFF" + struct.pack("<I", 4 + 8 + len(payload)) + b"WEBP" + b"VP8X" + struct.pack("<I", len(payload)) + payload


class WebpSizeTest(unittest.TestCase):
    """webp_size reads all three WebP header variants."""

    def test_variants(self) -> None:
        self.assertEqual(build.webp_size(vp8(820, 648)), (820, 648))
        self.assertEqual(build.webp_size(vp8l(539, 719)), (539, 719))
        self.assertEqual(build.webp_size(vp8x(800, 1001)), (800, 1001))

    def test_rejects_non_webp(self) -> None:
        with self.assertRaises(ValueError):
            build.webp_size(b"\x89PNG\r\n\x1a\n" + b"\x00" * 30)

    def test_real_images(self) -> None:
        """Every image in src/img parses, and is roughly the expected web size."""
        for p in sorted(build.IMG.glob("*.webp")):
            w, h = build.webp_size(p.read_bytes())
            self.assertTrue(100 < w <= 1600 and 100 < h <= 1600, p.name)


class RenderTest(unittest.TestCase):
    """Card and library rendering."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.img = Path(self.tmp.name)
        (self.img / "AAA.webp").write_bytes(vp8(800, 600))
        self.cards = {
            "AAA": ("INT", "Dr. A", 'Says "hi" & it\'s fine.', None),
            "BBB": ("EXT", "Dr. B", "Two links.", [("The post", "https://www.instagram.com/p/BBB/"),
                                                  ("His Instagram", "https://www.instagram.com/drb/")]),
            "CCC": (None, "Dr. C", "No photo.", None),
        }
        (self.img / "BBB.webp").write_bytes(vp8(10, 10))

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_default_link_badge_and_escaping(self) -> None:
        out = build.render_card("AAA", self.cards["AAA"], set(), self.img)
        self.assertIn('<a class="ph" href="https://www.instagram.com/p/AAA/"', out)
        self.assertIn('width="800" height="600"', out)
        self.assertIn('<span class="badge int">Internal</span>', out)
        self.assertIn('alt="Dr. A: Says &quot;hi&quot; &amp; it&#x27;s fine."', out)
        self.assertIn(">View on Instagram</a>", out)

    def test_custom_links_use_first_for_image(self) -> None:
        out = build.render_card("BBB", self.cards["BBB"], set(), self.img)
        self.assertIn('<a class="ph" href="https://www.instagram.com/p/BBB/"', out)
        self.assertIn(">The post</a> · <a href=\"https://www.instagram.com/drb/\"", out)
        self.assertIn('<span class="badge ext">External</span>', out)

    def test_nophoto_tile_needs_no_image(self) -> None:
        out = build.render_card("CCC", self.cards["CCC"], {"CCC"}, self.img)
        self.assertIn('<a class="ph none"', out)
        self.assertNotIn("<img", out)

    def test_missing_image_fails_fast(self) -> None:
        with self.assertRaises(FileNotFoundError):
            build.render_card("CCC", self.cards["CCC"], set(), self.img)

    def test_zoom_link_opens_local_image(self) -> None:
        card = ("INT", "Dr. Z", "Two cases.", [("Profile", "https://www.instagram.com/drz/"), ("Second case", "zoom:BBB")])
        out = build.render_card("ZZZ", card, {"ZZZ"}, self.img)
        self.assertIn('class="zoomlink" data-zoom="data:image/webp;base64,', out)
        self.assertIn('<a class="ph none" href="https://www.instagram.com/drz/"', out)
        lib = build.render_library({"ZZZ": card}, [("1a. Test", ["ZZZ"])], self.img)
        self.assertNotIn("zoomlink", lib)  # the sources list keeps web links only

    def test_zoom_link_missing_image_fails_fast(self) -> None:
        with self.assertRaises(FileNotFoundError):
            build.link_html("Second case", "zoom:NOPE", self.img)

    def test_library_and_count(self) -> None:
        groups = [("1. One", ["AAA", "BBB"]), ("2. Two", ["CCC", "AAA"])]
        lib = build.render_library(self.cards, groups)
        self.assertEqual(lib.count("<h4>"), 2)
        self.assertIn('(<a href="https://www.instagram.com/drb/" target="_blank" rel="noopener">His Instagram</a>)', lib)
        # AAA counted once; the profile link on BBB is not a post.
        self.assertEqual(build.library_count(self.cards, groups), 3)

    def test_figures_never_wider_than_real_size(self) -> None:
        out = build.build('<img src="IMG:AAA" alt="x">', self.cards, set(), [], self.img)
        self.assertIn('width="800" height="600" style="max-width:min(100%,800px)" alt="x"', out)

    def test_build_unknown_key_fails_fast(self) -> None:
        with self.assertRaises(KeyError):
            build.build("EX:ZZZ", self.cards, set(), [], self.img)


class SiteDataTest(unittest.TestCase):
    """The real template and data agree with each other."""

    def setUp(self) -> None:
        self.template = (build.SRC / "index.src.html").read_text(encoding="utf-8")

    def test_every_placeholder_resolves(self) -> None:
        for key in re.findall(r"EX:([\w-]+)", self.template):
            self.assertIn(key, build.C)
            if key not in build.NOPHOTO:
                self.assertTrue((build.IMG / f"{key}.webp").exists(), key)
        for key in re.findall(r'src="IMG:([\w-]+)"', self.template):
            self.assertTrue((build.IMG / f"{key}.webp").exists(), key)
        for _, keys in build.GROUPS:
            for key in keys:
                self.assertIn(key, build.C)

    def test_built_page_has_no_leftover_placeholders(self) -> None:
        out = build.build(self.template, build.C, build.NOPHOTO, build.GROUPS)
        for marker in ("EX:", "IMG:", "LIBRARY", "LIBCOUNT"):
            self.assertNotIn(marker, out)

    def test_no_group_chat_wording(self) -> None:
        """Content rule: the public site never refers to the private chat or its members."""
        out = build.build(self.template, build.C, build.NOPHOTO, build.GROUPS)
        text = re.sub(r"data:image/webp;base64,[A-Za-z0-9+/=]+", "", out)
        banned = r"\bmembers?\b|\bmember's\b|\bour group\b|\bgroup chat\b|whatsapp|\bchat\b|\bof us\b|\bwe've\b|\bwe're\b|\bour take\b"
        hits = [m.group(0) for m in re.finditer(banned, text, re.I)]
        self.assertEqual(hits, [])

    def test_composite_cards_are_labeled(self) -> None:
        """Content rule: every card in the composite graft library groups has an Internal/External badge."""
        composite = [h for h, _ in build.GROUPS if "composite" in h.lower()]
        self.assertEqual(len(composite), 2)
        for heading, keys in build.GROUPS:
            if heading in composite:
                for key in keys:
                    self.assertIn(build.C[key][0], ("INT", "EXT"), key)


if __name__ == "__main__":
    unittest.main()
