import mlx_whisper
import time
import audio2wav
import threading
import queue
import tkinter as tk
import argparse
import sys
import os

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
            frame = audio2wav.record_audio()
            if frame is None:
                continue
            audio_q.put(frame)
    except Exception as e:
        print(f"[録音エラー]\n{e}", file=sys.stderr)

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
def transcribe_audio_thread(audio_q, result_q, lang_mode, enable_translate, backend, model_name, oov_queue=None, translate_q=None):
    """
    音声認識スレッド。バックエンドに応じて処理を切り替える。
    backend: 'mlx', 'openai', 'stable-ts', または 'hf'
    model_name: 使用するモデル名
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
    else:
        raise ValueError(f"未対応のバックエンド: {backend}")

    utterance_id = 0

    while True:
        try:
            frame = audio_q.get()
            if frame is None:
                audio_q.task_done()
                break

            audio_sec = len(frame) / 16000.0 if hasattr(frame, "__len__") else 0.0
            t_asr_start = time.time()

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
            
            text = result.get("text", "").strip()
            detected_lang = result.get("language", lang_mode)
            audio_q.task_done()
            asr_sec = time.time() - t_asr_start

            if not text:
                continue

            utterance_id += 1
            print(f"[timing] uid={utterance_id} audio={audio_sec:.2f}s asr={asr_sec:.2f}s aqlen={audio_q.qsize()}")

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
            print(f"[文字起こしエラー]\n{e}", file=sys.stderr)
            import traceback
            traceback.print_exc()
            audio_q.task_done()

FONT_MIN = 8
FONT_MAX = 96
FONT_DEFAULT = 14


def start_pip_window(result_q, stop_ev, backend=None, registry=None, reload_cb=None, oov_queue=None, translate_enabled=False):
    pip = tk.Toplevel()
    pip.title("asrivia")
    pip.geometry("600x180")
    pip.minsize(360, 120)
    pip.attributes("-topmost", True)
    pip.attributes("-alpha", 1.0)

    font_size = tk.IntVar(value=FONT_DEFAULT)

    # ボタンバーを最初にpack(side=BOTTOM)して最下部を確保
    button_frame = tk.Frame(pip)
    button_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=5, pady=4)

    text_label = tk.Label(
        pip,
        text="認識結果がここに表示されます",
        font=("Arial", FONT_DEFAULT),
        wraplength=580,
        justify="left",
        anchor="nw",
    )
    text_label.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=10, pady=8)

    def update_wraplength(event=None):
        try:
            w = pip.winfo_width()
        except tk.TclError:
            return
        if w > 40:
            text_label.config(wraplength=w - 40)

    pip.bind("<Configure>", update_wraplength)

    def change_font(delta):
        new_size = max(FONT_MIN, min(FONT_MAX, font_size.get() + delta))
        font_size.set(new_size)
        text_label.config(font=("Arial", new_size))

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
    state = {"uid": None, "text": "", "translated": None, "translate_enabled": translate_enabled}

    def render():
        if state["text"] == "":
            return
        if state["translate_enabled"]:
            tr = state["translated"] if state["translated"] is not None else "..."
            text_label.config(text=f"{state['text']}\n→ {tr}")
        else:
            text_label.config(text=state["text"])

    def poll_queue():
        try:
            while True:
                msg = result_q.get_nowait()
                kind, uid, payload = msg
                if kind == "text":
                    state["uid"] = uid
                    state["text"] = payload
                    state["translated"] = None
                    render()
                elif kind == "translation":
                    if uid == state["uid"]:
                        state["translated"] = payload
                        render()
                    # 古い翻訳が遅れて到着した場合は破棄
                result_q.task_done()
        except queue.Empty:
            pass
        if not stop_ev.is_set():
            pip.after(100, poll_queue)
        else:
            pip.destroy()
    
    poll_queue()
    pip.protocol("WM_DELETE_WINDOW", stop_ev.set)
    pip.mainloop()

# mainブランチ準拠: main()構造統一、backend/model引数のみ差分
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--language", choices=["ja", "en", "auto"], default="ja", help="認識言語モード: ja=日本語 en=英語 auto=自動判定")
    parser.add_argument("--translate", action="store_true", help="翻訳も実行する(指定しないと翻訳なし)")
    parser.add_argument("--translator", choices=["opus", "gemma"], default="opus", help="翻訳器: opus=軽量CPU(デフォルト, 高速) gemma=TranslateGemma 4B(高品質, GPU)")
    # mainブランチ準拠: backend/model引数のみ差分
    parser.add_argument("--backend", choices=["mlx", "openai", "stable-ts", "hf"], default="mlx", help="ASRバックエンド: mlx=ローカル(デフォルト) openai=ローカルPyTorch版Whisper stable-ts=Whisper+VAD hf=HuggingFace Whisper+biasing")
    parser.add_argument("--dict", action="store_true", dest="dict_only", help="辞書登録UIのみ起動（ASRなし）")
    parser.add_argument("--model", type=str, default=None, help="使用するモデル名(mlx: HFリポジトリパス、openai: Whisperモデル名)")
    # 動的セグメンテーション関連オプション
    parser.add_argument("--dynamic-vad", action="store_true", help="VADベースの動的セグメンテーションを有効化")
    parser.add_argument("--silence-threshold", type=float, default=0.01, help="無音判定閾値 (default: 0.01)")
    parser.add_argument("--silence-duration", type=float, default=0.5, help="無音継続時間[秒] (default: 0.5)")
    parser.add_argument("--min-record", type=float, default=0.5, help="最小録音時間[秒] (default: 0.5)")
    parser.add_argument("--max-record", type=float, default=5.0, help="最大録音時間[秒] (default: 5.0)")
    parser.add_argument("--overlap", type=float, default=0.0, help="オーバーラップ時間[秒] (default: 0.0)")
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
    
    print(f"ASRバックエンド: {args.backend}")
    print(f"使用モデル: {args.model}")

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

    audio_q = queue.Queue()
    result_q = queue.Queue()
    stop_ev = threading.Event()
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
        args=(audio_q, result_q, args.language, args.translate, args.backend, args.model, oov_queue, translate_q),
        daemon=True
    ).start()

    if args.translate:
        threading.Thread(
            target=translate_worker_thread,
            args=(translate_q, result_q, translator),
            daemon=True
        ).start()

    start_pip_window(result_q, stop_ev, args.backend, hf_registry, hf_reload_cb, oov_queue, translate_enabled=args.translate)

if __name__ == "__main__":
    main()
