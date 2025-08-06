import torch
from silero_vad import get_speech_timestamps, load_silero_vad
import mlx_whisper
import time
import audio2wav
import threading
import queue
import tkinter as tk
import numpy as np

# Load Silero VAD model
vad_model = load_silero_vad(device='cpu')

def record_audio_thread(audio_q):
    while True:
        frame = audio2wav.record_audio()
        audio_q.put(frame)

def transcribe_audio_thread(audio_q, result_q):
    filtered_phrases = [
        "ご視聴ありがとうございました。",
        "おやすみなさい。",
        "ありがとうございました。",
        "お疲れ様でした。",
        "お待ちしております。",
    ]
    
    while True:
        frame = audio_q.get()
        
        # VAD processing with silero-vad
        speech_timestamps = get_speech_timestamps(frame, vad_model, sampling_rate=16000)
        
        # Skip if no speech detected
        if not speech_timestamps:
            audio_q.task_done()
            continue
        
        # Extract only speech segments for Whisper
        speech_segments = []
        for timestamp in speech_timestamps:
            start_sample = timestamp['start']
            end_sample = timestamp['end']
            speech_segments.append(frame[start_sample:end_sample])
        
        # Concatenate speech segments using numpy
        if speech_segments:
            concatenated_audio = np.concatenate(speech_segments)
            
            text = mlx_whisper.transcribe(
                concatenated_audio,
                path_or_hf_repo="mlx-community/whisper-large-v3-turbo",
                language="ja"
            )
            
            if text["text"].strip() and text["text"] not in filtered_phrases:
                result_q.put(text["text"])
        
        audio_q.task_done()

def start_pip_window(result_q, stop_ev):
    pip = tk.Toplevel()
    pip.title("Transcription")
    pip.geometry("400x300+50+50")
    pip.attributes("-topmost", True)
    pip.configure(bg="black")
    
    text_area = tk.Text(
        pip, 
        bg="black", 
        fg="white", 
        wrap=tk.WORD,
        font=("Arial", 12)
    )
    text_area.pack(fill=tk.BOTH, expand=True)
    
    def update_text():
        try:
            while True:
                text = result_q.get_nowait()
                text_area.insert(tk.END, text + "\n")
                text_area.see(tk.END)
                result_q.task_done()
        except queue.Empty:
            pass
        
        if not stop_ev.is_set():
            pip.after(100, update_text)
    
    update_text()
    pip.mainloop()

def main():
    audio_q = queue.Queue(maxsize=10)
    result_q = queue.Queue()
    stop_ev = threading.Event()
    
    # Start threads
    audio_thread = threading.Thread(target=record_audio_thread, args=(audio_q,))
    transcribe_thread = threading.Thread(target=transcribe_audio_thread, args=(audio_q, result_q))
    
    audio_thread.daemon = True
    transcribe_thread.daemon = True
    
    audio_thread.start()
    transcribe_thread.start()
    
    # Start GUI
    root = tk.Tk()
    root.withdraw()  # Hide main window
    
    try:
        start_pip_window(result_q, stop_ev)
    except KeyboardInterrupt:
        stop_ev.set()
        print("\nStopping...")
    finally:
        stop_ev.set()

if __name__ == "__main__":
    main()
