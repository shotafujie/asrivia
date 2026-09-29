"""辞書ウィンドウを1つに保ち、登録文を単語欄に入れて開く DictLauncher のテスト。

非表示の実 tk.Tk を使う(Toplevel の生死と Entry の状態を観測するため)。
"""

import tkinter as tk

import pytest

from asr.biasing import WordRegistry
from asr.dict_window import DictLauncher


@pytest.fixture
def root():
    r = tk.Tk()
    r.withdraw()
    yield r
    r.destroy()


@pytest.fixture
def launcher(root, tmp_path):
    registry = WordRegistry.load(str(tmp_path / "words.json"))
    return DictLauncher(root, registry)


def _toplevels(root):
    return [w for w in root.winfo_children() if isinstance(w, tk.Toplevel)]


# TC-011-1
def test_first_open_creates_one_window(root, launcher):
    dw = launcher.open()
    assert dw.win.winfo_exists()
    assert len(_toplevels(root)) == 1


# TC-012-1
def test_second_open_reuses_window(root, launcher):
    first = launcher.open()
    second = launcher.open()
    assert second is first
    assert len(_toplevels(root)) == 1


# TC-013-1
def test_open_after_close_creates_new_window(root, launcher):
    first = launcher.open()
    first.win.destroy()
    second = launcher.open()
    assert second is not first
    assert second.win.winfo_exists()


# TC-014-1
def test_prefill_fills_and_selects_word_entry(launcher):
    dw = launcher.open(prefill="アスレビア来てますね")
    assert dw.entry.get() == "アスレビア来てますね"
    assert dw.entry.selection_present()
    assert dw.entry.index(tk.SEL_FIRST) == 0
    assert dw.entry.index(tk.SEL_LAST) == len("アスレビア来てますね")


# TC-014-2
def test_prefill_replaces_existing_input(launcher):
    dw = launcher.open()
    dw.entry.insert(0, "書きかけ")
    launcher.open(prefill="JAIST")
    assert dw.entry.get() == "JAIST"


# TC-015-1
def test_open_without_prefill_keeps_input(launcher):
    dw = launcher.open()
    dw.entry.insert(0, "書きかけ")
    launcher.open()
    assert dw.entry.get() == "書きかけ"


# TC-022-1
def test_add_with_reading_registers_reading(launcher):
    dw = launcher.open()
    dw.entry.insert(0, "Claude")
    dw.reading_entry.insert(0, "クロード")
    dw._on_add()
    assert launcher.registry.get("Claude").reading == "クロード"
    assert dw.reading_entry.get() == ""


# TC-025-1
def test_edit_dialog_shows_current_reading(launcher):
    launcher.registry.add("Claude Code", reading="くろーどこーど")
    dw = launcher.open()
    dlg = dw._on_edit("Claude Code")
    assert dlg.reading_entry.get() == "くろーどこーど"


# TC-025-2
def test_edit_dialog_reading_empty_when_no_reading(launcher):
    launcher.registry.add("Agile")
    dw = launcher.open()
    dlg = dw._on_edit("Agile")
    assert dlg.reading_entry.get() == ""


# TC-026-1
def test_edit_dialog_apply_updates_reading_and_boost(launcher, tmp_path):
    launcher.registry.add("Claude Code", boost=2.0, note="AI", reading="くろーどこーど")
    dw = launcher.open()
    dlg = dw._on_edit("Claude Code")
    dlg.reading_entry.delete(0, tk.END)
    dlg.reading_entry.insert(0, "くろーどこーど、くらうどこーど")
    dlg.boost_var.set(3.0)
    dlg.apply()
    bw = WordRegistry.load(str(tmp_path / "words.json")).get("Claude Code")
    assert bw.reading == "くろーどこーど、くらうどこーど"
    assert bw.boost == 3.0
    assert bw.note == "AI"
