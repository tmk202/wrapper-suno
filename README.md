# Suno Focus Music — auto generator

Tool nhỏ tạo nhạc Focus / lo-fi / chill hàng loạt, tự tải về folder, đặt tên theo ngày + preset.

Hai backend:
- **`--backend api`** — gọi Suno HTTP API (cần `SUNO_API_KEY` trong `.env`, vài trăm MB RAM)
- **`--backend browser`** — điều khiển suno.com bằng Playwright (login 1 lần, cookie lưu lại, ~200 MB)

Sau khi generate xong có thể merge tất cả thành 1 file bằng `merge.py`. Thumbnail YouTube bạn tự upload vào `thumbnails/` rồi dùng `validate_thumbnail.py` kiểm tra spec.

## ⚠️ Về plan Suno của bạn

Khảo sát tài khoản hiện tại (chrome-devtools snapshot, 2026-06-24):
- **Plan: Free** (có nút "Upgrade to Pro")
- **Credits: 30** (mỗi lượt generate = 2 tracks, hết 2 credit/lần)
- **Còn ~15 lần generate** trước khi phải nạp hoặc chờ reset

Nếu bạn đang ở Pro/Premier thì bỏ qua cảnh báo này.

## 1. Setup chung (1 lần)

```bash
cd ~/Documents/nnt/CODE/suno-focus-music
python3 -m venv .venv
source .venv/bin/activate
```

## 2. Chọn backend

### A. API backend (cần key + plan có API access)

```bash
pip install -r requirements.txt
cp .env.example .env
# mở .env, paste SUNO_API_KEY
```

**Suno chính hãng KHÔNG có public API mở** (đã test: `https://api.suno.ai` trả 503 cho mọi request). Nguồn key khả thi:
- Wrapper bên thứ 3: **sunoapi.org**, **piapi.ai**, **kie.ai** — đăng ký gói nhỏ (~5-10 USD), lấy key từ dashboard, đổi `SUNO_API_BASE` trong `.env` cho đúng.

```bash
python generate.py --check
python generate.py --backend api --preset deep_focus --count 3
```

### B. Browser backend (dùng account Suno có sẵn — khuyến nghị cho bạn)

```bash
pip install -r requirements-browser.txt
playwright install chromium
```

**Lần chạy đầu tiên** mở 1 cửa sổ browser (headed, không ẩn). Bạn đăng nhập Suno bình thường. Sau khi vào được `/create`, script tự lưu cookies vào `suno_cookies.json` rồi chạy tiếp. Từ lần sau hoàn toàn tự động.

```bash
python generate.py --backend browser --preset deep_focus --count 2
# thêm --no-headless nếu muốn xem browser chạy
```

**Script sẽ tự động:**
1. Vào `https://suno.com/create`
2. Click tab **Advanced** (không phải Simple)
3. Chọn radio **Instrumental** (trong nhóm Lyrics)
4. Paste style prompt vào ô **Styles** (counter 0/1000)
5. (Tuỳ chọn) điền **Song Title**
6. Click **Create song** — trừ 2 credit, tạo 2 tracks
7. Đợi 2 clip mới xuất hiện ở panel bên phải
8. Click **More options** → **Download** trên từng clip, lưu file `.mp3` về folder `output/YYYY-MM-DD/`

## 3. Preset có sẵn

```bash
python generate.py --list
```

| Preset | Vibe |
|---|---|
| `deep_focus` | lo-fi hip hop + piano, 70 BPM |
| `calm_piano` | ambient piano không drums, 60 BPM |
| `coffee_shop` | soft jazz acoustic, 90 BPM |
| `chill_beats` | chillhop boom bap, 85 BPM |
| `nature_ambient` | pad + mưa nhẹ, 55 BPM |
| `minimal_techno` | deep work loop, 120 BPM |

Thêm preset mới: mở `presets.py`, copy 1 block rồi sửa `style` / `bpm` / `duration`.

## 4. Generate

```bash
# Browser backend (khuyến nghị)
python generate.py --backend browser --preset deep_focus     --count 2
python generate.py --backend browser --preset calm_piano     --count 3 --mood "late night coding"
python generate.py --backend browser --preset nature_ambient --count 2 --no-headless

# API backend (nếu có key)
python generate.py --backend api --preset deep_focus --count 5
```

File rơi vào `./output/YYYY-MM-DD/<preset>_<index>_<title>.mp3` (hoặc `.wav` tuỳ Suno trả về).

## 5. Tuỳ chỉnh style

Mở `presets.py`, sửa `style` của preset. Style prompt là text tự nhiên, Suno sẽ hiểu:

| Bạn muốn | Thêm vào style |
|---|---|
| Lo-fi hơn | `lo-fi, vinyl crackle, tape hiss, warm saturation` |
| Không vocal | `instrumental, no vocals` |
| Piano là chính | `piano-led, sparse drums, soft pad` |
| Có mưa / nature | `rain ambience, distant thunder, no drums` |
| Năng lượng hơn | `upbeat drums, bright synth, 100 BPM` |
| Tối / cinematic | `dark ambient, low pad, cinematic, reverb heavy` |

## 6. Lỗi thường gặp

**Browser backend:**
- `playwright is not installed` → `pip install -r requirements-browser.txt && playwright install chromium`
- `Create song button stayed disabled` → form không hợp lệ (style prompt rỗng, hoặc Suno chặn IP). Check `suno_debug.png`.
- `no new clips appeared` → generation fail. Check `suno_debug.png` + thử `--no-headless` để xem trực tiếp.
- Cookie hết hạn → xoá `suno_cookies.json`, chạy lại, đăng nhập lại.
- Hết credits → upgrade plan hoặc đợi reset (free plan reset hàng tháng).

**API backend:**
- `SUNO_API_KEY missing` → paste key vào `.env`.
- `submit failed 401` → key sai / hết hạn.
- `submit failed 402` → hết credit.
- `could not find audio url in response` → wrapper API version khác, sửa parser trong `generate.py`.

## 7. Mở rộng (khi cần)

- **Auto chạy mỗi sáng** → set cron: `0 7 * * * cd /path/to/suno-focus-music && .venv/bin/python generate.py --backend browser --preset deep_focus --count 2`
- **Upload thẳng lên YouTube** → thêm bước YouTube Data API sau khi download.
- **Bỏ browser, dùng API thật của Suno** → base URL là `https://studio-api-prod.suno.com`, auth bằng `browser-token` header + `authorization: Bearer <clerk JWT>`. Có thể bắt từ network log khi đăng nhập web (mình đã verify qua DevTools). Viết wrapper riêng nếu bạn muốn đi sâu hướng này.

## 8. Thumbnail YouTube

Tool **không tự generate thumbnail** — đó là lựa chọn sáng tạo của bạn. Workflow:

1. **Thiết kế thumbnail** trong Canva/Photoshop/Figma (1280×720, 16:9, JPG/PNG, < 2 MB)
2. **Drop file vào `thumbnails/`**
3. **Validate:**
   ```bash
   python validate_thumbnail.py
   python validate_thumbnail.py thumbnails/your.jpg --strict
   ```
4. **Upload lên YouTube** khi publish video (YouTube Studio → Custom thumbnail)

Xem chi tiết trong [`thumbnails/README.md`](thumbnails/README.md).

## 9. Tổ chức video (1 video = 1 folder)

Mỗi video YouTube = 1 folder tự chứu trong `videos/`:

```
videos/v01/
├── audio.mp3         # nhạc nền (copy từ output/...)
├── thumbnail.jpg     # bạn upload bằng tay
└── notes.md          # title, description, tags, publish checklist
```

### Tự động tạo folder mới khi generate

Sau khi `generate.py` merge xong, `setup_videos.py` tự chạy:
- Tìm MP3 mới trong `output/YYYY-MM-DD/` chưa có folder
- Tạo `videos/v{NN}/{audio.mp3, notes.md}` (idempotent — chạy nhiều lần OK)
- Skip file preview (`*v55preview*`) và file đã có folder (theo content hash)

**Manual run:**
```bash
python setup_videos.py                              # today's output
python setup_videos.py output/2026-06-24            # specific date
python setup_videos.py --dry                        # preview only
```

Xem chi tiết trong [`videos/README.md`](videos/README.md).

## 10. Ghi chú kỹ thuật (từ session khảo sát)

Khảo sát UI thật bằng Chrome DevTools MCP (2026-06-24), selectors trong `suno_browser.py` map từ accessibility tree:

| Phần tử | Selector |
|---|---|
| Tab Advanced | `get_by_role("tab", name=re.compile("^Advanced$"))` |
| Radio Instrumental | `get_by_role("radio", name=re.compile("^Instrumental$"))` |
| Textarea Styles | tìm textarea có `/1000` trong vùng cha |
| Textbox Song Title | `get_by_role("textbox", name=re.compile("Song Title"))` |
| Button Create song | `get_by_role("button", name=re.compile("^Create song$"))` |
| Button More options (per clip) | `button:has-text('More options')` |
| Button Download (trong menu) | `get_by_role("button", name=re.compile("^Download$"))` |

Nếu Suno update UI, thay đổi chỉ tập trung ở các helper này — flow tổng thể giữ nguyên.
