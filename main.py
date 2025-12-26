import mlx_whisper
import time
import audio2wav
import threading
import queue
import tkinter as tk
import argparse
import subprocess
import sys
import os

def translate_with_plamo(text, from_lang, to_lang):
    try:
        result = subprocess.run(
            [
                "plamo-translate",
                "--from", from_lang,
                "--to", to_lang,
                "--input", text
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=60
        )
        if result.returncode != 0:
            err = result.stderr.decode().strip()
            print(f"[PLaMo翻訳エラー]\n{err}", file=sys.stderr)
            return f"[翻訳エラー]"
        return result.stdout.decode().strip()
    except Exception as e:
        print(f"[PLaMo呼び出し例外]\n{e}", file=sys.stderr)
        return f"[翻訳エラー: {e}]"

def detect_translation_direction(lang):
    # Whisper認識言語から翻訳方向を決定
    # plamo-translate仕様に合わせて英語表記へ変更
    if lang == "ja":
        return ("Japanese", "English")
    elif lang == "en":
        return ("English", "Japanese")
    else:
        return (None, None)

# mainブランチ準拠: record_audio_thread構造そのままコピー
def record_audio_thread(audio_q):
    try:
        while True:
            frame = audio2wav.record_audio()
            audio_q.put(frame)
    except Exception as e:
        print(f"[録音エラー]\n{e}", file=sys.stderr)

# mainブランチ準拠: transcribe_audio_thread構造を統一、backend対応のみ追加
def transcribe_audio_thread(audio_q, result_q, lang_mode, enable_translate, backend, model_name):
    """
    音声認識スレッド。バックエンドに応じて処理を切り替える。
    backend: 'mlx', 'openai', または 'stable-ts'
    model_name: 使用するモデル名(mlx: HFリポジトリパス、openai/stable-ts: Whisperモデル名)
    """
    # mainブランチ準拠: backend選択のみ差分
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
    else:
        raise ValueError(f"未対応のバックエンド: {backend}")
    
    while True:
        try:
            frame = audio_q.get()
            if frame is None:
                audio_q.task_done()
                break
            
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
            
            text = result.get("text", "").strip()
            detected_lang = result.get("language", lang_mode)
            audio_q.task_done()
            
            if not text:
                continue
            
            # mainブランチ準拠: 翻訳処理
            translated = None
            if enable_translate:
                from_lang, to_lang = detect_translation_direction(detected_lang)
                if from_lang and to_lang:
                    translated = translate_with_plamo(text, from_lang, to_lang)
            
            # mainブランチ準拠: 結果はタプル形式で送信
            result_q.put((text, translated))
            
        except Exception as e:
            print(f"[文字起こしエラー]\n{e}", file=sys.stderr)
            import traceback
            traceback.print_exc()
            audio_q.task_done()

# mainブランチ準拠: start_pip_window構造そのままコピー
def start_pip_window(result_q, stop_ev):
    pip = tk.Toplevel()
    pip.title("asrivia")
    pip.geometry("500x110")
    pip.attributes("-topmost", True)
    pip.attributes("-alpha", 1.0)
    
    font_size = tk.IntVar(value=14)
    text_label = tk.Label(pip, text="認識結果がここに表示されます", font=("Arial", 14), wraplength=480, justify="left")
    text_label.pack(pady=10)
    # mainブランチ準拠: 翻訳結果も同じラベルで表示、文字色を白に変更
    translate_label = tk.Label(pip, text="", font=("Arial", 12), fg="white", wraplength=480, justify="left")
    translate_label.pack(pady=5)
    
    def change_font(delta):
        new_size = font_size.get() + delta
        if new_size < 8:
            new_size = 8
        elif new_size > 32:
            new_size = 32
        font_size.set(new_size)
        text_label.config(font=("Arial", new_size))
        translate_label.config(font=("Arial", max(8, new_size - 2)))
    
    button_frame = tk.Frame(pip)
    button_frame.pack(side=tk.BOTTOM, pady=5)
    btn_decrease = tk.Button(button_frame, text="－", command=lambda: change_font(-2))
    btn_decrease.pack(side=tk.LEFT, padx=5)
    btn_increase = tk.Button(button_frame, text="＋", command=lambda: change_font(2))
    btn_increase.pack(side=tk.LEFT, padx=5)
    
    # mainブランチ準拠: poll_queue構造そのままコピー
    def poll_queue():
        try:
            while True:
                text, translated = result_q.get_nowait()
                # mainブランチ準拠: 認識結果と翻訳結果を「→」形式で表示
                if translated:
                    text_label.config(text=f"{text}\n→ {translated}")
                else:
                    text_label.config(text=text)
                # translate_labelは使用しないので空にする
                translate_label.config(text="")
                result_q.task_done()
        except queue.Empty:
            pass
        if not stop_ev.is_set():
            pip.after(250, poll_queue)
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
    # mainブランチ準拠: backend/model引数のみ差分
    parser.add_argument("--backend", choices=["mlx", "openai", "stable-ts"], default="mlx", help="ASRバックエンド: mlx=ローカル(デフォルト) openai=ローカルPyTorch版Whisper stable-ts=Whisper+VAD")
    parser.add_argument("--model", type=str, default=None, help="使用するモデル名(mlx: HFリポジトリパス、openai: Whisperモデル名)")
    # 動的セグメンテーション関連オプション
    parser.add_argument("--dynamic-vad", action="store_true", help="VADベースの動的セグメンテーションを有効化")
    parser.add_argument("--silence-threshold", type=float, default=0.01, help="無音判定閾値 (default: 0.01)")
    parser.add_argument("--silence-duration", type=float, default=0.5, help="無音継続時間[秒] (default: 0.5)")
    parser.add_argument("--min-record", type=float, default=0.5, help="最小録音時間[秒] (default: 0.5)")
    parser.add_argument("--max-record", type=float, default=5.0, help="最大録音時間[秒] (default: 5.0)")
    parser.add_argument("--overlap", type=float, default=0.0, help="オーバーラップ時間[秒] (default: 0.0)")
    args = parser.parse_args()
    
    # mainブランチ準拠: デフォルトモデル設定のみ差分
    if args.model is None:
        if args.backend == "mlx":
            args.model = "mlx-community/whisper-large-v3-turbo"
        elif args.backend == "openai":
            args.model = "large-v3-turbo"
        elif args.backend == "stable-ts":
            args.model = "large-v3-turbo"
    
    print(f"ASRバックエンド: {args.backend}")
    print(f"使用モデル: {args.model}")

    root = tk.Tk()
    root.withdraw()

    audio_q = queue.Queue()
    result_q = queue.Queue()
    stop_ev = threading.Event()

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
    
    # mainブランチ準拠: スレッド起動構造そのままコピー
    threading.Thread(target=record_audio_thread, args=(audio_q,), daemon=True).start()
    
    threading.Thread(
        target=transcribe_audio_thread,
        args=(audio_q, result_q, args.language, args.translate, args.backend, args.model),
        daemon=True
    ).start()
    
    start_pip_window(result_q, stop_ev)

if __name__ == "__main__":
    main()
