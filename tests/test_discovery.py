"""Dependency-free crawler discovery checks; run with unittest discovery."""
import functools
import http.server
import json
from pathlib import Path
import re
import subprocess
import threading
import unittest
import urllib.request
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
CANONICAL = "https://claude.suedeai.ai/"
LESSONS = [
    "clean-build-is-not-proof",
    "empty-environment-variables",
    "money-path-defaults-fail-closed",
    "deploy-conventions-are-attack-surface",
    "registry-vs-process-table",
    "when-documentation-is-silent-measure",
]
LESSON_URLS = [CANONICAL + slug + "/" for slug in LESSONS]
PERSON = "https://suedeai.ai/founder#person"
ORGANIZATION = "https://suedeai.ai/#organization"


def json_ld(html):
    return json.loads(re.search(r'<script type="application/ld\+json">(.*?)</script>', html, re.S).group(1))


def nodes_of_type(graph, kind):
    return [node for node in graph["@graph"] if node.get("@type") == kind]


class DiscoveryTests(unittest.TestCase):
    def test_source_discovery(self):
        robots = (ROOT / "robots.txt").read_text()
        self.assertEqual(robots, "User-agent: *\nAllow: /\n\nSitemap: " + CANONICAL + "sitemap.xml\n")
        sitemap = ET.parse(ROOT / "sitemap.xml").getroot()
        ns = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
        self.assertEqual(sitemap.tag, "{" + ns["s"] + "}urlset")
        self.assertEqual([node.text for node in sitemap.findall("s:url/s:loc", ns)], [CANONICAL] + LESSON_URLS)
        self.assertEqual(len(sitemap), 1 + len(LESSONS))
        for url in sitemap:
            self.assertEqual(len(url), 1)
        html = (ROOT / "index.html").read_text()
        canonical = re.search(r'<link rel="canonical" href="([^"]+)"', html).group(1)
        self.assertEqual(canonical.rstrip("/") + "/", CANONICAL)
        self.assertIn("<title>Claude Code Field Notes: Running AI Coding Agents in Production | Jason Colapietro</title>", html)
        graph = json_ld(html)
        ids = {node.get("@id") for node in graph["@graph"]}
        self.assertIn(PERSON, ids)
        self.assertIn(ORGANIZATION, ids)
        overview = nodes_of_type(graph, "Article")[0]
        self.assertEqual(overview["@id"], CANONICAL + "#article")
        self.assertEqual([part["url"] for part in overview["hasPart"]], LESSON_URLS)
        for slug in LESSONS:
            self.assertIn(f'href="/{slug}/"', html)

    def test_lesson_pages(self):
        titles = set()
        for position, (slug, url) in enumerate(zip(LESSONS, LESSON_URLS)):
            with self.subTest(slug=slug):
                html = (ROOT / slug / "index.html").read_text()
                self.assertEqual(re.search(r'<link rel="canonical" href="([^"]+)"', html).group(1), url)
                self.assertEqual(re.search(r'<meta property="og:url" content="([^"]+)"', html).group(1), url)
                title = re.search(r"<title>([^<]+)</title>", html).group(1)
                self.assertTrue(title.endswith(" | Claude Code Field Notes"), title)
                titles.add(title)
                description = re.search(r'<meta name="description" content="([^"]+)">', html).group(1)
                self.assertLessEqual(len(description), 160)
                self.assertNotIn("noindex", html)
                graph = json_ld(html)
                ids = {node.get("@id") for node in graph["@graph"]}
                self.assertIn(PERSON, ids)
                self.assertIn(ORGANIZATION, ids)
                article = nodes_of_type(graph, "Article")[0]
                self.assertEqual(article["@id"], url + "#article")
                self.assertEqual(article["mainEntityOfPage"], url)
                self.assertEqual(article["description"], description)
                self.assertEqual(article["author"], {"@id": PERSON})
                self.assertEqual(article["publisher"], {"@id": ORGANIZATION})
                self.assertEqual(article["isPartOf"], {"@id": CANONICAL + "#article"})
                self.assertIn(f"<h1>{article['headline']}</h1>", html)
                crumbs = nodes_of_type(graph, "BreadcrumbList")[0]["itemListElement"]
                self.assertEqual([crumb["item"] for crumb in crumbs], [CANONICAL, url])
                self.assertIn('href="/"', html)
                if position > 0:
                    self.assertIn(f'rel="prev" href="/{LESSONS[position - 1]}/"', html)
                if position < len(LESSONS) - 1:
                    self.assertIn(f'rel="next" href="/{LESSONS[position + 1]}/"', html)
                related = re.search(r'<section class="related".*?</section>', html, re.S).group(0)
                self.assertRegex(related, r'href="https://(skills|agents|seo)\.suedeai\.ai/')
        self.assertEqual(len(titles), len(LESSONS))

    def test_vercel_headers_and_preview_cancellation(self):
        config = json.loads((ROOT / "vercel.json").read_text())
        headers = {rule["source"]: {h["key"].lower(): h["value"] for h in rule["headers"]} for rule in config["headers"]}
        self.assertEqual(headers["/robots.txt"]["content-type"], "text/plain; charset=utf-8")
        self.assertEqual(headers["/sitemap.xml"]["content-type"], "application/xml; charset=utf-8")
        for environment, expected in [("production", 1), ("preview", 0), ("development", 0), ("", 0)]:
            result = subprocess.run(["sh", "-c", config["ignoreCommand"]], env={"VERCEL_ENV": environment}, check=False)
            self.assertEqual(result.returncode, expected, environment)

    def test_static_http(self):
        handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(ROOT))
        with http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler) as server:
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                for path, types in [("robots.txt", {"text/plain"}), ("sitemap.xml", {"application/xml", "text/xml"})]:
                    with urllib.request.urlopen(f"http://127.0.0.1:{server.server_port}/{path}") as response:
                        self.assertEqual(response.status, 200)
                        self.assertIn(response.headers.get_content_type(), types)
                        self.assertEqual(response.read(), (ROOT / path).read_bytes())
                for path in [""] + [slug + "/" for slug in LESSONS]:
                    with urllib.request.urlopen(f"http://127.0.0.1:{server.server_port}/{path}") as response:
                        self.assertEqual(response.status, 200)
                        self.assertEqual(response.headers.get_content_type(), "text/html")
                        self.assertEqual(response.read(), (ROOT / path / "index.html").read_bytes())
            finally:
                server.shutdown()
                thread.join()


if __name__ == "__main__":
    unittest.main()
