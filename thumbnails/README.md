# Thumbnails

This folder is for **your custom YouTube thumbnails** that you upload by hand.

The AI wrapper doesn't generate thumbnails for you — those are a personal/creative
choice and you know your channel aesthetic better than any model.

## YouTube custom thumbnail spec (verified 2025)

| Property | Recommended | Min | Max |
|---|---|---|---|
| Dimensions | **1280 × 720** (16:9) | 640 × 360 | (anything 16:9; YouTube downscales) |
| File size | < 500 KB (recommended) | — | **2 MB** (hard limit) |
| Format | JPG or PNG | — | JPG, JPEG, PNG, GIF |
| Aspect ratio | 16:9 (1.778) | — | (other ratios get cropped or rejected) |

## How to use

1. **Design your thumbnail** in your tool of choice (Canva, Photoshop, Figma…).
   Aim for: bold readable text, high contrast, one clear focal point, your channel branding.
2. **Export as JPG or PNG**, 1280 × 720, keep file under 2 MB.
3. **Drop the file here** in `thumbnails/`.
4. **Validate before upload:**
   ```bash
   python validate_thumbnail.py
   ```
   It will check dimensions, file size, format, and aspect ratio.
5. **Upload to YouTube** when you publish the video (YouTube Studio → video → "Custom thumbnail" → upload).

## Naming convention (suggested)

Use a prefix that matches your merged audio file, so you can pair them:
```
thumbnails/2026-06-24_deep-focus.jpg   ← pairs with output/2026-06-24/merged.mp3
thumbnails/2026-06-25_piano-vibes.png
```

Or just `thumbnail.jpg` if you reuse the same one across videos.

## Validate a single file

```bash
python validate_thumbnail.py thumbnails/my-thumb.jpg
python validate_thumbnail.py thumbnails/my-thumb.jpg --strict
# --strict also fails on aspect ratio / recommended size mismatch
```

## What the validator does

- ✅ Format (.jpg/.jpeg/.png/.gif only)
- ✅ File size (≤ 2 MB)
- ✅ Min dimensions (≥ 640 × 360)
- ✅ Recommended dimensions (1280 × 720, warn-only by default)
- ✅ Aspect ratio = 16:9 (warn-only by default, --strict to enforce)
