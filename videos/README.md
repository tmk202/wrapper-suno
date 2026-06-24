# Videos

Each video = 1 self-contained folder. Drop your thumbnail in, edit `notes.md`, upload to YouTube.

## Structure

```
videos/
├── v01/
│   ├── audio.mp3         # the music for this video
│   ├── thumbnail.jpg     # YOU upload this (1280x720, <2MB)
│   └── notes.md          # title, description, tags, publishing checklist
├── v02/
│   ├── audio.mp3
│   ├── thumbnail.jpg     # (upload by hand)
│   └── notes.md
├── v03/ ... v04/ v05/    # same pattern
└── README.md
```

## Why this layout

- **1 video = 1 folder** → dễ di chuyển, share, backup
- **Audio + thumbnail + notes cùng chỗ** → không phải nhớ "file này đi với file kia"
- **ID theo thứ tự** (v01, v02, ...) → sort tự nhiên, dễ mở rộng

## Workflow cho mỗi video

1. **Mở `vXX/notes.md`** → sửa title, description, tags (gợi ý có sẵn)
2. **Drop `thumbnail.jpg`** vào `vXX/` (hoặc `.png`)
3. **Validate thumbnail:**
   ```bash
   python validate_thumbnail.py videos/v01
   ```
4. **Mở YouTube Studio** → upload video + chọn custom thumbnail
5. **Tick checklist trong `notes.md`** (ngày publish, URL)

## Nếu muốn thêm video mới

Tạo folder mới theo pattern:
```bash
mkdir videos/v06
cp /path/to/new-audio.mp3 videos/v06/audio.mp3
cp notes.template.md videos/v06/notes.md   # copy từ v01 rồi sửa
```

## Nếu bạn muốn dùng 1 audio cho nhiều video

Copy `audio.mp3` vào nhiều folder:
```bash
cp videos/v01/audio.mp3 videos/v06/audio.mp3
```
(Sẽ tốn disk nhưng mỗi video độc lập, dễ sửa thumbnail cho từng variant.)

## Skipped audio files

Có 4 file MP3 trong `output/2026-06-24/` **chưa được map vào video**:
- `deep_focus_01_v4_2m12s.mp3` (2:12, lo-fi, short)
- `deep_focus_02_v4_2m19s.mp3` (2:18, lo-fi, short)
- `deep_focus_03_v55preview_1m.mp3` (1:00, preview only — cần Pro để mở full)
- `deep_focus_04_v55preview_1m.mp3` (1:00, preview only)

Muốn dùng thì tạo `v06/`, `v07/`, ... và copy vào.
