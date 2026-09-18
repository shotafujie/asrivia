"""BT機器の unpair 等でストリーム読み取りが OSError(PaMacCore -50 等)を出しても
録音スレッドが落ちずに復旧することを検証するテスト。

`_open_stream` を差し替えることで実際の PortAudio デバイスに触れずに検証する。
"""

import time

import numpy as np

from audio2wav import AudioRecorder, DynamicAudioRecorder

CHUNK = 1024


class _FailNTimesStream:
    """最初の N 回だけ read() で OSError を出し、以降は無音データを返す偽ストリーム。"""

    def __init__(self, fail_times, chunk=CHUNK):
        self.fail_times = fail_times
        self.chunk = chunk
        self.read_calls = 0

    def read(self, n, exception_on_overflow=False):
        self.read_calls += 1
        if self.read_calls <= self.fail_times:
            raise OSError(-50, "Unknown Error")
        return np.zeros(n, dtype=np.float32).tobytes()

    def stop_stream(self):
        pass

    def close(self):
        pass


class _AlwaysFailStream:
    """read() が常に OSError を出す偽ストリーム(デバイスが消えたままの状態)。"""

    def read(self, n, exception_on_overflow=False):
        raise OSError(-50, "Unknown Error")

    def stop_stream(self):
        pass

    def close(self):
        pass


def test_recovers_from_transient_read_error():
    """read() が一時的に失敗しても、ストリームを再オープンして録音を継続する。"""
    rec = DynamicAudioRecorder(max_record_seconds=0.2)
    rec.REOPEN_BACKOFF_SECONDS = 0.01
    fake = _FailNTimesStream(fail_times=2)
    rec._open_stream = lambda pa: fake

    rec.start_recording()
    time.sleep(0.3)
    rec.stop_recording()

    assert not rec.audio_queue.empty()
    assert fake.read_calls > 2


def test_falls_back_to_default_device_after_repeated_failures():
    """指定デバイスでの読み取りが規定回数連続失敗したら既定デバイス(None)にフォールバックする。"""
    rec = DynamicAudioRecorder(max_record_seconds=0.2, device_index=5)
    rec.REOPEN_BACKOFF_SECONDS = 0.01
    rec.MAX_REOPEN_RETRIES = 1
    rec._open_stream = lambda pa: _AlwaysFailStream()

    rec.start_recording()
    time.sleep(0.2)
    rec.stop_recording()

    assert rec.device_index is None


def test_status_reflects_reconnection():
    """読み取り失敗中は status が reconnecting になり、復旧後は ok・停止後は stopped になる。"""
    rec = DynamicAudioRecorder(max_record_seconds=0.2)
    rec.REOPEN_BACKOFF_SECONDS = 0.05
    fake = _FailNTimesStream(fail_times=3)
    rec._open_stream = lambda pa: fake

    rec.start_recording()

    seen_reconnecting = False
    deadline = time.monotonic() + 1.0
    while time.monotonic() < deadline:
        if rec.status == "reconnecting":
            seen_reconnecting = True
            break
        time.sleep(0.005)
    assert seen_reconnecting, "reconnecting 状態が一度も観測されなかった"

    deadline = time.monotonic() + 1.0
    while time.monotonic() < deadline and rec.status != "ok":
        time.sleep(0.005)
    assert rec.status == "ok"

    rec.stop_recording()
    assert rec.status == "stopped"


def test_fixed_recorder_recovers_from_transient_read_error():
    """固定長録音の AudioRecorder も同じ復旧処理を継承している。"""
    rec = AudioRecorder(record_seconds=0.2)
    rec.REOPEN_BACKOFF_SECONDS = 0.01
    fake = _FailNTimesStream(fail_times=2)
    rec._open_stream = lambda pa: fake

    rec.start_recording()
    time.sleep(0.3)
    rec.stop_recording()

    assert not rec.audio_queue.empty()
    assert fake.read_calls > 2
