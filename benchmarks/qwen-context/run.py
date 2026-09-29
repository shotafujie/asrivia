"""Qwen3-ASR: 辞書(context)あり/なしの比較ベンチマーク。

koepus コーパスの verified 発話(人手修正済みの正解テキスト付き)を、同じ Session で
2条件で認識し、次を比べる。

- base: context なしで Session を直接呼ぶ(辞書を使わない従来の挙動)
- ctx:  QwenASRBackend.transcribe 経由(context + 漏れガード。再認識の時間も計測に含む)

- 登録語再現率: 正解に登録語を含む(発話, 語)のうち、認識結果にもその語が出た割合
- 誤挿入: 正解に無い登録語が認識結果に出た回数(context による押し付けの副作用)
- CER: 全発話の文字誤り率(正規化後)
- レイテンシ: 1発話あたりの transcribe 時間

辞書は評価前に固定したものを外部ファイルで渡す(固有名詞をリポジトリに含めないため)。
発話ごとの結果と語ごとの表は --out-dir(既定: local/, gitignore 済み)に書き、
標準出力には語名を含まない集計だけを出す。

    uv run python benchmarks/qwen-context/run.py --dict benchmarks/qwen-context/local/dict.txt
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import random
import sqlite3
import statistics
import sys
import time
import unicodedata
import wave
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from asr.qwen_asr_backend import SAMPLE_RATE, QwenASRBackend  # noqa: E402

DEFAULT_DB = Path(os.environ.get("KOEPUS_DATA_DIR", "")) / "koepus.sqlite3"
HERE = Path(__file__).resolve().parent


def normalize(text: str) -> str:
    """NFKC・小文字化し、句読点/記号/空白を除く(表記ゆれで CER を水増ししない)。"""
    text = unicodedata.normalize("NFKC", text).lower()
    return "".join(
        ch for ch in text if not unicodedata.category(ch)[0] in ("P", "Z", "S")
    )


def edit_distance(a: str, b: str) -> int:
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def load_wav(path: str) -> np.ndarray:
    with wave.open(path, "rb") as w:
        assert w.getframerate() == SAMPLE_RATE and w.getnchannels() == 1
        assert w.getsampwidth() == 2
        pcm = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16)
    return (pcm.astype(np.float32) / 32768.0)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dict", required=True, help="登録語ファイル(1行1語)")
    ap.add_argument("--db", default=str(DEFAULT_DB))
    ap.add_argument("--model", default="Qwen/Qwen3-ASR-1.7B")
    ap.add_argument("--out-dir", default=str(HERE / "local"))
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()

    words = [
        line.strip()
        for line in Path(args.dict).read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.startswith("#")
    ]
    nwords = [normalize(w) for w in words]

    con = sqlite3.connect(f"file:{args.db}?mode=ro", uri=True)
    rows = con.execute(
        "select id, audio_path, corrected_text from utterances "
        "where status='verified' and corrected_text != '' order by id"
    ).fetchall()
    if args.limit:
        rows = rows[: args.limit]
    audios = {uid: load_wav(p) for uid, p, _ in rows}  # 読み込みは計測外

    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    words_json = out / "words.json"
    words_json.write_text(
        json.dumps([{"word": w} for w in words], ensure_ascii=False), encoding="utf-8"
    )
    backend = QwenASRBackend(args.model, language="ja", registry_path=str(words_json))
    session = backend.session

    def run_base(audio):
        return session.transcribe((audio, SAMPLE_RATE), language="Japanese").text.strip()

    def run_ctx(audio):
        return backend.transcribe(audio)["text"]

    conds = {"base": run_base, "ctx": run_ctx}
    for uid, _, _ in rows[:2]:  # ウォームアップ
        for fn in conds.values():
            fn(audios[uid])

    rng = random.Random(args.seed)
    results = []
    for i, (uid, _, ref) in enumerate(rows):
        order = list(conds)
        rng.shuffle(order)  # 条件の実行順による熱・キャッシュの偏りを消す
        rec = {"id": uid, "ref": ref}
        for name in order:
            t0 = time.perf_counter()
            hyp = conds[name](audios[uid])
            rec[f"{name}_sec"] = time.perf_counter() - t0
            rec[f"{name}_hyp"] = hyp
        results.append(rec)
        print(f"\r{i + 1}/{len(rows)}", end="", file=sys.stderr, flush=True)
    print(file=sys.stderr)

    summary = {"n_utt": len(rows), "n_words": len(words)}
    per_word = {w: {"ref": 0} for w in words}
    for name in conds:
        errs = chars = hit = total = ins = 0
        for rec in results:
            nref, nhyp = normalize(rec["ref"]), normalize(rec[f"{name}_hyp"])
            errs += edit_distance(nref, nhyp)
            chars += len(nref)
            for w, nw in zip(words, nwords):
                in_ref, in_hyp = nw in nref, nw in nhyp
                if in_ref:
                    total += 1
                    hit += in_hyp
                    per_word[w][name] = per_word[w].get(name, 0) + in_hyp
                    if name == "base":
                        per_word[w]["ref"] += 1
                elif in_hyp:
                    ins += 1
                    per_word[w][f"{name}_ins"] = per_word[w].get(f"{name}_ins", 0) + 1
        secs = [rec[f"{name}_sec"] for rec in results]
        summary[name] = {
            "cer": errs / chars,
            "word_recall": f"{hit}/{total}",
            "word_recall_rate": hit / total if total else None,
            "false_insertions": ins,
            "latency_median_s": statistics.median(secs),
            "latency_min_s": min(secs),
            "latency_p90_s": sorted(secs)[int(len(secs) * 0.9)],
        }
    summary["env"] = {
        "machine": platform.machine(),
        "os": platform.platform(),
        "model": args.model,
        "context_chars": len(backend.context),
    }

    (out / "results.jsonl").write_text(
        "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in results), encoding="utf-8"
    )
    (out / "per_word.json").write_text(
        json.dumps(per_word, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (out / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
