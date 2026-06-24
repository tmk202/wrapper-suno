#!/usr/bin/env python3
"""Create video folders for any MP3 in an output/ folder that isn't yet foldered.

Idempotent: uses MD5 hash of audio content to detect already-foldered files.
Safe to run multiple times — never duplicates a folder.

Usage:
  python setup_videos.py                         # today's output folder
  python setup_videos.py output/2026-06-24       # specific folder
  python setup_videos.py output/2026-06-24 --dry # show what would be created
"""

from __future__ import annotations

import argparse
import hashlib
import shutil
import subprocess
import sys
import time
from pathlib import Path

VIDEOS_DIR = Path("videos")
DEFAULT_OUTPUT = Path("output") / time.strftime("%Y-%m-%d")


# ---------- helpers ----------

def file_hash(path: Path) -> str:
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def format_duration(seconds: float) -> str:
    s = int(seconds)
    h, rem = divmod(s, 3600)
    m, sec = divmod(rem, 60)
    if h > 0:
        return f"{h}:{m:02d}:{sec:02d}"
    return f"{m}:{sec:02d}"


def get_duration(path: Path) -> float:
    try:
        out = subprocess.check_output(
            [
                "ffprobe", "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                str(path),
            ],
            stderr=subprocess.STDOUT, timeout=15,
        ).decode().strip()
        return float(out)
    except Exception:
        return 0.0


def get_existing_video_hashes(videos_dir: Path) -> set[str]:
    """Return the set of audio.mp3 hashes already present in any video folder."""
    hashes: set[str] = set()
    if not videos_dir.is_dir():
        return hashes
    for vid_dir in videos_dir.iterdir():
        if vid_dir.is_dir() and (vid_dir / "audio.mp3").exists():
            hashes.add(file_hash(vid_dir / "audio.mp3"))
    return hashes


def get_next_id(videos_dir: Path) -> int:
    """Return the next v{NN} ID (1-based, 2-digit zero-padded)."""
    ids: list[int] = []
    if videos_dir.is_dir():
        for d in videos_dir.iterdir():
            if d.is_dir() and d.name.startswith("v") and d.name[1:].isdigit():
                ids.append(int(d.name[1:]))
    return (max(ids) + 1) if ids else 1


def suggest_title(audio_path: Path) -> str:
    """Best-effort title suggestion from filename patterns."""
    name = audio_path.stem.lower()
    rules = [
        ("merged",      "Lo-fi Focus Mix (Full Session)"),
        ("deep_focus",  "Lo-fi Deep Focus"),
        ("calm_piano",  "Calm Piano for Focus"),
        ("chill_beats", "Chill Beats for Working"),
        ("coffee_shop", "Coffee Shop Jazz"),
        ("nature_ambient", "Nature Ambient Soundscape"),
        ("minimal_techno", "Minimal Techno for Deep Work"),
    ]
    for key, title in rules:
        if key in name:
            return title
    return f"Focus Music — {audio_path.stem}"


def build_notes(vid_id: str, audio_path: Path, output_dir: Path, title: str) -> str:
    """Render the notes.md template for a new video folder."""
    duration_sec = get_duration(audio_path)
    duration_str = format_duration(duration_sec) if duration_sec > 0 else "?"

    # show source as relative path (e.g. output/2026-06-24/merged.mp3)
    try:
        source_rel = audio_path.resolve().relative_to(Path.cwd().resolve())
    except ValueError:
        source_rel = audio_path

    return f"""# {vid_id}: {title}

## YouTube upload
- **Title:** {title}
- **Description:** (edit me)
- **Tags:** focus, study, instrumental, lofi

## File info
- **Audio:** `audio.mp3` (this file)
- **Duration:** {duration_str}
- **Source:** `{source_rel}`

## Publishing checklist
- [ ] `thumbnail.jpg` uploaded (1280x720, <2MB)
- [ ] `python validate_thumbnail.py videos/{vid_id}` passes
- [ ] Title tuned for SEO
- [ ] Description polished
- [ ] Tags set in YouTube Studio
- [ ] Published date: ____________
- [ ] YouTube URL: ____________
"""


# ---------- core ----------

def setup_videos(
    output_dir: Path,
    videos_dir: Path = VIDEOS_DIR,
    dry_run: bool = False,
) -> list[Path]:
    """Create video folders for any MP3 in output_dir not yet in videos_dir.

    Returns list of new video folders created (or would be created if dry_run).
    """
    if not output_dir.is_dir():
        print(f"  output folder not found: {output_dir}")
        return []

    audios = sorted(output_dir.glob("*.mp3"))
    if not audios:
        print(f"  no MP3 files in {output_dir}")
        return []

    videos_dir.mkdir(parents=True, exist_ok=True)
    existing_hashes = get_existing_video_hashes(videos_dir)
    next_id = get_next_id(videos_dir)

    # Sort: merged.mp3 first, then alphabetical by filename (deterministic)
    sorted_audios = sorted(
        audios,
        key=lambda p: (0 if "merged" in p.name.lower() else 1, p.name.lower()),
    )

    verb = "would create" if dry_run else "create"
    print(f"Scanning {output_dir}:")
    print(f"  {len(audios)} MP3 file(s) found")
    print(f"  {len(existing_hashes)} already foldered (by content hash)")
    if dry_run:
        print(f"  mode: dry-run (no files will be written)")
    print()

    new_folders: list[Path] = []
    for audio in sorted_audios:
        h = file_hash(audio)
        if h in existing_hashes:
            print(f"  ↻ skip  {audio.name}  (already in a video folder)")
            continue

        vid_id = f"v{next_id:02d}"
        vid_dir = videos_dir / vid_id
        title = suggest_title(audio)

        if dry_run:
            print(f"  → {verb}  {vid_id}/  {audio.name}  ('{title}')")
        else:
            vid_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy(audio, vid_dir / "audio.mp3")
            notes = build_notes(vid_id, audio, output_dir, title)
            (vid_dir / "notes.md").write_text(notes, encoding="utf-8")
            print(f"  + {vid_id}/  {audio.name}  → '{title}'")
            new_folders.append(vid_dir)
        next_id += 1

    if not new_folders:
        print("\n  (nothing new to set up — all audio files are already foldered)")
    else:
        print(f"\n  ✓ {len(new_folders)} new video folder(s) ready")
        if not dry_run:
            print("  → drop thumbnail.jpg into each, then `python validate_thumbnail.py`")

    return new_folders


# ---------- CLI ----------

def main():
    ap = argparse.ArgumentParser(
        description="Create video folders for new MP3s in an output/ folder (idempotent).",
    )
    ap.add_argument("output", nargs="?", default=None,
                    help="output folder with MP3s (default: today's output/YYYY-MM-DD)")
    ap.add_argument("--dry", action="store_true",
                    help="show what would be created without writing anything")
    args = ap.parse_args()

    output_dir = Path(args.output) if args.output else DEFAULT_OUTPUT
    new = setup_videos(output_dir, VIDEOS_DIR, dry_run=args.dry)
    return 0 if new or args.dry else 1


if __name__ == "__main__":
    sys.exit(main())
