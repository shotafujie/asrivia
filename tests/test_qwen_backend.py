"""QwenASRBackend(opt-in バックエンド / MLX実装)のユニットテスト。

実モデル(`Qwen/Qwen3-ASR-0.6B`)に依存させないよう、`mlx_qwen3_asr` を
ダミーモジュールとして `sys.modules` に注入して検証する。検証する契約は
`asr/biased_whisper.py` の `BiasingWhisperBackend` と同じく
「numpy float32 @16kHz を受け取り Whisper 互換 dict を返す」こと。

MLX 実装(`mlx-qwen3-asr`)は numpy/タプル入力を直接受けるため、一時 WAV は不要。
`Session` でモデルを一度だけロードし、認識ごとに使い回す。
"""

import sys
import types

import numpy as np
import pytest


class _FakeResult:
    def __init__(self, text, language="ja"):
        self.text = text
        self.language = language


class _FakeSession:
    """`mlx_qwen3_asr.Session` の代役。生成/呼び出しを記録する。"""

    last_init = None
    instances = 0

    def __init__(self, model, **kwargs):
        type(self).last_init = {"model": model, "kwargs": kwargs}
        type(self).instances += 1
        self.transcribe_calls = []

    def transcribe(self, audio, language=None, **kwargs):
        self.transcribe_calls.append(
            {"audio": audio, "language": language, "kwargs": kwargs}
        )
        return _FakeResult("こんにちは")


@pytest.fixture(autouse=True)
def fake_mlx_qwen(monkeypatch):
    """`from mlx_qwen3_asr import Session` をダミーに差し替える。"""
    _FakeSession.last_init = None
    _FakeSession.instances = 0
    mod = types.ModuleType("mlx_qwen3_asr")
    mod.Session = _FakeSession
    monkeypatch.setitem(sys.modules, "mlx_qwen3_asr", mod)
    return mod


def _make_backend(**kwargs):
    from asr.qwen_asr_backend import QwenASRBackend

    return QwenASRBackend(**kwargs)


def _audio():
    return np.zeros(16000, dtype=np.float32)


def test_returns_whisper_compatible_dict():
    be = _make_backend(language="ja")
    result = be.transcribe(_audio())
    assert result == {"text": "こんにちは", "language": "ja"}


def test_language_ja_maps_to_japanese():
    be = _make_backend(language="ja")
    be.transcribe(_audio())
    assert be.session.transcribe_calls[0]["language"] == "Japanese"


def test_language_en_maps_to_english():
    be = _make_backend(language="en")
    be.transcribe(_audio())
    assert be.session.transcribe_calls[0]["language"] == "English"


def test_language_auto_maps_to_none():
    be = _make_backend(language="auto")
    be.transcribe(_audio())
    assert be.session.transcribe_calls[0]["language"] is None


def test_audio_passed_as_16k_tuple():
    """numpy@16kHz を (array, 16000) タプルで渡す(サンプルレート曖昧性の排除)。"""
    be = _make_backend(language="ja")
    audio = _audio()
    be.transcribe(audio)
    passed = be.session.transcribe_calls[0]["audio"]
    assert isinstance(passed, tuple)
    assert passed[1] == 16000
    assert passed[0] is audio


def test_session_loaded_with_default_model():
    _make_backend()
    assert _FakeSession.last_init["model"] == "Qwen/Qwen3-ASR-0.6B"


def test_session_loaded_once_and_reused():
    """モデルは生成時に1度だけロードし、認識ごとに使い回す。"""
    be = _make_backend(language="ja")
    be.transcribe(_audio())
    be.transcribe(_audio())
    assert _FakeSession.instances == 1
    assert len(be.session.transcribe_calls) == 2
