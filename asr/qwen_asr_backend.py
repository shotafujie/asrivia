"""Qwen3-ASR backend (opt-in) — MLX 実装(`mlx-qwen3-asr`)。

ユーザー自身の検証(自声20文 2026-04)で `Qwen/Qwen3-ASR-0.6B` が CER 8.44% と
Whisper 系を大きく上回り、英字(Python/GitHub 等)をカタカナ化せず出せる。

推論は Apple Silicon 向けに最適化された MLX 実装で行う(torch/transformers 非依存)。
`mlx-qwen3-asr` は numpy 配列 / (array, sample_rate) タプルを直接受けるため一時 WAV は不要。
`Session` でモデルを一度だけロードし、認識ごとに使い回す。

`asr/biased_whisper.py` の `BiasingWhisperBackend` と同じく
「numpy float32 @16kHz を受け取り Whisper 互換 dict を返す」契約に合わせる。
v1 ではホットワード biasing(words.json / 辞書UI)は非対応。biasing が要る場合は
従来の `hf` バックエンドを使う。
"""

from __future__ import annotations

import numpy as np

SAMPLE_RATE = 16000

# asrivia 内部の言語コード -> qwen3-asr が受け取る言語名。"auto"/未知は None(自動判定)。
_LANG_MAP = {"ja": "Japanese", "en": "English"}


class QwenASRBackend:
    """Qwen3-ASR 1.7B バックエンド(MLX)。transcribe(frame) -> {"text", "language"}。"""

    def __init__(
        self,
        model_name: str = "Qwen/Qwen3-ASR-1.7B",
        language: str = "ja",
    ):
        self.model_name = model_name
        self.language = language

        # 重依存のため遅延 import(他バックエンド利用時に巻き込まない)。
        from mlx_qwen3_asr import Session

        print(f"[Qwen3-ASR/MLX] モデルをロード中: {model_name}")
        self.session = Session(model=model_name)
        print("[Qwen3-ASR/MLX] モデルのロードが完了しました")

    def transcribe(self, audio: np.ndarray) -> dict:
        """numpy float32 @16kHz を認識し Whisper 互換 dict を返す。

        サンプルレートの曖昧さを避けるため (array, 16000) タプルで渡す。
        """
        language = _LANG_MAP.get(self.language)  # "auto"/未知 -> None
        result = self.session.transcribe((audio, SAMPLE_RATE), language=language)
        return {
            "text": result.text.strip(),
            "language": self.language,
        }
