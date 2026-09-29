# 検証レポート: qwen バックエンドで辞書(words.json)を context として反映する

- 検証日: 2026-09-29
- 検証者: verifier サブエージェント（独立検証）
- 対象コミット: `a140e35`（ブランチ `feature/qwen-context-biasing`。未コミットの変更 `asr/qwen_asr_backend.py` / `main.py` / `tests/test_qwen_backend.py` ほかを含む作業ツリーを検証）
- 対象仕様: `spec.md` / 対象テスト設計: `test-design.md`

## 判定サマリ

| 判定 | 件数 |
|------|------|
| PASS | 8 |
| FAIL | 0 |
| BLOCKED | 0 |
| **仕様の総数** | 8 |

## 仕様別の判定

記法は `docs/TRACEABILITY.md` に従う。判定は `PASS` / `FAIL` / `BLOCKED` の3値のみ。

- **SPEC-001**: PASS (TC-001-1)
- **SPEC-002**: PASS (TC-002-1)
- **SPEC-003**: PASS (TC-003-1, TC-003-2, TC-003-3, TC-003-4)
- **SPEC-004**: PASS (TC-004-1)
- **SPEC-005**: PASS (TC-005-1)
- **SPEC-006**: PASS (TC-006-1, TC-006-2)
- **SPEC-007**: PASS (TC-007-1, TC-007-2)
- **SPEC-008**: PASS (TC-008-1, TC-008-2, TC-008-3)

テストケースとテストコードの対応（テスト定義直上のコメント `# TC-NNN-M` による）:

| TC | テスト関数 (`tests/test_qwen_backend.py`) | 結果 |
|----|------|------|
| TC-001-1 | `test_no_registry_path_passes_empty_context` | PASSED |
| TC-002-1 | `test_registered_words_are_passed_as_context` | PASSED |
| TC-003-1 | `test_build_context_joins_words_in_registration_order` | PASSED |
| TC-003-2 | `test_build_context_empty` | PASSED |
| TC-003-3 | `test_context_from_words_json_keeps_registration_order` | PASSED |
| TC-003-4 | `test_empty_words_json_passes_empty_context` | PASSED |
| TC-004-1 | `test_missing_registry_file_passes_empty_context` | PASSED |
| TC-005-1 | `test_registry_file_update_is_reflected_on_next_transcribe` | PASSED |
| TC-006-1 | `test_context_leak_is_retried_without_context` | PASSED |
| TC-006-2 | `test_leak_detection_ignores_case_and_width` | PASSED |
| TC-007-1 | `test_two_registered_words_are_not_treated_as_leak` | PASSED |
| TC-007-2 | `test_same_word_repeated_counts_as_one` | PASSED |
| TC-008-1 | `test_broken_words_json_keeps_previous_context` | PASSED |
| TC-008-2 | `test_fixed_words_json_is_reflected_after_broken` | PASSED |
| TC-008-3 | `test_broken_words_json_at_startup_passes_empty_context` | PASSED |

## 実行したコマンドと出力

判定の根拠。**要約せず、実際の出力を貼る。**

```
$ uv run pytest -v
============================= test session starts ==============================
platform darwin -- Python 3.11.15, pytest-9.1.1, pluggy-1.6.0 -- /Users/fujiemon/dev/speech/recognition/asrivia/.venv/bin/python3
cachedir: .pytest_cache
rootdir: /Users/fujiemon/dev/speech/recognition/asrivia
configfile: pyproject.toml
collecting ... collected 62 items

tests/test_audio_concurrency.py::test_concurrent_device_enumeration_no_segfault PASSED [  1%]
tests/test_audio_concurrency.py::test_recorder_active_with_device_enumeration_no_segfault PASSED [  3%]
tests/test_audio_recovery.py::test_recovers_from_transient_read_error PASSED [  4%]
tests/test_audio_recovery.py::test_falls_back_to_default_device_after_repeated_failures PASSED [  6%]
tests/test_audio_recovery.py::test_status_reflects_reconnection PASSED   [  8%]
tests/test_audio_recovery.py::test_fixed_recorder_recovers_from_transient_read_error PASSED [  9%]
tests/test_dynamic_vad.py::test_returns_none_when_no_speech_detected PASSED [ 11%]
tests/test_dynamic_vad.py::test_returns_audio_when_speech_detected PASSED [ 12%]
tests/test_edit_result.py::test_edit_updates_matching_uid PASSED         [ 14%]
tests/test_edit_result.py::test_edit_unknown_uid_is_noop PASSED          [ 16%]
tests/test_edit_result.py::test_edit_to_empty_text_is_rejected PASSED    [ 17%]
tests/test_edit_result.py::test_edit_strips_surrounding_whitespace PASSED [ 19%]
tests/test_edit_result.py::test_edit_same_text_needs_no_redraw PASSED    [ 20%]
tests/test_edit_result.py::test_edit_keeps_existing_translation PASSED   [ 22%]
tests/test_hallucination_filter.py::test_blocks_typical_hallucination_phrase PASSED [ 24%]
tests/test_hallucination_filter.py::test_blocks_phrase_with_punctuation_and_whitespace PASSED [ 25%]
tests/test_hallucination_filter.py::test_blocks_other_known_phrases PASSED [ 27%]
tests/test_hallucination_filter.py::test_allows_genuine_speech_containing_thanks PASSED [ 29%]
tests/test_hallucination_filter.py::test_allows_normal_speech PASSED     [ 30%]
tests/test_hallucination_filter.py::test_blocks_when_whisper_reports_no_speech PASSED [ 32%]
tests/test_hallucination_filter.py::test_allows_confident_result_even_if_no_speech_prob_moderate PASSED [ 33%]
tests/test_hallucination_filter.py::test_handles_result_without_segments PASSED [ 35%]
tests/test_koepus_writer.py::test_write_pair_writes_wav_and_json PASSED  [ 37%]
tests/test_koepus_writer.py::test_write_pair_leaves_no_tmp_files PASSED  [ 38%]
tests/test_koepus_writer.py::test_write_pair_clips_overflow_samples PASSED [ 40%]
tests/test_koepus_writer.py::test_write_pair_stem_suffix_and_no_collision PASSED [ 41%]
tests/test_koepus_writer.py::test_extract_confidence_averages_avg_logprob PASSED [ 43%]
tests/test_koepus_writer.py::test_extract_confidence_returns_none_for_empty_segments PASSED [ 45%]
tests/test_koepus_writer.py::test_extract_confidence_returns_none_when_segments_missing PASSED [ 46%]
tests/test_koepus_writer.py::test_extract_confidence_returns_none_for_non_dict_result PASSED [ 48%]
tests/test_live_captions.py::test_partial_buffer_is_none_before_any_speech PASSED [ 50%]
tests/test_live_captions.py::test_partial_buffer_is_none_during_silence_only PASSED [ 51%]
tests/test_live_captions.py::test_partial_buffer_returns_speech_snapshot_with_uid PASSED [ 53%]
tests/test_live_captions.py::test_segment_uid_increments_per_segment PASSED [ 54%]
tests/test_live_captions.py::test_partial_then_final_appends_to_history PASSED [ 56%]
tests/test_live_captions.py::test_history_keeps_recent_utterances_up_to_max PASSED [ 58%]
tests/test_live_captions.py::test_late_partial_after_final_is_dropped PASSED [ 59%]
tests/test_live_captions.py::test_partial_for_next_utterance_coexists_with_history PASSED [ 61%]
tests/test_live_captions.py::test_partial_survives_delayed_earlier_final PASSED [ 62%]
tests/test_live_captions.py::test_translation_attaches_to_matching_history_entry PASSED [ 64%]
tests/test_qwen_backend.py::test_returns_whisper_compatible_dict PASSED  [ 66%]
tests/test_qwen_backend.py::test_language_ja_maps_to_japanese PASSED     [ 67%]
tests/test_qwen_backend.py::test_language_en_maps_to_english PASSED      [ 69%]
tests/test_qwen_backend.py::test_language_auto_maps_to_none PASSED       [ 70%]
tests/test_qwen_backend.py::test_audio_passed_as_16k_tuple PASSED        [ 72%]
tests/test_qwen_backend.py::test_session_loaded_with_default_model PASSED [ 74%]
tests/test_qwen_backend.py::test_session_loaded_once_and_reused PASSED   [ 75%]
tests/test_qwen_backend.py::test_no_registry_path_passes_empty_context PASSED [ 77%]
tests/test_qwen_backend.py::test_registered_words_are_passed_as_context PASSED [ 79%]
tests/test_qwen_backend.py::test_missing_registry_file_passes_empty_context PASSED [ 80%]
tests/test_qwen_backend.py::test_registry_file_update_is_reflected_on_next_transcribe PASSED [ 82%]
tests/test_qwen_backend.py::test_build_context_joins_words_in_registration_order PASSED [ 83%]
tests/test_qwen_backend.py::test_build_context_empty PASSED              [ 85%]
tests/test_qwen_backend.py::test_context_leak_is_retried_without_context PASSED [ 87%]
tests/test_qwen_backend.py::test_leak_detection_ignores_case_and_width PASSED [ 88%]
tests/test_qwen_backend.py::test_two_registered_words_are_not_treated_as_leak PASSED [ 90%]
tests/test_qwen_backend.py::test_context_from_words_json_keeps_registration_order PASSED [ 91%]
tests/test_qwen_backend.py::test_empty_words_json_passes_empty_context PASSED [ 93%]
tests/test_qwen_backend.py::test_same_word_repeated_counts_as_one PASSED [ 95%]
tests/test_qwen_backend.py::test_broken_words_json_keeps_previous_context PASSED [ 96%]
tests/test_qwen_backend.py::test_fixed_words_json_is_reflected_after_broken PASSED [ 98%]
tests/test_qwen_backend.py::test_broken_words_json_at_startup_passes_empty_context PASSED [100%]

=============================== warnings summary ===============================
<frozen importlib._bootstrap>:241
  <frozen importlib._bootstrap>:241: DeprecationWarning: builtin type SwigPyPacked has no __module__ attribute

<frozen importlib._bootstrap>:241
  <frozen importlib._bootstrap>:241: DeprecationWarning: builtin type SwigPyObject has no __module__ attribute

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
======================== 62 passed, 2 warnings in 4.64s ========================
sys:1: DeprecationWarning: builtin type swigvarlink has no __module__ attribute

(終了コード: 0)
```

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

`trace-check.sh` の出力から転記する（出力は種別ごとに件数がある場合のみ行を出し、合計は「孤児: 0件」）。

| # | 孤児 | 件数 |
|---|------|------|
| 1 | 検証されていない仕様 | 0 |
| 2 | テストケースの無い仕様 | 0 |
| 3 | 設計にあるがコードに無いTC | 0 |
| 4 | コードにあるが設計に無いTC | 0 |
| 5 | 親仕様が存在しないTC | 0 |
| 6 | 同一IDの二重定義（アイテム内） | 0 |
| — | **合計** | **0** |

## 所見

判定を左右しないが記録すべきもの。

1. **空文字 context と「context 未指定」をテストが区別していない（SPEC-001 / 004 / 006 / 008 のテスト）。**
   ヘルパー `_context_of` は `call["kwargs"].get("context", "")` であり、`context` 引数そのものが渡されない実装でも
   TC-001-1 / TC-003-4 / TC-004-1 / TC-006-1（2回目の呼び出し）/ TC-008-3 は通る。同様に TC-006-1 の偽応答
   `_leaky_reply` と TC-006-2 の偽応答も `kwargs.get("context")` の偽値判定なので、未指定と空文字を区別しない。
   仕様は「context を空文字で呼ぶ」であり、テストは仕様より狭い。現在の実装（`asr/qwen_asr_backend.py`）は
   `context=self.context` / `context=""` を常に明示的に渡しているため、現時点で実害は観測されない。
2. **TC-006-2 は再認識の回数と2回目の context を直接アサートしていない。** 戻り値が `"x"` であること
   （偽応答が context 偽値のときだけ返す文字列）から間接的に再認識を確認している。TC-006-1 は回数と2回目の
   context を直接確認しているので、SPEC-006 全体としては補完されている。
3. **SPEC-005 のテストは語の「追加」のみ。** 登録語の削除・並べ替えが次の認識に反映されることを確かめる TC は無い。
   実装上は mtime 変化時に context 全体を作り直しているが、これはテスト結果による保証ではない。
4. **SPEC-002「すべて」は2語で確認（TC-002-1）。** 3語の完全一致は TC-003-3 が確認しており、実質的に補完されている。
5. **アプリ起動時の壊れた words.json（仕様外・テスト対象外）。** `main.py` は `--backend qwen` のとき、
   バックエンド生成とは別に `WordRegistry.load("words.json")` を例外処理なしで呼ぶ（辞書UI用の共有 registry）。
   `WordRegistry.load` は `json.loads` を直接呼ぶため、起動時点で words.json が壊れているとこの行で例外になると読める。
   SPEC-008 / TC-008-3 はバックエンド単体の「生成と認識」についての保証であり、アプリ起動経路はテストされていない。
   （コード読解による所見。実行による確認はしていない）
6. **捕捉される例外の範囲（仕様外）。** 読み直し時に捕捉されるのは `ValueError` / `KeyError` / `TypeError` のみ。
   JSON 構文エラー（`json.JSONDecodeError`）や UTF-8 デコードエラーは `ValueError` の派生なので捕捉されるが、
   ファイル読み取り時の `OSError`（権限エラー等）は捕捉されず、認識時に例外になると読める。SPEC-008 の
   「JSON として読めない」の範囲に含めるかは仕様上曖昧。
7. **読めなかった mtime も「読んだ」と記録される。** 読み込み失敗時も記録 mtime を更新するため、同じ mtime のまま
   壊れた内容が後から正常になった場合は検出されない。spec.md の既知の制約（mtime ベースの検出）の範囲内。
8. **重複登録語。** `WordRegistry` は語をキーとする dict に格納するため、words.json 内の同一語は1つにまとまり、
   最初の出現位置に並ぶ。SPEC-003 は重複時の扱いを定めていない。
9. **範囲外の項目は未確認。** PiP の 📚 ボタン表示（`main.py` の条件が `registry is not None` に変更されている）と
   効果の大きさ（`benchmarks/qwen-context/`）は本検証の範囲外であり、確認していない。
