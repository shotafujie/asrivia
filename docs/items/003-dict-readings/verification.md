# 検証レポート: 辞書の「読み」で認識結果を置き換える

- 検証日: 2026-09-29
- 検証者: verifier サブエージェント（独立検証）
- 対象コミット: `3a186a2`（HEAD。ただし未コミットの変更あり: `asr/biasing/registry.py` / `asr/dict_window.py` / `docs/items/003-dict-readings/spec.md` / `docs/items/003-dict-readings/test-design.md` / `tests/test_dict_launcher.py`。この作業ツリーの状態を検証した）
- 対象仕様: `spec.md` / 対象テスト設計: `test-design.md`

## 判定サマリ

| 判定 | 件数 |
|------|------|
| PASS | 10 |
| FAIL | 0 |
| BLOCKED | 0 |
| **仕様の総数** | 10 |

## 仕様別の判定

記法は `docs/TRACEABILITY.md` に従う。判定は `PASS` / `FAIL` / `BLOCKED` の3値のみ。

- **SPEC-016**: PASS (TC-016-1, TC-016-2)
- **SPEC-017**: PASS (TC-017-1, TC-017-2)
- **SPEC-018**: PASS (TC-018-1)
- **SPEC-019**: PASS (TC-019-1, TC-019-2)
- **SPEC-020**: PASS (TC-020-1, TC-020-2)
- **SPEC-021**: PASS (TC-021-1, TC-021-2, TC-021-3)
- **SPEC-022**: PASS (TC-022-1)
- **SPEC-023**: PASS (TC-023-1, TC-023-2, TC-023-3)
- **SPEC-025**: PASS (TC-025-1, TC-025-2)
- **SPEC-026**: PASS (TC-026-1)

TC とテスト関数の対応（テスト定義直上のコメントで確認）:
TC-016-1..TC-023-3 は `tests/test_readings.py`、TC-022-1 / TC-025-1 / TC-025-2 / TC-026-1 は `tests/test_dict_launcher.py`
（`test_add_with_reading_registers_reading` / `test_edit_dialog_shows_current_reading` / `test_edit_dialog_reading_empty_when_no_reading` / `test_edit_dialog_apply_updates_reading_and_boost`）。

## 実行したコマンドと出力

実行時点で利用者のアプリ（`main.py --backend qwen --dynamic-vad`、PID 22803 ほか）が別プロセスで起動中だった（`pgrep -fl main.py` で確認）。

```
$ cd /Users/fujiemon/dev/speech/recognition/asrivia && uv run pytest -v
============================= test session starts ==============================
platform darwin -- Python 3.11.15, pytest-9.1.1, pluggy-1.6.0 -- /Users/fujiemon/dev/speech/recognition/asrivia/.venv/bin/python3
cachedir: .pytest_cache
rootdir: /Users/fujiemon/dev/speech/recognition/asrivia
configfile: pyproject.toml
collecting ... collected 91 items

tests/test_audio_concurrency.py::test_concurrent_device_enumeration_no_segfault PASSED [  1%]
tests/test_audio_concurrency.py::test_recorder_active_with_device_enumeration_no_segfault PASSED [  2%]
tests/test_audio_recovery.py::test_recovers_from_transient_read_error PASSED [  3%]
tests/test_audio_recovery.py::test_falls_back_to_default_device_after_repeated_failures PASSED [  4%]
tests/test_audio_recovery.py::test_status_reflects_reconnection PASSED   [  5%]
tests/test_audio_recovery.py::test_fixed_recorder_recovers_from_transient_read_error PASSED [  6%]
tests/test_caption_to_dict.py::test_prefill_is_text_of_given_utterance PASSED [  7%]
tests/test_caption_to_dict.py::test_prefill_reflects_inline_edit PASSED  [  8%]
tests/test_caption_to_dict.py::test_prefill_excludes_translation PASSED  [  9%]
tests/test_caption_to_dict.py::test_prefill_for_unknown_uid_is_none PASSED [ 10%]
tests/test_dict_launcher.py::test_first_open_creates_one_window PASSED   [ 12%]
tests/test_dict_launcher.py::test_second_open_reuses_window PASSED       [ 13%]
tests/test_dict_launcher.py::test_open_after_close_creates_new_window PASSED [ 14%]
tests/test_dict_launcher.py::test_prefill_fills_and_selects_word_entry PASSED [ 15%]
tests/test_dict_launcher.py::test_prefill_replaces_existing_input PASSED [ 16%]
tests/test_dict_launcher.py::test_open_without_prefill_keeps_input PASSED [ 17%]
tests/test_dict_launcher.py::test_add_with_reading_registers_reading PASSED [ 18%]
tests/test_dict_launcher.py::test_edit_dialog_shows_current_reading PASSED [ 19%]
tests/test_dict_launcher.py::test_edit_dialog_reading_empty_when_no_reading PASSED [ 20%]
tests/test_dict_launcher.py::test_edit_dialog_apply_updates_reading_and_boost PASSED [ 21%]
tests/test_dynamic_vad.py::test_returns_none_when_no_speech_detected PASSED [ 23%]
tests/test_dynamic_vad.py::test_returns_audio_when_speech_detected PASSED [ 24%]
tests/test_edit_result.py::test_edit_updates_matching_uid PASSED         [ 25%]
tests/test_edit_result.py::test_edit_unknown_uid_is_noop PASSED          [ 26%]
tests/test_edit_result.py::test_edit_to_empty_text_is_rejected PASSED    [ 27%]
tests/test_edit_result.py::test_edit_strips_surrounding_whitespace PASSED [ 28%]
tests/test_edit_result.py::test_edit_same_text_needs_no_redraw PASSED    [ 29%]
tests/test_edit_result.py::test_edit_keeps_existing_translation PASSED   [ 30%]
tests/test_hallucination_filter.py::test_blocks_typical_hallucination_phrase PASSED [ 31%]
tests/test_hallucination_filter.py::test_blocks_phrase_with_punctuation_and_whitespace PASSED [ 32%]
tests/test_hallucination_filter.py::test_blocks_other_known_phrases PASSED [ 34%]
tests/test_hallucination_filter.py::test_allows_genuine_speech_containing_thanks PASSED [ 35%]
tests/test_hallucination_filter.py::test_allows_normal_speech PASSED     [ 36%]
tests/test_hallucination_filter.py::test_blocks_when_whisper_reports_no_speech PASSED [ 37%]
tests/test_hallucination_filter.py::test_allows_confident_result_even_if_no_speech_prob_moderate PASSED [ 38%]
tests/test_hallucination_filter.py::test_handles_result_without_segments PASSED [ 39%]
tests/test_koepus_writer.py::test_write_pair_writes_wav_and_json PASSED  [ 40%]
tests/test_koepus_writer.py::test_write_pair_leaves_no_tmp_files PASSED  [ 41%]
tests/test_koepus_writer.py::test_write_pair_clips_overflow_samples PASSED [ 42%]
tests/test_koepus_writer.py::test_write_pair_stem_suffix_and_no_collision PASSED [ 43%]
tests/test_koepus_writer.py::test_extract_confidence_averages_avg_logprob PASSED [ 45%]
tests/test_koepus_writer.py::test_extract_confidence_returns_none_for_empty_segments PASSED [ 46%]
tests/test_koepus_writer.py::test_extract_confidence_returns_none_when_segments_missing PASSED [ 47%]
tests/test_koepus_writer.py::test_extract_confidence_returns_none_for_non_dict_result PASSED [ 48%]
tests/test_live_captions.py::test_partial_buffer_is_none_before_any_speech PASSED [ 49%]
tests/test_live_captions.py::test_partial_buffer_is_none_during_silence_only PASSED [ 50%]
tests/test_live_captions.py::test_partial_buffer_returns_speech_snapshot_with_uid PASSED [ 51%]
tests/test_live_captions.py::test_segment_uid_increments_per_segment PASSED [ 52%]
tests/test_live_captions.py::test_partial_then_final_appends_to_history PASSED [ 53%]
tests/test_live_captions.py::test_history_keeps_recent_utterances_up_to_max PASSED [ 54%]
tests/test_live_captions.py::test_late_partial_after_final_is_dropped PASSED [ 56%]
tests/test_live_captions.py::test_partial_for_next_utterance_coexists_with_history PASSED [ 57%]
tests/test_live_captions.py::test_partial_survives_delayed_earlier_final PASSED [ 58%]
tests/test_live_captions.py::test_translation_attaches_to_matching_history_entry PASSED [ 59%]
tests/test_qwen_backend.py::test_returns_whisper_compatible_dict PASSED  [ 60%]
tests/test_qwen_backend.py::test_language_ja_maps_to_japanese PASSED     [ 61%]
tests/test_qwen_backend.py::test_language_en_maps_to_english PASSED      [ 62%]
tests/test_qwen_backend.py::test_language_auto_maps_to_none PASSED       [ 63%]
tests/test_qwen_backend.py::test_audio_passed_as_16k_tuple PASSED        [ 64%]
tests/test_qwen_backend.py::test_session_loaded_with_default_model PASSED [ 65%]
tests/test_qwen_backend.py::test_session_loaded_once_and_reused PASSED   [ 67%]
tests/test_qwen_backend.py::test_no_registry_path_passes_empty_context PASSED [ 68%]
tests/test_qwen_backend.py::test_registered_words_are_passed_as_context PASSED [ 69%]
tests/test_qwen_backend.py::test_missing_registry_file_passes_empty_context PASSED [ 70%]
tests/test_qwen_backend.py::test_registry_file_update_is_reflected_on_next_transcribe PASSED [ 71%]
tests/test_qwen_backend.py::test_build_context_joins_words_in_registration_order PASSED [ 72%]
tests/test_qwen_backend.py::test_build_context_empty PASSED              [ 73%]
tests/test_qwen_backend.py::test_context_leak_is_dropped PASSED          [ 74%]
tests/test_qwen_backend.py::test_leak_detection_ignores_case_and_width PASSED [ 75%]
tests/test_qwen_backend.py::test_two_registered_words_are_not_treated_as_leak PASSED [ 76%]
tests/test_qwen_backend.py::test_context_from_words_json_keeps_registration_order PASSED [ 78%]
tests/test_qwen_backend.py::test_empty_words_json_passes_empty_context PASSED [ 79%]
tests/test_qwen_backend.py::test_same_word_repeated_counts_as_one PASSED [ 80%]
tests/test_qwen_backend.py::test_broken_words_json_keeps_previous_context PASSED [ 81%]
tests/test_qwen_backend.py::test_fixed_words_json_is_reflected_after_broken PASSED [ 82%]
tests/test_qwen_backend.py::test_broken_words_json_at_startup_passes_empty_context PASSED [ 83%]
tests/test_readings.py::test_reading_is_replaced_with_word PASSED        [ 84%]
tests/test_readings.py::test_every_occurrence_is_replaced PASSED         [ 85%]
tests/test_readings.py::test_multiple_readings_with_mixed_separators PASSED [ 86%]
tests/test_readings.py::test_empty_reading_items_are_ignored PASSED      [ 87%]
tests/test_readings.py::test_longer_reading_wins PASSED                  [ 89%]
tests/test_readings.py::test_words_without_reading_do_not_change_text PASSED [ 90%]
tests/test_readings.py::test_missing_words_json_returns_text_unchanged PASSED [ 91%]
tests/test_readings.py::test_reading_is_saved_and_loaded PASSED          [ 92%]
tests/test_readings.py::test_legacy_words_json_without_reading PASSED    [ 93%]
tests/test_readings.py::test_updated_reading_is_used_on_next_apply PASSED [ 94%]
tests/test_readings.py::test_broken_words_json_keeps_previous_readings PASSED [ 95%]
tests/test_readings.py::test_broken_words_json_at_startup_returns_text_unchanged PASSED [ 96%]
tests/test_readings.py::test_hiragana_reading_matches_katakana_output PASSED [ 97%]
tests/test_readings.py::test_katakana_reading_matches_hiragana_output PASSED [ 98%]
tests/test_readings.py::test_unmatched_text_keeps_its_kana PASSED        [100%]

=============================== warnings summary ===============================
<frozen importlib._bootstrap>:241
  <frozen importlib._bootstrap>:241: DeprecationWarning: builtin type SwigPyPacked has no __module__ attribute

<frozen importlib._bootstrap>:241
  <frozen importlib._bootstrap>:241: DeprecationWarning: builtin type SwigPyObject has no __module__ attribute

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
======================== 91 passed, 2 warnings in 5.41s ========================
sys:1: DeprecationWarning: builtin type swigvarlink has no __module__ attribute
exit=0
```

同じ条件（アプリ起動中）で続けて2回、全件を再実行した（`tests/test_audio_recovery.py` の負荷依存の失敗の有無を観測するため）。

```
$ uv run pytest -q   # 2回目
91 passed, 2 warnings in 5.52s
exit=0
$ uv run pytest -q   # 3回目
91 passed, 2 warnings in 5.32s
exit=0
```

レポート作成前（古い verification.md の状態）の実行結果:

```
$ ~/dev/.claude/hooks/trace-check.sh docs/items/003-dict-readings
=== traceability check ===
スコープ: docs/items/003-dict-readings （このアイテムに属するIDのみ検査）

[003-dict-readings] 仕様 10件 / テストケース 19件
  [1] 検証されていない仕様: 2件
      SPEC-025
      SPEC-026

[テストコード] 検出したテストケースID: 19件 (探索起点: .)

孤児: 合計 2件 — 鎖が切れています。
孤児の意味と対処は docs/TRACEABILITY.md の「孤児（orphan）の定義」を参照。
exit=1
```

本レポート作成後の実行結果:

```
$ ~/dev/.claude/hooks/trace-check.sh docs/items/003-dict-readings
=== traceability check ===
スコープ: docs/items/003-dict-readings （このアイテムに属するIDのみ検査）

[003-dict-readings] 仕様 10件 / テストケース 19件

[テストコード] 検出したテストケースID: 19件 (探索起点: .)

孤児: 0件 — 仕様・テスト設計・テストコード・検証はすべて対応が取れています。
exit=0
```

## トレーサビリティ

`trace-check.sh` の出力（本レポート作成後）から転記する。

| # | 孤児 | 件数 |
|---|------|------|
| 1 | 検証されていない仕様 | 0 |
| 2 | テストケースの無い仕様 | 0 |
| 3 | 設計にあるがコードに無いTC | 0 |
| 4 | コードにあるが設計に無いTC | 0 |
| 5 | 親仕様が存在しないTC | 0 |

（出力は「孤児: 0件」。項目別の行は件数0のため出力されていない。）

## 所見

判定を左右しないが記録すべきもの。

1. **`tests/test_audio_recovery.py` の負荷依存の失敗は今回再現しなかった。** 呼び出し元からは「アプリ起動中の負荷で失敗することが観測されている」と伝えられていたが、アプリ（`main.py --backend qwen --dynamic-vad`）起動中に全件実行を3回行い、3回とも 91 passed / exit 0 だった。失敗が起きる条件はこの検証では特定できていない。フレーキーである可能性は残る。
2. **SPEC-026 のテストは仕様より狭い。**
   - TC-026-1 は `_EditDialog.apply()` を直接呼んでおり、仕様の文言である「『適用』（ボタン）を押す」経路は通していない。コードを読むと「適用」ボタンの `command` は `self.apply` だが、この結線はテストで保証されていない。
   - 「入力値に更新」を検証しているのは、空でない読み（「くろーどこーど、くらうどこーど」）と boost 3.0 の1ケースだけ。読み欄を空にして適用すると読みが消える（読みなしに戻せる）ことは検証されていない。
   - 実装は読みを `strip()` してから保存している。前後に空白を含む入力では保存値が「入力値」と一致しない。SPEC-017 と合わせれば実害はないと考えられるが、仕様には書かれていない振る舞いである。
   - 保存の確認は、words.json を `WordRegistry.load` で読み直す方法で行っている（仕様の「words.json に保存される」は満たす）。`reload_cb`（置換器やバックエンドへの反映通知）が呼ばれることは検証されていないが、SPEC-021 の mtime による再読込で反映される設計であり、仕様の範囲外。
3. **SPEC-025 は、編集ダイアログを開く経路として `DictWindow._on_edit(word)` を直接呼んでいる。** 一覧の UI 操作（ダブルクリックやボタン）から開く経路はテストされていない（辞書ウィンドウの一覧表示は spec.md で範囲外）。
4. **未登録の語に対する `_on_edit` は `None` を返し、`update_entry` は未登録の語に対して何もしない**（コードを読んで確認）。仕様には書かれておらず、テストも無い。
5. SPEC ID の欠番: SPEC-024 はこのアイテムには定義されていない（`tests/test_qwen_backend.py` に TC-024-1 / TC-024-2 がある。SPEC-024 は `docs/items/001-qwen-context-biasing/spec.md` で定義されている。スコープ検査では孤児として出ていない）。spec.md では SPEC-023 が SPEC-022 より前に並んでいるが、判定には影響しない。
6. 前回の verification.md は SPEC-025 / SPEC-026 を含んでおらず、孤児として検出されていた。本レポートで全面的に書き直した。
