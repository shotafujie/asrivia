"""Qwen3-ASR backend (opt-in) — MLX 実装(`mlx-qwen3-asr`)。

ユーザー自身の検証(自声20文 2026-04)で `Qwen/Qwen3-ASR-0.6B` が CER 8.44% と
Whisper 系を大きく上回り、英字(Python/GitHub 等)をカタカナ化せず出せる。

推論は Apple Silicon 向けに最適化された MLX 実装で行う(torch/transformers 非依存)。
`mlx-qwen3-asr` は numpy 配列 / (array, sample_rate) タプルを直接受けるため一時 WAV は不要。
`Session` でモデルを一度だけロードし、認識ごとに使い回す。

`asr/biased_whisper.py` の `BiasingWhisperBackend` と同じく
「numpy float32 @16kHz を受け取り Whisper 互換 dict を返す」契約に合わせる。
辞書(words.json / 辞書UI)の登録語は、Qwen3-ASR のシステムプロンプト(`context`)に
並べて渡す。hf の logits 加点と違いモデルへの「ヒント」なので効き目は保証されない。
効果は `benchmarks/qwen-context/` で測る。words.json は mtime を見て自動で読み直す。

短い発話ではモデルが context の単語リストをそのまま出力することがある(ベンチで観測)。
出力に登録語が LEAK_MIN_WORDS 語以上含まれたら漏れとみなし、context なしで認識し直す。
"""

from __future__ import annotations

import os
import unicodedata

import numpy as np

SAMPLE_RATE = 16000

# asrivia 内部の言語コード -> qwen3-asr が受け取る言語名。"auto"/未知は None(自動判定)。
_LANG_MAP = {"ja": "Japanese", "en": "English"}


# 出力にこの数以上の登録語が含まれたら context の漏れとみなす
LEAK_MIN_WORDS = 3


def build_context(words: list[str]) -> str:
    """登録語を登録順に並べた context 文字列を返す(0語なら空文字)。"""
    return ", ".join(words)


def _fold(text: str) -> str:
    return unicodedata.normalize("NFKC", text).lower()


class QwenASRBackend:
    """Qwen3-ASR 1.7B バックエンド(MLX)。transcribe(frame) -> {"text", "language"}。"""

    def __init__(
        self,
        model_name: str = "Qwen/Qwen3-ASR-1.7B",
        language: str = "ja",
        registry_path: str | None = None,
    ):
        self.model_name = model_name
        self.language = language
        self.registry_path = registry_path
        self._registry_mtime: float | None = None
        self.context = ""
        self._folded_words: list[str] = []
        self._reload_if_changed()

        # 重依存のため遅延 import(他バックエンド利用時に巻き込まない)。
        from mlx_qwen3_asr import Session

        print(f"[Qwen3-ASR/MLX] モデルをロード中: {model_name}")
        self.session = Session(model=model_name)
        print("[Qwen3-ASR/MLX] モデルのロードが完了しました")

    def _reload_if_changed(self):
        """words.json の mtime が変わっていたら context を作り直す。"""
        if self.registry_path is None:
            return
        try:
            mtime = os.path.getmtime(self.registry_path)
        except OSError:
            mtime = 0.0
        if mtime == self._registry_mtime:
            return
        from .biasing import WordRegistry

        self._registry_mtime = mtime
        try:
            registry = WordRegistry.load(self.registry_path)
        except (ValueError, KeyError, TypeError) as e:
            # 辞書UIの保存途中を読んだ場合など。直前の context を使い続け、次の更新で読み直す
            print(f"[Qwen3-ASR/MLX] words.json を読めないため直前の辞書を継続: {e}")
            return
        words = [bw.word for bw in registry.all()]
        self.context = build_context(words)
        self._folded_words = [_fold(w) for w in words]
        print(f"[Qwen3-ASR/MLX] 辞書を context に反映: {len(registry)}語")

    def _is_context_leak(self, text: str) -> bool:
        folded = _fold(text)
        # 異なる登録語の数で数える(同じ語の繰り返しは1)
        return sum(w in folded for w in set(self._folded_words)) >= LEAK_MIN_WORDS

    def transcribe(self, audio: np.ndarray) -> dict:
        """numpy float32 @16kHz を認識し Whisper 互換 dict を返す。

        サンプルレートの曖昧さを避けるため (array, 16000) タプルで渡す。
        """
        self._reload_if_changed()
        language = _LANG_MAP.get(self.language)  # "auto"/未知 -> None
        result = self.session.transcribe(
            (audio, SAMPLE_RATE), language=language, context=self.context
        )
        if self.context and self._is_context_leak(result.text):
            print("[Qwen3-ASR/MLX] context の漏れを検出したため context なしで再認識")
            result = self.session.transcribe(
                (audio, SAMPLE_RATE), language=language, context=""
            )
        return {
            "text": result.text.strip(),
            "language": self.language,
        }
