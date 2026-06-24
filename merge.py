#!/usr/bin/env python3
"""Merge all MP3 files in a folder into a single file using ffmpeg.

Usage:
  python merge.py                                    # merge today's output
  python merge.py output/2026-06-24                  # merge specific folder
  python merge.py output/2026-06-24 --output mix.mp3 # custom name
  python merge.py --strict                           # enforce 1-hour minimum

The 1-hour minimum rule is currently DISABLED by default (testing mode).
Pass --strict to re-enable it.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from pathlib import Path


MIN_DURATION_SECONDS = 3600  # 1 hour production target
DEFAULT_OUTPUT_NAME = "merged.mp3"


# ---------- helpers ----------

def ffprobe_duration(path: Path) -> float:
    """Return duration in seconds (float) for an audio file via ffprobe."""
    try:
        out = subprocess.check_output(
            [
                "ffprobe", "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                str(path),
            ],
            stderr=subprocess.STDOUT,
            timeout=15,
        ).decode().strip()
        return float(out)
    except Exception as e:
        print(f"  warning: could not probe {path.name}: {e}", file=sys.stderr)
        return 0.0


def format_duration(seconds: float) -> str:
    """Format seconds as H:MM:SS or M:SS."""
    s = int(seconds)
    h, rem = divmod(s, 3600)
    m, sec = divmod(rem, 60)
    if h > 0:
        return f"{h}:{m:02d}:{sec:02d}"
    return f"{m}:{sec:02d}"


def find_mp3s(folder: Path) -> list[Path]:
    """Return all .mp3 files in folder, sorted alphabetically (so order is deterministic).

    Skips files whose name starts with 'merged' so running merge repeatedly
    doesn't compound (a second merge would otherwise include the first merged.mp3).
    """
    return sorted(
        p for p in folder.iterdir()
        if p.is_file()
        and p.suffix.lower() == ".mp3"
        and not p.stem.lower().startswith("merged")
    )


# ---------- core merge ----------

def merge_tracks(
    input_dir: Path,
    output_path: Path,
    min_duration_seconds: int | None = None,
) -> Path | None:
    """Concatenate all .mp3 in input_dir into output_path using ffmpeg's concat demuxer.

    Returns the output path on success, or None if the 1-hour rule failed.
    """
    mp3s = find_mp3s(input_dir)
    if not mp3s:
        print(f"  no mp3 files found in {input_dir}")
        return None

    # Probe each file
    print(f"  found {len(mp3s)} mp3 file(s):")
    durations: list[tuple[Path, float]] = []
    for p in mp3s:
        d = ffprobe_duration(p)
        durations.append((p, d))
        print(f"    {format_duration(d):>8s}  {p.name}")

    total = sum(d for _, d in durations)
    print(f"  total: {format_duration(total)} ({total:.0f}s)")

    # 1-hour minimum rule (production mode)
    # Currently disabled per user request — re-enable by uncommenting.
    if min_duration_seconds is not None and total < min_duration_seconds:
        print(
            f"  ✗ total {format_duration(total)} < required {format_duration(min_duration_seconds)} "
            f"— skipping merge (rule enforcement ON)"
        )
        return None

    # Build ffmpeg concat list
    list_file = input_dir / "_concat_list.txt"
    with list_file.open("w", encoding="utf-8") as f:
        for p, _ in durations:
            # ffmpeg concat demuxer wants paths quoted; escape single quotes
            safe = str(p.absolute()).replace("'", "'\\''")
            f.write(f"file '{safe}'\n")

    # Run ffmpeg (no re-encoding → fast, lossless copy)
    cmd = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0",
        "-i", str(list_file),
        "-c", "copy",
        str(output_path),
    ]
    print(f"  running: {' '.join(cmd)}")
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=180,
        )
    except subprocess.TimeoutExpired:
        print("  ffmpeg timed out after 180s")
        return None
    if result.returncode != 0:
        print(f"  ffmpeg failed (exit {result.returncode}):")
        print(result.stderr[-1000:] if result.stderr else "(no stderr)")
        return None

    # Clean up list file
    try:
        list_file.unlink()
    except Exception:
        pass

    # Verify the merged file
    out_dur = ffprobe_duration(output_path)
    print(f"  ✓ merged file: {output_path.name}  ({format_duration(out_dur)}, {output_path.stat().st_size // 1024} KB)")
    return output_path


# ---------- CLI ----------

def main():
    ap = argparse.ArgumentParser(description="Merge all MP3s in a folder into one file (ffmpeg).")
    ap.add_argument("folder", nargs="?", default=None,
                    help="folder containing mp3 files (default: today's output/YYYY-MM-DD)")
    ap.add_argument("--output", default=DEFAULT_OUTPUT_NAME,
                    help=f"output filename (default: {DEFAULT_OUTPUT_NAME})")
    ap.add_argument("--strict", action="store_true",
                    help="enforce the 1-hour minimum rule (disabled by default for testing)")
    args = ap.parse_args()

    if args.folder:
        folder = Path(args.folder)
    else:
        # default to today's output
        folder = Path("output") / time.strftime("%Y-%m-%d")
    if not folder.is_dir():
        print(f"  folder not found: {folder}")
        sys.exit(1)

    print(f"Merging MP3s in: {folder}")
    min_dur = MIN_DURATION_SECONDS if args.strict else None
    if min_dur is not None:
        print(f"  rule: 1-hour minimum ({format_duration(min_dur)}) — ENFORCED")
    else:
        print(f"  rule: 1-hour minimum ({format_duration(MIN_DURATION_SECONDS)}) — DISABLED (testing)")

    out = folder / args.output
    result = merge_tracks(folder, out, min_duration_seconds=min_dur)
    if result is None:
        sys.exit(2)
    print(f"\nDone: {result}")


if __name__ == "__main__":
    main()
