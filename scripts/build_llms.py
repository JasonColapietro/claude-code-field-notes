"""Build llms.txt and llms-full.txt from the served HTML pages.

Usage: python3 scripts/build_llms.py [--check]

The text comes from the pages themselves (title, description, Article
headline and the article body), so the machine-readable copies cannot drift
from what a reader sees. --check exits non-zero when either file is stale.
"""
import html
import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = "https://claude.suedeai.ai/"
LESSONS = [
    "clean-build-is-not-proof",
    "empty-environment-variables",
    "money-path-defaults-fail-closed",
    "deploy-conventions-are-attack-surface",
    "registry-vs-process-table",
    "when-documentation-is-silent-measure",
]


class Body(HTMLParser):
    """Collects block text from one element subtree as Markdown-ish lines."""

    BLOCKS = {"p", "li", "h1", "h2", "h3", "pre", "div"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.out, self.buf, self.stack, self.hrefs = [], [], [], []

    def flush(self):
        text = "".join(self.buf)
        self.buf = []
        if "pre" in self.stack:
            if text.strip("\n"):
                self.out.append("```\n" + text.strip("\n") + "\n```")
            return
        text = re.sub(r"\s+", " ", text).strip()
        if text:
            self.out.append(text)

    def handle_starttag(self, tag, attrs):
        if tag in self.BLOCKS:
            self.flush()
        if tag in ("strong", "b"):
            self.buf.append("**")
        elif tag == "li":
            self.buf.append("- ")
        elif tag == "h2":
            self.buf.append("### ")
        elif tag == "a":
            href = dict(attrs).get("href", "")
            if href.startswith("/"):
                href = BASE + href.lstrip("/")
            self.hrefs.append(href if href.startswith("http") and "pre" not in self.stack else "")
            if self.hrefs[-1]:
                self.buf.append("[")
        self.stack.append(tag)

    def handle_endtag(self, tag):
        if tag in ("strong", "b"):
            self.buf.append("**")
        elif tag == "a" and self.hrefs:
            href = self.hrefs.pop()
            if href:
                self.buf.append("](" + href + ")")
        if tag in self.BLOCKS:
            self.flush()
        if self.stack and self.stack[-1] == tag:
            self.stack.pop()

    def handle_data(self, data):
        self.buf.append(data)


def section(html_text, start, end):
    i = html_text.index(start)
    j = html_text.index(end, i)
    return html_text[i:j]


def to_text(fragment):
    parser = Body()
    parser.feed(fragment)
    parser.flush()
    return "\n\n".join(parser.out)


def meta(html_text, name):
    m = re.search(r'<meta name="%s" content="([^"]+)">' % name, html_text)
    return html.unescape(m.group(1)) if m else ""


def article_node(html_text):
    graph = json.loads(re.search(r'<script type="application/ld\+json">(.*?)</script>', html_text, re.S).group(1))
    return next(n for n in graph["@graph"] if n["@type"] == "Article")


def build():
    home = (ROOT / "index.html").read_text()
    home_desc = meta(home, "description")
    lessons = []
    for n, slug in enumerate(LESSONS, 1):
        page = (ROOT / slug / "index.html").read_text()
        node = article_node(page)
        body = section(page, "<article>", "</article>")
        body = re.sub(r"<h1>.*?</h1>", "", body, flags=re.S)
        body = re.sub(r'<p class="(byline|deck)">.*?</p>', "", body, flags=re.S)
        lessons.append((n, slug, node["headline"], meta(page, "description"), to_text(body)))
    pattern = to_text(section(home, "<h2>The pattern underneath</h2>", "<footer>"))
    about = to_text(section(home, "<footer>", "</footer>"))

    short = [
        "# Claude Code Field Notes",
        "",
        "> " + home_desc,
        "",
        "Written by Jason Colapietro (also known as Johnny Suede), founder and CEO of Suede AI. "
        "Suede AI runs AEO, GEO and SEO for businesses and builds AI agents in Suede AI Agent Studio.",
        "",
        "## Lessons",
        "",
    ]
    short += [f"- [{h}]({BASE}{s}/): {d}" for _, s, h, d, _ in lessons]
    short += [
        "",
        "## Full text",
        "",
        f"- [llms-full.txt]({BASE}llms-full.txt): the overview and all six lessons as plain Markdown",
        "",
        "## About the author",
        "",
        "- [Jason Colapietro, founder page](https://suedeai.ai/founder)",
        "- [Suede AI](https://suedeai.ai/): company home",
        "- [Suede AI SEO](https://seo.suedeai.ai/): SEO, GEO, AEO and AI search visibility",
        "- [Suede AI Agent Studio](https://agents.suedeai.ai/): build AI agents and workflow automation",
        "- [Open-source Claude Code skill pack](https://github.com/JasonColapietro/suede-creator-skills)",
        "",
    ]

    full = [
        "# Claude Code Field Notes: Running AI Coding Agents in Production",
        "",
        "> " + home_desc,
        "",
        f"Source: {BASE}",
        "Author: Jason Colapietro (Johnny Suede), founder and CEO of Suede AI (https://suedeai.ai/founder)",
        "Published: 2026-07-27",
        "",
        "Abridged from The Complete Claude Code Compendium. Each lesson below is the full text of its page.",
        "",
    ]
    for n, slug, headline, desc, text in lessons:
        full += [f"## Lesson {n}: {headline}", "", f"Source: {BASE}{slug}/", "", "> " + desc, "", text, ""]
    full += ["## The pattern underneath", "", re.sub(r"^### The pattern underneath\n\n", "", pattern), ""]
    full += ["## About the author", "", about, ""]
    return "\n".join(short), "\n".join(full)


def main():
    short, full = build()
    targets = {ROOT / "llms.txt": short, ROOT / "llms-full.txt": full}
    if "--check" in sys.argv:
        stale = [p.name for p, text in targets.items() if not p.exists() or p.read_text() != text]
        if stale:
            sys.exit("stale: " + ", ".join(stale) + " (run python3 scripts/build_llms.py)")
        return
    for path, text in targets.items():
        path.write_text(text)


if __name__ == "__main__":
    main()
