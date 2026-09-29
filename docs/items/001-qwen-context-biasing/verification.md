# 検証レポート: qwen バックエンドで辞書(words.json)を context として反映する

- 検証日: 2026-09-29
- 検証者: verifier サブエージェント（独立検証）
- 対象コミット: `f6881a1`（ブランチ `fix/qwen-leak-drop`。HEAD に未コミットの変更あり: README.md / asr/qwen_asr_backend.py / spec.md / test-design.md / tests/test_qwen_backend.py。検証はこの作業ツリーの状態に対して行った）
- 対象仕様: `spec.md` / 対象テスト設計: `test-design.md`
- 廃番: SPEC-006（spec.md 上で廃番。判定対象外）

## 判定サマリ

| 判定 | 件数 |
|------|------|
| PASS | 8 |
| FAIL | 0 |
| BLOCKED | 0 |
| **仕様の総数** | 8 |

## 仕様別の判定

- **SPEC-001**: PASS (TC-001-1)
- **SPEC-002**: PASS (TC-002-1)
- **SPEC-003**: PASS (TC-003-1, TC-003-2, TC-003-3, TC-003-4)
- **SPEC-004**: PASS (TC-004-1)
- **SPEC-005**: PASS (TC-005-1)
- **SPEC-024**: PASS (TC-024-1, TC-024-2)
- **SPEC-007**: PASS (TC-007-1, TC-007-2)
- **SPEC-008**: PASS (TC-008-1, TC-008-2, TC-008-3)

TC とテスト関数の対応（テスト定義直上の `# TC-NNN-M` コメント、tests/test_qwen_backend.py）:

| TC | テスト | 結果 |
|----|--------|------|
| TC-001-1 | test_no_registry_path_passes_empty_context | PASSED |
| TC-002-1 | test_registered_words_are_passed_as_context | PASSED |
| TC-003-1 | test_build_context_joins_words_in_registration_order | PASSED |
| TC-003-2 | test_build_context_empty | PASSED |
| TC-003-3 | test_context_from_words_json_keeps_registration_order | PASSED |
| TC-003-4 | test_empty_words_json_passes_empty_context | PASSED |
| TC-004-1 | test_missing_registry_file_passes_empty_context | PASSED |
| TC-005-1 | test_registry_file_update_is_reflected_on_next_transcribe | PASSED |
| TC-024-1 | test_context_leak_is_dropped | PASSED |
| TC-024-2 | test_leak_detection_ignores_case_and_width | PASSED |
| TC-007-1 | test_two_registered_words_are_not_treated_as_leak | PASSED |
| TC-007-2 | test_same_word_repeated_counts_as_one | PASSED |
| TC-008-1 | test_broken_words_json_keeps_previous_context | PASSED |
| TC-008-2 | test_fixed_words_json_is_reflected_after_broken | PASSED |
| TC-008-3 | test_broken_words_json_at_startup_passes_empty_context | PASSED |

## 実行したコマンドと出力

```
$ cd /Users/fujiemon/dev/speech/recognition/asrivia && uv run pytest -v
============================= test session starts ==============================
platform darwin -- Python 3.11.15, pytest-9.1.1, pluggy-1.6.0 -- /Users/fujiemon/dev/speech/recognition/asrivia/.venv/bin/python3
cachedir: .pytest_cache
rootdir: /Users/fujiemon/dev/speech/recognition/asrivia
configfile: pyproject.toml
collecting ... collected 88 items

tests/test_audio_concurrency.py::test_concurrent_device_enumeration_no_segfault PASSED [  1%]
tests/test_audio_concurrency.py::test_recorder_active_with_device_enumeration_no_segfault PASSED [  2%]
tests/test_audio_recovery.py::test_recovers_from_transient_read_error PASSED [  3%]
tests/test_audio_recovery.py::test_falls_back_to_default_device_after_repeated_failures PASSED [  4%]
tests/test_audio_recovery.py::test_status_reflects_reconnection PASSED   [  5%]
tests/test_audio_recovery.py::test_fixed_recorder_recovers_from_transient_read_error PASSED [  6%]
tests/test_caption_to_dict.py::test_prefill_is_text_of_given_utterance PASSED [  7%]
tests/test_caption_to_dict.py::test_prefill_reflects_inline_edit PASSED  [  9%]
tests/test_caption_to_dict.py::test_prefill_excludes_translation PASSED  [ 10%]
tests/test_caption_to_dict.py::test_prefill_for_unknown_uid_is_none PASSED [ 11%]
tests/test_dict_launcher.py::test_first_open_creates_one_window PASSED   [ 12%]
tests/test_dict_launcher.py::test_second_open_reuses_window PASSED       [ 13%]
tests/test_dict_launcher.py::test_open_after_close_creates_new_window PASSED [ 14%]
tests/test_dict_launcher.py::test_prefill_fills_and_selects_word_entry PASSED [ 15%]
tests/test_dict_launcher.py::test_prefill_replaces_existing_input PASSED [ 17%]
tests/test_dict_launcher.py::test_open_without_prefill_keeps_input PASSED [ 18%]
tests/test_dict_launcher.py::test_add_with_reading_registers_reading PASSED [ 19%]
tests/test_dynamic_vad.py::test_returns_none_when_no_speech_detected PASSED [ 20%]
tests/test_dynamic_vad.py::test_returns_audio_when_speech_detected PASSED [ 21%]
tests/test_edit_result.py::test_edit_updates_matching_uid PASSED         [ 22%]
tests/test_edit_result.py::test_edit_unknown_uid_is_noop PASSED          [ 23%]
tests/test_edit_result.py::test_edit_to_empty_text_is_rejected PASSED    [ 25%]
tests/test_edit_result.py::test_edit_strips_surrounding_whitespace PASSED [ 26%]
tests/test_edit_result.py::test_edit_same_text_needs_no_redraw PASSED    [ 27%]
tests/test_edit_result.py::test_edit_keeps_existing_translation PASSED   [ 28%]
tests/test_hallucination_filter.py::test_blocks_typical_hallucination_phrase PASSED [ 29%]
tests/test_hallucination_filter.py::test_blocks_phrase_with_punctuation_and_whitespace PASSED [ 30%]
tests/test_hallucination_filter.py::test_blocks_other_known_phrases PASSED [ 31%]
tests/test_hallucination_filter.py::test_allows_genuine_speech_containing_thanks PASSED [ 32%]
tests/test_hallucination_filter.py::test_allows_normal_speech PASSED     [ 34%]
tests/test_hallucination_filter.py::test_blocks_when_whisper_reports_no_speech PASSED [ 35%]
tests/test_hallucination_filter.py::test_allows_confident_result_even_if_no_speech_prob_moderate PASSED [ 36%]
tests/test_hallucination_filter.py::test_handles_result_without_segments PASSED [ 37%]
tests/test_koepus_writer.py::test_write_pair_writes_wav_and_json PASSED  [ 38%]
tests/test_koepus_writer.py::test_write_pair_leaves_no_tmp_files PASSED  [ 39%]
tests/test_koepus_writer.py::test_write_pair_clips_overflow_samples PASSED [ 40%]
tests/test_koepus_writer.py::test_write_pair_stem_suffix_and_no_collision PASSED [ 42%]
tests/test_koepus_writer.py::test_extract_confidence_averages_avg_logprob PASSED [ 43%]
tests/test_koepus_writer.py::test_extract_confidence_returns_none_for_empty_segments PASSED [ 44%]
tests/test_koepus_writer.py::test_extract_confidence_returns_none_when_segments_missing PASSED [ 45%]
tests/test_koepus_writer.py::test_extract_confidence_returns_none_for_non_dict_result PASSED [ 46%]
tests/test_live_captions.py::test_partial_buffer_is_none_before_any_speech PASSED [ 47%]
tests/test_live_captions.py::test_partial_buffer_is_none_during_silence_only PASSED [ 48%]
tests/test_live_captions.py::test_partial_buffer_returns_speech_snapshot_with_uid PASSED [ 50%]
tests/test_live_captions.py::test_segment_uid_increments_per_segment PASSED [ 51%]
tests/test_live_captions.py::test_partial_then_final_appends_to_history PASSED [ 52%]
tests/test_live_captions.py::test_history_keeps_recent_utterances_up_to_max PASSED [ 53%]
tests/test_live_captions.py::test_late_partial_after_final_is_dropped PASSED [ 54%]
tests/test_live_captions.py::test_partial_for_next_utterance_coexists_with_history PASSED [ 55%]
tests/test_live_captions.py::test_partial_survives_delayed_earlier_final PASSED [ 56%]
tests/test_live_captions.py::test_translation_attaches_to_matching_history_entry PASSED [ 57%]
tests/test_qwen_backend.py::test_returns_whisper_compatible_dict PASSED  [ 59%]
tests/test_qwen_backend.py::test_language_ja_maps_to_japanese PASSED     [ 60%]
tests/test_qwen_backend.py::test_language_en_maps_to_english PASSED      [ 61%]
tests/test_qwen_backend.py::test_language_auto_maps_to_none PASSED       [ 62%]
tests/test_qwen_backend.py::test_audio_passed_as_16k_tuple PASSED        [ 63%]
tests/test_qwen_backend.py::test_session_loaded_with_default_model PASSED [ 64%]
tests/test_qwen_backend.py::test_session_loaded_once_and_reused PASSED   [ 65%]
tests/test_qwen_backend.py::test_no_registry_path_passes_empty_context PASSED [ 67%]
tests/test_qwen_backend.py::test_registered_words_are_passed_as_context PASSED [ 68%]
tests/test_qwen_backend.py::test_missing_registry_file_passes_empty_context PASSED [ 69%]
tests/test_qwen_backend.py::test_registry_file_update_is_reflected_on_next_transcribe PASSED [ 70%]
tests/test_qwen_backend.py::test_build_context_joins_words_in_registration_order PASSED [ 71%]
tests/test_qwen_backend.py::test_build_context_empty PASSED              [ 72%]
tests/test_qwen_backend.py::test_context_leak_is_dropped PASSED          [ 73%]
tests/test_qwen_backend.py::test_leak_detection_ignores_case_and_width PASSED [ 75%]
tests/test_qwen_backend.py::test_two_registered_words_are_not_treated_as_leak PASSED [ 76%]
tests/test_qwen_backend.py::test_context_from_words_json_keeps_registration_order PASSED [ 77%]
tests/test_qwen_backend.py::test_empty_words_json_passes_empty_context PASSED [ 78%]
tests/test_qwen_backend.py::test_same_word_repeated_counts_as_one PASSED [ 79%]
tests/test_qwen_backend.py::test_broken_words_json_keeps_previous_context PASSED [ 80%]
tests/test_qwen_backend.py::test_fixed_words_json_is_reflected_after_broken PASSED [ 81%]
tests/test_qwen_backend.py::test_broken_words_json_at_startup_passes_empty_context PASSED [ 82%]
tests/test_readings.py::test_reading_is_replaced_with_word PASSED        [ 84%]
tests/test_readings.py::test_every_occurrence_is_replaced PASSED         [ 85%]
tests/test_readings.py::test_multiple_readings_with_mixed_separators PASSED [ 86%]
tests/test_readings.py::test_empty_reading_items_are_ignored PASSED      [ 87%]
tests/test_readings.py::test_longer_reading_wins PASSED                  [ 88%]
tests/test_readings.py::test_words_without_reading_do_not_change_text PASSED [ 89%]
tests/test_readings.py::test_missing_words_json_returns_text_unchanged PASSED [ 90%]
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
======================== 88 passed, 2 warnings in 5.35s ========================
sys:1: DeprecationWarning: builtin type swigvarlink has no __module__ attribute
```

終了コード: 0

```
$ ~/dev/.claude/hooks/trace-check.sh docs/items/001-qwen-context-biasing
=== traceability check ===
スコープ: docs/items/001-qwen-context-biasing （このアイテムに属するIDのみ検査）

[001-qwen-context-biasing] 仕様 8件 / テストケース 15件

[テストコード] 検出したテストケースID: 15件 (探索起点: .)

孤児: 0件 — 仕様・テスト設計・テストコード・検証はすべて対応が取れています。

(終了コード: 0)
```

## トレーサビリティ

`trace-check.sh` の出力（上記、本レポート書き出し後に実行）から転記。

| # | 孤児 | 件数 |
|---|------|------|
| 1 | 検証されていない仕様 | 0 |
| 2 | テストケースの無い仕様 | 0 |
| 3 | 設計にあるがコードに無いTC | 0 |
| 4 | コードにあるが設計に無いTC | 0 |
| 5 | 親仕様が存在しないTC | 0 |

（出力の「孤児: 0件」から転記。1〜5 のどの種別の行も出力に現れていない）

## 所見

判定を左右しないが記録すべきもの。

1. **「context を空文字で呼ぶ」をテストが区別できていない（テストが仕様より狭い）。**
   テストのヘルパ `_context_of` は `call["kwargs"].get("context", "")` で、context 引数が**渡されなかった**場合も空文字として扱う。
   そのため TC-001-1 / TC-003-4 / TC-004-1 / TC-008-3 は「context=\"\" を渡した」と「context を渡さなかった」を区別しない。
   SPEC-001 / SPEC-004 は「context を空文字で呼ぶ」と書いているので、厳密にはこのテストは仕様より弱い。
   なお実装（asr/qwen_asr_backend.py:107-109）は常に `context=self.context` を渡しており、現状では差は出ていない。
2. **SPEC-024 の「異なる登録語」の数え方で、仕様にない振る舞いがある（プローブで観測）。**
   照合は NFKC＋小文字化した登録語の集合で数えるため、次のようになる。スクラッチのスクリプトで偽の Session を使って確認した（リポジトリは変更していない）。
   - 大文字小文字だけが違う語を別々に登録（`AI` / `ai` / `JAIST`）し、出力が `"AI ai JAIST"` の場合、2語と数えられて破棄されない（出力 `'AI ai JAIST'` がそのまま返った）。登録上は3語だが、照合上は1語にまとまる。
   - 空文字の語 `{"word": ""}` が words.json にあると、どの出力にも一致する語として数えられる。`["", "JAIST", "情報保障"]` を登録し、出力が `"JAISTで情報保障"` の場合、登録語2語しか含まない出力が破棄された（戻り値 `''`）。SPEC-007 の意図に反する。
     辞書UI（asr/dict_window.py:97）は空の語を登録しないため、手で編集した words.json に限る。
3. **スキーマ違反の words.json は SPEC-008 の対象外で、認識が例外になる（プローブで観測）。**
   JSON として読めるが `word` が文字列でない `[{"word": 1}]` の場合、`build_context` で
   `TypeError: sequence item 0: expected str instance, int found` が発生する。この処理は try の外（asr/qwen_asr_backend.py:91）なので、生成時・認識時に例外が呼び出し元に出る。
   SPEC-008 は「JSON として読めない場合」に限っているため判定には影響しないが、「例外を出さない」という保証の外にある入力が存在する。
   なお `{"x": 1}`（リストでない JSON）は TypeError が捕捉され、context は空文字になった。
4. **SPEC-024 / SPEC-007 の境界は両側ともテストされている。** TC-024-2 がちょうど3語、TC-024-1 が4語、TC-007-1 がちょうど2語、TC-007-2 が1語（同じ語を3回繰り返す）。登録語を1つも含まない出力が context 付きでそのまま返ることは、TC として明示的には設計されていない（SPEC-007 の「2以下」には0が含まれる）。
5. **SPEC-005 は語の追加だけをテストしている。** 語の削除や並べ替えで context から語が消えることはテストされていない。「更新後の登録語が反映される」の一部だけを確かめている。
6. **SPEC-002 は2語だけでテストしている。** 「すべて」を2語（英字1・日本語1）で代表させている。SPEC-003 の TC-003-3（3語の完全一致）が実質的に補っている。
7. 既知の制約（部分文字列一致による短語の誤一致、2語以下の辞書で漏れを検出できないこと、mtime 依存）は仕様として受け入れ済みのため、判定・所見の対象にしていない。
