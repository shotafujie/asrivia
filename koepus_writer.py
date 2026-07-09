"""koepus 連携: 認識結果ごとに wav + sidecar JSON を koepus の incoming/ へ書き出す。

契約は /Users/fujiemon/dev/speech/corpus/koepus/docs/integrations/asrivia.md を参照。
書き込み順序は wav.tmp -> json.tmp -> wav rename -> json rename。koepus 側の watch は
*.json を起点にファイルを取り込むため、JSON を最後に確定配置することで「wav がまだ
書き終わっていないのに JSON だけ見えてしまう」レースを避ける。

このモジュールは mlx_whisper / pyaudio / main を import しない(numpy と標準ライブラリのみ)。
テストを重いネイティブ依存から切り離すため。
"""

from __future__ import annotations

import json
import os
import secrets
import wave
from datetime import datetime
from pathlib import Path

import numpy as np


def extract_confidence(result) -> float | None:
    """Whisper系result dictからsegmentsのavg_logprob平均を取り出す。

    segmentsが無い/空、avg_logprobキーが無い、resultがdictでない場合はNoneを返す。
    """
    if not isinstance(result, dict):
        return None

    segments = result.get("segments")
    if not segments:
        return None

    logprobs = []
    for seg in segments:
        if isinstance(seg, dict) and "avg_logprob" in seg:
            logprobs.append(seg["avg_logprob"])

    if not logprobs:
        return None

    return sum(logprobs) / len(logprobs)


def write_pair(
    incoming_dir: Path,
    frame: np.ndarray,
    *,
    hypothesis: str,
    asr_model: str,
    language: str | None,
    confidence: float | None,
    dynamic_vad: bool,
    now: datetime | None = None,
) -> Path:
    """frame(float32 PCM) と sidecar JSON をincoming_dirへatomicに書き出し、JSONパスを返す。"""
    incoming_dir = Path(incoming_dir)
    incoming_dir.mkdir(parents=True, exist_ok=True)

    if now is None:
        now = datetime.now().astimezone()

    stem = f"{now:%Y%m%dT%H%M%S}_{secrets.token_hex(3)}_asrivia"

    wav_path = incoming_dir / f"{stem}.wav"
    wav_tmp_path = incoming_dir / f"{stem}.wav.tmp"
    json_path = incoming_dir / f"{stem}.json"
    json_tmp_path = incoming_dir / f"{stem}.json.tmp"

    pcm16 = (np.clip(frame, -1.0, 1.0) * 32767).astype(np.int16)
    with wave.open(str(wav_tmp_path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(16000)
        wf.writeframes(pcm16.tobytes())
    os.replace(wav_tmp_path, wav_path)

    backend = asr_model.split(":", 1)[0]
    payload = {
        "source": "asrivia",
        "recorded_at": now.isoformat(timespec="seconds"),
        "asr_model": asr_model,
        "hypothesis": hypothesis,
        "confidence": confidence,
        "channels": ["air"],
        "meta": {
            "app": "asrivia",
            "backend": backend,
            "language": language,
            "dynamic_vad": dynamic_vad,
        },
    }
    json_tmp_path.write_text(
        json.dumps(payload, ensure_ascii=False), encoding="utf-8"
    )
    os.replace(json_tmp_path, json_path)

    return json_path
