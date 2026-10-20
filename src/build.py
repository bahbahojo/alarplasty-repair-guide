"""Build index.html from src/index.src.html, the card data below and src/img/*.webp.

No dependencies. Run from anywhere:  python3 src/build.py

Placeholders replaced in the template:
  EX:KEY             an example card (data in C)
  <img src="IMG:KEY" an inline base64 WebP, plus its width and height
  LIBRARY            the "Instagram examples by method" list (built from GROUPS)
  LIBCOUNT           the number of distinct Instagram posts in that list
"""
from __future__ import annotations

import base64
import html
import re
import struct
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

SRC = Path(__file__).resolve().parent
ROOT = SRC.parent
IMG = SRC / "img"

Link = Tuple[str, str]  # (label, url)
Card = Tuple[Optional[str], str, str, Optional[List[Link]]]  # (badge, by, why, links)

# ---------------------------------------------------------------------------
# Card data.  key: (badge, by, why, links_or_None)
#   badge: 'INT', 'EXT' or None
#   links: None means one "View on Instagram" link to https://www.instagram.com/p/KEY/.
#          Otherwise the first link is also where the image points.
# ---------------------------------------------------------------------------
C: Dict[str, Card] = {
    'DRKpan3DK2B': (None, 'Dr. Tolga Bilece, November 2025',
        'A conservative alarplasty: only a thin sliver of outer skin removed, nostril size kept. On the operating table.',
        None),
    'CtxKAyvsVrC': (None, 'Dr. Sam Most, June 2023',
        'A long-term revision result. The nostrils look fuller after derotation. This patient never had an alarplasty. Video, so play it on Instagram.',
        None),
    'DNlENwgRSK6': (None, 'Dr. Ari Hyman, August 2025',
        'Seven months after a revision to bring down an upturned tip.',
        None),
    'CvzpOS9LfUA': (None, 'Dr. Ari Hyman, August 2023',
        'Three months after a revision to correct uneven nostrils. Shared as an example of strong derotation.',
        None),
    'CfKFXSSM_ij': ('INT', 'Dr. Oguzhan Oguz',
        'Rebuilding a lost nostril from the inside: before, at 1 month and at 7 months. The group thought it healed well. He posted the same case again in April 2026 as a video.',
        [('Photo post', 'https://www.instagram.com/p/CfKFXSSM_ij/'), ('April 2026 video', 'https://www.instagram.com/p/DW9bqs9DP2O/')]),
    'DA_U7hhzFpO': ('INT', 'Dr. Kidakorn Kiranantawat (Thailand), 2024',
        'Severe nostril narrowing after cosmetic surgery, fixed with a composite graft from the ear. Shown 1 year and 10 months later.',
        None),
    'C9T-1AKikBg': ('INT', 'Dr. Sercan Göde',
        '"Larger and better nostrils are possible." Rib cartilage plus composite grafts, on darker skin.',
        None),
    'C7AHUWHr0EC': ('INT', 'Dr. Ahmet Halit Aydın, May 2024',
        'A complicated ethnic revision with a composite graft on one side. One of the very few Black patients we found.',
        None),
    'nazari1': ('INT', 'Dr. Shahriar Nazari (Iran)',
        'From his Instagram stories, tagged "alar expansion". His captions read "nasal reconstruction and enlarging the nasal ala".',
        [('His Instagram', 'https://www.instagram.com/drnazari.ent/')]),
    'C2PcmLwCJjr': ('INT', 'Dr. Sercan Göde, 2024',
        'An alar retraction repair. One member remembers this case differently, as outside grafts that scarred, so ask him directly.',
        None),
    'C4aw7VvLpcT': ('EXT', 'Dr. Jason Roostaeian (US)',
        '"Correcting the over-resected alar base." Members felt these healed well, with visibly bigger nostrils.',
        None),
    'DdjfmFaiHD1': ('EXT', 'Dr. Amir Sazgar (Tehran), October 2026',
        'One month after rebuilding a nose with six failed surgeries and past skin death. Too early to judge the scars.',
        [('The post', 'https://www.instagram.com/p/DdjfmFaiHD1/'), ('His Instagram', 'https://www.instagram.com/dr.sazgar/')]),
    'DUmywnTE25f': ('EXT', 'Dr. Shingyochi (Japan), February 2026',
        'A difficult alar revision. You can see the old alarplasty scars at the base of the nostrils.',
        [('The post', 'https://www.instagram.com/p/DUmywnTE25f/'), ('A 2025 case', 'https://www.instagram.com/p/DKQwfgBzBS9/'), ('His Instagram', 'https://www.instagram.com/dr_shingyochi/')]),
    'Dc-6ZC0DtEn': (None, 'Dr. Sercan Göde, September 2026',
        '"Alar base reversing by local island flaps." Taken on the operating table, so expect it to settle.',
        None),
    'DeW6vF1jt3r': (None, 'Dr. Sercan Göde, October 2026',
        "One year after a complex revision with flaps. The early scars looked rough. One of the few one-year results we've seen.",
        None),
    'DdyuYXvOeFV': (None, 'Dr. Sercan Göde',
        '"Alar base reduction reversal." A lip island flap case, before and after.',
        None),
    'DWZJXExjdWT': (None, 'Dr. Sercan Göde, March 2026',
        'A complicated revision with flaps. The video has close-ups of the scars, and members disagreed on how visible they are.',
        None),
    'DXOl6j1jTTu': (None, 'Dr. Sercan Göde, April 2026',
        'Five months after a complex revision. Members found the scars noticeable even with a filter.',
        None),
    'DTrpzjbCB2S': (None, 'Dr. Sercan Göde, January 2026',
        'Tip and columella skin death, two months after reconstruction. Shared to show how his flaps work.',
        None),
    'Cwo231ssL6S': (None, 'Dr. Sercan Göde',
        'A revision that lengthened the columella and improved retraction. Members think an island flap was used.',
        None),
    'DHOkgaOie6A': (None, 'Dr. Sercan Göde, March 2025',
        'An alar retraction repair. Members noticed teardrop notches afterwards, like this one.',
        None),
    'DaDwPhCDK2-': (None, 'Dr. Oguzhan Oguz, June 2026',
        '"When tissue is lost, reconstruction becomes the only option." Members felt his flaps were less refined than Göde\'s.',
        None),
    'DWkekGciEX0': (None, 'Dr. Sercan Göde, March 2026',
        'An extreme revision on a Black patient after skin death. A very severe case, and the scars are visible.',
        None),
    'DcIw_t7jiQn': (None, 'Dr. Ziad Katrib',
        'Reinforcing a weak tip with rib cartilage. Structure before skin.',
        None),
    'DVfzFTJk8OF': (None, 'Dr. Shingyochi (Japan), March 2026',
        'Fixing the scar and the shape around the nostril.',
        None),
}
NOPHOTO: Set[str] = {'DWkekGciEX0', 'DHOkgaOie6A'}
GROUPS: List[Tuple[str, List[str]]] = [
    ('1. Derotation', ['CtxKAyvsVrC', 'DNlENwgRSK6', 'CvzpOS9LfUA']),
    ('2a. Internal composite grafts', ['CfKFXSSM_ij', 'DA_U7hhzFpO', 'C9T-1AKikBg', 'C7AHUWHr0EC', 'nazari1', 'C2PcmLwCJjr']),
    ('2b. External composite grafts', ['C4aw7VvLpcT', 'DdjfmFaiHD1', 'DUmywnTE25f']),
    ('3b. Lip and cheek island flaps', ['Dc-6ZC0DtEn', 'DeW6vF1jt3r', 'DdyuYXvOeFV', 'DWZJXExjdWT', 'DXOl6j1jTTu', 'DTrpzjbCB2S', 'Cwo231ssL6S', 'DHOkgaOie6A', 'DaDwPhCDK2-', 'DWkekGciEX0']),
    ('4. Other', ['DRKpan3DK2B', 'DcIw_t7jiQn', 'DVfzFTJk8OF']),
]

BADGES: Dict[str, Tuple[str, str]] = {"INT": ("int", "Internal"), "EXT": ("ext", "External")}
A = ' target="_blank" rel="noopener"'


def post_url(key: str) -> str:
    """Return the Instagram post URL for a shortcode."""
    return f"https://www.instagram.com/p/{key}/"


def card_links(key: str, card: Card) -> List[Link]:
    """Return a card's links, filling in the default single Instagram link."""
    links = card[3]
    return links if links is not None else [("View on Instagram", post_url(key))]


def webp_size(data: bytes) -> Tuple[int, int]:
    """Read (width, height) from a WebP file header.

    WebP is a RIFF container. The first chunk after "WEBP" is one of:
      VP8   lossy:    14-bit width/height at bytes 26 and 28 (after a 3-byte start code)
      VP8L  lossless: 1 signature byte, then width-1 and height-1 packed as 14 bits each
      VP8X  extended: 24-bit canvas width-1 and height-1 at bytes 24 and 27
    """
    if data[:4] != b"RIFF" or data[8:12] != b"WEBP":
        raise ValueError("not a WebP file")
    chunk = data[12:16]
    if chunk == b"VP8 ":
        if data[23:26] != b"\x9d\x01\x2a":
            raise ValueError("bad VP8 start code")
        w, h = struct.unpack("<HH", data[26:30])
        return w & 0x3FFF, h & 0x3FFF
    if chunk == b"VP8L":
        if data[20] != 0x2F:
            raise ValueError("bad VP8L signature")
        bits = int.from_bytes(data[21:25], "little")
        return (bits & 0x3FFF) + 1, ((bits >> 14) & 0x3FFF) + 1
    if chunk == b"VP8X":
        w = int.from_bytes(data[24:27], "little") + 1
        h = int.from_bytes(data[27:30], "little") + 1
        return w, h
    raise ValueError(f"unknown WebP chunk {chunk!r}")


def img_attrs(key: str, img_dir: Path = IMG) -> str:
    """Return 'src="data:..." width="W" height="H"' for src/img/KEY.webp. Fails if the file is missing."""
    data = (img_dir / f"{key}.webp").read_bytes()
    w, h = webp_size(data)
    return f'src="data:image/webp;base64,{base64.b64encode(data).decode("ascii")}" width="{w}" height="{h}"'


def render_card(key: str, card: Card, nophoto: Set[str], img_dir: Path = IMG) -> str:
    """Render one example card as a single-line <figure class="ex">."""
    badge, by, why, _ = card
    links = card_links(key, card)
    e_by, e_why = html.escape(by), html.escape(why)
    if key in nophoto:
        ph = f'<a class="ph none" href="{links[0][1]}"{A}>Photo only viewable on Instagram</a>'
    else:
        ph = (f'<a class="ph" href="{links[0][1]}"{A}><img {img_attrs(key, img_dir)} '
              f'alt="{e_by}: {e_why}" loading="lazy"></a>')
    b = ""
    if badge:
        cls, label = BADGES[badge]
        b = f'<span class="badge {cls}">{label}</span>'
    lk = " · ".join(f'<a href="{u}"{A}>{html.escape(t)}</a>' for t, u in links)
    return (f'<figure class="ex">{ph}<figcaption>{b}<p class="by">{e_by}</p>'
            f'<p class="why">{e_why}</p><p class="lk">{lk}</p></figcaption></figure>')


def render_library(cards: Dict[str, Card], groups: List[Tuple[str, List[str]]]) -> str:
    """Render the "Instagram examples by method" lists, one <h4> + <ul> per group."""
    out = []
    for heading, keys in groups:
        items = []
        for key in keys:
            badge, by, why, _ = cards[key]
            links = card_links(key, cards[key])
            b = ""
            if badge:
                cls, label = BADGES[badge]
                b = f' <span class="badge {cls}">{label}</span>'
            extra = ""
            if len(links) > 1:
                extra = ' <span class="small">(' + ", ".join(
                    f'<a href="{u}"{A}>{html.escape(t)}</a>' for t, u in links[1:]) + ")</span>"
            items.append(f'<li><a href="{links[0][1]}"{A}>{html.escape(by)}</a>{b}{extra}'
                         f'<p>{html.escape(why)}</p></li>')
        out.append(f'<h4>{html.escape(heading)}</h4><ul class="lib">{"".join(items)}</ul>')
    return "\n".join(out)


def library_count(cards: Dict[str, Card], groups: List[Tuple[str, List[str]]]) -> int:
    """Count distinct Instagram post URLs (not profile links) across the library."""
    urls = {u for _, keys in groups for k in keys for _, u in card_links(k, cards[k])
            if u.startswith("https://www.instagram.com/p/")}
    return len(urls)


def build(template: str, cards: Dict[str, Card], nophoto: Set[str],
          groups: List[Tuple[str, List[str]]], img_dir: Path = IMG) -> str:
    """Replace every placeholder in the template. Unknown keys or missing images raise."""
    out = re.sub(r"EX:([\w-]+)", lambda m: render_card(m.group(1), cards[m.group(1)], nophoto, img_dir), template)
    out = re.sub(r'src="IMG:([\w-]+)"', lambda m: img_attrs(m.group(1), img_dir), out)
    out = out.replace("LIBCOUNT", str(library_count(cards, groups)))
    out = out.replace("LIBRARY", render_library(cards, groups))
    return out


def main() -> None:
    """Build index.html at the repo root."""
    template = (SRC / "index.src.html").read_text(encoding="utf-8")
    out = build(template, C, NOPHOTO, GROUPS)
    (ROOT / "index.html").write_text(out, encoding="utf-8")
    print(f"index.html: {len(out.encode('utf-8')) / 1e6:.2f} MB")


if __name__ == "__main__":
    main()
