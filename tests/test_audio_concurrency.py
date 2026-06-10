"""PortAudio(PyAudio)を複数スレッドから同時に初期化/終了すると macOS で
segfault する回帰を防ぐテスト。

`pyaudio.PyAudio()` / `.terminate()` は内部で PortAudio の
`Pa_Initialize` / `Pa_Terminate` を呼ぶが、これらはスレッドアンセーフな
グローバル状態を触る。デバイス選択UI(`list_input_devices()`)と録音スレッドが
それぞれ別の PortAudio コンテキストを同時に生成/破棄したことで segfault していた。

segfault はプロセスごと落とすので `try/except` では捕捉できない。サブプロセスで
並行アクセスを叩き、exit code が 0(= segfault していない)であることを検証する。
"""

import subprocess
import sys
import textwrap
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# list_input_devices() を多スレッドで同時に叩く。修正前は PortAudio の
# Pa_Initialize/Pa_Terminate が競合して高確率で SIGSEGV(exit 139)になる。
_HAMMER_SNIPPET = textwrap.dedent(
    """
    import threading
    import audio2wav

    def hammer():
        for _ in range(100):
            audio2wav.list_input_devices()

    threads = [threading.Thread(target=hammer) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    print("OK")
    """
)

# 録音スレッド稼働中にデバイス列挙を叩く、実際の起動シーケンスに近いシナリオ。
_RECORDER_PLUS_ENUM_SNIPPET = textwrap.dedent(
    """
    import threading
    import time
    import audio2wav

    audio2wav.initialize_recorder(mode="dynamic")  # 録音スレッドが PortAudio を握る

    stop = threading.Event()

    def hammer():
        while not stop.is_set():
            audio2wav.list_input_devices()

    threads = [threading.Thread(target=hammer) for _ in range(6)]
    for t in threads:
        t.start()
    time.sleep(1.0)
    stop.set()
    for t in threads:
        t.join()
    audio2wav.cleanup()
    print("OK")
    """
)


def _run(snippet: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-c", snippet],
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
    )


def test_concurrent_device_enumeration_no_segfault():
    # 競合は確率的なので複数回試行し、毎回クラッシュしないことを要求する。
    for trial in range(3):
        proc = _run(_HAMMER_SNIPPET)
        assert proc.returncode == 0, (
            f"trial {trial}: segfault したか異常終了 rc={proc.returncode}\n"
            f"stdout={proc.stdout!r}\nstderr={proc.stderr!r}"
        )
        assert "OK" in proc.stdout


def test_recorder_active_with_device_enumeration_no_segfault():
    proc = _run(_RECORDER_PLUS_ENUM_SNIPPET)
    assert proc.returncode == 0, (
        f"segfault したか異常終了 rc={proc.returncode}\n"
        f"stdout={proc.stdout!r}\nstderr={proc.stderr!r}"
    )
    assert "OK" in proc.stdout
