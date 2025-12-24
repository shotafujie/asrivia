import pyaudio
import numpy as np
import threading
import queue
import time


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


class DynamicAudioRecorder:
    """VADベースの動的セグメンテーションをサポートする音声レコーダー"""

    def __init__(self, rate=16000, chunk=1024, channels=1,
                 silence_threshold=0.01, silence_duration=0.5,
                 min_record_seconds=0.5, max_record_seconds=5.0,
                 overlap_seconds=0.0):
        self.rate = rate
        self.chunk = chunk
        self.channels = channels
        self.format = pyaudio.paFloat32

        # VAD パラメータ
        self.silence_threshold = silence_threshold  # 無音と判定するエネルギー閾値
        self.silence_duration = silence_duration    # 無音がこの時間続いたら発話終了
        self.min_record_seconds = min_record_seconds  # 最小録音時間
        self.max_record_seconds = max_record_seconds  # 最大録音時間
        self.overlap_seconds = overlap_seconds      # オーバーラップ時間

        self.audio_queue = queue.Queue()
        self.stop_event = threading.Event()
        self.overlap_buffer = []  # オーバーラップ用バッファ

    def _calculate_energy(self, audio_chunk):
        """音声チャンクのエネルギー（RMS）を計算"""
        return np.sqrt(np.mean(audio_chunk ** 2))

    def record_audio(self):
        """バックグラウンドで音声を連続録音"""
        pa = pyaudio.PyAudio()
        stream = pa.open(rate=self.rate,
                        channels=self.channels,
                        format=self.format,
                        input=True,
                        frames_per_buffer=self.chunk)

        while not self.stop_event.is_set():
            data = stream.read(self.chunk)
            chunk_array = np.frombuffer(data, dtype=np.float32)
            self.audio_queue.put(chunk_array)

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
        """VADベースで動的に音声チャンクを取得"""
        audio_data = list(self.overlap_buffer)  # 前回のオーバーラップを先頭に
        self.overlap_buffer = []

        chunk_duration = self.chunk / self.rate
        silence_chunks_needed = int(self.silence_duration / chunk_duration)
        min_chunks = int(self.min_record_seconds / chunk_duration)
        max_chunks = int(self.max_record_seconds / chunk_duration)
        overlap_chunks = int(self.overlap_seconds / chunk_duration)

        consecutive_silence = 0
        is_speaking = False

        while len(audio_data) < max_chunks:
            try:
                chunk = self.audio_queue.get(timeout=1)
                audio_data.append(chunk)

                energy = self._calculate_energy(chunk)

                if energy > self.silence_threshold:
                    # 発話検出
                    is_speaking = True
                    consecutive_silence = 0
                else:
                    # 無音
                    consecutive_silence += 1

                # 発話開始後、無音が一定時間続いたら終了
                if is_speaking and consecutive_silence >= silence_chunks_needed:
                    if len(audio_data) >= min_chunks:
                        break

            except queue.Empty:
                if self.stop_event.is_set():
                    break

        if not audio_data:
            return None

        # オーバーラップ用に末尾を保存
        if overlap_chunks > 0 and len(audio_data) > overlap_chunks:
            self.overlap_buffer = audio_data[-overlap_chunks:]

        return np.concatenate(audio_data)


recorder = None
recorder_mode = "fixed"  # "fixed" or "dynamic"


def initialize_recorder(mode="fixed", **kwargs):
    """
    レコーダーを初期化

    Args:
        mode: "fixed" (固定3秒) or "dynamic" (VADベース動的セグメンテーション)
        **kwargs: DynamicAudioRecorderのパラメータ
            - silence_threshold: 無音判定閾値 (default: 0.01)
            - silence_duration: 無音継続時間 (default: 0.5秒)
            - min_record_seconds: 最小録音時間 (default: 0.5秒)
            - max_record_seconds: 最大録音時間 (default: 5.0秒)
            - overlap_seconds: オーバーラップ時間 (default: 0.0秒)
    """
    global recorder, recorder_mode
    recorder_mode = mode

    if recorder is None:
        if mode == "dynamic":
            recorder = DynamicAudioRecorder(**kwargs)
        else:
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
