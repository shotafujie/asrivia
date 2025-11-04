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
import numpy as np
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
    print("[DEBUG] record_audio_thread started", type(audio_q))
    try:
        # 修正: audio2wav.record_audio()から得られるデータがfloat32スカラーの場合に
        # 配列に蓄積してから1D numpy配列として返却する
        frames = []  # フレームを蓄積するリスト
        sample_rate = 16000  # サンプリングレート
        chunk_duration = 1.0  # 音声チャンクの長さ(秒)
        target_length = int(sample_rate * chunk_duration)  # 目標サンプル数
        print(f"[DEBUG] target_length set to {target_length} (chunk_duration={chunk_duration}s)")
        
        for frame in audio2wav.record_audio():
            print("[DEBUG] audio2wav.record_audio() yielded", type(frame), getattr(frame, 'shape', frame), frame)
            
            # frameがnumpy配列でそのまま使える場合(1D配列)
            if isinstance(frame, np.ndarray) and frame.ndim == 1:
                audio_q.put(frame)
                print("[DEBUG] audio_q.put (1D ndarray)", type(frame), getattr(frame, 'shape', frame))
            # frameがスカラー値(float32など)の場合は配列に蓄積
            elif isinstance(frame, (float, np.floating, np.number)):
                frames.append(float(frame))
                print(f"[DEBUG] frame appended, frames length now: {len(frames)}/{target_length}")
                # 目標長に達したら1D配列としてqueueにput
                if len(frames) >= target_length:
                    audio_array = np.array(frames, dtype=np.float32)
                    audio_q.put(audio_array)
                    print(f"[DEBUG] ★ audio_q.put (accumulated array) shape={audio_array.shape}, frames_count={len(frames)}")
                    frames = []  # リストをクリア
                    print(f"[DEBUG] frames cleared, ready for next batch")
            else:
                # 想定外の型の場合はスキップ
                print(f"[DEBUG] Unexpected frame type: {type(frame)}, skipping")
                
    except Exception as e:
        print(f"[録音エラー]\n{e}", file=sys.stderr)
def transcribe_audio_thread(audio_q, result_q, lang_mode, enable_translate, backend, model_name):
    print(f"[DEBUG] transcribe_audio_thread started backend={backend} model_name={model_name}", type(audio_q), type(result_q))
    """
    音声認識スレッド。バックエンドに応じて処理を切り替える。
    backend: 'mlx' または 'openai'
    model_name: 使用するモデル名(mlx: HFリポジトリパス、openai: Whisperモデル名)
    """
    if backend == "mlx":
        print(f"[MLX] モデル: {model_name}")
    elif backend == "openai":
        import whisper
        print(f"[PyTorch Whisper] モデルをロード中: {model_name}")
        asr_model = whisper.load_model(model_name)
        print("[PyTorch Whisper] モデルのロードが完了しました")
    else:
        raise ValueError(f"未対応のバックエンド: {backend}")
    
    print("[DEBUG] transcribe_audio_thread initialization done")
    
    while True:
        try:
            print("[DEBUG] audio_q.get() before")
            frame = audio_q.get()
            print("[DEBUG] audio_q.get() after", type(frame), getattr(frame, 'shape', frame), frame)
            
            if frame is None:
                print("[DEBUG] frame is None, skipping")
                audio_q.task_done()
                break
            
            if not isinstance(frame, np.ndarray):
                print("[DEBUG] frame is not np.ndarray", type(frame))
                audio_q.task_done()
                continue
            
            if frame.ndim != 1 or frame.size == 0:
                print("[DEBUG] frame ndim/size invalid", frame.ndim, frame.size)
                audio_q.task_done()
                continue
            
            print(f"[DEBUG] Recognition (backend={backend}) start", type(frame), getattr(frame, 'shape', frame))
            
            if backend == "mlx":
                if lang_mode == "auto":
                    result = mlx_whisper.transcribe(frame, path_or_hf_repo=model_name)
                else:
                    result = mlx_whisper.transcribe(frame, path_or_hf_repo=model_name, language=lang_mode)
                text = result.get("text", "").strip()
                detected_lang = result.get("language", lang_mode)
            elif backend == "openai":
                if lang_mode == "auto":
                    result = asr_model.transcribe(frame)
                else:
                    result = asr_model.transcribe(frame, language=lang_mode)
                text = result.get("text", "").strip()
                detected_lang = result.get("language", lang_mode)
            
            print(f"[DEBUG] Recognition result: text={text}, detected_lang={detected_lang}")
            audio_q.task_done()
            
            if not text:
                print("[DEBUG] Recognition result is empty text, skipping")
                continue
            
            translated = None
            if enable_translate:
                from_lang, to_lang = detect_translation_direction(detected_lang)
                print(f"[DEBUG] Translation requested: from={from_lang}, to={to_lang}")
                if from_lang and to_lang:
                    translated = translate_with_plamo(text, from_lang, to_lang)
                    print(f"[DEBUG] Translated: {translated}")
            
            print(f"[DEBUG 認識結果] text: {text}, translated: {translated}")
            result_q.put((text, translated))
            print(f"[DEBUG] result_q.put", type(text), type(translated))
            
        except Exception as e:
            print(f"[文字起こしエラー]\n{e}", file=sys.stderr)
            import traceback
            traceback.print_exc()
            audio_q.task_done()
def start_pip_window(result_q, stop_ev):
    print("[DEBUG] start_pip_window called", type(result_q), type(stop_ev))
    pip = tk.Toplevel()
    print("[DEBUG] PiPウィンドウ生成", type(pip))
    pip.title("asrivia")
    pip.geometry("500x220")
    pip.attributes("-topmost", True)
    pip.attributes("-alpha", 1.0)
    
    font_size = tk.IntVar(value=14)
    text_label = tk.Label(pip, text="認識結果がここに表示されます", font=("Arial", 14), wraplength=480, justify="left")
    text_label.pack(pady=10)
    translate_label = tk.Label(pip, text="", font=("Arial", 12), fg="blue", wraplength=480, justify="left")
    translate_label.pack(pady=5)
    
    def change_font(delta):
        new_size = font_size.get() + delta
        if new_size < 8:
            new_size = 8
        elif new_size > 32:
            new_size = 32
        font_size.set(new_size)
        print(f"[DEBUG] change_font: new_size={new_size}")
        text_label.config(font=("Arial", new_size))
        translate_label.config(font=("Arial", max(8, new_size - 2)))
    
    button_frame = tk.Frame(pip)
    button_frame.pack(side=tk.BOTTOM, pady=5)
    btn_decrease = tk.Button(button_frame, text="－", command=lambda: change_font(-2))
    btn_decrease.pack(side=tk.LEFT, padx=5)
    btn_increase = tk.Button(button_frame, text="＋", command=lambda: change_font(2))
    btn_increase.pack(side=tk.LEFT, padx=5)
    
    def poll_queue():
        print("[DEBUG] poll_queue called")
        while not result_q.empty():
            try:
                text, translated = result_q.get_nowait()
                print(f"[DEBUG 表示更新] text: {text}, translated: {translated}")
                text_label.config(text=text)
                if translated:
                    translate_label.config(text=f"翻訳: {translated}")
                else:
                    translate_label.config(text="")
                result_q.task_done()
            except queue.Empty:
                print("[DEBUG] result_q empty in poll_queue")
                pass
        if not stop_ev.is_set():
            pip.after(500, poll_queue)
        else:
            print("[DEBUG] PiPウィンドウ閉じる (stop_ev set)")
            pip.destroy()
    
    poll_queue()
    pip.protocol("WM_DELETE_WINDOW", stop_ev.set)
    pip.mainloop()
def main():
    print("[DEBUG] main() start")
    parser = argparse.ArgumentParser()
    parser.add_argument("--language", choices=["ja", "en", "auto"], default="ja", help="認識言語モード: ja=日本語 en=英語 auto=自動判定")
    parser.add_argument("--translate", action="store_true", help="翻訳も実行する(指定しないと翻訳なし)")
    parser.add_argument("--backend", choices=["mlx", "openai"], default="mlx", help="ASRバックエンド: mlx=ローカル(デフォルト) openai=ローカルPyTorch版Whisper")
    parser.add_argument("--model", type=str, default=None, help="使用するモデル名(mlx: HFリポジトリパス、openai: Whisperモデル名)")
    args = parser.parse_args()
    print(f"[DEBUG] args: {args}")
    
    if args.model is None:
        if args.backend == "mlx":
            args.model = "mlx-community/whisper-large-v3-turbo"
            print("[DEBUG] モデル名未指定→mlxデフォルトモデル設定", args.model)
        elif args.backend == "openai":
            args.model = "large-v3-turbo"
            print("[DEBUG] モデル名未指定→openaiデフォルトモデル設定", args.model)
    
    print(f"ASRバックエンド: {args.backend}")
    print(f"使用モデル: {args.model}")
    
    root = tk.Tk()
    root.withdraw()
    
    audio_q = queue.Queue()
    result_q = queue.Queue()
    stop_ev = threading.Event()
    print("[DEBUG] queue/event created", type(audio_q), type(result_q), type(stop_ev))
    
    audio2wav.initialize_recorder()
    print("[DEBUG] initialize_recorder() called")
    
    print("[DEBUG] Launching recording/transcribe threads...")
    threading.Thread(target=record_audio_thread, args=(audio_q,), daemon=True).start()
    print("[DEBUG] record_audio_thread launched")
    
    threading.Thread(
        target=transcribe_audio_thread,
        args=(audio_q, result_q, args.language, args.translate, args.backend, args.model),
        daemon=True
    ).start()
    print("[DEBUG] transcribe_audio_thread launched")
    
    start_pip_window(result_q, stop_ev)
    print("[DEBUG] main() end")
if __name__ == "__main__":
    main()
