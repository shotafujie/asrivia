import mlx_whisper
import time
import audio2wav
import threading
import queue
import tkinter as tk
import argparse

def record_audio_thread(audio_q):
    while True:
        frame = audio2wav.record_audio()
        audio_q.put(frame)

def transcribe_audio_thread(audio_q, result_q, language_mode):
    filtered_phrases = [
        "ご視聴ありがとうございました。",
        "おやすみなさい。",
        "ありがとうございました。",
        "お疲れ様でした。",
        "お待ちしております。",
    ]
    while True:
        frame = audio_q.get()
        # 言語切り替え
        if language_mode == "auto":
            # 自動判定
            text_result = mlx_whisper.transcribe(
                frame,
                path_or_hf_repo="mlx-community/whisper-large-v3-turbo",
                language=None  # 自動判定
            )
        else:
            # ja/enを明示
            text_result = mlx_whisper.transcribe(
                frame,
                path_or_hf_repo="mlx-community/whisper-large-v3-turbo",
                language=language_mode
            )
        text = text_result["text"]
        if text.strip() and text not in filtered_phrases:
            result_lang = text_result.get("language", "")
            # 画面にも現在の認識言語を明示（自動時のみ）
            if language_mode == "auto" and result_lang:
                result_q.put(f"[{result_lang.upper()}] {text}")
            else:
                result_q.put(text)
        audio_q.task_done()

def start_pip_window(result_q, stop_ev):
    pip = tk.Toplevel()
    pip.title('認識結果')
    pip.geometry('400x140+1000+100')
    pip.attributes('-topmost', True)
    font_base = 14
    font_size = tk.IntVar(value=font_base)
    label = tk.Label(pip, text='認識中...', font=('Arial', font_base))
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
    # 追加: コマンドライン引数パース
    parser = argparse.ArgumentParser()
    parser.add_argument("--language", choices=["ja", "en", "auto"], default="ja",
                        help="認識言語モード: ja=日本語 en=英語 auto=自動判定")
    args = parser.parse_args()

    root = tk.Tk()
    root.withdraw()
    audio_q = queue.Queue()
    result_q = queue.Queue()
    stop_ev = threading.Event()
    audio2wav.initialize_recorder()
    threading.Thread(target=record_audio_thread, args=(audio_q,), daemon=True).start()
    threading.Thread(target=transcribe_audio_thread, args=(audio_q, result_q, args.language), daemon=True).start()
    start_pip_window(result_q, stop_ev)

if __name__ == "__main__":
    main()
