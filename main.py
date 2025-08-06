import mlx_whisper
import time
import audio2wav
import threading
import queue
import tkinter as tk
import torch
import silero_vad
from silero_vad import load_silero_vad, get_speech_timestamps

# Load Silero VAD model
vad_model = load_silero_vad()

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
        speech_timestamps = get_speech_timestamps(frame, vad_model)
        
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
        
        # Concatenate speech segments
        if speech_segments:
            concatenated_audio = torch.cat(speech_segments, dim=0)
            
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
    pip.title('認識結果')
    pip.geometry('400x140+1000+100')
    pip.attributes('-topmost', True)
    
    font_base = 14
    font_size = tk.IntVar(value=font_base)
    
    label = tk.Label(pip, text='認識中...', font=('Arial', font_base))
    label.pack(expand=True, fill='both')
    
    # フォントサイズ可変ボタン
    control_frame = tk.Frame(pip)
    control_frame.pack(side="bottom", pady=7)
    
    minus_btn = tk.Button(control_frame, text="－", width=2, command=lambda: change_font(-2))
    minus_btn.pack(side="left", padx=3)
    
    plus_btn = tk.Button(control_frame, text="＋", width=2, command=lambda: change_font(2))
    plus_btn.pack(side="left", padx=3)
    
    def change_font(diff):
        # 8〜48の範囲を推奨
        newsize = max(8, min(48, font_size.get() + diff))
        font_size.set(newsize)
        label.config(font=('Arial', newsize))
    
    def poll_queue():
        try:
            while True:
                new_text = result_q.get_nowait()
                label.config(text=new_text)
