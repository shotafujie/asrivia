"""Whisper の無音幻聴フィルタのテスト。

背景: VAD の無音破棄(全区間無音セグメントの破棄)だけでは、短いノイズで
is_speaking が立ったセグメントや、ライブ仮字幕の部分バッファで
「ご視聴ありがとうございました」等の定型幻聴が出る。
テキストのブラックリスト照合と Whisper の no_speech_prob の両面で弾く。
"""

from main import is_probable_hallucination


def _result(no_speech_prob=0.1, avg_logprob=-0.3):
    return {"segments": [{"no_speech_prob": no_speech_prob, "avg_logprob": avg_logprob}]}


# --- ブラックリスト照合 ---

def test_blocks_typical_hallucination_phrase():
    assert is_probable_hallucination("ご視聴ありがとうございました", _result())


def test_blocks_phrase_with_punctuation_and_whitespace():
    assert is_probable_hallucination(" ご視聴ありがとうございました。 ", _result())
    assert is_probable_hallucination("ご視聴、ありがとうございました！", _result())


def test_blocks_other_known_phrases():
    assert is_probable_hallucination("チャンネル登録をお願いします", _result())
    assert is_probable_hallucination("ご清聴ありがとうございました", _result())


def test_allows_genuine_speech_containing_thanks():
    """幻聴フレーズを一部に含むだけの長い実発話は通す。"""
    text = "今日の配信はここまでですが本編の資料は明日共有します、ご視聴ありがとうございました、また明日の定例でこの続きを議論しましょう"
    assert not is_probable_hallucination(text, _result())


def test_allows_normal_speech():
    assert not is_probable_hallucination("今日はコエパスの設計を進めます", _result())


# --- no_speech_prob 照合 ---

def test_blocks_when_whisper_reports_no_speech():
    """全セグメントが no_speech_prob 高 + avg_logprob 低なら無音由来とみなす。"""
    assert is_probable_hallucination(
        "何かの文章", _result(no_speech_prob=0.9, avg_logprob=-1.5)
    )


def test_allows_confident_result_even_if_no_speech_prob_moderate():
    assert not is_probable_hallucination(
        "普通の発話", _result(no_speech_prob=0.5, avg_logprob=-0.2)
    )


def test_handles_result_without_segments():
    assert not is_probable_hallucination("セグメント情報なし", {})
