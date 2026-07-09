"""koepus_writer.write_pair / extract_confidence のテスト。

背景: asrivia の認識結果(wav + 仮説テキスト)を koepus の incoming/ ディレクトリへ
wav + sidecar JSON のペアとして書き出す必要がある(Issue shotafujie/asrivia#15)。
koepus 側の watch は *.json をトリガに取り込むため、wav を先に確定させてから
json を最後にrenameする atomic write の手順が壊れていないかを重点的に検証する。
"""

import json
import wave
from datetime import datetime, timezone, timedelta

import numpy as np
import pytest

from koepus_writer import extract_confidence, write_pair


JST = timezone(timedelta(hours=9))


def test_write_pair_writes_wav_and_json():
    """wav/json のペアが正しい形式で書かれる。"""
    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory() as tmp:
        incoming_dir = Path(tmp) / "incoming"
        frame = np.zeros(16000, dtype=np.float32)
        now = datetime(2026, 7, 10, 12, 34, 56, tzinfo=JST)

        json_path = write_pair(
            incoming_dir,
            frame,
            hypothesis="こんにちは",
            asr_model="mlx:mlx-community/whisper-large-v3-turbo",
            language="ja",
            confidence=-0.31,
            dynamic_vad=True,
            now=now,
        )

        assert json_path.exists()
        wav_path = json_path.with_suffix(".wav")
        assert wav_path.exists()

        with wave.open(str(wav_path), "rb") as wf:
            assert wf.getframerate() == 16000
            assert wf.getnchannels() == 1
            assert wf.getsampwidth() == 2
            assert wf.getnframes() == len(frame)

        data = json.loads(json_path.read_text(encoding="utf-8"))
        assert data["source"] == "asrivia"
        assert data["recorded_at"] == "2026-07-10T12:34:56+09:00"
        assert data["hypothesis"] == "こんにちは"
        assert data["channels"] == ["air"]
        assert data["meta"] == {
            "app": "asrivia",
            "backend": "mlx",
            "language": "ja",
            "dynamic_vad": True,
        }


def test_write_pair_leaves_no_tmp_files(tmp_path):
    """書き込み完了後に .tmp ファイルが残らないこと。"""
    frame = np.zeros(1600, dtype=np.float32)
    json_path = write_pair(
        tmp_path,
        frame,
        hypothesis="test",
        asr_model="mlx:whisper",
        language="ja",
        confidence=None,
        dynamic_vad=False,
    )
    tmp_files = list(tmp_path.glob("*.tmp"))
    assert tmp_files == []
    assert json_path.parent == tmp_path


def test_write_pair_clips_overflow_samples(tmp_path):
    """float32の±1.0を超える値はクリップされてint16の最大値になる。"""
    frame = np.array([2.0, -2.0, 0.0], dtype=np.float32)
    json_path = write_pair(
        tmp_path,
        frame,
        hypothesis="clip",
        asr_model="mlx:whisper",
        language="ja",
        confidence=None,
        dynamic_vad=False,
    )
    wav_path = json_path.with_suffix(".wav")
    with wave.open(str(wav_path), "rb") as wf:
        raw = wf.readframes(wf.getnframes())
    samples = np.frombuffer(raw, dtype=np.int16)
    assert samples[0] == 32767
    assert samples[1] == -32767
    assert samples[2] == 0


def test_write_pair_stem_suffix_and_no_collision(tmp_path):
    """stem が _asrivia で終わり、同時刻の複数呼び出しでも衝突しないこと。"""
    frame = np.zeros(160, dtype=np.float32)
    now = datetime(2026, 7, 10, 12, 0, 0, tzinfo=JST)

    json_path1 = write_pair(
        tmp_path, frame, hypothesis="a", asr_model="mlx:whisper",
        language="ja", confidence=None, dynamic_vad=False, now=now,
    )
    json_path2 = write_pair(
        tmp_path, frame, hypothesis="b", asr_model="mlx:whisper",
        language="ja", confidence=None, dynamic_vad=False, now=now,
    )

    assert json_path1.stem.endswith("_asrivia")
    assert json_path2.stem.endswith("_asrivia")
    assert json_path1 != json_path2

    files = list(tmp_path.glob("*"))
    assert len(files) == 4


def test_extract_confidence_averages_avg_logprob():
    """segmentsのavg_logprobの平均を返す。"""
    result = {
        "segments": [
            {"avg_logprob": -0.2},
            {"avg_logprob": -0.4},
        ]
    }
    assert extract_confidence(result) == pytest.approx(-0.3)


def test_extract_confidence_returns_none_for_empty_segments():
    """segmentsが空リストならNone。"""
    assert extract_confidence({"segments": []}) is None


def test_extract_confidence_returns_none_when_segments_missing():
    """segmentsキーが無ければNone。"""
    assert extract_confidence({"text": "hello"}) is None


def test_extract_confidence_returns_none_for_non_dict_result():
    """resultがdictでなければNone。"""
    assert extract_confidence("not a dict") is None
    assert extract_confidence(None) is None
