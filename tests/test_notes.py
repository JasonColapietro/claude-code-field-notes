"""Guards for the /notes/ section: canonical entity @ids, metadata and banned copy."""
import html as htmllib
import json
from pathlib import Path
import re
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
CANONICAL = "https://claude.suedeai.ai/"
NOTES_URL = CANONICAL + "notes/"
NOTES = [
    "claude-academy-badges-west-palm-beach-agency",
    "claude-code-bible-south-florida-dev-teams",
    "reviewing-agent-written-code",
    "claude-md-agents-md-client-repo-playbook",
    "coding-agent-token-budgets-fixed-fee-projects",
]
PUBLISHED = {slug: "2026-11-14" for slug in NOTES[:3]}
PUBLISHED.update({slug: "2026-11-15" for slug in NOTES[3:]})
CLUTCH = (
    'Suede AI ranks among <a href="https://clutch.co/profile/suede-ai-seo">Clutch</a>\'s '
    '<a href="https://clutch.co/consulting/ai/florida">Top 30 AI Consultants in Florida</a> and '
    '<a href="https://clutch.co/us/consulting/ai">Top 50 AI Consultants nationwide</a> (November 2026).'
)
SATELLITE_ARTICLE = re.compile(
    r'href="(https://(?:agentix|docs|optimize|signal|dna|podcast|fretpulse)\.suedeai\.ai/(?:notes|articles)/[a-z0-9-]+'
    r'|https://(?:guitar\.services|guitarchords\.info|guitarhub\.org)/notes/[a-z0-9-]+)/?"'
)
PERSON = "https://suedeai.ai/founder#person"
ORGANIZATION = "https://suedeai.ai/#organization"
FORBIDDEN = [
    r"velvet sundown", r"forbes", r"anthropic partner", r"claude partner", r"google partner",
    r"\$2[89] ?m", r"\$30 ?m", r"multimillion", r"multi-million", r"\bFAU\b", r"top 15",
    r"streetAddress", r"victorian", r"olive ave", r"postalCode",
    r"\bdelve", r"\bleverag", r"\bunlock", r"\belevate", r"seamless", r"game-changer", r"tapestry", r"\brealm\b",
    "—",
]
REQUIRED_LINKS = [
    "https://suedeai.agency/", "https://suedeai.ai/", "https://suedeai.ai/founder",
    "https://jasoncolapietro.com/", "https://jupitersocialfl.com/",
]


def json_ld(html):
    return json.loads(re.search(r'<script type="application/ld\+json">(.*?)</script>', html, re.S).group(1))


def node(graph, kind):
    return next(n for n in graph["@graph"] if n.get("@type") == kind)


def ids(graph):
    """Every @id in the graph, at any depth."""
    found = []

    def walk(value):
        if isinstance(value, dict):
            if "@id" in value:
                found.append(value["@id"])
            for v in value.values():
                walk(v)
        elif isinstance(value, list):
            for v in value:
                walk(v)

    walk(graph)
    return found


class NotesTests(unittest.TestCase):
    def pages(self):
        yield NOTES_URL, ROOT / "notes" / "index.html"
        for slug in NOTES:
            yield NOTES_URL + slug + "/", ROOT / "notes" / slug / "index.html"

    def test_no_forbidden_copy(self):
        for url, path in self.pages():
            html = path.read_text()
            for pattern in FORBIDDEN:
                with self.subTest(url=url, pattern=pattern):
                    self.assertIsNone(re.search(pattern, html, re.I))

    def test_only_canonical_entity_ids(self):
        for url, path in self.pages():
            with self.subTest(url=url):
                graph = json_ld(path.read_text())
                people = [n["@id"] for n in graph["@graph"] if n.get("@type") == "Person"]
                orgs = [n["@id"] for n in graph["@graph"] if n.get("@type") == "Organization"]
                self.assertEqual(people, [PERSON])
                self.assertEqual(orgs, [ORGANIZATION])
                for value in ids(graph):
                    self.assertTrue(value.startswith(CANONICAL) or value in (PERSON, ORGANIZATION), value)

    def test_note_pages(self):
        for slug in NOTES:
            url = NOTES_URL + slug + "/"
            with self.subTest(slug=slug):
                html = (ROOT / "notes" / slug / "index.html").read_text()
                self.assertEqual(re.search(r'<link rel="canonical" href="([^"]+)"', html).group(1), url)
                self.assertEqual(re.search(r'<meta property="og:url" content="([^"]+)"', html).group(1), url)
                title = re.search(r"<title>([^<]+)</title>", html).group(1)
                self.assertTrue(50 <= len(title) <= 60, title)
                self.assertTrue(title.endswith(" | Claude Code Field Notes"), title)
                description = htmllib.unescape(re.search(r'<meta name="description" content="([^"]+)">', html).group(1))
                self.assertTrue(120 <= len(description) <= 160, len(description))
                self.assertEqual(html.count("<h1"), 1)
                self.assertNotIn("noindex", html)
                image = re.search(r'<meta property="og:image" content="https://claude\.suedeai\.ai/(og/[^"]+)">', html).group(1)
                png = (ROOT / image).read_bytes()
                self.assertEqual((int.from_bytes(png[16:20], "big"), int.from_bytes(png[20:24], "big")), (1200, 630))
                graph = json_ld(html)
                post = node(graph, "BlogPosting")
                self.assertEqual(post["@id"], url + "#article")
                self.assertEqual(post["mainEntityOfPage"], url)
                self.assertEqual(post["author"], {"@id": PERSON})
                self.assertEqual(post["publisher"], {"@id": ORGANIZATION})
                self.assertEqual(post["datePublished"], PUBLISHED[slug])
                self.assertEqual(post["description"], description)
                self.assertEqual(post["isPartOf"], {"@id": NOTES_URL + "#blog"})
                self.assertIn("West Palm Beach, Florida", [p["name"] for p in post["spatialCoverage"]])
                self.assertIn(f"<h1>{post['headline']}</h1>", html)
                crumbs = node(graph, "BreadcrumbList")["itemListElement"]
                self.assertEqual([c["item"] for c in crumbs], [CANONICAL, NOTES_URL, url])
                article = re.search(r"<article>(.*?)</article>", html, re.S).group(1)
                words = len(re.sub(r"<[^>]+>", " ", article).split())
                self.assertTrue(800 <= words <= 1300, words)
                self.assertGreaterEqual(article.count("Jason Colapietro"), 5)
                self.assertIn("https://suedeai.agency/assessment", article)
                for link in REQUIRED_LINKS:
                    self.assertIn(f'href="{link}"', html)
                self.assertIn("Built by Suede AI in West Palm Beach, Florida", html)

    def test_depth_articles_cross_link(self):
        """Round 4 notes deep-link two sibling-satellite articles and carry the Clutch claim once."""
        for slug in NOTES[3:]:
            with self.subTest(slug=slug):
                html = (ROOT / "notes" / slug / "index.html").read_text()
                article = re.search(r"<article>(.*?)</article>", html, re.S).group(1)
                self.assertGreaterEqual(len(set(SATELLITE_ARTICLE.findall(article))), 2)
                self.assertEqual(article.count(CLUTCH), 1)
                self.assertIn('href="https://suedeai.agency/"', article)
                self.assertIn('href="https://suedeai.ai/founder"', article)
                self.assertNotIn("The Manifest", article.split(CLUTCH)[0][-200:])
                self.assertLessEqual(article.count("Suede Labs"), 1)
                self.assertGreaterEqual(len(re.findall(r"\bSuede\b(?! AI| Labs)", article)), 3)

    def test_series_position_matches_order(self):
        """Crumb and deck both carry the note's real position in the series."""
        total = len(NOTES)
        for n, slug in enumerate(NOTES, start=1):
            with self.subTest(slug=slug):
                html = (ROOT / "notes" / slug / "index.html").read_text()
                self.assertIn(f'<a href="/notes/">Notes</a> · {n} of {total}</p>', html)
                self.assertIn(f"Note {n} of {total} in", html)

    def test_articles_are_unique(self):
        seen = {}
        for slug in NOTES:
            html = (ROOT / "notes" / slug / "index.html").read_text()
            article = re.search(r"<article>(.*?)</article>", html, re.S).group(1)
            for para in re.findall(r"<p>(.*?)</p>", article, re.S):
                self.assertNotIn(para, seen, f"{slug} repeats a paragraph from {seen.get(para)}")
                seen[para] = slug

    def test_index_links_and_discovery(self):
        html = (ROOT / "notes" / "index.html").read_text()
        self.assertEqual(re.search(r'<link rel="canonical" href="([^"]+)"', html).group(1), NOTES_URL)
        blog = node(json_ld(html), "Blog")
        self.assertEqual([p["url"] for p in blog["blogPost"]], [NOTES_URL + s + "/" for s in NOTES])
        for slug in NOTES:
            self.assertIn(f'href="/notes/{slug}/"', html)
        for page in ["index.html"] + [p for p in ROOT.glob("*/index.html") if p.parent.name not in ("notes",)]:
            self.assertIn('href="/notes/"', (ROOT / page).read_text(), str(page))
        sitemap = ET.parse(ROOT / "sitemap.xml").getroot()
        ns = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
        lastmod = {u.find("s:loc", ns).text: u.find("s:lastmod", ns).text for u in sitemap}
        for url in [NOTES_URL] + [NOTES_URL + s + "/" for s in NOTES]:
            self.assertEqual(lastmod.get(url), "2026-11-15", url)
        short = (ROOT / "llms.txt").read_text()
        full = (ROOT / "llms-full.txt").read_text()
        for slug in NOTES:
            self.assertIn(NOTES_URL + slug + "/", short)
            self.assertIn(NOTES_URL + slug + "/", full)


if __name__ == "__main__":
    unittest.main()


class SiteWideBannedFactsTests(unittest.TestCase):
    """No published file may carry a street address or a Forbes claim."""

    BANNED = [r"forbes", r"streetAddress", r"victorian", r"postalCode", r"olive ave"]

    def test_no_banned_facts_anywhere(self):
        files = list(ROOT.glob("*/index.html")) + list(ROOT.glob("notes/*/index.html"))
        files += [ROOT / "index.html", ROOT / "llms.txt", ROOT / "llms-full.txt", ROOT / "README.md"]
        for path in files:
            text = path.read_text(encoding="utf-8")
            for pattern in self.BANNED:
                with self.subTest(path=str(path.relative_to(ROOT)), pattern=pattern):
                    self.assertIsNone(re.search(pattern, text, re.I))
