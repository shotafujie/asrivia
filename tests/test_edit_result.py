"""確定字幕のインライン編集(apply_edit)のテスト。

PiPウィンドウで確定発話をダブルクリック編集したときの状態遷移。
編集は画面表示のみに反映する(koepus・翻訳へは伝播しない)。
"""

from main import apply_edit, apply_result_message, make_ui_state


def make_state_with_history():
    state = make_ui_state()
    apply_result_message(state, "text", 1, "こんにちわ")
    apply_result_message(state, "text", 2, "テストです")
    return state


def test_edit_updates_matching_uid():
    state = make_state_with_history()
    assert apply_edit(state, 1, "こんにちは") is True
    assert state["history"][0]["text"] == "こんにちは"
    assert state["history"][1]["text"] == "テストです"


def test_edit_unknown_uid_is_noop():
    state = make_state_with_history()
    assert apply_edit(state, 99, "だれ？") is False
    assert [e["text"] for e in state["history"]] == ["こんにちわ", "テストです"]


def test_edit_to_empty_text_is_rejected():
    """空文字・空白のみへの編集は誤操作とみなして棄却する。"""
    state = make_state_with_history()
    assert apply_edit(state, 1, "") is False
    assert apply_edit(state, 1, "   ") is False
    assert state["history"][0]["text"] == "こんにちわ"


def test_edit_strips_surrounding_whitespace():
    state = make_state_with_history()
    assert apply_edit(state, 1, "  こんにちは  ") is True
    assert state["history"][0]["text"] == "こんにちは"


def test_edit_same_text_needs_no_redraw():
    state = make_state_with_history()
    assert apply_edit(state, 1, "こんにちわ") is False


def test_edit_keeps_existing_translation():
    """表示のみの編集なので、既にある翻訳表示はそのまま残す。"""
    state = make_state_with_history()
    apply_result_message(state, "translation", 1, "Hello")
    apply_edit(state, 1, "こんにちは")
    assert state["history"][0]["translated"] == "Hello"
