"""二段デコード(ライブ仮字幕 + 確定再デコード)のテスト。

first pass(小型モデル)が録音途中のバッファを認識して仮字幕を出し、
発話確定後に second pass(従来のASR)が同じ uid で置き換える。

- DynamicAudioRecorder.get_partial_buffer: 録音中バッファのスナップショット取得
- apply_result_message: UI の表示状態遷移(partial/text/translation の uid 整合)
"""

import threading
import time

import numpy as np

from audio2wav import DynamicAudioRecorder
from main import apply_result_message, make_ui_state

CHUNK = 1024
SILENT = np.zeros(CHUNK, dtype=np.float32)
SPEECH = np.full(CHUNK, 0.5, dtype=np.float32)  # energy 0.5 > threshold 0.01


# ---------------------------------------------------------------------------
# DynamicAudioRecorder.get_partial_buffer
# ---------------------------------------------------------------------------

def test_partial_buffer_is_none_before_any_speech():
    """収集が始まっていなければ None。"""
    rec = DynamicAudioRecorder(max_record_seconds=0.2)
    assert rec.get_partial_buffer() is None


def test_partial_buffer_is_none_during_silence_only():
    """無音チャンクしか来ていない間は None(無音を first pass に渡すと幻聴するため)。"""
    rec = DynamicAudioRecorder(max_record_seconds=0.3)  # max_chunks = 4
    for c in [SILENT, SILENT]:
        rec.audio_queue.put(c)

    t = threading.Thread(target=rec.get_audio_chunk)
    t.start()
    time.sleep(0.2)
    assert rec.get_partial_buffer() is None
    # 残りを無音で埋めて終了させる
    for c in [SILENT, SILENT]:
        rec.audio_queue.put(c)
    t.join(timeout=2)
    assert not t.is_alive()


def test_partial_buffer_returns_speech_snapshot_with_uid():
    """発話中は (uid, 蓄積バッファ) を返し、uid は確定セグメントと一致する。"""
    rec = DynamicAudioRecorder(max_record_seconds=0.3, silence_duration=0.1)
    rec.audio_queue.put(SPEECH)
    rec.audio_queue.put(SPEECH)

    result_box = {}

    def run():
        result_box["segment"] = rec.get_audio_chunk()

    t = threading.Thread(target=run)
    t.start()

    partial = None
    deadline = time.time() + 2
    while partial is None and time.time() < deadline:
        partial = rec.get_partial_buffer()
        time.sleep(0.01)
    assert partial is not None, "発話中に部分バッファが取得できるはず"
    uid, buf = partial
    assert isinstance(uid, int)
    assert len(buf) >= CHUNK

    # 無音を送って発話を確定させる
    rec.audio_queue.put(SILENT)
    rec.audio_queue.put(SILENT)
    t.join(timeout=2)
    assert not t.is_alive()
    assert result_box["segment"] is not None

    # 確定後は部分バッファはクリアされ、uid はレコーダーの segment_uid と一致
    assert rec.get_partial_buffer() is None
    assert rec.segment_uid == uid


def test_segment_uid_increments_per_segment():
    """セグメントごとに uid が単調増加する(無音破棄セグメントでも増える)。"""
    rec = DynamicAudioRecorder(max_record_seconds=0.2)
    for c in [SILENT, SILENT, SILENT]:
        rec.audio_queue.put(c)
    assert rec.get_audio_chunk() is None
    first_uid = rec.segment_uid

    for c in [SPEECH, SILENT, SILENT]:
        rec.audio_queue.put(c)
    assert rec.get_audio_chunk() is not None
    assert rec.segment_uid == first_uid + 1


# ---------------------------------------------------------------------------
# apply_result_message: UI 表示状態遷移(複数発話の履歴表示)
# ---------------------------------------------------------------------------

def _texts(state):
    return [e["text"] for e in state["history"]]


def test_partial_then_final_appends_to_history():
    state = make_ui_state(translate_enabled=False)
    assert apply_result_message(state, "partial", 1, "こんにち")
    assert state["partial"] == "こんにち"

    assert apply_result_message(state, "text", 1, "こんにちは")
    assert state["partial"] is None
    assert _texts(state) == ["こんにちは"]


def test_history_keeps_recent_utterances_up_to_max():
    """確定発話は履歴に積まれ、上限を超えると古い行から消える。"""
    state = make_ui_state(translate_enabled=False, history_max=3)
    for uid, text in [(1, "一"), (2, "二"), (3, "三"), (4, "四")]:
        apply_result_message(state, "text", uid, text)
    assert _texts(state) == ["二", "三", "四"]


def test_late_partial_after_final_is_dropped():
    """確定済み uid 以下の仮字幕は破棄する(遅延到着)。"""
    state = make_ui_state(translate_enabled=False)
    apply_result_message(state, "text", 2, "確定テキスト")

    assert not apply_result_message(state, "partial", 2, "遅れた仮字幕")
    assert not apply_result_message(state, "partial", 1, "もっと遅れた仮字幕")
    assert state["partial"] is None


def test_partial_for_next_utterance_coexists_with_history():
    """次の発話の仮字幕は、確定履歴と共存する(履歴の下にグレー表示)。"""
    state = make_ui_state(translate_enabled=False)
    apply_result_message(state, "text", 1, "前の発話")

    assert apply_result_message(state, "partial", 2, "次の発話の途中")
    assert state["partial"] == "次の発話の途中"
    assert _texts(state) == ["前の発話"]


def test_partial_survives_delayed_earlier_final():
    """仮字幕(uid=3)表示中に遅れて届いた確定(uid=2)は、仮字幕を消さない。"""
    state = make_ui_state(translate_enabled=False)
    apply_result_message(state, "partial", 3, "三番目の途中")
    apply_result_message(state, "text", 2, "二番目")
    assert state["partial"] == "三番目の途中"

    apply_result_message(state, "text", 3, "三番目")
    assert state["partial"] is None


def test_translation_attaches_to_matching_history_entry():
    state = make_ui_state(translate_enabled=True)
    apply_result_message(state, "text", 1, "こんにちは")
    apply_result_message(state, "text", 2, "次")

    assert apply_result_message(state, "translation", 1, "Hello")
    assert state["history"][0]["translated"] == "Hello"
    assert state["history"][1]["translated"] is None

    # 履歴から消えた uid の翻訳は破棄
    assert not apply_result_message(state, "translation", 99, "Ghost")
