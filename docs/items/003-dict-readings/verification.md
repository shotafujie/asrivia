# 検証レポート: 辞書の「読み」で認識結果を置き換える

- 検証日: 2026-09-29
- 検証者: verifier サブエージェント（独立検証）
- 対象コミット: `96fa168`（ブランチ feature/dict-readings。未コミットの作業ツリー変更を含む状態を検証: `asr/biasing/readings.py` 新規, `asr/biasing/registry.py` / `asr/dict_window.py` / `main.py` / `tests/test_dict_launcher.py` 変更, `tests/test_readings.py` 新規）
- 対象仕様: `spec.md` / 対象テスト設計: `test-design.md`

## 判定サマリ

| 判定 | 件数 |
|------|------|
| PASS | 7 |
| FAIL | 0 |
| BLOCKED | 0 |
| **仕様の総数** | 7 |

## 仕様別の判定

- **SPEC-016**: PASS (TC-016-1, TC-016-2)
- **SPEC-017**: PASS (TC-017-1, TC-017-2)
- **SPEC-018**: PASS (TC-018-1)
- **SPEC-019**: PASS (TC-019-1, TC-019-2)
- **SPEC-020**: PASS (TC-020-1, TC-020-2)
- **SPEC-021**: PASS (TC-021-1, TC-021-2, TC-021-3)
- **SPEC-022**: PASS (TC-022-1)

TC とテスト関数の対応（テスト定義直上のコメントで確認）:

| TC | テスト |
|----|--------|
| TC-016-1 | tests/test_readings.py::test_reading_is_replaced_with_word |
| TC-016-2 | tests/test_readings.py::test_every_occurrence_is_replaced |
| TC-017-1 | tests/test_readings.py::test_multiple_readings_with_mixed_separators |
| TC-017-2 | tests/test_readings.py::test_empty_reading_items_are_ignored |
| TC-018-1 | tests/test_readings.py::test_longer_reading_wins |
| TC-019-1 | tests/test_readings.py::test_words_without_reading_do_not_change_text |
| TC-019-2 | tests/test_readings.py::test_missing_words_json_returns_text_unchanged |
| TC-020-1 | tests/test_readings.py::test_reading_is_saved_and_loaded |
| TC-020-2 | tests/test_readings.py::test_legacy_words_json_without_reading |
| TC-021-1 | tests/test_readings.py::test_updated_reading_is_used_on_next_apply |
| TC-021-2 | tests/test_readings.py::test_broken_words_json_keeps_previous_readings |
| TC-021-3 | tests/test_readings.py::test_broken_words_json_at_startup_returns_text_unchanged |
| TC-022-1 | tests/test_dict_launcher.py::test_add_with_reading_registers_reading |

## 実行したコマンドと出力

```
$ cd /Users/fujiemon/dev/speech/recognition/asrivia && uv run pytest -v
============================= test session starts ==============================
platform darwin -- Python 3.11.15, pytest-9.1.1, pluggy-1.6.0 -- /Users/fujiemon/dev/speech/recognition/asrivia/.venv/bin/python3
cachedir: .pytest_cache
rootdir: /Users/fujiemon/dev/speech/recognition/asrivia
configfile: pyproject.toml
collecting ... collected 85 items

tests/test_audio_concurrency.py::test_concurrent_device_enumeration_no_segfault PASSED [  1%]
tests/test_audio_concurrency.py::test_recorder_active_with_device_enumeration_no_segfault PASSED [  2%]
tests/test_audio_recovery.py::test_recovers_from_transient_read_error PASSED [  3%]
tests/test_audio_recovery.py::test_falls_back_to_default_device_after_repeated_failures PASSED [  4%]
tests/test_audio_recovery.py::test_status_reflects_reconnection PASSED   [  5%]
tests/test_audio_recovery.py::test_fixed_recorder_recovers_from_transient_read_error PASSED [  7%]
tests/test_caption_to_dict.py::test_prefill_is_text_of_given_utterance PASSED [  8%]
tests/test_caption_to_dict.py::test_prefill_reflects_inline_edit PASSED  [  9%]
tests/test_caption_to_dict.py::test_prefill_excludes_translation PASSED  [ 10%]
tests/test_caption_to_dict.py::test_prefill_for_unknown_uid_is_none PASSED [ 11%]
tests/test_dict_launcher.py::test_first_open_creates_one_window PASSED   [ 12%]
tests/test_dict_launcher.py::test_second_open_reuses_window PASSED       [ 14%]
tests/test_dict_launcher.py::test_open_after_close_creates_new_window PASSED [ 15%]
tests/test_dict_launcher.py::test_prefill_fills_and_selects_word_entry PASSED [ 16%]
tests/test_dict_launcher.py::test_prefill_replaces_existing_input PASSED [ 17%]
tests/test_dict_launcher.py::test_open_without_prefill_keeps_input PASSED [ 18%]
tests/test_dict_launcher.py::test_add_with_reading_registers_reading PASSED [ 20%]
tests/test_dynamic_vad.py::test_returns_none_when_no_speech_detected PASSED [ 21%]
tests/test_dynamic_vad.py::test_returns_audio_when_speech_detected PASSED [ 22%]
tests/test_edit_result.py::test_edit_updates_matching_uid PASSED         [ 23%]
tests/test_edit_result.py::test_edit_unknown_uid_is_noop PASSED          [ 24%]
tests/test_edit_result.py::test_edit_to_empty_text_is_rejected PASSED    [ 25%]
tests/test_edit_result.py::test_edit_strips_surrounding_whitespace PASSED [ 27%]
tests/test_edit_result.py::test_edit_same_text_needs_no_redraw PASSED    [ 28%]
tests/test_edit_result.py::test_edit_keeps_existing_translation PASSED   [ 29%]
tests/test_hallucination_filter.py::test_blocks_typical_hallucination_phrase PASSED [ 30%]
tests/test_hallucination_filter.py::test_blocks_phrase_with_punctuation_and_whitespace PASSED [ 31%]
tests/test_hallucination_filter.py::test_blocks_other_known_phrases PASSED [ 32%]
tests/test_hallucination_filter.py::test_allows_genuine_speech_containing_thanks PASSED [ 34%]
tests/test_hallucination_filter.py::test_allows_normal_speech PASSED     [ 35%]
tests/test_hallucination_filter.py::test_blocks_when_whisper_reports_no_speech PASSED [ 36%]
tests/test_hallucination_filter.py::test_allows_confident_result_even_if_no_speech_prob_moderate PASSED [ 37%]
tests/test_hallucination_filter.py::test_handles_result_without_segments PASSED [ 38%]
tests/test_koepus_writer.py::test_write_pair_writes_wav_and_json PASSED  [ 40%]
tests/test_koepus_writer.py::test_write_pair_leaves_no_tmp_files PASSED  [ 41%]
tests/test_koepus_writer.py::test_write_pair_clips_overflow_samples PASSED [ 42%]
tests/test_koepus_writer.py::test_write_pair_stem_suffix_and_no_collision PASSED [ 43%]
tests/test_koepus_writer.py::test_extract_confidence_averages_avg_logprob PASSED [ 44%]
tests/test_koepus_writer.py::test_extract_confidence_returns_none_for_empty_segments PASSED [ 45%]
tests/test_koepus_writer.py::test_extract_confidence_returns_none_when_segments_missing PASSED [ 47%]
tests/test_koepus_writer.py::test_extract_confidence_returns_none_for_non_dict_result PASSED [ 48%]
tests/test_live_captions.py::test_partial_buffer_is_none_before_any_speech PASSED [ 49%]
tests/test_live_captions.py::test_partial_buffer_is_none_during_silence_only PASSED [ 50%]
tests/test_live_captions.py::test_partial_buffer_returns_speech_snapshot_with_uid PASSED [ 51%]
tests/test_live_captions.py::test_segment_uid_increments_per_segment PASSED [ 52%]
tests/test_live_captions.py::test_partial_then_final_appends_to_history PASSED [ 54%]
tests/test_live_captions.py::test_history_keeps_recent_utterances_up_to_max PASSED [ 55%]
tests/test_live_captions.py::test_late_partial_after_final_is_dropped PASSED [ 56%]
tests/test_live_captions.py::test_partial_for_next_utterance_coexists_with_history PASSED [ 57%]
tests/test_live_captions.py::test_partial_survives_delayed_earlier_final PASSED [ 58%]
tests/test_live_captions.py::test_translation_attaches_to_matching_history_entry PASSED [ 60%]
tests/test_qwen_backend.py::test_returns_whisper_compatible_dict PASSED  [ 61%]
tests/test_qwen_backend.py::test_language_ja_maps_to_japanese PASSED     [ 62%]
tests/test_qwen_backend.py::test_language_en_maps_to_english PASSED      [ 63%]
tests/test_qwen_backend.py::test_language_auto_maps_to_none PASSED       [ 64%]
tests/test_qwen_backend.py::test_audio_passed_as_16k_tuple PASSED        [ 65%]
tests/test_qwen_backend.py::test_session_loaded_with_default_model PASSED [ 67%]
tests/test_qwen_backend.py::test_session_loaded_once_and_reused PASSED   [ 68%]
tests/test_qwen_backend.py::test_no_registry_path_passes_empty_context PASSED [ 69%]
tests/test_qwen_backend.py::test_registered_words_are_passed_as_context PASSED [ 70%]
tests/test_qwen_backend.py::test_missing_registry_file_passes_empty_context PASSED [ 71%]
tests/test_qwen_backend.py::test_registry_file_update_is_reflected_on_next_transcribe PASSED [ 72%]
tests/test_qwen_backend.py::test_build_context_joins_words_in_registration_order PASSED [ 74%]
tests/test_qwen_backend.py::test_build_context_empty PASSED              [ 75%]
tests/test_qwen_backend.py::test_context_leak_is_retried_without_context PASSED [ 76%]
tests/test_qwen_backend.py::test_leak_detection_ignores_case_and_width PASSED [ 77%]
tests/test_qwen_backend.py::test_two_registered_words_are_not_treated_as_leak PASSED [ 78%]
tests/test_qwen_backend.py::test_context_from_words_json_keeps_registration_order PASSED [ 80%]
tests/test_qwen_backend.py::test_empty_words_json_passes_empty_context PASSED [ 81%]
tests/test_qwen_backend.py::test_same_word_repeated_counts_as_one PASSED [ 82%]
tests/test_qwen_backend.py::test_broken_words_json_keeps_previous_context PASSED [ 83%]
tests/test_qwen_backend.py::test_fixed_words_json_is_reflected_after_broken PASSED [ 84%]
tests/test_qwen_backend.py::test_broken_words_json_at_startup_passes_empty_context PASSED [ 85%]
tests/test_readings.py::test_reading_is_replaced_with_word PASSED        [ 87%]
tests/test_readings.py::test_every_occurrence_is_replaced PASSED         [ 88%]
tests/test_readings.py::test_multiple_readings_with_mixed_separators PASSED [ 89%]
tests/test_readings.py::test_empty_reading_items_are_ignored PASSED      [ 90%]
tests/test_readings.py::test_longer_reading_wins PASSED                  [ 91%]
tests/test_readings.py::test_words_without_reading_do_not_change_text PASSED [ 92%]
tests/test_readings.py::test_missing_words_json_returns_text_unchanged PASSED [ 94%]
tests/test_readings.py::test_reading_is_saved_and_loaded PASSED          [ 95%]
tests/test_readings.py::test_legacy_words_json_without_reading PASSED    [ 96%]
tests/test_readings.py::test_updated_reading_is_used_on_next_apply PASSED [ 97%]
tests/test_readings.py::test_broken_words_json_keeps_previous_readings PASSED [ 98%]
tests/test_readings.py::test_broken_words_json_at_startup_returns_text_unchanged PASSED [100%]

=============================== warnings summary ===============================
<frozen importlib._bootstrap>:241
  <frozen importlib._bootstrap>:241: DeprecationWarning: builtin type SwigPyPacked has no __module__ attribute

<frozen importlib._bootstrap>:241
  <frozen importlib._bootstrap>:241: DeprecationWarning: builtin type SwigPyObject has no __module__ attribute

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
======================== 85 passed, 2 warnings in 6.11s ========================
sys:1: DeprecationWarning: builtin type swigvarlink has no __module__ attribute
$ echo $?
0
```

```
$ ~/dev/.claude/hooks/trace-check.sh docs/items/003-dict-readings
=== traceability check ===
スコープ: docs/items/003-dict-readings （このアイテムに属するIDのみ検査）

[003-dict-readings] 仕様 7件 / テストケース 13件

[テストコード] 検出したテストケースID: 13件 (探索起点: .)

孤児: 0件 — 仕様・テスト設計・テストコード・検証はすべて対応が取れています。
$ echo $?
0
```

## トレーサビリティ

`trace-check.sh` の出力（レポート作成後の実行、終了コード 0）は「孤児: 0件」で、カテゴリ別の孤児行は出力されていない。

| # | 孤児 | 件数 |
|---|------|------|
| 1 | 検証されていない仕様 | 0 |
| 2 | テストケースの無い仕様 | 0 |
| 3 | 設計にあるがコードに無いTC | 0 |
| 4 | コードにあるが設計に無いTC | 0 |
| 5 | 親仕様が存在しないTC | 0 |

参考: レポート作成前の実行では `[1] 検証されていない仕様: 7件 (verification.md が未作成)`（SPEC-016〜SPEC-022）で exit 1 だった。それ以外の孤児は出ていなかった。

## 所見

判定は変えないが記録すべきもの。

1. **SPEC-021 の「更新された場合」はテストより広い。** 実装は words.json の mtime が前回と異なるときだけ読み直す（`asr/biasing/readings.py` `_reload_if_changed`）。TC-021-1 / TC-021-2 はいずれも `os.utime` で mtime を +10 秒進めてから検証しており、「mtime が変わらない（同一タイムスタンプ内の）更新」のケースは検証されていない。APFS はナノ秒精度のため実害は小さいと考えられるが、仕様の保証は「更新された場合」全般であり、テストはその部分集合しか確かめていない。
2. **仕様に書かれていない振る舞い: 読めていた words.json が削除された場合。** 削除されると mtime が 0.0 扱いになり、`WordRegistry.load` が空の辞書を返すため置換表が空になる（直前の読みは保持されない）。SPEC-021 は「JSON として読めない場合」のみを規定しており、ファイル消失時の扱いは仕様・テストとも未定義。
3. **仕様に書かれていない振る舞い: 同じ読みを複数の登録語が持つ場合。** 置換表は `dict` で、words.json 上で後に現れる語が黙って勝つ。仕様・テスト設計とも未定義。
4. **SPEC-016 の「すべて置き換える」は部分文字列一致である。** 語境界を見ないため、短い読み（例: 2文字のカタカナ）を登録すると無関係な語の一部も置換される。仕様の文言どおりの振る舞いだが、利用上のリスクとして記録する。半角カナ（ｸﾛｰﾄﾞ）や表記ゆれは置換されない（仕様上も要求なし）。
5. **SPEC-017 の「前後の空白を除いた」について。** TC-017-1 は区切り直後の先頭空白（「, ダイスト」）、TC-017-2 は空白のみの要素を検証しているが、読みの末尾に空白が付いた非空要素（例「クロード ,ダイスト」）の除去は直接は検証していない。実装は各要素に `strip()` を適用している。
6. **SPEC-022 のテストは `_on_add()` を直接呼んでいる。** 「追加」ボタンの押下（`invoke`）経由ではないため、ボタンと `_on_add` の結線は検証範囲外。GUI 表示を伴う確認は spec.md の範囲外（手動確認）と整合する。
7. **範囲外項目（手動確認）は判定対象外。** `main.py` では hf / qwen バックエンドのときのみ確定テキストに `ReadingReplacer("words.json").apply` を適用する差分を確認したが、字幕・翻訳・koepus への受け渡しは自動テストで検証していない（spec.md の範囲外として明記済み）。
8. 既存テストを含む全 85 件が成功（終了コード 0）。他機能の回帰は観測されなかった。
