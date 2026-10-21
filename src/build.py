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
        'Longer-term results of a complex revision with nasal lengthening and tip and alar reconstruction. The nostrils look fuller. Video, so play it on Instagram.',
        None),
    'DNlENwgRSK6': (None, 'Dr. Ari Hyman, August 2025',
        'Seven months after a revision to bring down an upturned tip.',
        None),
    'CvzpOS9LfUA': (None, 'Dr. Ari Hyman, August 2023',
        'Three months after a revision to correct uneven nostrils.',
        None),
    'CfKFXSSM_ij': ('INT', 'Dr. Oguzhan Oguz',
        'His caption: "Reconstruction of nostril and alar base with skin graft", for a nostril lost to a complication. Before, at 1 month and at 7 months. He posted the same case again in April 2026 as a video.',
        [('Photo post', 'https://www.instagram.com/p/CfKFXSSM_ij/'), ('April 2026 video', 'https://www.instagram.com/p/DW9bqs9DP2O/')]),
    'DA_U7hhzFpO': ('EXT', 'Dr. Kidakorn Kiranantawat (Thailand), 2024',
        'A nostril scarred nearly shut after cosmetic surgery. The scar was released, then a skin-and-cartilage graft from the ear was placed on the raw edge of the opened nostril. Shown 1 year and 10 months later.',
        None),
    'C7AHUWHr0EC': ('INT', 'Dr. Ahmet Halit Aydın, May 2024',
        'A complicated ethnic revision with rib cartilage and a composite ear graft, then a touch-up on the nostrils. Shown about 2 years later. One of few public examples on darker skin.',
        None),
    'nazari1': ('INT', 'Dr. Shahriar Nazari (Iran)',
        'Two cases from his Instagram stories, tagged "alar expansion". His captions read "nasal reconstruction and enlarging the nasal ala".',
        [('View on Instagram', 'https://www.instagram.com/p/DdedpjFNy-d/'), ('Second case', 'zoom:nazari2')]),
    'C4aw7VvLpcT': ('EXT', 'Dr. Jason Roostaeian (US)',
        '"Correcting the over-resected alar base." These appear to have healed well, with visibly bigger nostrils.',
        None),
    'DdjfmFaiHD1': ('EXT', 'Dr. Amir Sazgar (Tehran), September 2026',
        'One month after rebuilding a nose with six failed surgeries and past skin death. Too early to judge the scars.',
        None),
    'DUmywnTE25f': (None, 'Dr. Shingyochi (Japan), February 2026',
        'An over-cut alarplasty from another clinic, repaired by rebuilding the nostril sill and revising the scars. His 2025 case used local flaps; he says he uses skin-and-cartilage grafts only when a flap can\'t be used.',
        [('View on Instagram', 'https://www.instagram.com/p/DUmywnTE25f/'), ('A 2025 case', 'https://www.instagram.com/p/DKQwfgBzBS9/')]),
    'Dc-6ZC0DtEn': (None, 'Dr. Sercan Göde, September 2026',
        '"Alar base reversing by local island flaps." Taken on the operating table, so expect it to settle.',
        None),
    'DdyuYXvOeFV': (None, 'Dr. Sercan Göde',
        '"Alar base reduction reversal." A lip island flap case, before and after.',
        None),
    'DWZJXExjdWT': (None, 'Dr. Sercan Göde, March 2026',
        'A complicated revision with flaps. The video has close-ups of the scars.',
        None),
    'DXOl6j1jTTu': (None, 'Dr. Sercan Göde, April 2026',
        'Five months after a complex revision.',
        None),
    'DTrpzjbCB2S': (None, 'Dr. Sercan Göde, January 2026',
        'Tip and columella skin death, two months after reconstruction. Shared to show how his flaps work.',
        None),
    'Cwo231ssL6S': (None, 'Dr. Sercan Göde, August 2023',
        '"Nostril show reduced, short columella lengthened, retractions improved." A closed revision with the patient\'s own rib cartilage, at 1 month.',
        None),
    'DHOkgaOie6A': (None, 'Dr. Sercan Göde, March 2025',
        'An alar retraction repair.',
        None),
    'DaDwPhCDK2-': (None, 'Dr. Oguzhan Oguz, June 2026',
        '"When tissue is lost, reconstruction becomes the only option."',
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
    ('1a. Internal composite grafts', ['CfKFXSSM_ij', 'nazari1', 'C7AHUWHr0EC']),
    ('1b. External composite grafts', ['C4aw7VvLpcT', 'DdjfmFaiHD1', 'DA_U7hhzFpO']),
    ('2b. Lip and cheek island flaps', ['DdyuYXvOeFV', 'Dc-6ZC0DtEn', 'DWZJXExjdWT', 'DXOl6j1jTTu', 'DTrpzjbCB2S', 'DHOkgaOie6A', 'DaDwPhCDK2-', 'DWkekGciEX0']),
    ('2. Other flap repairs', ['DUmywnTE25f']),
    ('3. Support and lining fixes', ['DcIw_t7jiQn', 'DVfzFTJk8OF']),
    ('4. Derotation', ['CtxKAyvsVrC', 'DNlENwgRSK6', 'CvzpOS9LfUA', 'Cwo231ssL6S']),
    ('Other', ['DRKpan3DK2B']),
]

BADGES: Dict[str, Tuple[str, str]] = {"INT": ("int", "Internal"), "EXT": ("ext", "External")}
A = ' target="_blank" rel="noopener"'


def post_url(key: str) -> str:
    """Return the Instagram post URL for a shortcode."""
    return f"https://www.instagram.com/p/{key}/"


def link_html(label: str, url: str, img_dir: Path = IMG) -> str:
    """Render one card link. A "zoom:KEY" url opens src/img/KEY.webp full screen (see the lightbox script)."""
    if url.startswith("zoom:"):
        data = (img_dir / f"{url[5:]}.webp").read_bytes()
        src = "data:image/webp;base64," + base64.b64encode(data).decode("ascii")
        return f'<a href="#" class="zoomlink" data-zoom="{src}">{html.escape(label)}</a>'
    return f'<a href="{url}"{A}>{html.escape(label)}</a>'


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


def figure_img_attrs(key: str, img_dir: Path = IMG) -> str:
    """Attributes for a paper figure: like img_attrs, but never shown wider than its real size, so diagrams aren't stretched."""
    w, _ = webp_size((img_dir / f"{key}.webp").read_bytes())
    return f'{img_attrs(key, img_dir)} style="max-width:min(100%,{w}px)"'


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
    lk = " · ".join(link_html(t, u, img_dir) for t, u in links)
    return (f'<figure class="ex">{ph}<figcaption>{b}<p class="by">{e_by}</p>'
            f'<p class="why">{e_why}</p><p class="lk">{lk}</p></figcaption></figure>')


def render_library(cards: Dict[str, Card], groups: List[Tuple[str, List[str]]], img_dir: Path = IMG) -> str:
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
            # Zoom links open local images; the sources list only lists places on the web.
            more = [(t, u) for t, u in links[1:] if not u.startswith("zoom:")]
            if more:
                extra = ' <span class="small">(' + ", ".join(
                    link_html(t, u, img_dir) for t, u in more) + ")</span>"
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
    out = re.sub(r'src="IMG:([\w-]+)"', lambda m: figure_img_attrs(m.group(1), img_dir), out)
    out = out.replace("LIBCOUNT", str(library_count(cards, groups)))
    out = out.replace("LIBRARY", render_library(cards, groups, img_dir))
    return out


def main() -> None:
    """Build index.html at the repo root."""
    template = (SRC / "index.src.html").read_text(encoding="utf-8")
    out = build(template, C, NOPHOTO, GROUPS)
    (ROOT / "index.html").write_text(out, encoding="utf-8")
    print(f"index.html: {len(out.encode('utf-8')) / 1e6:.2f} MB")


if __name__ == "__main__":
    main()
