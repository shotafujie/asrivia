"""確定字幕から辞書登録を開くときの登録文(dict_prefill_text)のテスト。"""

from main import apply_edit, apply_result_message, dict_prefill_text, make_ui_state


def _state():
    state = make_ui_state(translate_enabled=True)
    apply_result_message(state, "text", 1, "今日はジャイストに行く")
    apply_result_message(state, "text", 2, "アスレビア来てますね")
    return state


# TC-009-1
def test_prefill_is_text_of_given_utterance():
    assert dict_prefill_text(_state(), 2) == "アスレビア来てますね"


# TC-009-2
def test_prefill_reflects_inline_edit():
    state = _state()
    apply_edit(state, 1, "今日はJAISTに行く")
    assert dict_prefill_text(state, 1) == "今日はJAISTに行く"


# TC-009-3
def test_prefill_excludes_translation():
    state = _state()
    apply_result_message(state, "translation", 2, "asrivia is here")
    assert dict_prefill_text(state, 2) == "アスレビア来てますね"


# TC-010-1
def test_prefill_for_unknown_uid_is_none():
    assert dict_prefill_text(_state(), 99) is None
