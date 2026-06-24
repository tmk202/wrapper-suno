#!/usr/bin/env python3
"""Validate YouTube thumbnail files against the official spec.

YouTube custom thumbnail rules (verified 2024-2025):
  - Recommended size: 1280 x 720 (16:9)
  - Min size:  640 x 360
  - Max size:  2 MB (custom thumbnail limit)
  - Formats:   JPG, JPEG, PNG, GIF

Usage:
  python validate_thumbnail.py                          # validate thumbnails/ folder
  python validate_thumbnail.py path/to/thumb.jpg        # single file
  python validate_thumbnail.py ./thumbnails/ --strict   # also fail on 16:9 mismatch
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    print("ERROR: Pillow not installed. Run: pip install Pillow")
    sys.exit(1)


# YouTube spec
SPEC = {
    "min_w": 640,
    "min_h": 360,
    "rec_w": 1280,
    "rec_h": 720,
    "max_bytes": 2 * 1024 * 1024,  # 2 MB
    "allowed_ext": {".jpg", ".jpeg", ".png", ".gif"},
}


def human_size(num: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if num < 1024 or unit == "GB":
            return f"{num:.1f} {unit}" if unit != "B" else f"{num} B"
        num /= 1024
    return f"{num:.1f} GB"


def check(path: Path, strict: bool = False) -> dict:
    """Return a dict of check results for a single file."""
    res = {
        "path": path,
        "exists": path.exists(),
        "errors": [],
        "warnings": [],
    }
    if not res["exists"]:
        res["errors"].append("file not found")
        return res

    # Extension check
    ext = path.suffix.lower()
    if ext not in SPEC["allowed_ext"]:
        res["errors"].append(
            f"format {ext!r} not allowed (use .jpg/.jpeg/.png/.gif)"
        )

    # File size
    size = path.stat().st_size
    res["size"] = size
    if size > SPEC["max_bytes"]:
        res["errors"].append(
            f"size {human_size(size)} > max {human_size(SPEC['max_bytes'])}"
        )
    elif size > SPEC["max_bytes"] * 0.9:
        res["warnings"].append(
            f"size {human_size(size)} close to max ({human_size(SPEC['max_bytes'])})"
        )

    # Image dimensions
    try:
        with Image.open(path) as im:
            w, h = im.size
            res["width"] = w
            res["height"] = h
            res["format"] = im.format
            res["mode"] = im.mode
    except Exception as e:
        res["errors"].append(f"cannot open as image: {e}")
        return res

    # Min size check
    if w < SPEC["min_w"] or h < SPEC["min_h"]:
        res["errors"].append(
            f"dimensions {w}x{h} < min {SPEC['min_w']}x{SPEC['min_h']}"
        )

    # Recommended size
    if w != SPEC["rec_w"] or h != SPEC["rec_h"]:
        if strict:
            res["errors"].append(
                f"dimensions {w}x{h} != recommended {SPEC['rec_w']}x{SPEC['rec_h']}"
            )
        else:
            res["warnings"].append(
                f"dimensions {w}x{h} != recommended {SPEC['rec_w']}x{SPEC['rec_h']} (YouTube will downscale, but 16:9 ideal)"
            )

    # Aspect ratio check (16:9 = 1.7778)
    if w > 0 and h > 0:
        ratio = w / h
        if abs(ratio - 16 / 9) > 0.01:
            msg = f"aspect ratio {ratio:.3f} is not 16:9 (1.778) — YouTube may crop or reject"
            if strict:
                res["errors"].append(msg)
            else:
                res["warnings"].append(msg)

    return res


def print_result(r: dict) -> None:
    p = r["path"]
    if not r["exists"]:
        print(f"  ✗ {p.name}  (not found)")
        return

    size = r.get("size", 0)
    w = r.get("width", "?")
    h = r.get("height", "?")
    fmt = r.get("format", "?")
    print(f"  {'✓' if not r['errors'] else '✗'} {p.name}  ({w}x{h}, {fmt}, {human_size(size)})")
    for w_msg in r["warnings"]:
        print(f"      ⚠ {w_msg}")
    for e in r["errors"]:
        print(f"      ✗ {e}")


def main():
    ap = argparse.ArgumentParser(description="Validate YouTube thumbnail files.")
    ap.add_argument("path", nargs="?", default="thumbnails",
                    help="file or folder to validate (default: thumbnails/)")
    ap.add_argument("--strict", action="store_true",
                    help="fail on dimension/aspect mismatch (not just size/format)")
    args = ap.parse_args()

    target = Path(args.path)
    if target.is_file():
        files = [target]
    elif target.is_dir():
        files = sorted(
            p for p in target.iterdir()
            if p.is_file() and p.suffix.lower() in SPEC["allowed_ext"]
        )
    else:
        print(f"  ✗ path not found: {target}")
        sys.exit(1)

    if not files:
        print(f"  (no thumbnail files in {target})")
        print("  drop your .jpg/.png here, then run again")
        return 0

    print(f"Validating {len(files)} file(s) in {target}:")
    print(f"  YouTube spec: {SPEC['rec_w']}x{SPEC['rec_h']} recommended, max {human_size(SPEC['max_bytes'])}\n")

    all_ok = True
    for f in files:
        r = check(f, strict=args.strict)
        print_result(r)
        if r["errors"]:
            all_ok = False

    print()
    if all_ok:
        print("All files OK ✓")
        return 0
    print("Some files have errors ✗ — fix them before uploading to YouTube")
    return 1


if __name__ == "__main__":
    sys.exit(main())
