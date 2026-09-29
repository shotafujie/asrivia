"""辞書の「読み」で認識結果を置き換える後処理。

context(ヒント)では直らない「英語の登録語がカタカナで出る」誤り(例: Claude →「クロード」)を、
読み → 登録語の文字列置換で確実に直す。words.json は mtime を見て自動で読み直す。
"""

from __future__ import annotations

import os
import re

from .registry import WordRegistry

_SEPARATORS = re.compile(r"[,、，]")


def _parse_readings(reading: str) -> list[str]:
    return [r.strip() for r in _SEPARATORS.split(reading) if r.strip()]


class ReadingReplacer:
    """読み → 登録語の置換表を words.json から作り、認識結果に適用する。"""

    def __init__(self, registry_path: str):
        self.registry_path = registry_path
        self._mtime: float | None = None
        self._pattern: re.Pattern | None = None
        self._table: dict[str, str] = {}
        self._reload_if_changed()

    def _reload_if_changed(self):
        try:
            mtime = os.path.getmtime(self.registry_path)
        except OSError:
            mtime = 0.0
        if mtime == self._mtime:
            return
        self._mtime = mtime
        try:
            registry = WordRegistry.load(self.registry_path)
        except (ValueError, KeyError, TypeError) as e:
            # 辞書UIの保存途中を読んだ場合など。直前の置換表を使い続け、次の更新で読み直す
            print(f"[辞書/読み] words.json を読めないため直前の読みを継続: {e}")
            return
        table = {}
        for bw in registry.all():
            for r in _parse_readings(bw.reading):
                table[r] = bw.word
        self._table = table
        # 長い読みを先に試す(「クロードコード」を「クロード」より優先)
        alts = sorted(table, key=len, reverse=True)
        self._pattern = re.compile("|".join(map(re.escape, alts))) if alts else None

    def apply(self, text: str) -> str:
        self._reload_if_changed()
        if self._pattern is None:
            return text
        return self._pattern.sub(lambda m: self._table[m.group(0)], text)
