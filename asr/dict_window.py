"""Dictionary window for word registration (tkinter Toplevel)."""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox
from typing import Callable

from .biasing import WordRegistry


class DictWindow:
    """Toplevel window for managing bias words."""

    def __init__(
        self,
        parent: tk.Tk,
        registry: WordRegistry,
        reload_cb: Callable[[], None] | None = None,
        oov_queue=None,
    ):
        self.win = tk.Toplevel(parent)
        self.win.title("単語登録 - asrivia")
        self.win.geometry("520x560")
        self.registry = registry
        self.reload_cb = reload_cb
        self.oov_queue = oov_queue  # queue.Queue of list[str]
        self._build_ui()
        self._refresh_list()
        if self.oov_queue:
            self._poll_oov()

    def _build_ui(self):
        # --- Input section ---
        input_frame = tk.LabelFrame(self.win, text="単語を追加", padx=10, pady=5)
        input_frame.pack(fill=tk.X, padx=10, pady=(10, 5))

        tk.Label(input_frame, text="登録する単語:").grid(row=0, column=0, sticky=tk.W)
        self.entry = tk.Entry(input_frame, width=30)
        self.entry.grid(row=0, column=1, padx=5)
        add_btn = tk.Button(input_frame, text="+ 追加", command=self._on_add)
        add_btn.grid(row=0, column=2, padx=5)

        tk.Label(input_frame, text="boost:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.boost_var = tk.DoubleVar(value=2.0)
        boost_frame = tk.Frame(input_frame)
        boost_frame.grid(row=1, column=1, columnspan=2, sticky=tk.W)
        self.boost_scale = tk.Scale(
            boost_frame, variable=self.boost_var,
            from_=0.5, to=5.0, resolution=0.5,
            orient=tk.HORIZONTAL, length=200,
        )
        self.boost_scale.pack(side=tk.LEFT)

        tk.Label(input_frame, text="メモ（任意）:").grid(row=2, column=0, sticky=tk.W)
        self.note_entry = tk.Entry(input_frame, width=30)
        self.note_entry.grid(row=2, column=1, padx=5, pady=5)

        # --- Word list section ---
        list_frame = tk.LabelFrame(self.win, text="登録済み単語", padx=10, pady=5)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # Scrollable frame
        canvas = tk.Canvas(list_frame, height=200)
        scrollbar = tk.Scrollbar(list_frame, orient=tk.VERTICAL, command=canvas.yview)
        self.list_inner = tk.Frame(canvas)
        self.list_inner.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")),
        )
        canvas.create_window((0, 0), window=self.list_inner, anchor=tk.NW)
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # --- OOV suggestion section ---
        self.oov_frame = tk.LabelFrame(
            self.win, text="登録候補（認識に自信がなかった箇所）", padx=10, pady=5
        )
        self.oov_frame.pack(fill=tk.X, padx=10, pady=(5, 10))
        self.oov_inner = tk.Frame(self.oov_frame)
        self.oov_inner.pack(fill=tk.X)

    def _on_add(self):
        word = self.entry.get().strip()
        boost = self.boost_var.get()
        note = self.note_entry.get().strip()
        if not word:
            return
        self.registry.add(word, boost, note)
        if self.reload_cb:
            self.reload_cb()
        self.entry.delete(0, tk.END)
        self.note_entry.delete(0, tk.END)
        self.boost_var.set(2.0)
        self._refresh_list()

    def _refresh_list(self):
        for widget in self.list_inner.winfo_children():
            widget.destroy()

        for bw in self.registry.all():
            row = tk.Frame(self.list_inner)
            row.pack(fill=tk.X, pady=2)

            # Word label (truncate long words)
            display = bw.word if len(bw.word) <= 16 else bw.word[:14] + "…"
            tk.Label(row, text=display, width=18, anchor=tk.W).pack(side=tk.LEFT)
            tk.Label(row, text=f"boost: {bw.boost:.1f}", width=10).pack(side=tk.LEFT)

            edit_btn = tk.Button(
                row, text="編集",
                command=lambda w=bw.word: self._on_edit(w),
            )
            edit_btn.pack(side=tk.LEFT, padx=2)

            del_btn = tk.Button(
                row, text="削除",
                command=lambda w=bw.word: self._on_delete(w),
            )
            del_btn.pack(side=tk.LEFT, padx=2)

            if bw.note:
                tk.Label(row, text=bw.note, fg="gray").pack(side=tk.LEFT, padx=5)

    def _on_delete(self, word: str):
        self.registry.remove(word)
        if self.reload_cb:
            self.reload_cb()
        self._refresh_list()

    def _on_edit(self, word: str):
        """Open a simple dialog to edit boost value."""
        bw = self.registry.get(word)
        if not bw:
            return

        dialog = tk.Toplevel(self.win)
        dialog.title(f"編集: {word}")
        dialog.geometry("300x150")

        tk.Label(dialog, text=f"単語: {word}").pack(pady=5)
        tk.Label(dialog, text="boost:").pack()
        boost_var = tk.DoubleVar(value=bw.boost)
        scale = tk.Scale(
            dialog, variable=boost_var,
            from_=0.5, to=5.0, resolution=0.5,
            orient=tk.HORIZONTAL, length=200,
        )
        scale.pack()

        def apply():
            self.registry.update_boost(word, boost_var.get())
            if self.reload_cb:
                self.reload_cb()
            self._refresh_list()
            dialog.destroy()

        tk.Button(dialog, text="適用", command=apply).pack(pady=10)

    def _poll_oov(self):
        """Poll OOV candidate queue and display suggestions."""
        if self.oov_queue:
            try:
                while True:
                    candidates = self.oov_queue.get_nowait()
                    self._show_oov_candidates(candidates)
            except Exception:
                pass
        if self.win.winfo_exists():
            self.win.after(1000, self._poll_oov)

    def _show_oov_candidates(self, candidates: list[str]):
        for widget in self.oov_inner.winfo_children():
            widget.destroy()

        for word in candidates:
            if word in self.registry:
                continue
            row = tk.Frame(self.oov_inner)
            row.pack(fill=tk.X, pady=1)
            tk.Label(row, text=f"「{word}」").pack(side=tk.LEFT)
            tk.Button(
                row, text="登録",
                command=lambda w=word: self._register_oov(w),
            ).pack(side=tk.LEFT, padx=5)
            tk.Button(
                row, text="無視",
                command=lambda r=row: r.destroy(),
            ).pack(side=tk.LEFT)

    def _register_oov(self, word: str):
        self.registry.add(word, self.boost_var.get())
        if self.reload_cb:
            self.reload_cb()
        self._refresh_list()
        # Refresh OOV display to remove registered word
        for widget in self.oov_inner.winfo_children():
            widget.destroy()
