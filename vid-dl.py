#!/usr/bin/env python3
"""
Video Downloader GUI — powered by yt-dlp
"""

import json
import queue
import shutil
import subprocess
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, scrolledtext, ttk

DEFAULT_OUTPUT = Path.home() / "Desktop"

# ──────────────────────────────────────────────
# Core logic (no changes from CLI version)
# ──────────────────────────────────────────────


def check_ytdlp():
    if shutil.which("yt-dlp"):
        return
    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", "yt-dlp", "--break-system-packages"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        subprocess.run(["pipx", "install", "yt-dlp"], check=False)


def get_ffmpeg_path() -> str | None:
    """Return path to ffmpeg. Falls back to imageio-ffmpeg if not in PATH."""
    # 1) Already in PATH — use it directly
    found = shutil.which("ffmpeg")
    if found:
        return found

    # 2) imageio-ffmpeg already installed
    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        pass

    # 3) Try to install imageio-ffmpeg on the fly
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pip",
            "install",
            "imageio-ffmpeg",
            "--break-system-packages",
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        try:
            import imageio_ffmpeg

            return imageio_ffmpeg.get_ffmpeg_exe()
        except ImportError:
            pass

    return None


def get_available_formats(url: str) -> list[dict]:
    result = subprocess.run(
        [sys.executable, "-m", "yt_dlp", "--dump-json", "--quiet", url],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0 or not result.stdout.strip():
        return []
    try:
        info = json.loads(result.stdout)
    except json.JSONDecodeError:
        return []

    seen, options = set(), []
    for f in reversed(info.get("formats", [])):
        height = f.get("height")
        if not height or f.get("vcodec", "none") == "none":
            continue
        label = f"{height}p"
        if label in seen:
            continue
        seen.add(label)
        fps = f.get("fps") or ""
        size = f.get("filesize") or f.get("filesize_approx")
        options.append(
            {
                "label": label,
                "height": height,
                "fps": int(fps) if fps else None,
                "filesize": size,
            }
        )
    options.sort(key=lambda x: x["height"], reverse=True)
    # Prepend "Best available"
    options.insert(
        0,
        {
            "label": "Best available (auto)",
            "height": 99999,
            "fps": None,
            "filesize": None,
        },
    )
    return options


def build_format_selector(option: dict) -> str:
    if option["height"] == 99999:
        return "bestvideo+bestaudio/best"
    h = option["height"]
    return f"bestvideo[height={h}]+bestaudio/best[height={h}]/best"


# ──────────────────────────────────────────────
# GUI
# ──────────────────────────────────────────────

BG = "#0f0f13"
PANEL = "#17171e"
BORDER = "#2a2a38"
ACCENT = "#00d4aa"
ACCENT2 = "#7b61ff"
TEXT = "#e8e8f0"
MUTED = "#6b6b85"
DANGER = "#ff5f6d"

FONT_TITLE = ("Courier New", 22, "bold")
FONT_LABEL = ("Courier New", 10)
FONT_MONO = ("Courier New", 9)
FONT_BTN = ("Courier New", 10, "bold")


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("[ VID-DL ]")
        self.configure(bg=BG)
        self.resizable(True, True)
        self.minsize(700, 580)

        self._formats: list[dict] = []
        self._log_queue: queue.Queue = queue.Queue()
        self._downloading = False

        self._build_ui()
        self._poll_log()

    # ── Build UI ──────────────────────────────
    def _build_ui(self):
        # Top bar
        bar = tk.Frame(self, bg=ACCENT2, height=3)
        bar.pack(fill="x")

        # Title
        title_frame = tk.Frame(self, bg=BG, pady=18)
        title_frame.pack(fill="x", padx=28)
        tk.Label(
            title_frame, text="[ VID-DL ]", font=FONT_TITLE, bg=BG, fg=ACCENT
        ).pack(side="left")
        tk.Label(
            title_frame,
            text="yt-dlp powered downloader",
            font=FONT_LABEL,
            bg=BG,
            fg=MUTED,
        ).pack(side="left", padx=14, pady=6)

        # Main card
        card = tk.Frame(
            self, bg=PANEL, bd=0, highlightthickness=1, highlightbackground=BORDER
        )
        card.pack(fill="both", expand=True, padx=24, pady=(0, 10))
        card.columnconfigure(0, weight=1)

        pad = {"padx": 20, "pady": 8}

        # ── URL row ──────────────────────────
        tk.Label(
            card, text="VIDEO URL", font=FONT_LABEL, bg=PANEL, fg=MUTED, anchor="w"
        ).grid(row=0, column=0, sticky="w", **pad)

        url_row = tk.Frame(card, bg=PANEL)
        url_row.grid(row=1, column=0, sticky="ew", padx=20, pady=(0, 4))
        url_row.columnconfigure(0, weight=1)

        self.url_var = tk.StringVar()
        self.url_entry = tk.Entry(
            url_row,
            textvariable=self.url_var,
            bg="#1e1e2a",
            fg=TEXT,
            insertbackground=ACCENT,
            relief="flat",
            font=FONT_MONO,
            bd=0,
            highlightthickness=1,
            highlightbackground=BORDER,
            highlightcolor=ACCENT,
        )
        self.url_entry.grid(row=0, column=0, sticky="ew", ipady=8, padx=(0, 8))

        self.fetch_btn = self._make_button(
            url_row,
            "FETCH QUALITIES",
            self._fetch_qualities,
            color=ACCENT2,
            width=16,
        )
        self.fetch_btn.grid(row=0, column=1)

        # ── Quality selector ─────────────────
        tk.Label(
            card, text="QUALITY", font=FONT_LABEL, bg=PANEL, fg=MUTED, anchor="w"
        ).grid(row=2, column=0, sticky="w", **pad)

        quality_frame = tk.Frame(card, bg=PANEL)
        quality_frame.grid(row=3, column=0, sticky="ew", padx=20, pady=(0, 8))
        quality_frame.columnconfigure(0, weight=1)

        self.quality_var = tk.StringVar(value="Press 'Fetch Qualities' first")
        style = ttk.Style()
        style.theme_use("clam")
        style.configure(
            "Custom.TCombobox",
            fieldbackground="#1e1e2a",
            background=PANEL,
            foreground=TEXT,
            arrowcolor=ACCENT,
            selectbackground="#1e1e2a",
            selectforeground=TEXT,
            bordercolor=BORDER,
            lightcolor=BORDER,
            darkcolor=BORDER,
            font=FONT_MONO,
        )
        style.map(
            "Custom.TCombobox",
            fieldbackground=[("readonly", "#1e1e2a")],
            foreground=[("readonly", TEXT)],
        )

        self.quality_combo = ttk.Combobox(
            quality_frame,
            textvariable=self.quality_var,
            state="readonly",
            style="Custom.TCombobox",
            font=FONT_MONO,
        )
        self.quality_combo.grid(row=0, column=0, sticky="ew", ipady=5)

        # ── Output dir ───────────────────────
        tk.Label(
            card, text="OUTPUT FOLDER", font=FONT_LABEL, bg=PANEL, fg=MUTED, anchor="w"
        ).grid(row=4, column=0, sticky="w", **pad)

        dir_row = tk.Frame(card, bg=PANEL)
        dir_row.grid(row=5, column=0, sticky="ew", padx=20, pady=(0, 8))
        dir_row.columnconfigure(0, weight=1)

        self.dir_var = tk.StringVar(value=DEFAULT_OUTPUT)
        dir_entry = tk.Entry(
            dir_row,
            textvariable=self.dir_var,
            bg="#1e1e2a",
            fg=TEXT,
            insertbackground=ACCENT,
            relief="flat",
            font=FONT_MONO,
            bd=0,
            highlightthickness=1,
            highlightbackground=BORDER,
            highlightcolor=ACCENT,
        )
        dir_entry.grid(row=0, column=0, sticky="ew", ipady=8, padx=(0, 8))

        self._make_button(
            dir_row, "BROWSE", self._browse_dir, color=MUTED, width=10
        ).grid(row=0, column=1)

        # ── Download button ───────────────────
        sep = tk.Frame(card, bg=BORDER, height=1)
        sep.grid(row=6, column=0, sticky="ew", padx=20, pady=10)

        self.dl_btn = self._make_button(
            card,
            "⬇  DOWNLOAD",
            self._start_download,
            color=ACCENT,
            width=18,
            big=True,
        )
        self.dl_btn.grid(row=7, column=0, padx=20, pady=(0, 14), sticky="ew")

        # ── Log ──────────────────────────────
        tk.Label(
            card, text="LOG", font=FONT_LABEL, bg=PANEL, fg=MUTED, anchor="w"
        ).grid(row=8, column=0, sticky="w", padx=20)

        self.log = scrolledtext.ScrolledText(
            card,
            height=10,
            bg="#0a0a10",
            fg="#7be0c8",
            font=FONT_MONO,
            relief="flat",
            bd=0,
            insertbackground=ACCENT,
            wrap="word",
            highlightthickness=1,
            highlightbackground=BORDER,
        )
        self.log.grid(row=9, column=0, sticky="ew", padx=20, pady=(4, 20))
        self.log.config(state="disabled")

        # Bottom accent
        bot = tk.Frame(self, bg=ACCENT, height=2)
        bot.pack(fill="x", side="bottom")

    def _make_button(self, parent, text, command, color=ACCENT, width=None, big=False):
        f = tk.Frame(parent, bg=color, padx=1, pady=1)
        font = ("Courier New", 11, "bold") if big else FONT_BTN
        btn = tk.Button(
            f,
            text=text,
            command=command,
            bg=PANEL,
            fg=color,
            activebackground=color,
            activeforeground=BG,
            relief="flat",
            font=font,
            cursor="hand2",
            bd=0,
            padx=14,
            pady=8 if big else 6,
        )
        if width:
            btn.config(width=width)
        btn.pack()

        def on_enter(_):
            btn.config(bg=color, fg=BG)

        def on_leave(_):
            btn.config(bg=PANEL, fg=color)

        btn.bind("<Enter>", on_enter)
        btn.bind("<Leave>", on_leave)

        # store inner btn for state changes
        f._inner_btn = btn
        return f

    # ── Actions ───────────────────────────────
    def _browse_dir(self):
        d = filedialog.askdirectory(initialdir=self.dir_var.get() or "/")
        if d:
            self.dir_var.set(d)

    def _fetch_qualities(self):
        url = self.url_var.get().strip()
        if not url:
            self._log("⚠  Please enter a URL first.\n")
            return
        self._log(f"→ Fetching formats for:\n  {url}\n")
        self.fetch_btn._inner_btn.config(state="disabled", text="FETCHING…")

        def worker():
            check_ytdlp()
            formats = get_available_formats(url)
            self._log_queue.put(("formats", formats))

        threading.Thread(target=worker, daemon=True).start()

    def _start_download(self):
        if self._downloading:
            return
        url = self.url_var.get().strip()
        if not url:
            self._log("⚠  Please enter a URL.\n")
            return
        if not self._formats:
            self._log("⚠  Fetch qualities first.\n")
            return

        sel = self.quality_var.get()
        opt = next(
            (f for f in self._formats if self._format_display(f) == sel),
            self._formats[0],
        )
        fmt = build_format_selector(opt)
        out_dir = self.dir_var.get().strip() or DEFAULT_OUTPUT

        self._log(f"\n▶ Downloading  [{sel}]\n  {url}\n  → {out_dir}\n")
        self._downloading = True
        self.dl_btn._inner_btn.config(state="disabled", text="DOWNLOADING…")

        def worker():
            check_ytdlp()
            ffmpeg = get_ffmpeg_path()
            if ffmpeg:
                self._log_queue.put(("log", f"  ffmpeg → {ffmpeg}\n"))
            else:
                self._log_queue.put(
                    ("log", "⚠  ffmpeg not found — streams may not merge.\n")
                )

            cmd = [
                sys.executable,
                "-m",
                "yt_dlp",
                "--output",
                f"{out_dir}/%(title)s.%(ext)s",
                "--format",
                fmt,
                "--merge-output-format",
                "mp4",
                "--add-header",
                "User-Agent:Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "--write-sub",
                "--sub-lang",
                "ca,es",
                "--newline",
                url,
            ]
            if ffmpeg:
                cmd += ["--ffmpeg-location", ffmpeg]

            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            for line in proc.stdout:
                self._log_queue.put(("log", line))
            proc.wait()
            ok = proc.returncode == 0
            self._log_queue.put(("done", ok))

        threading.Thread(target=worker, daemon=True).start()

    # ── Helpers ───────────────────────────────
    def _format_display(self, opt: dict) -> str:
        if opt["height"] == 99999:
            return opt["label"]
        fps = f" @ {opt['fps']}fps" if opt.get("fps") else ""
        size = (
            f"  (~{opt['filesize'] / 1024 / 1024:.0f} MB)"
            if opt.get("filesize")
            else ""
        )
        return f"{opt['label']}{fps}{size}"

    def _log(self, msg: str):
        self.log.config(state="normal")
        self.log.insert("end", msg)
        self.log.see("end")
        self.log.config(state="disabled")

    def _poll_log(self):
        try:
            while True:
                kind, data = self._log_queue.get_nowait()
                if kind == "log":
                    self._log(data)
                elif kind == "formats":
                    self._formats = data
                    if data:
                        labels = [self._format_display(f) for f in data]
                        self.quality_combo["values"] = labels
                        self.quality_combo.current(0)
                        self._log(f"✔ Found {len(data) - 1} resolution(s).\n")
                    else:
                        self._log("✖ Could not retrieve formats.\n")
                    self.fetch_btn._inner_btn.config(
                        state="normal", text="FETCH QUALITIES"
                    )
                elif kind == "done":
                    if data:
                        self._log("\n✔ Download complete!\n")
                    else:
                        self._log("\n✖ Download failed.\n")
                    self._downloading = False
                    self.dl_btn._inner_btn.config(state="normal", text="⬇  DOWNLOAD")
        except queue.Empty:
            pass
        self.after(100, self._poll_log)


if __name__ == "__main__":
    app = App()
    app.mainloop()
