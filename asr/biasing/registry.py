"""Word registry for contextual biasing (hotword boosting)."""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from pathlib import Path


@dataclass
class BiasWord:
    word: str
    boost: float = 2.0
    note: str = ""


class WordRegistry:
    """JSON-backed registry of bias words."""

    def __init__(self, words: list[BiasWord] | None = None):
        self._words: dict[str, BiasWord] = {}
        self._path: Path | None = None
        if words:
            for w in words:
                self._words[w.word] = w

    @classmethod
    def load(cls, path: str) -> WordRegistry:
        registry = cls()
        registry._path = Path(path)
        if registry._path.exists():
            data = json.loads(registry._path.read_text(encoding="utf-8"))
            for entry in data:
                bw = BiasWord(
                    word=entry["word"],
                    boost=entry.get("boost", 2.0),
                    note=entry.get("note", ""),
                )
                registry._words[bw.word] = bw
        return registry

    def save(self, path: str | None = None):
        p = Path(path) if path else self._path
        if p is None:
            raise ValueError("No path specified")
        self._path = p
        data = [asdict(w) for w in self._words.values()]
        p.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def add(self, word: str, boost: float = 2.0, note: str = ""):
        self._words[word] = BiasWord(word=word, boost=boost, note=note)
        if self._path:
            self.save()

    def remove(self, word: str):
        self._words.pop(word, None)
        if self._path:
            self.save()

    def update_boost(self, word: str, boost: float):
        if word in self._words:
            self._words[word].boost = boost
            if self._path:
                self.save()

    def all(self) -> list[BiasWord]:
        return list(self._words.values())

    def get(self, word: str) -> BiasWord | None:
        return self._words.get(word)

    def __len__(self) -> int:
        return len(self._words)

    def __contains__(self, word: str) -> bool:
        return word in self._words
