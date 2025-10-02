#!/usr/bin/env python3
"""
OSHA 29 CFR 1910 Scraper (minimal)

Simplified design:
- Browser-like headers & optional UA rotation (per request with --rotate-ua).
- Warm-up (can skip with --no-warmup).
- Always fetch sitemap plus (optionally) index unless --sitemap-only.
- Always performs conditional GET (ETag / Last-Modified) for existing pages to avoid re-downloading unchanged content (304 Not Modified) unless --force is supplied.
- Image assets downloaded locally and src rewritten to relative path.
- Always generates per-regulation Markdown (content.md) and a CSV manifest (manifest.csv) alongside JSON manifest.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import random
import re
import time
from datetime import datetime, timezone
from typing import Any, Dict, Iterator, List, Optional, Set, Tuple
from urllib.parse import urljoin, urlparse
from xml.etree import ElementTree as ET

import requests
from bs4 import BeautifulSoup
from bs4.element import Tag  # type: ignore
from markdownify import markdownify as md_convert


def improve_image_processing(
    soup: BeautifulSoup,
    base_url: str = "https://www.osha.gov",
    images_dir: Optional[str] = None,
    session: Optional[requests.Session] = None,
) -> None:
    """Process images: normalize URLs, download locally, tidy alt text.

    Parameters
    ----------
    soup: BeautifulSoup
        Parsed HTML fragment containing images to normalize.
    base_url: str
        Base URL for resolving relative paths.
    images_dir: Optional[str]
        Destination directory for downloaded images (created if missing).
    session: Optional[requests.Session]
        Existing session (required for downloading images). If None, images are not fetched.
    """
    print(f"[DEBUG] improve_image_processing images_dir={images_dir}")
    for img in soup.find_all("img"):
        src: str = img.get("src", "")  # type: ignore[assignment]
        if src.startswith("/"):
            img["src"] = base_url + src  # type: ignore[index]
            src = img["src"]  # type: ignore[index]
        if images_dir and src and session:
            try:
                import urllib.parse

                parsed_url = urllib.parse.urlparse(src)
                filename = os.path.basename(parsed_url.path) or "image.jpg"
                if "." not in filename:
                    filename += ".jpg"
                os.makedirs(images_dir, exist_ok=True)
                local_path = os.path.join(images_dir, filename)
                if not os.path.exists(local_path):
                    headers = {
                        "Referer": "https://www.osha.gov/laws-regs/regulations/standardnumber/1910"
                    }
                    resp = session.get(src, headers=headers, timeout=30)
                    if resp.status_code == 200:
                        with open(local_path, "wb") as f:
                            f.write(resp.content)
                        print(f"[INFO] Downloaded image: {filename}")
                    else:
                        print(f"[WARN] Image status {resp.status_code}: {src}")
                img["src"] = f"images/{filename}"  # type: ignore[index]
            except Exception as e:  # pragma: no cover
                print(f"[WARN] Image download failed {src}: {e}")
        # Alt text cleanup
        alt: str = img.get("alt", "")  # type: ignore[assignment]
        if len(alt) > 200:
            if "Figure" in alt and ". " in alt:
                img["alt"] = alt.split(". ")[0] + "."  # type: ignore[index]
            else:
                img["alt"] = alt[:200] + "..."  # type: ignore[index]


INDEX_URL = "https://www.osha.gov/laws-regs/regulations/standardnumber/1910"
ROBOTS_URL = "https://www.osha.gov/robots.txt"
SITEMAP_INDEX = "https://www.osha.gov/sites/default/files/sitemap-index.xml"
BASE_DOMAIN = "www.osha.gov"

REG_LINK_PATTERN = re.compile(
    r"/laws-regs/regulations/standardnumber/1910/1910\.\d+[a-zA-Z0-9\-]*$"
)


def extract_regulation_number(url: str) -> Tuple[int, str]:
    """Extract regulation number for numerical sorting.

    Example: '/laws-regs/regulations/standardnumber/1910/1910.1000AppA' -> (1000, 'AppA')
    Returns tuple (main_number, suffix) for proper numerical sorting.
    """
    match = re.search(r"1910\.(\d+)([a-zA-Z]*.*)?$", url)
    if match:
        main_num = int(match.group(1))
        suffix = match.group(2) or ""
        return (main_num, suffix)
    return (999999, url)  # fallback for malformed URLs


DEFAULT_CRAWL_DELAY = 3.0
OUTPUT_DIR = "regulations"
MANIFEST_FILENAME = "manifest.json"

# A pool of mainstream desktop UAs (recent versions). Add or prune as needed.
BROWSER_USER_AGENTS: List[str] = [
    # Chrome (Windows) - Latest
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    # Chrome (macOS) - Latest
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    # Firefox (Windows) - Latest
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:133.0) Gecko/20100101 Firefox/133.0",
    # Firefox (macOS) - Latest
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:133.0) Gecko/20100101 Firefox/133.0",
    # Safari (macOS) - Latest
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.2 Safari/605.1.15",
    # Edge (Windows) - Latest
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0",
]

DEFAULT_USER_AGENT = BROWSER_USER_AGENTS[0]


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ------------------------------------------------------------------
# Robots parsing
# ------------------------------------------------------------------


def fetch_robots_crawl_delay(
    session: requests.Session, user_agent: str = "*"
) -> Optional[float]:
    try:
        r = session.get(ROBOTS_URL, timeout=30)
        if r.status_code != 200:
            return None
        text = r.text
    except requests.RequestException:
        return None
    blocks = re.split(r"\n\s*\n", text)
    ua = user_agent.lower()
    found_delay: Optional[float] = None
    for block in blocks:
        lines = [
            ln.strip()
            for ln in block.splitlines()
            if ln.strip() and not ln.strip().startswith("#")
        ]
        if not lines:
            continue
        agents = [
            ln.split(":", 1)[1].strip().lower()
            for ln in lines
            if ln.lower().startswith("user-agent:")
        ]
        if not agents:
            continue
        if ua in agents or ("*" in agents and ua == "*"):
            for ln in lines:
                if ln.lower().startswith("crawl-delay:"):
                    val = ln.split(":", 1)[1].strip()
                    try:
                        found_delay = float(val)
                    except ValueError:
                        pass
    return found_delay


# ------------------------------------------------------------------
# Sitemaps
# ------------------------------------------------------------------


def iter_sitemap_urls(
    session: requests.Session, sitemap_url: str, timeout: int = 40
) -> Iterator[str]:
    try:
        r = session.get(sitemap_url, timeout=timeout)
        r.raise_for_status()
    except requests.RequestException as e:
        print(f"[WARN] Failed sitemap {sitemap_url}: {e}")
        return iter(())
    try:
        root = ET.fromstring(r.content)
    except ET.ParseError as e:
        print(f"[WARN] Sitemap parse error {sitemap_url}: {e}")
        return iter(())
    ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}

    for sm_el in root.findall("sm:sitemap", ns):
        loc_el = sm_el.find("sm:loc", ns)
        if loc_el is not None and loc_el.text:
            yield from iter_sitemap_urls(session, loc_el.text.strip(), timeout=timeout)

    for url_el in root.findall("sm:url", ns):
        loc_el = url_el.find("sm:loc", ns)
        if loc_el is not None and loc_el.text:
            yield loc_el.text.strip()


def sitemap_regulation_urls(session: requests.Session) -> Set[str]:
    prefix = "https://www.osha.gov/laws-regs/regulations/standardnumber/1910/"
    urls: Set[str] = set()
    for url in iter_sitemap_urls(session, SITEMAP_INDEX):
        if url.startswith(prefix) and REG_LINK_PATTERN.search(urlparse(url).path):
            urls.add(url.split("#")[0])
    return urls


# ------------------------------------------------------------------
# Fetch & parsing helpers
# ------------------------------------------------------------------


def rich_headers() -> Dict[str, str]:
    return {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Cache-Control": "max-age=0",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "sec-ch-ua": '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "DNT": "1",
    }


def fetch(
    session: requests.Session,
    url: str,
    timeout: int = 40,
    debug: bool = False,
    referer: Optional[str] = None,
) -> Optional[requests.Response]:
    headers: Dict[str, str] = {}
    if referer:
        headers["Referer"] = referer
    try:
        r = session.get(url, headers=headers, timeout=timeout)
        if debug:
            print(f"[DEBUG] GET {url} -> {r.status_code}")
            for k, v in list(r.headers.items())[:20]:
                print(f"[DEBUG]   {k}: {v}")
            snippet = r.text[:500].replace("\n", "\\n")
            print(f"[DEBUG]   BodySnippet: {snippet}")
        return r
    except requests.RequestException as e:
        if debug:
            print(f"[DEBUG] Exception fetching {url}: {e}")
        return None


def extract_regulation_links(index_html: str, base_url: str) -> Set[str]:
    soup = BeautifulSoup(index_html, "html.parser")
    links: Set[str] = set()
    for a_tag in soup.find_all("a", href=True):  # type: ignore[assignment]
        if not isinstance(a_tag, Tag):  # defensive
            continue
        href_attr = a_tag.get("href")
        if not isinstance(href_attr, str):
            continue
        href = href_attr.strip()
        full = urljoin(base_url, href)
        parsed = urlparse(full)
        if parsed.netloc != BASE_DOMAIN:
            continue
        if REG_LINK_PATTERN.search(parsed.path):
            links.add(full.split("#")[0])
    return links


def apply_content_filtering(
    html: str,
    images_dir: Optional[str] = None,
    session: Optional[requests.Session] = None,
) -> str:
    """Filter navigation/UI clutter and process images."""
    soup = BeautifulSoup(html, "html.parser")
    article = soup.find("article")
    target = article or soup.find("main") or soup.body
    if not target:
        return html
    unwanted_selectors = [
        "script",
        "style",
        "nav",
        "footer",
        "form",
        "noscript",
        "header",
        ".navbar-header",
        "#navbar",
        ".usa-banner",
        ".breadcrumb",
        "#block-osha-theme-breadcrumb",
        ".dialog-off-canvas-main-canvas > header",
        "#google_translate_element2",
        ".skiptranslate",
        ".goog-te-gadget",
        "[id*='google_translate']",
        "[class*='google-translate']",
        "[class*='goog-te']",
        "[aria-hidden='true']",
        ".navbar",
        ".navigation",
        "#block-cart",
        ".skip-link",
        ".visually-hidden",
    ]
    for selector in unwanted_selectors:
        for tag in target.select(selector):  # type: ignore[union-attr]
            if isinstance(tag, Tag):
                tag.decompose()
    for tag in target.find_all(attrs={"aria-hidden": "true"}):  # type: ignore[union-attr]
        if isinstance(tag, Tag):
            tag.decompose()
    improve_image_processing(target, images_dir=images_dir, session=session)  # type: ignore[arg-type]
    return str(target)


def extract_main_text(
    html: str,
    images_dir: Optional[str] = None,
    session: Optional[requests.Session] = None,
) -> str:
    filtered_html = apply_content_filtering(
        html, images_dir=images_dir, session=session
    )
    soup = BeautifulSoup(filtered_html, "html.parser")
    text = soup.get_text("\n")
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    filtered_lines: List[str] = []
    skip_patterns: List[Optional[str]] = [
        r"^Select Language$",
        r"^Languages$",
        r"^\([A-Za-z\-\s]+\)$",
        r"^[A-Za-z\s]+$" if len(lines) > 100 else None,
        r"^Here's how you know$",
        r"^An official website",
        r"^The \.gov means",
        r"^Federal government websites",
        r"^The site is secure",
        r"^U\.S\. Department of Labor$",
        r"^MENU$",
        r"^Contact Us$",
        r"^FAQ$",
        r"^A to Z Index$",
        r"^Skip to main content$",
    ]
    for line in lines:
        if len(line) < 100 and any(
            lang in line
            for lang in [
                "Afrikaans",
                "Albanian",
                "Arabic",
                "Chinese",
                "French",
                "German",
                "Spanish",
                "Russian",
                "Japanese",
                "Korean",
                "Portuguese",
                "Italian",
            ]
        ):
            continue
        if any(
            pattern and re.match(pattern, line, re.IGNORECASE)
            for pattern in skip_patterns
        ):
            continue
        filtered_lines.append(line)
    result = "\n".join(filtered_lines)
    lines2 = result.split("\n")
    start_idx = 0
    for i, line in enumerate(lines2):
        if any(
            marker in line
            for marker in ["Part Number:", "Standard Number:", "1910.", "CFR"]
        ):
            start_idx = i
            break
    final_result = "\n".join(lines2[start_idx:]) if start_idx > 0 else result
    for i, line in enumerate(final_result.split("\n")):
        if line.strip() == "Title:" and i + 1 < len(final_result.split("\n")):
            title_line = final_result.split("\n")[i + 1].strip()
            if title_line == "[Reserved]":
                return "RESERVED_REGULATION"
            break
    return final_result


# ------------------------------------------------------------------
# Manifest
# ------------------------------------------------------------------


def load_manifest(path: str) -> Dict[str, Any]:
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                print("[WARN] Manifest invalid. Starting new.")
    return {"generated_at": None, "pages": []}


def save_manifest(path: str, manifest: Dict[str, Any]) -> None:
    manifest["generated_at"] = utc_now_iso()
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
    os.replace(tmp, path)


def manifest_lookup(manifest: Dict[str, Any], url: str) -> Optional[Dict[str, Any]]:
    for p in manifest["pages"]:
        if p["url"] == url:
            return p
    return None


# ------------------------------------------------------------------
# Rate Limiter
# ------------------------------------------------------------------
class RateLimiter:
    def __init__(self, crawl_delay: float):
        self.crawl_delay = crawl_delay
        self.last_time = 0.0

    def wait(self) -> None:
        now = time.time()
        wait_for = self.last_time + self.crawl_delay - now
        if wait_for > 0:
            time.sleep(wait_for)
        self.last_time = time.time()


# ------------------------------------------------------------------
# Page processing
# ------------------------------------------------------------------


def process_page(
    url: str,
    session: requests.Session,
    args: argparse.Namespace,
    rate_limiter: RateLimiter,
    manifest: Dict[str, Any],
) -> bool:
    existing_entry = manifest_lookup(manifest, url)
    headers: Dict[str, str] = {}
    # Always use conditional GET for existing pages unless force
    if existing_entry and not args.force:
        if existing_entry.get("etag"):
            headers["If-None-Match"] = str(existing_entry["etag"])
        if existing_entry.get("last_modified"):
            headers["If-Modified-Since"] = str(existing_entry["last_modified"])
    headers["Referer"] = (
        "https://www.osha.gov/laws-regs/regulations/standardnumber/1910"
    )
    if args.rotate_ua:
        session.headers["User-Agent"] = random.choice(BROWSER_USER_AGENTS)
    rate_limiter.wait()
    time.sleep(random.uniform(0.5, 1.5))
    try:
        r = session.get(url, headers=headers, timeout=args.timeout)
    except requests.RequestException as e:
        print(f"[WARN] Request failed {url}: {e}")
        return False
    if r.status_code == 304:
        print(f"[NOT MOD] {url}")
        if existing_entry:
            existing_entry["last_checked"] = utc_now_iso()
        return False
    if r.status_code != 200:
        print(f"[WARN] Non-200 {r.status_code} for {url}")
        if args.debug:
            snippet = r.text[:500].replace("\n", "\\n")
            print(f"[DEBUG] BodySnippet: {snippet}")
        return False
    html_bytes = r.content
    html_text = r.text
    regulation_id = url.rstrip("/").split("/")[-1]
    page_dir = os.path.join(args.output, regulation_id)
    os.makedirs(page_dir, exist_ok=True)
    raw_path = os.path.join(page_dir, "raw.html")
    text_path = os.path.join(page_dir, "text.txt")
    meta_path = os.path.join(page_dir, "meta.json")
    md_path = os.path.join(page_dir, "content.md")  # always generate markdown now
    images_dir = os.path.join(page_dir, "images")
    with open(raw_path, "wb") as f:
        f.write(html_bytes)
    main_text = extract_main_text(html_text, images_dir=images_dir, session=session)
    if main_text == "RESERVED_REGULATION":
        print(f"[SKIP] {url} - Reserved regulation")
        return False
    with open(text_path, "w", encoding="utf-8") as f:
        f.write(main_text)
    # Markdown generation (mandatory)
    try:
        filtered_html = apply_content_filtering(
            html_text, images_dir=images_dir, session=session
        )
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(md_convert(filtered_html))  # type: ignore[arg-type]
    except Exception as e:  # pragma: no cover
        print(f"[WARN] Markdown conversion failed {url}: {e}")
        md_path = None
    meta: Dict[str, Any] = {
        "url": url,
        "regulation_id": regulation_id,
        "downloaded_at": utc_now_iso(),
        "last_checked": utc_now_iso(),
        "http_status": r.status_code,
        "sha256_html": sha256_bytes(html_bytes),
        "size_bytes": len(html_bytes),
        "raw_file": os.path.relpath(raw_path, args.output),
        "text_file": os.path.relpath(text_path, args.output),
        "etag": r.headers.get("ETag"),
        "last_modified": r.headers.get("Last-Modified"),
        "user_agent": session.headers.get("User-Agent"),
    }
    if md_path:
        meta["markdown_file"] = os.path.relpath(md_path, args.output)
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)
    pages = [p for p in manifest["pages"] if p["url"] != url]
    pages.append(meta)
    manifest["pages"] = pages
    print(f"[OK ] {url}")
    return True


# ------------------------------------------------------------------
# CSV export
# ------------------------------------------------------------------


def export_csv(manifest: Dict[str, Any], path: str) -> None:
    fields = [
        "regulation_id",
        "url",
        "downloaded_at",
        "last_checked",
        "http_status",
        "sha256_html",
        "size_bytes",
        "raw_file",
        "text_file",
        "markdown_file",
        "etag",
        "last_modified",
    ]
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for p in manifest["pages"]:
            writer.writerow({k: p.get(k, "") for k in fields})
    print(f"[INFO] CSV exported to {path}")


# ------------------------------------------------------------------
# CLI
# ------------------------------------------------------------------


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(
        description="OSHA 1910 scraper (minimal). Markdown & CSV always generated."
    )
    ap.add_argument("--output", default=OUTPUT_DIR)
    ap.add_argument("--timeout", type=int, default=40)
    ap.add_argument(
        "--limit", type=int, default=0, help="Process only first N URLs (debugging)"
    )
    ap.add_argument(
        "--force",
        action="store_true",
        help="Ignore conditional GET; re-download all content",
    )
    ap.add_argument(
        "--sitemap-only",
        action="store_true",
        help="Skip index fetch; rely solely on sitemap.",
    )
    ap.add_argument(
        "--rotate-ua",
        action="store_true",
        help="Rotate a random browser UA for each page request.",
    )
    ap.add_argument("--debug", action="store_true")
    ap.add_argument(
        "--no-warmup", action="store_true", help="Skip initial warm-up root request."
    )
    return ap.parse_args()


def main() -> None:
    args = parse_args()
    os.makedirs(args.output, exist_ok=True)
    manifest_path = os.path.join(args.output, MANIFEST_FILENAME)
    csv_path = os.path.join(args.output, "manifest.csv")  # default CSV path
    manifest = load_manifest(manifest_path)
    session = requests.Session()
    session.headers.update(rich_headers())
    session.headers["User-Agent"] = DEFAULT_USER_AGENT
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry

    retry_strategy = Retry(
        total=3, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504]
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    detected_delay = fetch_robots_crawl_delay(session) or DEFAULT_CRAWL_DELAY
    if not args.no_warmup and not args.sitemap_only:
        for warm_url in ["https://www.osha.gov/", "https://www.osha.gov/laws-regs"]:
            try:
                time.sleep(random.uniform(1.0, 3.0))
                wr = session.get(warm_url, timeout=30)
                if args.debug:
                    print(f"[DEBUG] Warm-up {warm_url} -> {wr.status_code}")
                if wr.status_code == 200:
                    break
            except requests.RequestException as e:
                if args.debug:
                    print(f"[DEBUG] Warm-up failed: {e}")
    print(f"[INFO] Crawl delay {detected_delay}s.")
    index_links: Set[str] = set()
    if args.sitemap_only:
        print("[INFO] Skipping index fetch (--sitemap-only).")
    else:
        idx_resp = fetch(
            session,
            INDEX_URL,
            timeout=args.timeout,
            debug=args.debug,
            referer="https://www.osha.gov/laws-regs",
        )
        if not idx_resp:
            print("[WARN] Index fetch failed (network). Will rely on sitemap.")
        elif idx_resp.status_code != 200:
            print(
                f"[WARN] Index status {idx_resp.status_code}. Continuing with sitemap."
            )
            if args.debug and idx_resp:
                snippet = (idx_resp.text[:600]).replace("\n", "\\n")
                print(f"[DEBUG] Index body snippet: {snippet}")
        else:
            index_links = extract_regulation_links(idx_resp.text, INDEX_URL)
            if args.debug:
                print(f"[DEBUG] Extracted {len(index_links)} links from index.")
    # Always include sitemap URLs
    print("[INFO] Collecting sitemap URLs...")
    sitemap_links = sitemap_regulation_urls(session)
    print(f"[INFO] Sitemap yielded {len(sitemap_links)} candidate regulation URLs.")
    all_urls = sorted(set(index_links) | sitemap_links, key=extract_regulation_number)
    print(f"[INFO] Total distinct regulation URLs: {len(all_urls)}")
    if args.limit > 0:
        all_urls = all_urls[: args.limit]
        print(f"[INFO] Limiting to first {len(all_urls)} URLs.")
    # Minimal: process all URLs (conditional GET handles unchanged pages) unless force just disables conditional headers
    to_fetch = all_urls
    print(f"[INFO] URLs to process: {len(to_fetch)} (force={args.force})")
    rate_limiter = RateLimiter(detected_delay)
    new_or_updated = 0
    for i, url in enumerate(to_fetch, 1):
        print(f"[PROC] ({i}/{len(to_fetch)}) {url}")
        changed = process_page(url, session, args, rate_limiter, manifest)
        if changed:
            new_or_updated += 1
        save_manifest(manifest_path, manifest)
    print(
        f"[DONE] New/updated pages this run: {new_or_updated}. Total in manifest: {len(manifest['pages'])}"
    )
    # Always export CSV
    export_csv(manifest, csv_path)


if __name__ == "__main__":
    main()
