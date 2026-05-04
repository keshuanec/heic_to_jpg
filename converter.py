#!/usr/bin/env python3
"""HEIC → JPG / PNG converter with a simple GUI."""

import os
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from PIL import Image
from pillow_heif import register_heif_opener

register_heif_opener()

SUPPORTED = {".heic", ".heif"}
OUTPUT_FORMATS = ["JPG", "PNG"]


def convert_files(paths: list[Path], output_dir: Path, fmt: str, quality: int,
                  progress_cb, done_cb, error_cb):
    total = len(paths)
    converted = 0
    errors = []

    for i, src in enumerate(paths):
        try:
            img = Image.open(src).convert("RGB")
            suffix = ".jpg" if fmt == "JPG" else ".png"
            dest = output_dir / (src.stem + suffix)
            save_kwargs = {"quality": quality, "optimize": True} if fmt == "JPG" else {}
            img.save(dest, **save_kwargs)
            converted += 1
        except Exception as e:
            errors.append(f"{src.name}: {e}")
        progress_cb(i + 1, total)

    done_cb(converted, errors)


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("HEIC → JPG / PNG Converter")
        self.resizable(False, False)
        self._files: list[Path] = []
        self._output_dir: Path | None = None
        self._build_ui()

    # ── UI ────────────────────────────────────────────────────────────────────

    def _build_ui(self):
        pad = {"padx": 10, "pady": 5}

        # ── Input files ───────────────────────────────────────────────────────
        frame_files = ttk.LabelFrame(self, text="Vstupní soubory")
        frame_files.pack(fill="x", **pad)

        self._lbl_files = ttk.Label(frame_files, text="Žádné soubory nevybrány", width=55)
        self._lbl_files.pack(side="left", padx=5, pady=5)

        btn_frame = ttk.Frame(frame_files)
        btn_frame.pack(side="right", padx=5, pady=5)
        ttk.Button(btn_frame, text="Vybrat soubory", command=self._pick_files).pack(side="left", padx=2)
        ttk.Button(btn_frame, text="Vybrat složku",  command=self._pick_folder).pack(side="left", padx=2)

        # ── Output dir ────────────────────────────────────────────────────────
        frame_out = ttk.LabelFrame(self, text="Výstupní složka")
        frame_out.pack(fill="x", **pad)

        self._lbl_out = ttk.Label(frame_out, text="Stejná složka jako originál", width=55)
        self._lbl_out.pack(side="left", padx=5, pady=5)
        ttk.Button(frame_out, text="Změnit", command=self._pick_output).pack(side="right", padx=5, pady=5)

        # ── Options ───────────────────────────────────────────────────────────
        frame_opts = ttk.LabelFrame(self, text="Nastavení")
        frame_opts.pack(fill="x", **pad)

        ttk.Label(frame_opts, text="Formát:").grid(row=0, column=0, padx=8, pady=5, sticky="w")
        self._fmt = tk.StringVar(value="JPG")
        fmt_menu = ttk.Combobox(frame_opts, textvariable=self._fmt, values=OUTPUT_FORMATS,
                                state="readonly", width=6)
        fmt_menu.grid(row=0, column=1, padx=4, pady=5, sticky="w")
        self._fmt.trace_add("write", lambda *_: self._on_fmt_change())

        self._quality_label = ttk.Label(frame_opts, text="Kvalita JPG: 90")
        self._quality_label.grid(row=0, column=2, padx=12, pady=5, sticky="w")
        self._quality = tk.IntVar(value=90)
        self._quality_slider = ttk.Scale(frame_opts, from_=50, to=100, orient="horizontal",
                                         variable=self._quality, length=160,
                                         command=self._on_quality)
        self._quality_slider.grid(row=0, column=3, padx=4, pady=5)

        # ── Progress ──────────────────────────────────────────────────────────
        frame_prog = ttk.Frame(self)
        frame_prog.pack(fill="x", padx=10, pady=(0, 5))

        self._progress = ttk.Progressbar(frame_prog, mode="determinate", length=400)
        self._progress.pack(side="left", fill="x", expand=True)
        self._lbl_progress = ttk.Label(frame_prog, text="0 / 0", width=10)
        self._lbl_progress.pack(side="right")

        # ── Convert button ────────────────────────────────────────────────────
        self._btn_convert = ttk.Button(self, text="Převést", command=self._start,
                                       style="Accent.TButton")
        self._btn_convert.pack(pady=(0, 10))

    # ── Event handlers ────────────────────────────────────────────────────────

    def _on_fmt_change(self):
        is_jpg = self._fmt.get() == "JPG"
        state = "normal" if is_jpg else "disabled"
        self._quality_slider.configure(state=state)
        self._quality_label.configure(text=f"Kvalita JPG: {self._quality.get()}" if is_jpg else "Kvalita PNG: –")

    def _on_quality(self, val):
        self._quality_label.configure(text=f"Kvalita JPG: {int(float(val))}")

    def _pick_files(self):
        paths = filedialog.askopenfilenames(
            title="Vyber HEIC soubory",
            filetypes=[("HEIC soubory", "*.heic *.HEIC *.heif *.HEIF"), ("Vše", "*.*")]
        )
        if paths:
            self._files = [Path(p) for p in paths]
            self._lbl_files.configure(text=f"{len(self._files)} souborů vybráno")

    def _pick_folder(self):
        folder = filedialog.askdirectory(title="Vyber složku s HEIC soubory")
        if folder:
            self._files = [p for p in Path(folder).rglob("*") if p.suffix.lower() in SUPPORTED]
            self._lbl_files.configure(text=f"{len(self._files)} souborů nalezeno ve složce")

    def _pick_output(self):
        folder = filedialog.askdirectory(title="Vyber výstupní složku")
        if folder:
            self._output_dir = Path(folder)
            self._lbl_out.configure(text=str(self._output_dir))

    def _start(self):
        if not self._files:
            messagebox.showwarning("Chyba", "Nevybral jsi žádné soubory.")
            return

        self._btn_convert.configure(state="disabled")
        self._progress["maximum"] = len(self._files)
        self._progress["value"] = 0

        def progress(done, total):
            self._progress["value"] = done
            self._lbl_progress.configure(text=f"{done} / {total}")
            self.update_idletasks()

        def done(count, errors):
            self._btn_convert.configure(state="normal")
            msg = f"Hotovo! Převedeno {count} / {len(self._files)} souborů."
            if errors:
                msg += f"\n\nChyby ({len(errors)}):\n" + "\n".join(errors[:10])
            messagebox.showinfo("Výsledek", msg)

        def error(e):
            self._btn_convert.configure(state="normal")
            messagebox.showerror("Chyba", str(e))

        def run_proper():
            total = len(self._files)
            converted = 0
            errors = []
            fmt = self._fmt.get()
            quality = self._quality.get()

            for i, src in enumerate(self._files):
                out_dir = self._output_dir or src.parent
                try:
                    img = Image.open(src).convert("RGB")
                    suffix = ".jpg" if fmt == "JPG" else ".png"
                    dest = out_dir / (src.stem + suffix)
                    save_kwargs = {"quality": quality, "optimize": True} if fmt == "JPG" else {}
                    img.save(dest, **save_kwargs)
                    converted += 1
                except Exception as e:
                    errors.append(f"{src.name}: {e}")
                progress(i + 1, total)

            done(converted, errors)

        threading.Thread(target=run_proper, daemon=True).start()


if __name__ == "__main__":
    app = App()
    app.mainloop()
