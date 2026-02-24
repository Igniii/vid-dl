# [ VID-DL ]

> A sleek, yt-dlp powered video downloader with a dark GUI — no command line required.

![Python](https://img.shields.io/badge/Python-3.10%2B-00d4aa?style=flat-square&logo=python&logoColor=white)
![yt-dlp](https://img.shields.io/badge/powered%20by-yt--dlp-7b61ff?style=flat-square)
![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-6b6b85?style=flat-square)
![License](https://img.shields.io/badge/license-MIT-00d4aa?style=flat-square)

---

## Features

- **Fetch available qualities** — lists all resolutions for any video URL before downloading
- **Quality selector** — choose from `Best available (auto)` down to the lowest resolution
- **Automatic dependency handling** — installs `yt-dlp` and `imageio-ffmpeg` on the fly if not found
- **FFmpeg auto-detection** — merges video + audio streams automatically
- **Subtitle download** — fetches `ca` and `es` subtitles when available
- **Output folder picker** — defaults to your Desktop, fully customizable
- **Live log panel** — real-time download progress streamed directly in the UI
- **Cross-platform** — works on Windows, macOS, and Linux

---

## Screenshot

```
┌─────────────────────────────────────────────┐
│  [ VID-DL ]   yt-dlp powered downloader     │
│                                             │
│  VIDEO URL                                  │
│  [ https://...                 ] [FETCH]    │
│                                             │
│  QUALITY                                    │
│  [ Best available (auto)      ▾]            │
│                                             │
│  OUTPUT FOLDER                              │
│  [ C:\Users\...\Desktop       ] [BROWSE]    │
│                                             │
│  ─────────────────────────────────────────  │
│         [ ⬇  DOWNLOAD ]                    │
│                                             │
│  LOG                                        │
│  ▶ Downloading  [1080p]                     │
│  [download]  42.3% of 128.50MiB            │
└─────────────────────────────────────────────┘
```

---

## Requirements

- Python **3.10+**
- `tkinter` (included with standard Python on Windows/macOS; on Linux: `sudo apt install python3-tk`)
- `yt-dlp` — installed automatically if missing
- `ffmpeg` — used for merging streams; falls back to `imageio-ffmpeg` if not in PATH

---

## Installation

```bash
# Clone the repo
git clone https://github.com/Igniii/vid-dl.git
cd vid-dl

# Run directly — no pip install needed
python main.py
```

> `yt-dlp` will be installed automatically on first run if it's not already available.

---

## Usage

1. **Paste a video URL** into the URL field (YouTube, Twitter/X, Instagram, and [many more](https://github.com/yt-dlp/yt-dlp/blob/master/supportedsites.md))
2. Click **FETCH QUALITIES** to retrieve available resolutions
3. Select your desired quality from the dropdown
4. Choose an **output folder** (defaults to your Desktop)
5. Click **⬇ DOWNLOAD** and watch the log

---

## How it Works

| Step | What happens |
|---|---|
| Fetch | Runs `yt-dlp --dump-json` to retrieve all available formats |
| Quality | Builds a `yt-dlp` format selector like `bestvideo[height=1080]+bestaudio` |
| Download | Spawns a `yt-dlp` subprocess and streams stdout to the log panel |
| Merge | Uses `ffmpeg` (or `imageio-ffmpeg`) to merge video and audio into `.mp4` |

---

## Project Structure

```
vid-dl/
└── main.py       # Everything — GUI + download logic in a single file
```

---

## Contributing

Pull requests are welcome. For major changes, please open an issue first to discuss what you'd like to change.

---

## License

[MIT](LICENSE)

---

<p align="center">
  Built with <a href="https://github.com/yt-dlp/yt-dlp">yt-dlp</a> + Python tkinter
</p>
