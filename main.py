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
            timeout=10
        )
        if result.returncode != 0:
            # 失敗時はエラー詳細を標準エラー出力
            err = result.stderr.decode().strip()
            print(f"[PLaMo翻訳エラー]\n{err}", file=sys.stderr)
            return f"[翻訳エラー]"
        return result.stdout.decode().strip()
    except Exception as e:
        print(f"[PLaMo呼び出し例外]\n{e}", file=sys.stderr)
        return f"[翻訳エラー: {e}]"

def detect_translation_direction(lang):
    # Whisper認識言語から翻訳方向を決定
    if lang == "ja":
        return ("ja", "en")
    elif lang == "en":
        return ("en", "ja")
    else:
        return (None, None)

def record_audio_thread(audio_q):
    try:
        # 修正: record_generator()からrecord_audio()へ変更
        for wav_path in audio2wav.record_audio():
            audio_q.put(wav_path)
    except Exception as e:
        print(f"[録音エラー]\n{e}", file=sys.stderr)

def transcribe_audio_thread(audio_q, result_q, lang_mode, enable_translate, backend, model_name):
    """
    音声認識スレッド。バックエンドに応じて処理を切り替える。
    backend: 'mlx' または 'openai'
    model_name: 使用するモデル名（mlx: HFリポジトリパス、openai: Whisperモデル名）
    """
    # バックエンドごとの初期化
    if backend == "mlx":
        # MLXバックエンド: mlx_whisperを使用（修正: 事前ロードなし、transcribe時に直接モデル名を指定）
        print(f"[MLX] モデル: {model_name}")
    elif backend == "openai":
        # OpenAIバックエンド: ローカルPyTorch版Whisperライブラリを使用
        import whisper
        print(f"[PyTorch Whisper] モデルをロード中: {model_name}")
        asr_model = whisper.load_model(model_name)
        print("[PyTorch Whisper] モデルのロードが完了しました")
    else:
        raise ValueError(f"未対応のバックエンド: {backend}")

    while True:
        try:
            wav_path = audio_q.get()
            if wav_path is None:
                break

            # バックエンドに応じて文字起こし処理
            if backend == "mlx":
                # MLXバックエンド（修正: 事前ロードなし、transcribeで直接モデル名指定）
                if lang_mode == "auto":
                    result = mlx_whisper.transcribe(wav_path, path_or_hf_repo=model_name)
                else:
                    result = mlx_whisper.transcribe(wav_path, path_or_hf_repo=model_name, language=lang_mode)
                text = result.get("text", "").strip()
                detected_lang = result.get("language", lang_mode)
            elif backend == "openai":
                # OpenAIバックエンド: ローカルPyTorch版Whisperライブラリを使用
                if lang_mode == "auto":
                    result = asr_model.transcribe(wav_path)
                else:
                    result = asr_model.transcribe(wav_path, language=lang_mode)
                text = result.get("text", "").strip()
                detected_lang = result.get("language", lang_mode)

            if not text:
                continue

            # 翻訳処理
            translated = None
            if enable_translate:
                from_lang, to_lang = detect_translation_direction(detected_lang)
                if from_lang and to_lang:
                    translated = translate_with_plamo(text, from_lang, to_lang)

            result_q.put((text, translated))

        except Exception as e:
            print(f"[文字起こしエラー]\n{e}", file=sys.stderr)
            import traceback
            traceback.print_exc()

def start_pip_window(result_q, stop_ev):
    pip = tk.Toplevel()
    pip.title("asrivia")
    pip.geometry("400x150")
    pip.attributes("-topmost", True)
    # 修正: 透明度を標準（1.0 = 不透明）に変更
    pip.attributes("-alpha", 1.0)

    text_label = tk.Label(pip, text="認識結果がここに表示されます", font=("Arial", 14), wraplength=380, justify="left")
    text_label.pack(pady=10)

    translate_label = tk.Label(pip, text="", font=("Arial", 12), fg="blue", wraplength=380, justify="left")
    translate_label.pack(pady=5)

    def poll_queue():
        while not result_q.empty():
            try:
                text, translated = result_q.get_nowait()
                text_label.config(text=text)
                if translated:
                    translate_label.config(text=f"翻訳: {translated}")
                else:
                    translate_label.config(text="")
            except queue.Empty:
                pass
        if not stop_ev.is_set():
            pip.after(500, poll_queue)
        else:
            pip.destroy()

    poll_queue()
    pip.protocol("WM_DELETE_WINDOW", stop_ev.set)
    pip.mainloop()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--language", choices=["ja", "en", "auto"], default="ja",
                        help="認識言語モード: ja=日本語 en=英語 auto=自動判定")
    parser.add_argument("--translate", action="store_true",
                        help="翻訳も実行する（指定しないと翻訳なし）")
    # ASRバックエンド選択引数を追加（デフォルトはmlx）
    parser.add_argument("--backend", choices=["mlx", "openai"], default="mlx",
                        help="ASRバックエンド: mlx=ローカル（デフォルト） openai=ローカルPyTorch版Whisper")
    # モデル指定引数を追加
    parser.add_argument("--model", type=str, default=None,
                        help="使用するモデル名（mlx: HFリポジトリパス、openai: Whisperモデル名）")
    args = parser.parse_args()
    
    # モデル名のデフォルト値設定
    if args.model is None:
        if args.backend == "mlx":
            args.model = "mlx-community/whisper-large-v3-turbo"  # mlxデフォルトモデル
        elif args.backend == "openai":
            args.model = "large-v3-turbo"  # PyTorch Whisperデフォルトモデル
    
    print(f"ASRバックエンド: {args.backend}")
    print(f"使用モデル: {args.model}")
    
    root = tk.Tk()
    root.withdraw()

    audio_q = queue.Queue()
    result_q = queue.Queue()
    stop_ev = threading.Event()

    audio2wav.initialize_recorder()

    threading.Thread(target=record_audio_thread, args=(audio_q,), daemon=True).start()
    threading.Thread(
        target=transcribe_audio_thread,
        args=(audio_q, result_q, args.language, args.translate, args.backend, args.model),
        daemon=True
    ).start()
    
    start_pip_window(result_q, stop_ev)

if __name__ == "__main__":
    main()
