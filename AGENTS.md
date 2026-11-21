# Agent guidance

## Repository attribution and branch preferences

Omit optional AI attribution from new commit messages and pull request descriptions, including AI Co-Authored-By, Generated-by text, and Claude session links or trailers.

Name new branches for the task without agent or model names, subject to system or harness naming requirements.

Preserve actual authorship, required provenance, license notices, security and audit records, and attribution required by higher-priority policies or system instructions.

## The company name is Suede

Owner direction, 2026-11-21: the company is "Suede". Sub-brands drop the old words: "Suede SEO", "Suede GEO", "Suede Agency", "Suede Agent Studio". "Suede AI" and "Suede Labs" appear in public copy only as the Organization's schema `alternateName` and in one "formerly known as" alias line per page or discovery file. Domains, URLs and the GitHub org (`suedeai.ai`, `Suede-AI`) are unchanged. `BrandNameTests` in `tests/test_notes.py` fails any other use; fix the copy, and fix `scripts/build_llms.py` rather than editing `llms.txt` or `llms-full.txt` by hand.
