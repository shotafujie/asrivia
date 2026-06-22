"""DynamicAudioRecorder.get_audio_chunk の無音セグメント破棄に関するテスト。

回帰の背景: VAD(動的セグメンテーション)を有効にしても、誰も発話していない無音区間で
`get_audio_chunk` が無音のままのセグメントを返していた。これが ASR に渡り、特に Whisper が
「ご視聴ありがとうございました」等のハルシネーションを出していた。発話が一度も検出されな
かったセグメントは None を返して破棄する(producer 側は None をスキップする)。

`get_audio_chunk` は `self.audio_queue` から読むだけなので、キューに直接チャンクを積めば
pyaudio を起動せずに検証できる。
"""

import numpy as np

from audio2wav import DynamicAudioRecorder

CHUNK = 1024


def _fill(rec, chunks):
    for c in chunks:
        rec.audio_queue.put(c)


def test_returns_none_when_no_speech_detected():
    """全区間が無音(エネルギーが閾値以下)なら None を返して破棄する。"""
    rec = DynamicAudioRecorder(max_record_seconds=0.2)  # max_chunks = 3
    silent = np.zeros(CHUNK, dtype=np.float32)
    _fill(rec, [silent, silent, silent])
    assert rec.get_audio_chunk() is None


def test_returns_audio_when_speech_detected():
    """発話(閾値超え)を含むセグメントは従来どおり音声を返す。"""
    rec = DynamicAudioRecorder(max_record_seconds=0.2)
    silent = np.zeros(CHUNK, dtype=np.float32)
    speech = np.full(CHUNK, 0.5, dtype=np.float32)  # energy 0.5 > threshold 0.01
    _fill(rec, [speech, silent, silent])
    out = rec.get_audio_chunk()
    assert out is not None
    assert len(out) == CHUNK * 3
