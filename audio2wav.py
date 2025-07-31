import pyaudio
import numpy as np
import threading
import queue

class AudioRecorder:
    def __init__(self, rate=16000, chunk=1024, channels=1, record_seconds=3):
        self.rate = rate
        self.chunk = chunk
        self.channels = channels
        self.record_seconds = record_seconds
        self.format = pyaudio.paFloat32
        self.audio_queue = queue.Queue()
        self.stop_event = threading.Event()

    def record_audio(self):
        pa = pyaudio.PyAudio()
        stream = pa.open(rate=self.rate,
                    channels=self.channels,
                    format=self.format,
                    input=True,
                    frames_per_buffer=self.chunk)

        while not self.stop_event.is_set():
            data = stream.read(self.chunk)
            self.audio_queue.put(np.frombuffer(data, dtype=np.float32))

        stream.stop_stream()
        stream.close()
        pa.terminate()

    def start_recording(self):
        self.stop_event.clear()
        self.recording_thread = threading.Thread(target=self.record_audio)
        self.recording_thread.start()

    def stop_recording(self):
        self.stop_event.set()
        self.recording_thread.join()

    def get_audio_chunk(self):
        required_chunks = int(self.rate / self.chunk * self.record_seconds)
        audio_data = []

        while len(audio_data) < required_chunks:
            try:
                audio_data.append(self.audio_queue.get(timeout=1))
            except queue.Empty:
                if self.stop_event.is_set():
                    break

        return np.concatenate(audio_data) if audio_data else None

recorder = None

def initialize_recorder():
    global recorder
    if recorder is None:
        recorder = AudioRecorder()
        recorder.start_recording()

def record_audio():
    global recorder
    if recorder is None:
        initialize_recorder()
    return recorder.get_audio_chunk()

def cleanup():
    global recorder
    if recorder is not None:
        recorder.stop_recording()
        recorder = None
