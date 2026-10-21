#!/usr/bin/env python3
"""Check the skill's references against live sources (stdlib only).

1. Every http(s) URL in the skill and README resolves (redirects to a different page are flagged).
2. Every HyperTrack API endpoint mentioned exists in the public OpenAPI spec, with the stated method.

Usage: python3 tools/check_refs.py [--no-urls]
"""

import argparse
import re
import sys
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SPEC_URL = "https://hypertrack.com/reference/openapi.yaml"
DOCS = sorted([*ROOT.glob("skills/**/*.md"), ROOT / "README.md"])
URL_RE = re.compile(r"https?://[^\s)\]>\"'`|*]+")
# Hosts that need auth, tokens, or are bases rather than pages.
SKIP_URL = re.compile(
    r"v3\.api\.hypertrack\.com|embed\.hypertrack\.com|trck\.at|127\.0\.0\.1|localhost|"
    r"api\.github\.com/repos/hypertrack/<|m2\.hypertrack\.com/$|<|\{|…"
)
API_PREFIX = r"/(?:orders|workers|places|nearby|oauth|geotags|visits|tracking)\b"
METHOD_PATH_RE = re.compile(r"\b(GET|POST|PATCH|PUT|DELETE)\s+`?(" + API_PREFIX + r"[^\s`|)]*)")
API_URL_RE = re.compile(r"v3\.api\.hypertrack\.com(" + API_PREFIX + r"[^\s'\"`)\\]*)")
BARE_PATH_RE = re.compile(r"`(" + API_PREFIX + r"[^`\s]*)`")


def fetch(url, limit=None):
    request = urllib.request.Request(url, headers={"User-Agent": "hypertrack-skills-check/1.0"})
    with urllib.request.urlopen(request, timeout=20) as response:
        return response.status, response.geturl(), response.read(limit)


def spec_operations():
    _, _, raw = fetch(SPEC_URL)
    text = raw.decode()
    paths_block = text[text.index("\npaths:") : text.index("\ncomponents:")]
    operations, current = {}, None
    for line in paths_block.splitlines():
        match = re.match(r"^ {2,3}(/\S*):\s*$", line)
        if match:
            current = match.group(1)
            operations[current] = set()
            continue
        match = re.match(r"^ {4,5}(get|post|patch|put|delete):\s*$", line)
        if match and current:
            operations[current].add(match.group(1).upper())
    return operations


def template_regex(path):
    parts = [("[^/]+" if re.fullmatch(r"\{[^}]+\}", p) else re.escape(p)) for p in path.rstrip("/").split("/")]
    return re.compile("^" + "/".join(parts) + "/?$")


def normalize(path):
    path = path.split("?")[0].rstrip(".,;:")
    path = re.sub(r"\{[^}]*\}|<[^>]*>|…", "x", path)
    return path


def check_urls(urls):
    failures, warnings = [], []

    def probe(url):
        try:
            status, final, _ = fetch(url, limit=2048)
            return url, status, final, None
        except urllib.error.HTTPError as error:
            return url, error.code, url, None
        except Exception as error:  # noqa: BLE001
            return url, None, url, str(error)

    with ThreadPoolExecutor(max_workers=8) as pool:
        for url, status, final, error in pool.map(probe, sorted(urls)):
            if error or status is None or status >= 400:
                failures.append(f"URL {url} -> {status or error}")
            elif final.rstrip("/") != url.rstrip("/") and urlpath(final) in ("", "/docs") and urlpath(url) not in ("", "/docs"):
                warnings.append(f"URL {url} redirects to {final} (moved or removed?)")
    return failures, warnings


def urlpath(url):
    return re.sub(r"^https?://[^/]+", "", url).split("?")[0].rstrip("/")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-urls", action="store_true", help="skip URL reachability checks")
    args = parser.parse_args()

    urls, endpoints = set(), set()
    for doc in DOCS:
        text = doc.read_text()
        for url in URL_RE.findall(text):
            url = url.rstrip(".,;:")
            if not SKIP_URL.search(url):
                urls.add(url)
        for method, path in METHOD_PATH_RE.findall(text):
            endpoints.add((method, normalize(path), doc.relative_to(ROOT)))
        for path in API_URL_RE.findall(text) + BARE_PATH_RE.findall(text):
            endpoints.add((None, normalize(path), doc.relative_to(ROOT)))

    failures, warnings = [], []
    operations = spec_operations()
    compiled = [(template_regex(p), p, methods) for p, methods in operations.items()]
    for method, path, doc in sorted(endpoints, key=lambda e: (str(e[2]), e[1], e[0] or "")):
        matches = [(p, m) for regex, p, m in compiled if regex.match(path.rstrip("/") or "/")]
        if not matches:
            failures.append(f"API {method or ''} {path} not in OpenAPI spec ({doc})".replace("  ", " "))
        elif method and not any(method in m for _, m in matches):
            failures.append(f"API {method} {path}: method not in spec, spec has {sorted(set().union(*[m for _, m in matches]))} ({doc})")
    print(f"checked {len(endpoints)} API endpoint mentions against {len(operations)} spec paths")

    if not args.no_urls:
        url_failures, url_warnings = check_urls(urls)
        failures += url_failures
        warnings += url_warnings
        print(f"checked {len(urls)} URLs")

    for warning in warnings:
        print(f"WARN {warning}")
    for failure in failures:
        print(f"FAIL {failure}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
