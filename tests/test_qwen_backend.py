"""QwenASRBackend(opt-in バックエンド / MLX実装)のユニットテスト。

実モデル(`Qwen/Qwen3-ASR-1.7B`)に依存させないよう、`mlx_qwen3_asr` を
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
        # テストが差し替えられる応答関数(kwargs -> text)
        self.reply = lambda kwargs: "こんにちは"

    def transcribe(self, audio, language=None, **kwargs):
        self.transcribe_calls.append(
            {"audio": audio, "language": language, "kwargs": kwargs}
        )
        return _FakeResult(self.reply(kwargs))


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
    assert _FakeSession.last_init["model"] == "Qwen/Qwen3-ASR-1.7B"


def test_session_loaded_once_and_reused():
    """モデルは生成時に1度だけロードし、認識ごとに使い回す。"""
    be = _make_backend(language="ja")
    be.transcribe(_audio())
    be.transcribe(_audio())
    assert _FakeSession.instances == 1
    assert len(be.session.transcribe_calls) == 2


# --- 辞書(words.json)を context として渡す ---------------------------------


def _write_words(path, words):
    import json

    path.write_text(
        json.dumps([{"word": w} for w in words], ensure_ascii=False),
        encoding="utf-8",
    )


def _context_of(call):
    return call["kwargs"].get("context", "")


# TC-001-1
def test_no_registry_path_passes_empty_context():
    """registry_path 未指定なら従来どおり context なし。"""
    be = _make_backend(language="ja")
    be.transcribe(_audio())
    assert _context_of(be.session.transcribe_calls[0]) == ""


# TC-002-1
def test_registered_words_are_passed_as_context(tmp_path):
    p = tmp_path / "words.json"
    _write_words(p, ["JAIST", "情報保障"])
    be = _make_backend(language="ja", registry_path=str(p))
    be.transcribe(_audio())
    ctx = _context_of(be.session.transcribe_calls[0])
    assert "JAIST" in ctx
    assert "情報保障" in ctx


# TC-004-1
def test_missing_registry_file_passes_empty_context(tmp_path):
    be = _make_backend(language="ja", registry_path=str(tmp_path / "none.json"))
    be.transcribe(_audio())
    assert _context_of(be.session.transcribe_calls[0]) == ""


# TC-005-1
def test_registry_file_update_is_reflected_on_next_transcribe(tmp_path):
    """辞書UIで words.json が更新されたら、次の認識から反映される。"""
    import os

    p = tmp_path / "words.json"
    _write_words(p, ["JAIST"])
    be = _make_backend(language="ja", registry_path=str(p))
    be.transcribe(_audio())

    _write_words(p, ["JAIST", "asrivia"])
    st = os.stat(p)
    os.utime(p, (st.st_atime, st.st_mtime + 10))  # mtime 分解能に依存させない
    be.transcribe(_audio())

    assert "asrivia" not in _context_of(be.session.transcribe_calls[0])
    assert "asrivia" in _context_of(be.session.transcribe_calls[1])


# TC-003-1
def test_build_context_joins_words_in_registration_order():
    from asr.qwen_asr_backend import build_context

    assert build_context(["JAIST", "情報保障", "Claude Code"]) == "JAIST, 情報保障, Claude Code"


# TC-003-2
def test_build_context_empty():
    from asr.qwen_asr_backend import build_context

    assert build_context([]) == ""


# --- context 漏れガード ------------------------------------------------------
# モデルが context の単語リストをそのまま出力することがある(実機では無音・雑音の短い区間で多発)。
# 出力に異なる登録語が3語以上含まれたら漏れとみなし、その区間を捨てる(空文字を返す)。


def _leaky_reply(kwargs):
    ctx = kwargs.get("context", "")
    return ctx if ctx else "ね、JAIST"


def _backend_with_words(tmp_path, words):
    p = tmp_path / "words.json"
    _write_words(p, words)
    return _make_backend(language="ja", registry_path=str(p))


# TC-024-1
def test_context_leak_is_dropped(tmp_path):
    be = _backend_with_words(tmp_path, ["JAIST", "情報保障", "asrivia", "Agile"])
    be.session.reply = _leaky_reply
    result = be.transcribe(_audio())
    assert result["text"] == ""
    assert len(be.session.transcribe_calls) == 1


# TC-024-2
def test_leak_detection_ignores_case_and_width(tmp_path):
    """全角/大文字小文字の違いで漏れを見逃さない(NFKC + 小文字化で照合)。"""
    be = _backend_with_words(tmp_path, ["JAIST", "asrivia", "Agile"])
    be.session.reply = lambda kw: "ＪＡＩＳＴ、ASRIVIA、agile" if kw.get("context") else "x"
    assert be.transcribe(_audio())["text"] == ""
    assert len(be.session.transcribe_calls) == 1


# TC-007-1
def test_two_registered_words_are_not_treated_as_leak(tmp_path):
    """登録語が2語までなら普通の発話として採用する(再認識しない)。"""
    be = _backend_with_words(tmp_path, ["JAIST", "情報保障", "asrivia"])
    be.session.reply = lambda kw: "JAISTで情報保障の研究"
    result = be.transcribe(_audio())
    assert result["text"] == "JAISTで情報保障の研究"
    assert len(be.session.transcribe_calls) == 1


# TC-003-3
def test_context_from_words_json_keeps_registration_order(tmp_path):
    p = tmp_path / "words.json"
    _write_words(p, ["情報保障", "JAIST", "Claude Code"])
    be = _make_backend(language="ja", registry_path=str(p))
    be.transcribe(_audio())
    assert _context_of(be.session.transcribe_calls[0]) == "情報保障, JAIST, Claude Code"


# TC-003-4
def test_empty_words_json_passes_empty_context(tmp_path):
    p = tmp_path / "words.json"
    _write_words(p, [])
    be = _make_backend(language="ja", registry_path=str(p))
    be.transcribe(_audio())
    assert _context_of(be.session.transcribe_calls[0]) == ""


# TC-007-2
def test_same_word_repeated_counts_as_one(tmp_path):
    be = _backend_with_words(tmp_path, ["JAIST", "情報保障", "asrivia"])
    be.session.reply = lambda kw: "JAIST、JAIST、JAIST"
    assert be.transcribe(_audio())["text"] == "JAIST、JAIST、JAIST"
    assert len(be.session.transcribe_calls) == 1


# --- 壊れた words.json(辞書UIの保存と読み込みが重なった場合など) ----------


def _bump_mtime(path, sec):
    import os

    st = os.stat(path)
    os.utime(path, (st.st_atime, st.st_mtime + sec))


# TC-008-1
def test_broken_words_json_keeps_previous_context(tmp_path):
    p = tmp_path / "words.json"
    _write_words(p, ["JAIST"])
    be = _make_backend(language="ja", registry_path=str(p))
    be.transcribe(_audio())

    p.write_text('[{"word": "JAIST"}, {"wo', encoding="utf-8")
    _bump_mtime(p, 10)
    be.transcribe(_audio())

    assert _context_of(be.session.transcribe_calls[1]) == "JAIST"


# TC-008-2
def test_fixed_words_json_is_reflected_after_broken(tmp_path):
    p = tmp_path / "words.json"
    _write_words(p, ["JAIST"])
    be = _make_backend(language="ja", registry_path=str(p))
    be.transcribe(_audio())

    p.write_text('[{"word": "JAIST"}, {"wo', encoding="utf-8")
    _bump_mtime(p, 10)
    be.transcribe(_audio())

    _write_words(p, ["JAIST", "asrivia"])
    _bump_mtime(p, 20)
    be.transcribe(_audio())

    assert "asrivia" in _context_of(be.session.transcribe_calls[2])


# TC-008-3
def test_broken_words_json_at_startup_passes_empty_context(tmp_path):
    p = tmp_path / "words.json"
    p.write_text("[{", encoding="utf-8")
    be = _make_backend(language="ja", registry_path=str(p))
    be.transcribe(_audio())
    assert _context_of(be.session.transcribe_calls[0]) == ""
