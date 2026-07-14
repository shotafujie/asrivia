import mlx_whisper
import re
import time
import audio2wav
import koepus_writer
import threading
import queue
import tkinter as tk
import argparse
import sys
import os
from pathlib import Path

from asr.translator_gemma import GemmaTranslator
from asr.translator_opus import OpusTranslator

def detect_translation_direction(lang):
    if lang == "ja":
        return ("ja", "en")
    elif lang == "en":
        return ("en", "ja")
    else:
        return (None, None)

# mainブランチ準拠: record_audio_thread構造そのままコピー
def record_audio_thread(audio_q):
    try:
        while True:
            item = audio2wav.record_audio()  # (uid, frame) または None(無音破棄)
            if item is None:
                continue
            audio_q.put(item)
    except Exception as e:
        print(f"[録音エラー]\n{e}", file=sys.stderr)


LIVE_MIN_BUFFER_SEC = 0.5  # これ未満の部分バッファは認識しない(短すぎて幻聴しやすい)

# Whisper が無音・ノイズ区間で出す定型幻聴フレーズ。
# VAD の全区間無音破棄をすり抜けた短ノイズや、ライブ仮字幕の部分バッファで出る。
HALLUCINATION_BLACKLIST = [
    "ご視聴ありがとうございました",
    "ご清聴ありがとうございました",
    "チャンネル登録をお願いします",
    "チャンネル登録",
    "最後までご視聴いただきありがとうございます",
    "おやすみなさい",
    "thank you for watching",
    "thanks for watching",
    "please subscribe",
]
# ブラックリスト句がテキストの大半を占めるときだけ幻聴とみなす(実発話の巻き込み防止)
HALLUCINATION_DOMINANCE_RATIO = 0.6
# Whisper 自身の無音判定: 全セグメントがこの両閾値を超えたら無音由来とみなす
NO_SPEECH_PROB_THRESHOLD = 0.6
AVG_LOGPROB_THRESHOLD = -1.0


def _normalize_for_blacklist(text):
    return re.sub(r"[\s。、．，,.!！?？~〜…・「」()（）]", "", text).lower()


def is_probable_hallucination(text, result):
    """無音・ノイズ由来の幻聴テキストなら True。

    1) 定型幻聴フレーズがテキストの大半を占める
    2) Whisper の全セグメントが no_speech_prob 高 かつ avg_logprob 低
    のいずれかで幻聴と判定する。
    """
    norm = _normalize_for_blacklist(text)
    if not norm:
        return True
    for phrase in HALLUCINATION_BLACKLIST:
        p = _normalize_for_blacklist(phrase)
        if p in norm and len(p) / len(norm) >= HALLUCINATION_DOMINANCE_RATIO:
            return True
    segments = result.get("segments") or []
    if segments and all(
        seg.get("no_speech_prob", 0.0) > NO_SPEECH_PROB_THRESHOLD
        and seg.get("avg_logprob", 0.0) < AVG_LOGPROB_THRESHOLD
        for seg in segments
    ):
        return True
    return False


def live_caption_thread(result_q, first_model, lang_mode, interval, final_busy):
    """first pass: 録音中のバッファを小型モデルで逐次認識し仮字幕を出す。

    確定パス(second pass)の実行中はティックをスキップして GPU を譲り、
    確定字幕のレイテンシに影響を与えない。
    """
    print(f"[ライブ字幕] first passモデル: {first_model} (間隔: {interval}s)")
    while True:
        time.sleep(interval)
        if final_busy.is_set():
            continue
        partial = audio2wav.get_partial_buffer()
        if partial is None:
            continue
        uid, buf = partial
        if len(buf) < 16000 * LIVE_MIN_BUFFER_SEC:
            continue
        try:
            if lang_mode == "auto":
                result = mlx_whisper.transcribe(buf, path_or_hf_repo=first_model)
            else:
                result = mlx_whisper.transcribe(buf, path_or_hf_repo=first_model, language=lang_mode)
        except Exception as e:
            print(f"[ライブ字幕エラー]\n{e}", file=sys.stderr)
            continue
        text = result.get("text", "").strip()
        if text and not is_probable_hallucination(text, result):
            result_q.put(("partial", uid, text))

TRANSLATE_QUEUE_MAX = 2  # バックプレッシャー: 溢れたら古いジョブを破棄して最新優先

def translate_worker_thread(translate_q, result_q, translator):
    while True:
        item = translate_q.get()
        if item is None:
            translate_q.task_done()
            break
        uid, text, src, tgt = item
        t0 = time.time()
        translated = translator.translate(text, src, tgt)
        translate_q.task_done()
        print(f"[timing] translate uid={uid} dt={time.time()-t0:.2f}s tqlen={translate_q.qsize()}")
        result_q.put(("translation", uid, translated))


# mainブランチ準拠: transcribe_audio_thread構造を統一、backend対応のみ追加
def transcribe_audio_thread(audio_q, result_q, lang_mode, enable_translate, backend, model_name, oov_queue=None, translate_q=None, koepus_cfg=None, final_busy=None):
    """
    音声認識スレッド。バックエンドに応じて処理を切り替える。
    backend: 'mlx', 'openai', 'stable-ts', または 'hf'
    model_name: 使用するモデル名
    koepus_cfg: koepus書き出し設定 dict({"dir", "backend", "model", "dynamic_vad"})。None なら無効
    final_busy: 確定ASR実行中を示すEvent。ライブ字幕スレッドがGPU競合回避に使う
    """
    if backend == "mlx":
        print(f"[MLX] モデル: {model_name}")
    elif backend == "openai":
        import whisper
        print(f"[PyTorch Whisper] モデルをロード中: {model_name}")
        asr_model = whisper.load_model(model_name)
        print("[PyTorch Whisper] モデルのロードが完了しました")
    elif backend == "stable-ts":
        import stable_whisper
        print(f"[Stable-TS] モデルをロード中: {model_name}")
        asr_model = stable_whisper.load_model(model_name)
        print("[Stable-TS] モデルのロードが完了しました")
    elif backend == "hf":
        from asr.biased_whisper import BiasingWhisperBackend
        asr_model = BiasingWhisperBackend(
            model_name=model_name,
            language=lang_mode,
            registry_path="words.json",
        )
    elif backend == "qwen":
        from asr.qwen_asr_backend import QwenASRBackend
        asr_model = QwenASRBackend(
            model_name=model_name,
            language=lang_mode,
        )
    else:
        raise ValueError(f"未対応のバックエンド: {backend}")

    while True:
        try:
            item = audio_q.get()
            if item is None:
                audio_q.task_done()
                break
            utterance_id, frame = item  # uid は録音側(レコーダー)で採番済み

            audio_sec = len(frame) / 16000.0 if hasattr(frame, "__len__") else 0.0
            t_asr_start = time.time()

            if final_busy is not None:
                final_busy.set()

            # mainブランチ準拠: backend分岐のみ差分
            if backend == "mlx":
                if lang_mode == "auto":
                    result = mlx_whisper.transcribe(frame, path_or_hf_repo=model_name)
                else:
                    result = mlx_whisper.transcribe(frame, path_or_hf_repo=model_name, language=lang_mode)
            elif backend == "openai":
                if lang_mode == "auto":
                    result = asr_model.transcribe(frame)
                else:
                    result = asr_model.transcribe(frame, language=lang_mode)
            elif backend == "stable-ts":
                # stable-ts: VAD有効化、condition_on_previous_text=False でハルシネーション軽減
                transcribe_options = {
                    "vad": "silero",
                    "condition_on_previous_text": False,
                    "word_timestamps": False,
                    "verbose": False,
                }
                if lang_mode != "auto":
                    transcribe_options["language"] = lang_mode
                stable_result = asr_model.transcribe(frame, **transcribe_options)
                # stable-ts の結果を Whisper 互換形式に変換
                result = {
                    "text": stable_result.text if hasattr(stable_result, 'text') else str(stable_result),
                    "language": stable_result.language if hasattr(stable_result, 'language') else lang_mode,
                }
            elif backend == "hf":
                result = asr_model.transcribe(frame)
                # OOV候補をoov_queueに送信
                if hasattr(asr_model, 'oov_candidates') and asr_model.oov_candidates:
                    if oov_queue is not None:
                        oov_queue.put(list(asr_model.oov_candidates))
            elif backend == "qwen":
                result = asr_model.transcribe(frame)

            if final_busy is not None:
                final_busy.clear()

            text = result.get("text", "").strip()
            detected_lang = result.get("language", lang_mode)
            audio_q.task_done()
            asr_sec = time.time() - t_asr_start

            if not text:
                continue

            # 無音幻聴(「ご視聴ありがとうございました」等)は表示・翻訳・koepusの前に破棄
            if is_probable_hallucination(text, result):
                print(f"[幻聴フィルタ] uid={utterance_id} 破棄: {text!r}")
                continue

            print(f"[timing] uid={utterance_id} audio={audio_sec:.2f}s asr={asr_sec:.2f}s aqlen={audio_q.qsize()}")

            # koepus へ wav + sidecar JSON を書き出す(失敗しても認識本体は止めない)
            if koepus_cfg is not None:
                try:
                    koepus_writer.write_pair(
                        koepus_cfg["dir"], frame,
                        hypothesis=text,
                        asr_model=f"{koepus_cfg['backend']}:{koepus_cfg['model']}",
                        language=detected_lang,
                        confidence=koepus_writer.extract_confidence(result),
                        dynamic_vad=koepus_cfg["dynamic_vad"],
                    )
                except Exception as e:
                    print(f"[koepus] 書き出し失敗: {e}", file=sys.stderr)

            # 認識テキストを即時UI表示
            result_q.put(("text", utterance_id, text))

            # 翻訳ジョブを別キューへ投入(バックプレッシャー: 上限超過時は古いジョブを破棄)
            if enable_translate and translate_q is not None:
                from_lang, to_lang = detect_translation_direction(detected_lang)
                if from_lang and to_lang:
                    while translate_q.qsize() >= TRANSLATE_QUEUE_MAX:
                        try:
                            dropped = translate_q.get_nowait()
                            translate_q.task_done()
                            print(f"[backpressure] 翻訳ジョブ破棄 uid={dropped[0]}")
                        except queue.Empty:
                            break
                    translate_q.put((utterance_id, text, from_lang, to_lang))
            
        except Exception as e:
            if final_busy is not None:
                final_busy.clear()
            print(f"[文字起こしエラー]\n{e}", file=sys.stderr)
            import traceback
            traceback.print_exc()
            audio_q.task_done()

FONT_MIN = 8
FONT_MAX = 96
FONT_DEFAULT = 14
PARTIAL_FG = "gray50"  # 仮字幕(未確定)の文字色


HISTORY_LINES_DEFAULT = 3  # 字幕として画面に残す確定発話の行数


def make_ui_state(translate_enabled=False, history_max=HISTORY_LINES_DEFAULT):
    """PiPウィンドウの表示状態。確定発話は history に積んで複数行表示する。"""
    return {
        "history": [],  # [{"uid", "text", "translated"}] 古い順
        "history_max": history_max,
        "partial": None,
        "partial_uid": None,
        "translate_enabled": translate_enabled,
    }


def apply_result_message(state, kind, uid, payload):
    """result_q のメッセージを表示状態に反映する。再描画が必要なら True。

    uid 整合ルール:
    - partial: 確定済みの最新 uid 以下は遅延到着として破棄
    - text(確定): 履歴に追記(上限超過で古い行を破棄)。その uid 以前の仮字幕を消す
    - translation: 履歴に残っている同 uid の行にだけ反映
    """
    if kind == "partial":
        last_uid = state["history"][-1]["uid"] if state["history"] else None
        if last_uid is not None and uid <= last_uid:
            return False
        state["partial"] = payload
        state["partial_uid"] = uid
        return True
    if kind == "text":
        state["history"].append({"uid": uid, "text": payload, "translated": None})
        del state["history"][:-state["history_max"]]
        if state["partial_uid"] is not None and state["partial_uid"] <= uid:
            state["partial"] = None
            state["partial_uid"] = None
        return True
    if kind == "translation":
        for entry in state["history"]:
            if entry["uid"] == uid:
                entry["translated"] = payload
                return True
        return False
    return False


def apply_edit(state, uid, new_text):
    """確定字幕の手動編集を表示状態に反映する。再描画が必要なら True。

    画面表示のみの編集(koepus・翻訳へは伝播しない)。
    空文字への編集は誤操作とみなして棄却し、既存の翻訳表示は保持する。
    """
    new_text = new_text.strip()
    if not new_text:
        return False
    for entry in state["history"]:
        if entry["uid"] == uid:
            if entry["text"] == new_text:
                return False
            entry["text"] = new_text
            return True
    return False


def start_pip_window(result_q, stop_ev, backend=None, registry=None, reload_cb=None, oov_queue=None, translate_enabled=False, history_lines=HISTORY_LINES_DEFAULT):
    pip = tk.Toplevel()
    pip.title("asrivia")
    pip.geometry("600x240")
    pip.minsize(360, 120)
    pip.attributes("-topmost", True)
    pip.attributes("-alpha", 1.0)

    font_size = tk.IntVar(value=FONT_DEFAULT)

    # ボタンバーを最初にpack(side=BOTTOM)して最下部を確保
    button_frame = tk.Frame(pip)
    button_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=5, pady=4)

    # 確定字幕は発話ごとに Label を並べる(ダブルクリックでその行だけ編集できるようにするため)
    history_frame = tk.Frame(pip)
    history_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=10, pady=(8, 0))

    # 仮字幕(未確定)は履歴の下にグレーで表示
    partial_label = tk.Label(
        pip,
        text="",
        font=("Arial", FONT_DEFAULT),
        wraplength=580,
        justify="left",
        anchor="nw",
        fg=PARTIAL_FG,
    )
    partial_label.pack(side=tk.TOP, fill=tk.X, padx=10, pady=(0, 8))

    entry_labels = []  # render() が作り直す確定字幕 Label 群(wraplength/font 更新用)

    def update_wraplength(event=None):
        try:
            w = pip.winfo_width()
        except tk.TclError:
            return
        if w > 40:
            for lbl in entry_labels:
                lbl.config(wraplength=w - 40)
            partial_label.config(wraplength=w - 40)

    pip.bind("<Configure>", update_wraplength)

    def change_font(delta):
        new_size = max(FONT_MIN, min(FONT_MAX, font_size.get() + delta))
        font_size.set(new_size)
        partial_label.config(font=("Arial", new_size))
        render()

    btn_decrease = tk.Button(button_frame, text="－", width=2, command=lambda: change_font(-2))
    btn_decrease.pack(side=tk.LEFT, padx=2)
    btn_increase = tk.Button(button_frame, text="＋", width=2, command=lambda: change_font(2))
    btn_increase.pack(side=tk.LEFT, padx=2)

    # 入力デバイス選択
    devices = audio2wav.list_input_devices()
    current_idx = audio2wav.get_current_device()

    def device_label(d):
        suffix = " (default)" if d.get("is_default") else ""
        return f"{d['index']}: {d['name']}{suffix}"

    if devices:
        labels = [device_label(d) for d in devices]
        label_to_index = {device_label(d): d["index"] for d in devices}
        initial_label = next(
            (lbl for lbl, idx in label_to_index.items() if idx == current_idx),
            labels[0],
        )
        device_var = tk.StringVar(value=initial_label)

        def on_device_change(selection):
            idx = label_to_index.get(selection)
            if idx is None:
                return
            try:
                audio2wav.switch_device(idx)
                print(f"[audio] デバイス切替 → {selection}")
            except Exception as e:
                print(f"[audio] デバイス切替失敗: {e}", file=sys.stderr)

        device_menu = tk.OptionMenu(button_frame, device_var, *labels, command=on_device_change)
        device_menu.config(width=18)
        device_menu.pack(side=tk.LEFT, padx=4)

    # 辞書ボタン（hfバックエンド時のみ表示）
    if backend == "hf" and registry is not None:
        from asr.dict_window import DictWindow
        def open_dict_window():
            DictWindow(pip, registry, reload_cb, oov_queue)
        btn_dict = tk.Button(button_frame, text="📚", command=open_dict_window)
        btn_dict.pack(side=tk.LEFT, padx=4)

    # 現在表示中の発話状態
    state = make_ui_state(translate_enabled=translate_enabled, history_max=history_lines)
    editing = {"uid": None}  # 編集中の確定発話 uid(編集中は再描画を保留)

    def render():
        # 編集中に作り直すと入力欄が消えるため、編集終了時の render() に任せる
        if editing["uid"] is not None:
            return
        for w in history_frame.winfo_children():
            w.destroy()
        entry_labels.clear()
        font = ("Arial", font_size.get())
        try:
            w = pip.winfo_width()
        except tk.TclError:
            return
        wraplength = w - 40 if w > 40 else 580
        if not state["history"]:
            placeholder = tk.Label(
                history_frame,
                text="認識結果がここに表示されます",
                font=font,
                wraplength=wraplength,
                justify="left",
                anchor="nw",
            )
            placeholder.pack(side=tk.TOP, fill=tk.X)
            entry_labels.append(placeholder)
        for entry in state["history"]:
            if state["translate_enabled"]:
                tr = entry["translated"] if entry["translated"] is not None else "..."
                line = f"{entry['text']}\n→ {tr}"
            else:
                line = entry["text"]
            lbl = tk.Label(
                history_frame,
                text=line,
                font=font,
                wraplength=wraplength,
                justify="left",
                anchor="nw",
            )
            lbl.pack(side=tk.TOP, fill=tk.X)
            lbl.bind("<Double-Button-1>", lambda e, uid=entry["uid"]: begin_edit(uid))
            entry_labels.append(lbl)
        partial_label.config(text=state["partial"] or "")

    def begin_edit(uid):
        if editing["uid"] is not None:
            return
        idx = next((i for i, e in enumerate(state["history"]) if e["uid"] == uid), None)
        if idx is None:
            return
        editing["uid"] = uid
        lbl = entry_labels[idx]
        var = tk.StringVar(value=state["history"][idx]["text"])
        editor = tk.Entry(history_frame, textvariable=var, font=("Arial", font_size.get()))
        editor.pack(after=lbl, fill=tk.X)
        lbl.pack_forget()
        editor.focus_set()
        editor.icursor(tk.END)

        def finish(commit):
            # render() が editor を destroy したときの FocusOut 再入を弾く
            if editing["uid"] != uid:
                return
            editing["uid"] = None
            if commit:
                apply_edit(state, uid, var.get())
            render()

        editor.bind("<Return>", lambda e: finish(True))
        editor.bind("<Escape>", lambda e: finish(False))
        editor.bind("<FocusOut>", lambda e: finish(False))

    def poll_queue():
        try:
            while True:
                msg = result_q.get_nowait()
                kind, uid, payload = msg
                if apply_result_message(state, kind, uid, payload):
                    render()
                result_q.task_done()
        except queue.Empty:
            pass
        if not stop_ev.is_set():
            pip.after(100, poll_queue)
        else:
            pip.destroy()
    
    render()
    poll_queue()
    pip.protocol("WM_DELETE_WINDOW", stop_ev.set)
    pip.mainloop()

# mainブランチ準拠: main()構造統一、backend/model引数のみ差分
def main():
    parser = argparse.ArgumentParser(
        prog="python main.py",
        description="asrivia — リアルタイム音声認識・翻訳ツール",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
よく使うコマンド例:
  python main.py                                  # デフォルト(MLX Whisper, 日本語)
  python main.py --dynamic-vad                    # 低遅延モード(発話終了を自動検知)
  python main.py --language auto --translate      # 言語自動判定 + 翻訳
  python main.py --backend qwen --dynamic-vad     # Qwen3-ASR(高精度, Apple Silicon)
  python main.py --backend hf --dynamic-vad       # HuggingFace Whisper + バイアシング
  python main.py --backend openai --language en   # PyTorch版Whisperで英語認識
  python main.py --backend mlx --model mlx-community/whisper-medium  # モデル指定
  python main.py --translate --translator gemma   # 高品質翻訳(TranslateGemma)
  python main.py --dict                           # 辞書登録UIのみ起動
  python main.py --dynamic-vad --koepus           # koepusコーパスへ自動書き出し
  python main.py --dynamic-vad --live-captions    # 二段デコード(発話中にライブ仮字幕)

ヒント: 全オプションは下の一覧を参照。`-h` でいつでもこの画面を表示できます。
""",
    )
    parser.add_argument("--language", choices=["ja", "en", "auto"], default="ja", help="認識言語モード: ja=日本語 en=英語 auto=自動判定")
    parser.add_argument("--translate", action="store_true", help="翻訳も実行する(指定しないと翻訳なし)")
    parser.add_argument("--translator", choices=["opus", "gemma"], default="opus", help="翻訳器: opus=軽量CPU(デフォルト, 高速) gemma=TranslateGemma 4B(高品質, GPU)")
    # mainブランチ準拠: backend/model引数のみ差分
    parser.add_argument("--backend", choices=["mlx", "openai", "stable-ts", "hf", "qwen"], default="mlx", help="ASRバックエンド: mlx=ローカル(デフォルト) openai=ローカルPyTorch版Whisper stable-ts=Whisper+VAD hf=HuggingFace Whisper+biasing qwen=Qwen3-ASR 1.7B MLX(高精度・biasing非対応)")
    parser.add_argument("--dict", action="store_true", dest="dict_only", help="辞書登録UIのみ起動（ASRなし）")
    parser.add_argument("--model", type=str, default=None, help="使用するモデル名(mlx: HFリポジトリパス、openai: Whisperモデル名)")
    # 動的セグメンテーション関連オプション
    parser.add_argument("--dynamic-vad", action="store_true", help="VADベースの動的セグメンテーションを有効化")
    parser.add_argument("--silence-threshold", type=float, default=0.01, help="無音判定閾値 (default: 0.01)")
    parser.add_argument("--silence-duration", type=float, default=0.5, help="無音継続時間[秒] (default: 0.5)")
    parser.add_argument("--min-record", type=float, default=0.5, help="最小録音時間[秒] (default: 0.5)")
    parser.add_argument("--max-record", type=float, default=5.0, help="最大録音時間[秒] (default: 5.0)")
    parser.add_argument("--overlap", type=float, default=0.0, help="オーバーラップ時間[秒] (default: 0.0)")
    # 二段デコード(ライブ仮字幕)オプション
    parser.add_argument("--live-captions", action="store_true", help="発話中にライブ仮字幕を表示(二段デコード。--dynamic-vad 必須, mlx/qwenバックエンドのみ)")
    parser.add_argument("--first-model", type=str, default="mlx-community/whisper-small-mlx", help="仮字幕用の小型モデル(HFリポジトリパス, default: mlx-community/whisper-small-mlx)")
    parser.add_argument("--live-interval", type=float, default=1.0, help="仮字幕の更新間隔[秒] (default: 1.0)")
    parser.add_argument("--history-lines", type=int, default=HISTORY_LINES_DEFAULT, help=f"字幕として残す確定発話の行数 (default: {HISTORY_LINES_DEFAULT})")
    # koepus連携オプション
    parser.add_argument("--koepus", action="store_true", help="認識1回ごとにwav+JSONをkoepusのincoming/へ書き出す")
    parser.add_argument("--koepus-dir", type=Path, default=None, help="koepusのincomingディレクトリ(未指定時は環境変数KOEPUS_INCOMING_DIRを使用)")
    args = parser.parse_args()
    
    # デフォルトモデル設定
    if args.model is None:
        if args.backend == "mlx":
            args.model = "mlx-community/whisper-large-v3-turbo"
        elif args.backend == "openai":
            args.model = "large-v3-turbo"
        elif args.backend == "stable-ts":
            args.model = "large-v3-turbo"
        elif args.backend == "hf":
            args.model = "openai/whisper-large-v3-turbo"
        elif args.backend == "qwen":
            args.model = "Qwen/Qwen3-ASR-1.7B"

    print(f"ASRバックエンド: {args.backend}")
    print(f"使用モデル: {args.model}")

    # koepus連携設定の組み立て
    koepus_cfg = None
    if args.koepus:
        koepus_dir = args.koepus_dir
        if koepus_dir is None:
            env_dir = os.environ.get("KOEPUS_INCOMING_DIR")
            if env_dir:
                koepus_dir = Path(env_dir)
        if koepus_dir is None:
            print("[koepus] --koepus-dir も環境変数 KOEPUS_INCOMING_DIR も未設定のため無効化します", file=sys.stderr)
        else:
            koepus_cfg = {
                "dir": koepus_dir,
                "backend": args.backend,
                "model": args.model,
                "dynamic_vad": args.dynamic_vad,
            }

    root = tk.Tk()
    root.withdraw()

    # --dict モード: 辞書UIのみ起動
    if args.dict_only:
        from asr.biasing import WordRegistry
        from asr.dict_window import DictWindow
        registry = WordRegistry.load("words.json")
        DictWindow(root, registry)
        root.mainloop()
        return

    # ライブ仮字幕の前提条件チェック(満たさなければ警告して無効化)
    if args.live_captions:
        if not args.dynamic_vad:
            print("[ライブ字幕] --dynamic-vad が無効のため仮字幕を無効化します", file=sys.stderr)
            args.live_captions = False
        elif args.backend not in ("mlx", "qwen"):
            print(f"[ライブ字幕] バックエンド {args.backend} は未対応のため仮字幕を無効化します(mlx/qwenのみ)", file=sys.stderr)
            args.live_captions = False

    audio_q = queue.Queue()
    result_q = queue.Queue()
    stop_ev = threading.Event()
    final_busy = threading.Event()
    oov_queue = queue.Queue() if args.backend == "hf" else None

    # hfバックエンド用: registryとreload_cbを事前準備
    hf_registry = None
    hf_reload_cb = None

    # レコーダー初期化
    if args.dynamic_vad:
        print(f"[動的VAD] 有効 (無音閾値: {args.silence_threshold}, 無音時間: {args.silence_duration}s, 最小: {args.min_record}s, 最大: {args.max_record}s, オーバーラップ: {args.overlap}s)")
        audio2wav.initialize_recorder(
            mode="dynamic",
            silence_threshold=args.silence_threshold,
            silence_duration=args.silence_duration,
            min_record_seconds=args.min_record,
            max_record_seconds=args.max_record,
            overlap_seconds=args.overlap
        )
    else:
        audio2wav.initialize_recorder(mode="fixed")

    # hfバックエンド: UIからregistryを共有するためにここでロード
    if args.backend == "hf":
        from asr.biasing import WordRegistry
        hf_registry = WordRegistry.load("words.json")
        # reload_cbはtranscribeスレッド内のbackendに委譲（mtime監視で自動リロード）
        hf_reload_cb = None  # backend側でmtime監視するため不要

    translator = None
    if args.translate:
        if args.translator == "gemma":
            translator = GemmaTranslator()
        else:
            translator = OpusTranslator()
    translate_q = queue.Queue() if args.translate else None

    threading.Thread(target=record_audio_thread, args=(audio_q,), daemon=True).start()

    threading.Thread(
        target=transcribe_audio_thread,
        args=(audio_q, result_q, args.language, args.translate, args.backend, args.model, oov_queue, translate_q, koepus_cfg, final_busy),
        daemon=True
    ).start()

    if args.live_captions:
        threading.Thread(
            target=live_caption_thread,
            args=(result_q, args.first_model, args.language, args.live_interval, final_busy),
            daemon=True
        ).start()

    if args.translate:
        threading.Thread(
            target=translate_worker_thread,
            args=(translate_q, result_q, translator),
            daemon=True
        ).start()

    start_pip_window(result_q, stop_ev, args.backend, hf_registry, hf_reload_cb, oov_queue, translate_enabled=args.translate, history_lines=args.history_lines)

if __name__ == "__main__":
    main()
