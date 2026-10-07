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


class DiscoveryTests(unittest.TestCase):
    def test_source_discovery(self):
        robots = (ROOT / "robots.txt").read_text()
        self.assertEqual(robots, "User-agent: *\nAllow: /\n\nSitemap: " + CANONICAL + "sitemap.xml\n")
        sitemap = ET.parse(ROOT / "sitemap.xml").getroot()
        ns = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
        self.assertEqual(sitemap.tag, "{" + ns["s"] + "}urlset")
        self.assertEqual([node.text for node in sitemap.findall("s:url/s:loc", ns)], [CANONICAL])
        self.assertEqual(len(sitemap), 1)
        self.assertEqual(len(sitemap[0]), 1)
        html = (ROOT / "index.html").read_text()
        canonical = re.search(r'<link rel="canonical" href="([^"]+)"', html).group(1)
        self.assertEqual(canonical.rstrip("/") + "/", CANONICAL)
        self.assertIn("<title>Claude Code Field Notes: Running AI Coding Agents in Production | Jason Colapietro</title>", html)
        graph = json.loads(re.search(r'<script type="application/ld\+json">(.*?)</script>', html, re.S).group(1))
        ids = {node.get("@id") for node in graph["@graph"]}
        self.assertIn("https://suedeai.ai/founder#person", ids)
        self.assertIn("https://suedeai.ai/#organization", ids)

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
            finally:
                server.shutdown()
                thread.join()


if __name__ == "__main__":
    unittest.main()
