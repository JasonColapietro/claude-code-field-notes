"""Render the 1200x630 Open Graph cards for the lesson pages.

Usage: python3 scripts/make_og.py SERIF_FONT SANS_FONT

The cards use the site's light palette from the inline stylesheet (--bg
#faf8f5, --fg #16130f, --mut #6b625a, --rule #e2dbd2, --accent #8a5a2b).
SERIF_FONT is a Georgia-metric serif (Gelasio, OFL, from google/fonts) and
SANS_FONT a system-style sans (Inter). Output: og/<slug>.png for each lesson
and og/home.png for the overview page.
"""
import json
import re
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
W, H = 1200, 630
BG, FG, MUT, RULE, ACCENT = "#faf8f5", "#16130f", "#6b625a", "#e2dbd2", "#8a5a2b"
LESSONS = [
    "clean-build-is-not-proof",
    "empty-environment-variables",
    "money-path-defaults-fail-closed",
    "deploy-conventions-are-attack-surface",
    "registry-vs-process-table",
    "when-documentation-is-silent-measure",
]


def wrap(draw, text, font, width):
    lines, line = [], ""
    for word in text.split():
        test = (line + " " + word).strip()
        if draw.textlength(test, font=font) <= width:
            line = test
        else:
            lines.append(line)
            line = word
    lines.append(line)
    return lines


def card(headline, kicker, out, serif, sans):
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    pad = 88
    d.rectangle([0, 0, W, 10], fill=ACCENT)
    k = ImageFont.truetype(sans, 24)
    d.text((pad, 78), kicker.upper(), font=k, fill=ACCENT, spacing=4)
    size = 76
    while True:
        f = ImageFont.truetype(serif, size)
        lines = wrap(d, headline, f, W - 2 * pad)
        if len(lines) <= 3 or size <= 52:
            break
        size -= 4
    y = 150
    for line in lines:
        d.text((pad, y), line, font=f, fill=FG)
        y += int(size * 1.18)
    d.line([pad, H - 128, W - pad, H - 128], fill=RULE, width=2)
    b = ImageFont.truetype(sans, 26)
    d.text((pad, H - 100), "Jason Colapietro", font=b, fill=FG)
    s = ImageFont.truetype(sans, 26)
    host = "claude.suedeai.ai"
    d.text((W - pad - d.textlength(host, font=s), H - 100), host, font=s, fill=MUT)
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out, optimize=True)


def main():
    serif, sans = sys.argv[1], sys.argv[2]
    for n, slug in enumerate(LESSONS, 1):
        html = (ROOT / slug / "index.html").read_text()
        graph = json.loads(re.search(r'<script type="application/ld\+json">(.*?)</script>', html, re.S).group(1))
        headline = next(x for x in graph["@graph"] if x["@type"] == "Article")["headline"]
        card(headline, f"Claude Code Field Notes · Lesson {n} of 6", ROOT / "og" / f"{slug}.png", serif, sans)
    card("Running AI coding agents in production: six lessons", "Claude Code Field Notes",
         ROOT / "og" / "home.png", serif, sans)


if __name__ == "__main__":
    main()
