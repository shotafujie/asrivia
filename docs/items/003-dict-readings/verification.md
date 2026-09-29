# 検証レポート: 辞書の「読み」で認識結果を置き換える

- 検証日: 2026-09-29
- 検証者: verifier サブエージェント（独立検証）
- 対象コミット: `e929372`（ブランチ `feature/dict-readings`。HEAD に未コミットの変更あり: `asr/biasing/readings.py` / `docs/items/003-dict-readings/spec.md` / `docs/items/003-dict-readings/test-design.md` / `tests/test_readings.py`。この作業ツリーの状態を検証した）
- 対象仕様: `spec.md` / 対象テスト設計: `test-design.md`

## 判定サマリ

| 判定 | 件数 |
|------|------|
| PASS | 8 |
| FAIL | 0 |
| BLOCKED | 0 |
| **仕様の総数** | 8 |

テストスイート全体は exit code 1（88件中 1 failed / 87 passed）。失敗した 1 件
`tests/test_audio_recovery.py::test_recovers_from_transient_read_error` はこのアイテムのどの TC にも対応しないため、
仕様別の判定には影響しないが、全体が緑ではないことをここに明記する（詳細は所見）。

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

TC とテスト関数の対応（テスト定義直上のコメントで確認）:

| TC | テスト | 結果 |
|----|--------|------|
| TC-016-1 | tests/test_readings.py::test_reading_is_replaced_with_word | PASSED |
| TC-016-2 | tests/test_readings.py::test_every_occurrence_is_replaced | PASSED |
| TC-017-1 | tests/test_readings.py::test_multiple_readings_with_mixed_separators | PASSED |
| TC-017-2 | tests/test_readings.py::test_empty_reading_items_are_ignored | PASSED |
| TC-018-1 | tests/test_readings.py::test_longer_reading_wins | PASSED |
| TC-019-1 | tests/test_readings.py::test_words_without_reading_do_not_change_text | PASSED |
| TC-019-2 | tests/test_readings.py::test_missing_words_json_returns_text_unchanged | PASSED |
| TC-020-1 | tests/test_readings.py::test_reading_is_saved_and_loaded | PASSED |
| TC-020-2 | tests/test_readings.py::test_legacy_words_json_without_reading | PASSED |
| TC-021-1 | tests/test_readings.py::test_updated_reading_is_used_on_next_apply | PASSED |
| TC-021-2 | tests/test_readings.py::test_broken_words_json_keeps_previous_readings | PASSED |
| TC-021-3 | tests/test_readings.py::test_broken_words_json_at_startup_returns_text_unchanged | PASSED |
| TC-022-1 | tests/test_dict_launcher.py::test_add_with_reading_registers_reading | PASSED |
| TC-023-1 | tests/test_readings.py::test_hiragana_reading_matches_katakana_output | PASSED |
| TC-023-2 | tests/test_readings.py::test_katakana_reading_matches_hiragana_output | PASSED |
| TC-023-3 | tests/test_readings.py::test_unmatched_text_keeps_its_kana | PASSED |

## 実行したコマンドと出力

判定の根拠。**要約せず、実際の出力を貼る。**

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
tests/test_audio_recovery.py::test_recovers_from_transient_read_error FAILED [  3%]
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
tests/test_qwen_backend.py::test_context_leak_is_retried_without_context PASSED [ 73%]
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

=================================== FAILURES ===================================
___________________ test_recovers_from_transient_read_error ____________________

    def test_recovers_from_transient_read_error():
        """read() が一時的に失敗しても、ストリームを再オープンして録音を継続する。"""
        rec = DynamicAudioRecorder(max_record_seconds=0.2)
        rec.REOPEN_BACKOFF_SECONDS = 0.01
        fake = _FailNTimesStream(fail_times=2)
        rec._open_stream = lambda pa: fake
    
        rec.start_recording()
        time.sleep(0.3)
        rec.stop_recording()
    
>       assert not rec.audio_queue.empty()
E       assert not True
E        +  where True = empty()
E        +    where empty = <queue.Queue object at 0x121e7d090>.empty
E        +      where <queue.Queue object at 0x121e7d090> = <audio2wav.DynamicAudioRecorder object at 0x121e2f890>.audio_queue

tests/test_audio_recovery.py:61: AssertionError
=============================== warnings summary ===============================
<frozen importlib._bootstrap>:241
  <frozen importlib._bootstrap>:241: DeprecationWarning: builtin type SwigPyPacked has no __module__ attribute

<frozen importlib._bootstrap>:241
  <frozen importlib._bootstrap>:241: DeprecationWarning: builtin type SwigPyObject has no __module__ attribute

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
=========================== short test summary info ============================
FAILED tests/test_audio_recovery.py::test_recovers_from_transient_read_error
============= 1 failed, 87 passed, 2 warnings in 75.95s (0:01:15) ==============
sys:1: DeprecationWarning: builtin type swigvarlink has no __module__ attribute
(終了コード: 1)
```

失敗したテストの再現確認（このアイテムの仕様外。事実の記録として）:

```
$ for i in 1 2 3 4 5; do uv run pytest -q tests/test_audio_recovery.py::test_recovers_from_transient_read_error 2>&1 | tail -1; done
1 failed in 3.26s
1 failed in 3.81s
1 failed in 3.79s
1 failed in 3.33s
1 failed in 3.78s
```

```
# main (a140e35) を git archive でスクラッチ領域に展開し、同じ venv で実行（作業ツリーは変更していない）
$ git archive main | tar -x -C <scratchpad>/main_tree && cd <scratchpad>/main_tree
$ for i in 1 2 3; do .venv/bin/python -m pytest -q -p no:cacheprovider tests/test_audio_recovery.py::test_recovers_from_transient_read_error 2>&1 | tail -1; done
1 failed in 4.11s
1 failed in 2.75s
1 failed in 2.82s
```

```
$ git diff main --stat   # audio2wav.py / tests/test_audio_recovery.py は差分に含まれない
 .gitignore                                         |   3 +
 README.md                                          |  21 ++-
 asr/biasing/readings.py                            |  68 +++++++
 asr/biasing/registry.py                            |   6 +-
 asr/dict_window.py                                 |  50 ++++-
 asr/qwen_asr_backend.py                            |  69 ++++++-
 benchmarks/qwen-context/README.md                  |  47 +++++
 benchmarks/qwen-context/run.py                     | 179 ++++++++++++++++++
 docs/items/001-qwen-context-biasing/spec.md        |  32 ++++
 docs/items/001-qwen-context-biasing/test-design.md |  43 +++++
 .../items/001-qwen-context-biasing/verification.md | 197 ++++++++++++++++++++
 docs/items/002-caption-to-dict/spec.md             |  25 +++
 docs/items/002-caption-to-dict/test-design.md      |  35 ++++
 docs/items/002-caption-to-dict/verification.md     | 165 +++++++++++++++++
 docs/items/003-dict-readings/spec.md               |  28 +++
 docs/items/003-dict-readings/test-design.md        |  45 +++++
 docs/items/003-dict-readings/verification.md       | 195 ++++++++++++++++++++
 main.py                                            |  50 ++++-
 tests/test_caption_to_dict.py                      |  34 ++++
 tests/test_dict_launcher.py                        |  88 +++++++++
 tests/test_qwen_backend.py                         | 201 ++++++++++++++++++++-
 tests/test_readings.py                             | 138 ++++++++++++++
 22 files changed, 1696 insertions(+), 23 deletions(-)
```

仕様の境界を確かめるための追加観測（スクラッチ領域の一時 words.json で `ReadingReplacer` を直接呼んだ。テストスイートの一部ではなく判定には使っていない）:

```
$ uv run python <scratchpad>/probe.py <scratchpad>
mixed output クロードこーど -> クロードこーど
unmatched katakana kept -> Claudeとテストとてすと
spaces around 、，-> JAIST/JAIST/JAIST
before クロード
same-second update w/o mtime bump -> Claude 1790678624.2494864
[辞書/読み] words.json を読めないため直前の読みを継続: string indices must be integers, not 'str'
valid JSON but non-list -> Claude
```

（各行の条件: 1行目 読み「クロードコード」に対し認識結果が「クロードこーど」（カナ混在）/ 2行目 読み「くろーど」で置換対象外のカタカナ・ひらがな / 3行目 読み「 ジャイスト 、 ダイスト ， ジェイスト」/ 4〜5行目 読みなしで生成後、mtime を手動で進めずに読みを追加 / 6〜7行目 読みありで生成後、`{"x":1}`（JSON としては正しいがリストでない）に書き換えて mtime を進めた）

```
$ ~/dev/.claude/hooks/trace-check.sh docs/items/003-dict-readings
=== traceability check ===
スコープ: docs/items/003-dict-readings （このアイテムに属するIDのみ検査）

[003-dict-readings] 仕様 8件 / テストケース 16件

[テストコード] 検出したテストケースID: 16件 (探索起点: .)

孤児: 0件 — 仕様・テスト設計・テストコード・検証はすべて対応が取れています。
(終了コード: 0)
```

## トレーサビリティ

`trace-check.sh` の出力から転記する（目視で「0件」と書かない）。出力は「孤児: 0件」で、種別ごとの行は出力されていない。
（参考: レポート作成前の実行では `[1] 検証されていない仕様: 1件 SPEC-023`・孤児合計 1件・exit 1 だった。前回レポートに SPEC-023 が無かったため。）

| # | 孤児 | 件数 |
|---|------|------|
| 1 | 検証されていない仕様 | 0 |
| 2 | テストケースの無い仕様 | 0 |
| 3 | 設計にあるがコードに無いTC | 0 |
| 4 | コードにあるが設計に無いTC | 0 |
| 5 | 親仕様が存在しないTC | 0 |

## 所見

- **テストスイート全体は赤（exit code 1）。** `tests/test_audio_recovery.py::test_recovers_from_transient_read_error` が
  `assert not rec.audio_queue.empty()` で失敗（`AssertionError: assert not True`）。単独実行でも 5/5 回失敗、
  main（a140e35）のスナップショットでも 3/3 回失敗した。`audio2wav.py` と `tests/test_audio_recovery.py` は
  `git diff main` に含まれない。検証時、別プロセスで `main.py --backend qwen --dynamic-vad` が起動中だった（`pgrep` で確認）。
  「不安定なテスト」と伝えられていたが、今回の環境では断続的ではなく毎回失敗しており、負荷起因かどうかは
  本検証では切り分けていない。このアイテムの TC ではないため仕様別判定には含めないが、全体として緑ではない。
- **SPEC-023 のテストが仕様より狭い（カナ混在）。** 仕様は「ひらがな・カタカナを区別せずに照合する」だが、
  TC-023-1/2/3 はいずれも「読み全体がひらがな」対「認識結果全体がカタカナ」（またはその逆）の組み合わせだけを検証している。
  追加観測では、読み「クロードコード」に対し認識結果「クロードこーど」（1語の中でカナが混在）は置換されなかった。
  実装を読むと、読みを「元の形・全カタカナ・全ひらがな」の3通りに展開して文字列一致させており、認識結果側は正規化していない。
  仕様の文言を「文字単位でかなの種別を区別しない」と読むなら満たされていない。仕様の意図がどちらかを上流で明確にすべき。
- **SPEC-023 後半「置換されない部分の文字は変えない」のテストはひらがなの側だけ。** TC-023-3 は置換対象外の
  「ひらがなのまま」が保たれることのみを確認し、置換対象外のカタカナは検証していない。追加観測では
  「クロードとテストとてすと」→「Claudeとテストとてすと」で両方保たれていた（テスト外の観測）。
- **SPEC-021 のテストは mtime を 10 秒進めて更新を表現している。** 実装は mtime の一致で再読込を省略する。
  追加観測では mtime を手動で進めなくても更新が反映されたが、これは今回のファイルシステムの mtime 分解能に依存する。
  mtime が変わらない書き換え（分解能の粗いファイルシステムでの同一時刻内の更新など）では、仕様の「次の置換から更新後の読みが使われる」
  は保証されない可能性があり、テストはこのケースを含まない。
- **SPEC-021「JSON として読めない場合」の範囲。** TC-021-2/3 は途中で切れた JSON のみ。追加観測では、JSON としては正しいが
  リストでない内容（`{"x":1}`）でも例外なく直前の読みで置換された。`OSError`（読み取り権限なし等）は捕捉対象に無いことを
  実装で確認したが、仕様は「JSON として読めない場合」に限っているため判定対象外。
- **SPEC-017 のテストは区切り文字ごとの空白パターンを網羅しない。** TC-017-1 の空白は `,` の後ろのみ、TC-017-2 の空要素は `,` のみ。
  追加観測では `、` `，` の前後の空白も除去されていた（テスト外の観測）。
- **仕様に書かれていない振る舞い（実装を読んで判明）:** 異なる登録語が同じ読みを持つ場合、置換表は後から処理した語で上書きされる
  （words.json 上で後ろの語が勝つ）。仕様・テスト設計のどちらにも記述が無い。
- 仕様書で SPEC-023 が SPEC-022 より前に記載されている（ID 順ではない）。trace-check には影響しない。
