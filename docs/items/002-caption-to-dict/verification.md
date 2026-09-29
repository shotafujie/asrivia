# 検証レポート: 確定字幕から辞書登録を開く

- 検証日: 2026-09-29
- 検証者: verifier サブエージェント（独立検証）
- 対象コミット: `8cc0eb6`（ブランチ feature/caption-to-dict。未コミットの変更 README.md / asr/dict_window.py / main.py / tests/test_caption_to_dict.py / tests/test_dict_launcher.py を含む作業ツリーを検証）
- 対象仕様: `spec.md` / 対象テスト設計: `test-design.md`

## 判定サマリ

| 判定 | 件数 |
|------|------|
| PASS | 7 |
| FAIL | 0 |
| BLOCKED | 0 |
| **仕様の総数** | 7 |

## 仕様別の判定

記法は `docs/TRACEABILITY.md` に従う。判定は `PASS` / `FAIL` / `BLOCKED` の3値のみ。

- **SPEC-009**: PASS (TC-009-1, TC-009-2, TC-009-3)
- **SPEC-010**: PASS (TC-010-1)
- **SPEC-011**: PASS (TC-011-1)
- **SPEC-012**: PASS (TC-012-1)
- **SPEC-013**: PASS (TC-013-1)
- **SPEC-014**: PASS (TC-014-1, TC-014-2)
- **SPEC-015**: PASS (TC-015-1)

spec.md の「範囲外」（右クリックメニューの表示、前面化とフォーカス、hf / qwen 以外でメニューが出ないこと）は手動確認事項であり、本レポートの判定対象外。GUI の表示操作・マイク・実モデルは使用していない。

## 実行したコマンドと出力

判定の根拠。**要約せず、実際の出力を貼る。**

```
$ uv run pytest -v
============================= test session starts ==============================
platform darwin -- Python 3.11.15, pytest-9.1.1, pluggy-1.6.0 -- /Users/fujiemon/dev/speech/recognition/asrivia/.venv/bin/python3
cachedir: .pytest_cache
rootdir: /Users/fujiemon/dev/speech/recognition/asrivia
configfile: pyproject.toml
collecting ... collected 72 items

tests/test_audio_concurrency.py::test_concurrent_device_enumeration_no_segfault PASSED [  1%]
tests/test_audio_concurrency.py::test_recorder_active_with_device_enumeration_no_segfault PASSED [  2%]
tests/test_audio_recovery.py::test_recovers_from_transient_read_error PASSED [  4%]
tests/test_audio_recovery.py::test_falls_back_to_default_device_after_repeated_failures PASSED [  5%]
tests/test_audio_recovery.py::test_status_reflects_reconnection PASSED   [  6%]
tests/test_audio_recovery.py::test_fixed_recorder_recovers_from_transient_read_error PASSED [  8%]
tests/test_caption_to_dict.py::test_prefill_is_text_of_given_utterance PASSED [  9%]
tests/test_caption_to_dict.py::test_prefill_reflects_inline_edit PASSED  [ 11%]
tests/test_caption_to_dict.py::test_prefill_excludes_translation PASSED  [ 12%]
tests/test_caption_to_dict.py::test_prefill_for_unknown_uid_is_none PASSED [ 13%]
tests/test_dict_launcher.py::test_first_open_creates_one_window PASSED   [ 15%]
tests/test_dict_launcher.py::test_second_open_reuses_window PASSED       [ 16%]
tests/test_dict_launcher.py::test_open_after_close_creates_new_window PASSED [ 18%]
tests/test_dict_launcher.py::test_prefill_fills_and_selects_word_entry PASSED [ 19%]
tests/test_dict_launcher.py::test_prefill_replaces_existing_input PASSED [ 20%]
tests/test_dict_launcher.py::test_open_without_prefill_keeps_input PASSED [ 22%]
tests/test_dynamic_vad.py::test_returns_none_when_no_speech_detected PASSED [ 23%]
tests/test_dynamic_vad.py::test_returns_audio_when_speech_detected PASSED [ 25%]
tests/test_edit_result.py::test_edit_updates_matching_uid PASSED         [ 26%]
tests/test_edit_result.py::test_edit_unknown_uid_is_noop PASSED          [ 27%]
tests/test_edit_result.py::test_edit_to_empty_text_is_rejected PASSED    [ 29%]
tests/test_edit_result.py::test_edit_strips_surrounding_whitespace PASSED [ 30%]
tests/test_edit_result.py::test_edit_same_text_needs_no_redraw PASSED    [ 31%]
tests/test_edit_result.py::test_edit_keeps_existing_translation PASSED   [ 33%]
tests/test_hallucination_filter.py::test_blocks_typical_hallucination_phrase PASSED [ 34%]
tests/test_hallucination_filter.py::test_blocks_phrase_with_punctuation_and_whitespace PASSED [ 36%]
tests/test_hallucination_filter.py::test_blocks_other_known_phrases PASSED [ 37%]
tests/test_hallucination_filter.py::test_allows_genuine_speech_containing_thanks PASSED [ 38%]
tests/test_hallucination_filter.py::test_allows_normal_speech PASSED     [ 40%]
tests/test_hallucination_filter.py::test_blocks_when_whisper_reports_no_speech PASSED [ 41%]
tests/test_hallucination_filter.py::test_allows_confident_result_even_if_no_speech_prob_moderate PASSED [ 43%]
tests/test_hallucination_filter.py::test_handles_result_without_segments PASSED [ 44%]
tests/test_koepus_writer.py::test_write_pair_writes_wav_and_json PASSED  [ 45%]
tests/test_koepus_writer.py::test_write_pair_leaves_no_tmp_files PASSED  [ 47%]
tests/test_koepus_writer.py::test_write_pair_clips_overflow_samples PASSED [ 48%]
tests/test_koepus_writer.py::test_write_pair_stem_suffix_and_no_collision PASSED [ 50%]
tests/test_koepus_writer.py::test_extract_confidence_averages_avg_logprob PASSED [ 51%]
tests/test_koepus_writer.py::test_extract_confidence_returns_none_for_empty_segments PASSED [ 52%]
tests/test_koepus_writer.py::test_extract_confidence_returns_none_when_segments_missing PASSED [ 54%]
tests/test_koepus_writer.py::test_extract_confidence_returns_none_for_non_dict_result PASSED [ 55%]
tests/test_live_captions.py::test_partial_buffer_is_none_before_any_speech PASSED [ 56%]
tests/test_live_captions.py::test_partial_buffer_is_none_during_silence_only PASSED [ 58%]
tests/test_live_captions.py::test_partial_buffer_returns_speech_snapshot_with_uid PASSED [ 59%]
tests/test_live_captions.py::test_segment_uid_increments_per_segment PASSED [ 61%]
tests/test_live_captions.py::test_partial_then_final_appends_to_history PASSED [ 62%]
tests/test_live_captions.py::test_history_keeps_recent_utterances_up_to_max PASSED [ 63%]
tests/test_live_captions.py::test_late_partial_after_final_is_dropped PASSED [ 65%]
tests/test_live_captions.py::test_partial_for_next_utterance_coexists_with_history PASSED [ 66%]
tests/test_live_captions.py::test_partial_survives_delayed_earlier_final PASSED [ 68%]
tests/test_live_captions.py::test_translation_attaches_to_matching_history_entry PASSED [ 69%]
tests/test_qwen_backend.py::test_returns_whisper_compatible_dict PASSED  [ 70%]
tests/test_qwen_backend.py::test_language_ja_maps_to_japanese PASSED     [ 72%]
tests/test_qwen_backend.py::test_language_en_maps_to_english PASSED      [ 73%]
tests/test_qwen_backend.py::test_language_auto_maps_to_none PASSED       [ 75%]
tests/test_qwen_backend.py::test_audio_passed_as_16k_tuple PASSED        [ 76%]
tests/test_qwen_backend.py::test_session_loaded_with_default_model PASSED [ 77%]
tests/test_qwen_backend.py::test_session_loaded_once_and_reused PASSED   [ 79%]
tests/test_qwen_backend.py::test_no_registry_path_passes_empty_context PASSED [ 80%]
tests/test_qwen_backend.py::test_registered_words_are_passed_as_context PASSED [ 81%]
tests/test_qwen_backend.py::test_missing_registry_file_passes_empty_context PASSED [ 83%]
tests/test_qwen_backend.py::test_registry_file_update_is_reflected_on_next_transcribe PASSED [ 84%]
tests/test_qwen_backend.py::test_build_context_joins_words_in_registration_order PASSED [ 86%]
tests/test_qwen_backend.py::test_build_context_empty PASSED              [ 87%]
tests/test_qwen_backend.py::test_context_leak_is_retried_without_context PASSED [ 88%]
tests/test_qwen_backend.py::test_leak_detection_ignores_case_and_width PASSED [ 90%]
tests/test_qwen_backend.py::test_two_registered_words_are_not_treated_as_leak PASSED [ 91%]
tests/test_qwen_backend.py::test_context_from_words_json_keeps_registration_order PASSED [ 93%]
tests/test_qwen_backend.py::test_empty_words_json_passes_empty_context PASSED [ 94%]
tests/test_qwen_backend.py::test_same_word_repeated_counts_as_one PASSED [ 95%]
tests/test_qwen_backend.py::test_broken_words_json_keeps_previous_context PASSED [ 97%]
tests/test_qwen_backend.py::test_fixed_words_json_is_reflected_after_broken PASSED [ 98%]
tests/test_qwen_backend.py::test_broken_words_json_at_startup_passes_empty_context PASSED [100%]

=============================== warnings summary ===============================
<frozen importlib._bootstrap>:241
  <frozen importlib._bootstrap>:241: DeprecationWarning: builtin type SwigPyPacked has no __module__ attribute

<frozen importlib._bootstrap>:241
  <frozen importlib._bootstrap>:241: DeprecationWarning: builtin type SwigPyObject has no __module__ attribute

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
======================== 72 passed, 2 warnings in 5.04s ========================
sys:1: DeprecationWarning: builtin type swigvarlink has no __module__ attribute
```

終了コード: `0`（72 passed, 2 warnings。skip / xfail なし）

```
$ ~/dev/.claude/hooks/trace-check.sh docs/items/002-caption-to-dict
=== traceability check ===
スコープ: docs/items/002-caption-to-dict （このアイテムに属するIDのみ検査）

[002-caption-to-dict] 仕様 7件 / テストケース 10件

[テストコード] 検出したテストケースID: 10件 (探索起点: .)

孤児: 0件 — 仕様・テスト設計・テストコード・検証はすべて対応が取れています。
exit=0
```

## トレーサビリティ

`trace-check.sh` の出力から転記する（目視で「0件」と書かない）。

| # | 孤児 | 件数 |
|---|------|------|
| 1 | 検証されていない仕様 | 0 |
| 2 | テストケースの無い仕様 | 0 |
| 3 | 設計にあるがコードに無いTC | 0 |
| 4 | コードにあるが設計に無いTC | 0 |
| 5 | 親仕様が存在しないTC | 0 |

## 所見

判定を左右しないが記録すべきもの。

- **TC-014-2 は選択状態を確認していない（仕様より狭い）。** SPEC-014 は「その登録文だけになり、全体が選択された状態になる」を要求するが、全選択の観測は TC-014-1（新規ウィンドウへの初回 open）でのみ行われている。既存ウィンドウを再利用して登録文を置き換える経路（右クリックで最も起こりやすい経路）で全選択になることは、テストでは保証されていない。
- **TC-013-1 の「閉じる」は `win.destroy()` の直接呼び出しで代替している。** 利用者がタイトルバーの閉じるボタンで閉じる経路は通っていない。実装を読んだ範囲では `asr/dict_window.py` に `WM_DELETE_WINDOW` のハンドラ設定が無く既定動作（destroy）になるため現時点では同等だが、将来「閉じる＝withdraw」に変えた場合この仕様の意味が変わり、テストは検出しない。
- **TC-013-1 は閉じた後の Toplevel 数を確認していない。** SPEC-013 の「新しい辞書ウィンドウを作る」は `second is not first` と生存で確認されており、SPEC-012 の一意性（1つ）が再オープン後にも保たれるかは観測していない。
- **SPEC-009 の「現在の表示テキスト」は、テストでは `state["history"]` の `text` と同一視されている。** 実装を読んだ範囲では、描画（`main.py` の履歴ラベル生成）も同じ `entry["text"]` を表示しており、翻訳有効時は `"{text}\n→ {翻訳}"` を表示する。登録文は原文部分だけで、仕様の「翻訳は含まない」と整合する。
- **登録文はメニュー表示時点で確定する（仕様に書かれていない振る舞い）。** `show_caption_menu` は右クリック時に `dict_prefill_text` を評価し、その値をメニュー項目のクロージャに保持する。メニュー表示中に同じ発話がインライン編集されると、編集前の文が入る可能性がある（実際には popup 中の編集は起こりにくい）。自動テストの対象外。
- 右クリックのバインド（`<Button-2>` / `<Button-3>` / `<Control-Button-1>`）と `dict_launcher is not None` の条件分岐は範囲外の手動確認事項であり、自動テストでは検証されていない。
