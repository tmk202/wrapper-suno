#!/usr/bin/env python3
"""Generate Focus Music in bulk via Suno.

Two backends:
  --backend api      call Suno HTTP API (needs SUNO_API_KEY in .env)
  --backend browser  drive suno.com in a real browser via Playwright
                     (needs pip install playwright + playwright install chromium)

Usage:
  python generate.py --list
  python generate.py --backend api     --preset deep_focus --count 3
  python generate.py --backend browser --preset calm_piano --count 5
  python generate.py --backend browser --preset coffee_shop --count 2 --no-headless

Output: ./output/YYYY-MM-DD/<preset>_<index>_<title>.mp3
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from datetime import date
from pathlib import Path

import requests
from dotenv import load_dotenv

from presets import PRESETS, get_preset, list_presets


def load_config():
    load_dotenv()
    api_key = os.getenv("SUNO_API_KEY", "").strip()
    if not api_key or api_key == "your_suno_api_key_here":
        print("ERROR: SUNO_API_KEY missing.")
        print("  1. Copy .env.example to .env")
        print("  2. Paste your Suno API key into .env")
        print("  3. Get a key at https://suno.com → Account → API")
        sys.exit(1)
    return {
        "api_key": api_key,
        "base": os.getenv("SUNO_API_BASE", "https://api.suno.ai/v1").rstrip("/"),
    }


def submit_track(cfg, preset: dict, idx: int, mood: str | None) -> str:
    """Send a generation request, return task id."""
    prompt = preset["style"]
    if mood:
        prompt = f"{prompt}, {mood}"

    payload = {
        "prompt": prompt,
        "style": preset["style"],
        "negative_tags": preset["negative"],
        "duration": preset["duration"],
        "instrumental": True,
        "title": f"{preset['label']} #{idx+1}",
    }
    headers = {
        "Authorization": f"Bearer {cfg['api_key']}",
        "Content-Type": "application/json",
    }

    r = requests.post(f"{cfg['base']}/generate", json=payload, headers=headers, timeout=60)
    if r.status_code >= 400:
        print(f"  submit failed ({r.status_code}): {r.text[:300]}")
        raise SystemExit(1)
    data = r.json()
    return data.get("id") or data.get("task_id") or data.get("clip_id")


def poll_track(cfg, task_id: str, timeout_s: int = 300) -> dict:
    """Poll the API until the track is ready. Return the full result dict."""
    headers = {"Authorization": f"Bearer {cfg['api_key']}"}
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        r = requests.get(f"{cfg['base']}/status/{task_id}", headers=headers, timeout=30)
        if r.status_code >= 400:
            print(f"  poll failed ({r.status_code}): {r.text[:200]}")
            time.sleep(5)
            continue
        data = r.json()
        status = (data.get("status") or "").lower()
        if status in ("complete", "completed", "success", "succeeded"):
            return data
        if status in ("error", "failed", "canceled"):
            print(f"  generation failed: {data}")
            raise SystemExit(1)
        print(f"  ...{status or 'queued'}", end="\r")
        time.sleep(6)
    print("  timed out waiting for track")
    raise SystemExit(1)


def download_audio(url: str, dest: Path) -> None:
    with requests.get(url, stream=True, timeout=120) as r:
        r.raise_for_status()
        with open(dest, "wb") as f:
            for chunk in r.iter_content(chunk_size=65536):
                f.write(chunk)


def main():
    ap = argparse.ArgumentParser(description="Bulk generate Focus Music via Suno")
    ap.add_argument("--backend", choices=["api", "browser"], default="api",
                    help="api = HTTP API (needs SUNO_API_KEY); browser = drive suno.com via Playwright")
    ap.add_argument("--preset", help="preset name (see --list)")
    ap.add_argument("--count", type=int, default=3, help="how many tracks to generate")
    ap.add_argument("--mood", help="optional extra mood hint, e.g. 'late night coding'")
    ap.add_argument("--output", default="./output", help="output folder")
    ap.add_argument("--list", action="store_true", help="list presets and exit")
    ap.add_argument("--check", action="store_true", help="verify API key is loaded, then exit")
    ap.add_argument("--no-headless", action="store_true",
                    help="(browser) show the browser window while generating")
    args = ap.parse_args()

    if args.list:
        print("Available presets:")
        list_presets()
        return

    if args.check:
        cfg = load_config()
        masked = cfg["api_key"][:6] + "..." + cfg["api_key"][-4:]
        print(f"API key loaded: {masked}")
        print(f"Base URL:       {cfg['base']}")
        print("OK. Run without --check to generate.")
        return

    if not args.preset:
        ap.error("--preset is required (use --list to see options)")

    preset = get_preset(args.preset)

    out_dir = Path(args.output) / date.today().isoformat()
    out_dir.mkdir(parents=True, exist_ok=True)
    print(f"Output folder: {out_dir}")
    print(f"Backend:       {args.backend}")
    print(f"Preset:        {preset['label']}")
    print(f"Tracks:        {args.count}")
    if args.mood:
        print(f"Mood hint:     {args.mood}")
    print()

    if args.backend == "api":
        run_api(preset, args.mood, args.count, out_dir, args.preset)
    else:
        style = preset["style"] + (f", {args.mood}" if args.mood else "")
        run_browser(style, args.count, out_dir, args.preset, headless=not args.no_headless)


def run_api(preset: dict, mood: str | None, count: int, out_dir: Path, preset_name: str) -> None:
    cfg = load_config()
    for i in range(count):
        print(f"[{i+1}/{count}] submitting...")
        task_id = submit_track(cfg, preset, i, mood)
        print(f"  task id: {task_id}")
        print("  generating (this usually takes 30-90s)...")
        result = poll_track(cfg, task_id)
        save_track_from_result(result, i, preset, preset_name, out_dir)


def save_track_from_result(result: dict, idx: int, preset: dict, preset_name: str, out_dir: Path) -> None:
    audio_url = (
        result.get("audio_url")
        or result.get("audioUrl")
        or (result.get("audio") or {}).get("url")
        or (result.get("output") or {}).get("audio_url")
    )
    if not audio_url:
        print(f"  could not find audio url in response: {list(result.keys())}")
        return
    title = (result.get("title") or preset["label"]).replace("/", "-")
    ext = "mp3" if audio_url.lower().endswith(".mp3") else "m4a"
    dest = out_dir / f"{preset_name}_{idx+1:02d}_{title}.{ext}"
    print(f"  downloading -> {dest.name}")
    download_audio(audio_url, dest)
    print(f"  saved: {dest}")
    print()


def run_browser(style: str, count: int, out_dir: Path, preset_name: str, headless: bool) -> None:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("ERROR: playwright is not installed.")
        print("  Run:  pip install -r requirements-browser.txt")
        print("  Then: playwright install chromium")
        sys.exit(1)
    try:
        from suno_browser import generate_batch
    except ImportError as e:
        print(f"ERROR: could not import suno_browser.py: {e}")
        print("  Make sure suno_browser.py is in the same folder as generate.py")
        sys.exit(1)

    print(f"headless:      {headless}")
    print("first run will ask you to log in once; cookies get saved.")
    print()

    # The browser backend downloads files itself (via page.expect_download)
    # into output/_inprogress, then we move them to the dated folder.
    paths = generate_batch(
        style=style,
        count=count,
        title_prefix=preset_name,
        headless=headless,
    )

    if not paths:
        print("\nno tracks collected — check suno_debug.png if it was written")
        return

    inprogress = Path("output/_inprogress")
    moved = 0
    for src in paths:
        dest = out_dir / src.name
        try:
            src.rename(dest)
            print(f"  moved: {dest.name}")
            moved += 1
        except Exception as e:
            print(f"  could not move {src.name}: {e}")
    if inprogress.exists() and not any(inprogress.iterdir()):
        inprogress.rmdir()

    print(f"\nDone. {moved}/{len(paths)} track(s) saved in {out_dir}")

    # Auto-merge: concat all MP3s in this folder into one file.
    # The 1-hour rule is currently DISABLED (testing mode).
    # To enforce it, pass strict=True or set MIN_DURATION_SECONDS in merge.py.
    try:
        from merge import merge_tracks, MIN_DURATION_SECONDS
        print(f"\nAuto-merge step (1-hour rule is DISABLED — {MIN_DURATION_SECONDS}s target):")
        merged = merge_tracks(out_dir, out_dir / "merged.mp3", min_duration_seconds=None)
        if merged:
            print(f"Merged file ready: {merged}")
    except Exception as e:
        print(f"  auto-merge failed: {e}")

    # Auto-setup video folders: create v{NN}/ for any new MP3 not yet foldered.
    # Idempotent — safe to run multiple times. Drops notes.md template + copies audio.
    # User adds thumbnail.jpg by hand later.
    try:
        from setup_videos import setup_videos
        print("\nAuto-setup video folders (idempotent):")
        setup_videos(out_dir)
    except Exception as e:
        print(f"  auto-setup-videos failed: {e}")


if __name__ == "__main__":
    main()
