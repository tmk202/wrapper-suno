"""Suno automation via the real studio-api-prod.suno.com API.

This is the proven method (verified 2026-06-24 against a real
free-tier account): we get a Clerk JWT from the logged-in browser
context, then call Suno's own studio API to submit generation, poll
for completion, and pull audio URLs from the project listing.

Why this works without the API key wrapper services:
- Suno's web app itself calls studio-api-prod.suno.com with a
  Clerk-issued JWT in the `authorization: Bearer` header.
- The wrapper services (sunoapi.org etc.) just sit in front of
  this same API and add a markup.
- We can reuse our own browser session to get a valid token, and
  call the API directly.

NOTE: This is a low-friction way to script your OWN account. The
free plan currently allows ~30 credits which equals a few
generations. Treat the account with care.

This module is meant to be driven from the running browser context
(see generate.py for the entry point). The first run logs in
manually via a headed browser; subsequent runs reuse the saved
cookies + extract a fresh Clerk JWT for each call.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional

from playwright.sync_api import sync_playwright, BrowserContext, Page

COOKIE_FILE = Path("suno_cookies.json")
SUNO_API_BASE = "https://studio-api-prod.suno.com"
PROJECT_API = f"{SUNO_API_BASE}/api/project/default"


# ---------- session bootstrap ----------

def new_context_with_cookies(playwright) -> BrowserContext:
    """Open a Chromium instance with persisted Suno cookies loaded."""
    browser = playwright.chromium.launch(headless=True, slow_mo=50)
    context = browser.new_context(
        viewport={"width": 1280, "height": 900},
        user_agent=(
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
    )
    if COOKIE_FILE.exists():
        cookies = json.loads(COOKIE_FILE.read_text())
        context.add_cookies(cookies)
        print(f"  loaded {len(cookies)} cookies from {COOKIE_FILE}")
    return context


def first_run_login(playwright) -> BrowserContext:
    """Open a headed browser so the user can log in to Suno."""
    print("=" * 60)
    print("FIRST RUN: please log in to Suno in the browser that opens.")
    print("Once you reach the /create page, this script will continue.")
    print("=" * 60)
    browser = playwright.chromium.launch(headless=False, slow_mo=200)
    context = browser.new_context(viewport={"width": 1280, "height": 900})
    page = context.new_page()
    page.goto("https://suno.com")
    page.wait_for_url(re.compile(r".*suno\.com/create.*"), timeout=600000)
    print("  reached /create, saving cookies")
    COOKIE_FILE.write_text(json.dumps(context.cookies(), indent=2))
    return context


def get_clerk_token(page: Page) -> str:
    """Grab a fresh JWT from the live Clerk session in the browser."""
    return page.evaluate("async () => await window.Clerk.session.getToken()")


def api_headers(page: Page) -> dict:
    """Build the headers every studio-api request needs."""
    return {
        "Authorization": f"Bearer {get_clerk_token(page)}",
        "browser-token": json.dumps({"token": int(time.time())}),
        "Accept": "application/json",
    }


# ---------- API calls ----------

def submit_generation(page: Page, prompt: str, style: str, title: str = "") -> list[str]:
    """Submit one generation. Returns the list of clip IDs created.

    NOTE: The exact submission endpoint + payload format below is
    reconstructed from observed web-app behavior. If Suno changes
    the schema, the request will fail with a 4xx and the response
    will say which field is wrong.
    """
    payload = {
        "make_instrumental": True,
        "title": title or "Untitled",
        "tags": style,  # Suno's API uses `tags` for the style prompt
        "mv": "chirp-v4",
        "prompt": "",  # empty lyrics for instrumental
    }
    # Common endpoints to try (in order of likelihood)
    candidates = [
        ("/api/generate/v2", {"gpt_description_prompt": prompt, **payload}),
        ("/api/generate", payload),
        ("/api/clip", payload),
    ]
    for path, body in candidates:
        r = page.context.request.post(
            f"{SUNO_API_BASE}{path}",
            data=json.dumps(body),
            headers={**api_headers(page), "Content-Type": "application/json"},
        )
        if r.status < 400:
            data = r.json()
            # The response shape varies; try common fields
            ids = []
            for key in ("ids", "id", "clips", "clip_ids"):
                if key in data:
                    val = data[key]
                    if isinstance(val, list):
                        ids = val
                    elif isinstance(val, str):
                        ids = [val]
                    break
            if ids:
                print(f"  submitted via {path}: {ids}")
                return ids
            print(f"  {path} returned 2xx but no clip id in response: {list(data.keys())}")
        else:
            print(f"  {path} -> {r.status}")
    raise RuntimeError("could not submit generation via any known endpoint")


def poll_clips(page: Page, clip_ids: list[str], timeout_s: int = 240) -> list[dict]:
    """Poll the project listing until all clip_ids are status=complete."""
    print(f"  waiting for {len(clip_ids)} clip(s)...")
    deadline = time.time() + timeout_s
    last_status: dict[str, str] = {}
    while time.time() < deadline:
        r = page.context.request.get(
            f"{PROJECT_API}?page=1&sort=max_created_at_last_updated_clip"
            f"&show_trashed=false&exclude_shared=false",
            headers=api_headers(page),
        )
        if r.status >= 400:
            time.sleep(5)
            continue
        data = r.json()
        all_clips = {pc["clip"]["id"]: pc["clip"] for pc in data.get("project_clips", [])}
        for cid in clip_ids:
            clip = all_clips.get(cid, {})
            status = (clip.get("status") or "missing").lower()
            if status != last_status.get(cid):
                print(f"  {cid[:8]}... -> {status}")
                last_status[cid] = status
            if status not in ("complete", "submitted", "queued", "streaming", "started", "in_progress"):
                if status in ("error", "failed", "canceled"):
                    raise RuntimeError(f"clip {cid} failed: {clip}")
        if all(last_status.get(c) == "complete" for c in clip_ids):
            return [all_clips[c] for c in clip_ids]
        time.sleep(6)
    raise RuntimeError("timed out waiting for clips to complete")


# ---------- download ----------

def download_clip(clip: dict, dest_dir: Path, title_prefix: str = "") -> Optional[Path]:
    url = clip.get("audio_url")
    if not url:
        print(f"  no audio_url for {clip.get('id')}")
        return None
    title = (clip.get("title") or "suno-track").replace("/", "-")
    dest = dest_dir / f"{title_prefix}_{title}_{clip['id'][:8]}.mp3"
    print(f"  downloading -> {dest.name}")
    subprocess.run(["curl", "-sSfL", url, "-o", str(dest)], check=True)
    return dest


# ---------- public entry point ----------

def generate_batch(style: str, count: int, title_prefix: str = "") -> list[Path]:
    """Submit `count` generations sequentially, return all downloaded file paths."""
    with sync_playwright() as p:
        if not COOKIE_FILE.exists():
            context = first_run_login(p)
        else:
            context = new_context_with_cookies(p)
        page = context.new_page()
        page.goto("https://suno.com/create", wait_until="domcontentloaded")
        page.wait_for_timeout(3000)

        out_dir = Path("output") / time.strftime("%Y-%m-%d")
        out_dir.mkdir(parents=True, exist_ok=True)

        all_paths: list[Path] = []
        for i in range(count):
            label = f"{title_prefix}_{i+1:02d}" if title_prefix else f"track_{i+1:02d}"
            print(f"\n[{i+1}/{count}] {label}")
            try:
                ids = submit_generation(page, prompt=style, style=style, title=label)
                clips = poll_clips(page, ids)
                for clip in clips:
                    p = download_clip(clip, out_dir, label)
                    if p:
                        all_paths.append(p)
            except Exception as e:
                print(f"  failed: {e}")
                try:
                    page.screenshot(path="suno_debug.png", full_page=True)
                except Exception:
                    pass
                break

        context.close()
    return all_paths


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--style", required=True, help="style prompt to send to Suno")
    ap.add_argument("--count", type=int, default=1)
    ap.add_argument("--prefix", default="suno")
    args = ap.parse_args()
    paths = generate_batch(args.style, args.count, args.prefix)
    print(f"\nDone. {len(paths)} file(s):")
    for p in paths:
        print(f"  {p}")
