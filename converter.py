#!/usr/bin/env python3
"""HEIC → JPG / PNG converter with a simple GUI and drag & drop support."""

import re
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from PIL import Image
from pillow_heif import register_heif_opener
from tkinterdnd2 import DND_FILES, TkinterDnD

register_heif_opener()

SUPPORTED = {".heic", ".heif"}
OUTPUT_FORMATS = ["JPG", "PNG"]


def _parse_dnd_paths(raw: str) -> list[Path]:
    """Parse the tkdnd path string: handles {path with spaces} and plain paths."""
    paths = []
    for token in re.findall(r"\{([^}]+)\}|(\S+)", raw):
        p = Path(token[0] or token[1])
        if p.is_dir():
            paths.extend(f for f in p.rglob("*") if f.suffix.lower() in SUPPORTED)
        elif p.suffix.lower() in SUPPORTED:
            paths.append(p)
    return paths


class App(TkinterDnD.Tk):
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

        # ── Drop zone ─────────────────────────────────────────────────────────
        self._drop_frame = tk.Frame(
            self, bg="#e8f4fd", relief="dashed", bd=2,
            highlightbackground="#2980b9", highlightthickness=2,
        )
        self._drop_frame.pack(fill="x", padx=10, pady=(10, 4))

        self._lbl_drop = tk.Label(
            self._drop_frame,
            text="Přetáhni sem HEIC soubory nebo složku",
            bg="#e8f4fd", fg="#2980b9",
            font=("Helvetica", 13), pady=18,
        )
        self._lbl_drop.pack(fill="x")

        for widget in (self._drop_frame, self._lbl_drop):
            widget.drop_target_register(DND_FILES)
            widget.dnd_bind("<<Drop>>",        self._on_drop)
            widget.dnd_bind("<<DragEnter>>",   self._on_drag_enter)
            widget.dnd_bind("<<DragLeave>>",   self._on_drag_leave)

        # ── File status + pick buttons ────────────────────────────────────────
        frame_files = ttk.LabelFrame(self, text="Vybrané soubory")
        frame_files.pack(fill="x", **pad)

        self._lbl_files = ttk.Label(frame_files, text="Žádné soubory nevybrány", width=45)
        self._lbl_files.pack(side="left", padx=5, pady=5)

        btn_frame = ttk.Frame(frame_files)
        btn_frame.pack(side="right", padx=5, pady=5)
        ttk.Button(btn_frame, text="Vybrat soubory", command=self._pick_files).pack(side="left", padx=2)
        ttk.Button(btn_frame, text="Vybrat složku",  command=self._pick_folder).pack(side="left", padx=2)
        ttk.Button(btn_frame, text="Vymazat",        command=self._clear_files).pack(side="left", padx=2)

        # ── Output dir ────────────────────────────────────────────────────────
        frame_out = ttk.LabelFrame(self, text="Výstupní složka")
        frame_out.pack(fill="x", **pad)

        self._lbl_out = ttk.Label(frame_out, text="Stejná složka jako originál", width=45)
        self._lbl_out.pack(side="left", padx=5, pady=5)
        ttk.Button(frame_out, text="Změnit", command=self._pick_output).pack(side="right", padx=5, pady=5)

        # ── Options ───────────────────────────────────────────────────────────
        frame_opts = ttk.LabelFrame(self, text="Nastavení")
        frame_opts.pack(fill="x", **pad)

        ttk.Label(frame_opts, text="Formát:").grid(row=0, column=0, padx=8, pady=5, sticky="w")
        self._fmt = tk.StringVar(value="JPG")
        ttk.Combobox(frame_opts, textvariable=self._fmt, values=OUTPUT_FORMATS,
                     state="readonly", width=6).grid(row=0, column=1, padx=4, pady=5, sticky="w")
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
        self._btn_convert = ttk.Button(self, text="Převést", command=self._start)
        self._btn_convert.pack(pady=(0, 10))

    # ── Drag & drop ───────────────────────────────────────────────────────────

    def _on_drag_enter(self, event):
        self._drop_frame.configure(bg="#cce8f9")
        self._lbl_drop.configure(bg="#cce8f9")

    def _on_drag_leave(self, event):
        self._drop_frame.configure(bg="#e8f4fd")
        self._lbl_drop.configure(bg="#e8f4fd")

    def _on_drop(self, event):
        self._on_drag_leave(event)
        new = _parse_dnd_paths(event.data)
        if not new:
            messagebox.showwarning("Žádné HEIC soubory", "Přetažené položky neobsahují žádné HEIC soubory.")
            return
        self._files.extend(new)
        self._update_file_label()

    # ── Event handlers ────────────────────────────────────────────────────────

    def _on_fmt_change(self):
        is_jpg = self._fmt.get() == "JPG"
        self._quality_slider.configure(state="normal" if is_jpg else "disabled")
        self._quality_label.configure(
            text=f"Kvalita JPG: {self._quality.get()}" if is_jpg else "Kvalita PNG: –"
        )

    def _on_quality(self, val):
        self._quality_label.configure(text=f"Kvalita JPG: {int(float(val))}")

    def _update_file_label(self):
        n = len(self._files)
        self._lbl_files.configure(text=f"{n} {'soubor' if n == 1 else 'souborů'} vybráno")

    def _pick_files(self):
        paths = filedialog.askopenfilenames(
            title="Vyber HEIC soubory",
            filetypes=[("HEIC soubory", "*.heic *.HEIC *.heif *.HEIF"), ("Vše", "*.*")]
        )
        if paths:
            self._files = [Path(p) for p in paths]
            self._update_file_label()

    def _pick_folder(self):
        folder = filedialog.askdirectory(title="Vyber složku s HEIC soubory")
        if folder:
            self._files = [p for p in Path(folder).rglob("*") if p.suffix.lower() in SUPPORTED]
            self._update_file_label()

    def _clear_files(self):
        self._files = []
        self._lbl_files.configure(text="Žádné soubory nevybrány")
        self._progress["value"] = 0
        self._lbl_progress.configure(text="0 / 0")

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
        total_count = len(self._files)

        def progress(done, total):
            self._progress["value"] = done
            self._lbl_progress.configure(text=f"{done} / {total}")
            self.update_idletasks()

        def done(count, errors):
            self._btn_convert.configure(state="normal")
            msg = f"Hotovo! Převedeno {count} / {total_count} souborů."
            if errors:
                msg += f"\n\nChyby ({len(errors)}):\n" + "\n".join(errors[:10])
            messagebox.showinfo("Výsledek", msg)

        fmt = self._fmt.get()
        quality = self._quality.get()
        files = list(self._files)
        output_dir = self._output_dir

        def run():
            converted, errors = 0, []
            for i, src in enumerate(files):
                out_dir = output_dir or src.parent
                try:
                    img = Image.open(src).convert("RGB")
                    suffix = ".jpg" if fmt == "JPG" else ".png"
                    save_kwargs = {"quality": quality, "optimize": True} if fmt == "JPG" else {}
                    img.save(out_dir / (src.stem + suffix), **save_kwargs)
                    converted += 1
                except Exception as e:
                    errors.append(f"{src.name}: {e}")
                progress(i + 1, len(files))
            done(converted, errors)

        threading.Thread(target=run, daemon=True).start()


if __name__ == "__main__":
    app = App()
    app.mainloop()
