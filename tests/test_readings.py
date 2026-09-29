"""辞書の「読み」による認識結果の置換(ReadingReplacer)と保存形式のテスト。"""

import json
import os

from asr.biasing import WordRegistry
from asr.biasing.readings import ReadingReplacer


def _write(path, entries):
    path.write_text(json.dumps(entries, ensure_ascii=False), encoding="utf-8")


def _replacer(tmp_path, entries):
    p = tmp_path / "words.json"
    _write(p, entries)
    return ReadingReplacer(str(p)), p


def _bump_mtime(path, sec):
    st = os.stat(path)
    os.utime(path, (st.st_atime, st.st_mtime + sec))


# TC-016-1
def test_reading_is_replaced_with_word(tmp_path):
    r, _ = _replacer(tmp_path, [{"word": "Claude", "reading": "クロード"}])
    assert r.apply("クロードで実装した") == "Claudeで実装した"


# TC-016-2
def test_every_occurrence_is_replaced(tmp_path):
    r, _ = _replacer(tmp_path, [{"word": "Claude", "reading": "クロード"}])
    assert r.apply("クロードとクロード") == "ClaudeとClaude"


# TC-017-1
def test_multiple_readings_with_mixed_separators(tmp_path):
    r, _ = _replacer(
        tmp_path, [{"word": "JAIST", "reading": "ジャイスト, ダイスト、ジェイスト，ジャイスド"}]
    )
    assert r.apply("ジャイスト") == "JAIST"
    assert r.apply("ダイスト") == "JAIST"
    assert r.apply("ジェイスト") == "JAIST"
    assert r.apply("ジャイスド") == "JAIST"


# TC-017-2
def test_empty_reading_items_are_ignored(tmp_path):
    r, _ = _replacer(tmp_path, [{"word": "Claude", "reading": "クロード,,  "}])
    assert r.apply("クロードで実装した") == "Claudeで実装した"
    assert r.apply("今日は晴れ") == "今日は晴れ"


# TC-018-1
def test_longer_reading_wins(tmp_path):
    r, _ = _replacer(
        tmp_path,
        [
            {"word": "Claude", "reading": "クロード"},
            {"word": "Claude Code", "reading": "クロードコード"},
        ],
    )
    assert r.apply("クロードコードで") == "Claude Codeで"


# TC-019-1
def test_words_without_reading_do_not_change_text(tmp_path):
    r, _ = _replacer(tmp_path, [{"word": "Claude"}])
    assert r.apply("クロードで実装した") == "クロードで実装した"


# TC-019-2
def test_missing_words_json_returns_text_unchanged(tmp_path):
    r = ReadingReplacer(str(tmp_path / "none.json"))
    assert r.apply("クロードで実装した") == "クロードで実装した"


# TC-020-1
def test_reading_is_saved_and_loaded(tmp_path):
    p = tmp_path / "words.json"
    reg = WordRegistry.load(str(p))
    reg.add("Claude", reading="クロード")
    data = json.loads(p.read_text(encoding="utf-8"))
    assert data[0]["reading"] == "クロード"
    assert WordRegistry.load(str(p)).get("Claude").reading == "クロード"


# TC-020-2
def test_legacy_words_json_without_reading(tmp_path):
    p = tmp_path / "words.json"
    _write(p, [{"word": "Agile", "boost": 2.0, "note": ""}, {"word": "JAIST"}])
    reg = WordRegistry.load(str(p))
    assert [bw.reading for bw in reg.all()] == ["", ""]


# TC-021-1
def test_updated_reading_is_used_on_next_apply(tmp_path):
    r, p = _replacer(tmp_path, [{"word": "Claude"}])
    assert r.apply("クロード") == "クロード"
    _write(p, [{"word": "Claude", "reading": "クロード"}])
    _bump_mtime(p, 10)
    assert r.apply("クロード") == "Claude"


# TC-021-2
def test_broken_words_json_keeps_previous_readings(tmp_path):
    r, p = _replacer(tmp_path, [{"word": "Claude", "reading": "クロード"}])
    assert r.apply("クロード") == "Claude"
    p.write_text('[{"word": "Claude", "rea', encoding="utf-8")
    _bump_mtime(p, 10)
    assert r.apply("クロード") == "Claude"


# TC-021-3
def test_broken_words_json_at_startup_returns_text_unchanged(tmp_path):
    p = tmp_path / "words.json"
    p.write_text("[{", encoding="utf-8")
    r = ReadingReplacer(str(p))
    assert r.apply("クロード") == "クロード"
