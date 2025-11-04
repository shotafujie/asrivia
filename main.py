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
    if lang in ["ja", "jpn", "japanese"]:
        return ("ja", "en")
    elif lang in ["en", "eng", "english"]:
        return ("en", "ja")
    else:
        return (lang, "English")

def record_audio_thread(audio_q):
    while True:
        frame = audio2wav.record_audio()
        audio_q.put(frame)

# ASRバックエンド分岐処理: mlxまたはopenaiを選択
def transcribe_audio_thread(audio_q, result_q, language_mode, enable_translate, backend, model_name):
    """
    ASR処理スレッド
    backend: 'mlx' または 'openai'
    model_name: 使用するモデル名（mlxの場合はHugging Faceリポジトリパス、openaiの場合はモデル名）
    """
    filtered_phrases = [
        "ご視聴ありがとうございました。",
        "おやすみなさい。",
        "ありがとうございました。",
        "お疲れ様でした。",
        "お待ちしております。",
    ]
    
    # OpenAI APIを使用する場合はクライアント初期化
    if backend == "openai":
        try:
            from openai import OpenAI
            client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
        except ImportError:
            print("Error: openai パッケージがインストールされていません。pip install openai を実行してください。", file=sys.stderr)
            return
        except Exception as e:
            print(f"Error: OpenAI初期化エラー: {e}", file=sys.stderr)
            return
    
    while True:
        frame = audio_q.get()
        
        # バックエンドに応じて音声認識処理を分岐
        try:
            if backend == "mlx":
                # mlx-whisperを使用（ローカルモデル）
                if language_mode == "auto":
                    text_result = mlx_whisper.transcribe(
                        frame,
                        path_or_hf_repo=model_name,
                        language=None
                    )
                else:
                    text_result = mlx_whisper.transcribe(
                        frame,
                        path_or_hf_repo=model_name,
                        language=language_mode
                    )
                text = text_result["text"]
                result_lang = text_result.get("language", "")
                
            elif backend == "openai":
                # OpenAI Whisper APIを使用
                import tempfile
                # 一時ファイルに音声データを保存
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
                    tmp_file.write(frame)
                    tmp_path = tmp_file.name
                
                try:
                    with open(tmp_path, "rb") as audio_file:
                        if language_mode == "auto":
                            transcription = client.audio.transcriptions.create(
                                model=model_name,
                                file=audio_file
                            )
                        else:
                            transcription = client.audio.transcriptions.create(
                                model=model_name,
                                file=audio_file,
                                language=language_mode
                            )
                    text = transcription.text
                    result_lang = language_mode if language_mode != "auto" else ""
                finally:
                    os.unlink(tmp_path)
            else:
                print(f"Error: 不明なバックエンド: {backend}", file=sys.stderr)
                audio_q.task_done()
                continue
                
        except Exception as e:
            print(f"Error: 音声認識エラー ({backend}): {e}", file=sys.stderr)
            audio_q.task_done()
            continue
        
        if text.strip() and text not in filtered_phrases:
            if enable_translate:
                from_lang, to_lang = detect_translation_direction(result_lang)
                translation = translate_with_plamo(text, from_lang, to_lang)
                if language_mode == "auto" and result_lang:
                    output = f"[{result_lang.upper()}] {text}\n→ [{to_lang}] {translation}"
                else:
                    output = f"{text}\n→ {translation}"
            else:
                if language_mode == "auto" and result_lang:
                    output = f"[{result_lang.upper()}] {text}"
                else:
                    output = text
            result_q.put(output)
        audio_q.task_done()

def start_pip_window(result_q, stop_ev):
    pip = tk.Toplevel()
    pip.title('asrivia')
    pip.geometry('480x180+1000+100')
    pip.attributes('-topmost', True)
    font_base = 14
    font_size = tk.IntVar(value=font_base)
    label = tk.Label(pip, text='認識中...', font=('Arial', font_base), anchor="w", justify="left")
    label.pack(expand=True, fill='both')
    control_frame = tk.Frame(pip)
    control_frame.pack(side="bottom", pady=7)
    minus_btn = tk.Button(control_frame, text="－", width=2, command=lambda: change_font(-2))
    minus_btn.pack(side="left", padx=3)
    plus_btn = tk.Button(control_frame, text="＋", width=2, command=lambda: change_font(2))
    plus_btn.pack(side="left", padx=3)
    def change_font(diff):
        newsize = max(8, min(48, font_size.get() + diff))
        font_size.set(newsize)
        label.config(font=('Arial', newsize))
    def poll_queue():
        try:
            while True:
                new_text = result_q.get_nowait()
                label.config(text=new_text)
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
                        help="ASRバックエンド: mlx=ローカル（デフォルト） openai=OpenAI API")
    # モデル指定引数を追加
    parser.add_argument("--model", type=str, default=None,
                        help="使用するモデル名（mlx: HFリポジトリパス、openai: モデル名）")
    args = parser.parse_args()
    
    # モデル名のデフォルト値設定
    if args.model is None:
        if args.backend == "mlx":
            args.model = "mlx-community/whisper-large-v3-turbo"  # mlxデフォルトモデル
        elif args.backend == "openai":
            args.model = "whisper-1"  # OpenAI デフォルトモデル
    
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
