import pyaudio
import numpy as np
import threading
import queue
import time


# PortAudio の Pa_Initialize/Pa_Terminate(pyaudio.PyAudio()/.terminate())は
# スレッドアンセーフなグローバル状態を触るため、複数スレッドから同時に呼ぶと
# macOS で segfault する。プロセス全体で単一インスタンスを共有し、生成と終了を
# それぞれ一度きりに限定することで競合を無くす。
_pa_instance = None
_pa_lock = threading.Lock()


def get_pyaudio():
    """プロセス共有の単一 PyAudio インスタンスを返す(無ければ生成)。"""
    global _pa_instance
    with _pa_lock:
        if _pa_instance is None:
            _pa_instance = pyaudio.PyAudio()
        return _pa_instance


class AudioRecorder:
    def __init__(self, rate=16000, chunk=1024, channels=1, record_seconds=3, device_index=None):
        self.rate = rate
        self.chunk = chunk
        self.channels = channels
        self.record_seconds = record_seconds
        self.format = pyaudio.paFloat32
        self.audio_queue = queue.Queue()
        self.stop_event = threading.Event()
        self.device_index = device_index

    def record_audio(self):
        pa = get_pyaudio()
        with _pa_lock:
            stream = pa.open(rate=self.rate,
                        channels=self.channels,
                        format=self.format,
                        input=True,
                        input_device_index=self.device_index,
                        frames_per_buffer=self.chunk)

        try:
            while not self.stop_event.is_set():
                data = stream.read(self.chunk, exception_on_overflow=False)
                self.audio_queue.put(np.frombuffer(data, dtype=np.float32))
        finally:
            stream.stop_stream()
            stream.close()
            # 共有インスタンスのため terminate() しない(cleanup() で一度だけ)。

    def start_recording(self):
        self.stop_event.clear()
        self.recording_thread = threading.Thread(target=self.record_audio)
        self.recording_thread.start()

    def stop_recording(self):
        self.stop_event.set()
        if hasattr(self, "recording_thread"):
            self.recording_thread.join()

    def change_device(self, device_index):
        self.stop_recording()
        self.device_index = device_index
        while not self.audio_queue.empty():
            try:
                self.audio_queue.get_nowait()
            except queue.Empty:
                break
        self.start_recording()

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
                 overlap_seconds=0.0, device_index=None):
        self.rate = rate
        self.chunk = chunk
        self.channels = channels
        self.format = pyaudio.paFloat32

        self.silence_threshold = silence_threshold
        self.silence_duration = silence_duration
        self.min_record_seconds = min_record_seconds
        self.max_record_seconds = max_record_seconds
        self.overlap_seconds = overlap_seconds

        self.audio_queue = queue.Queue()
        self.stop_event = threading.Event()
        self.overlap_buffer = []
        self.device_index = device_index

    def _calculate_energy(self, audio_chunk):
        return np.sqrt(np.mean(audio_chunk ** 2))

    def record_audio(self):
        pa = get_pyaudio()
        with _pa_lock:
            stream = pa.open(rate=self.rate,
                            channels=self.channels,
                            format=self.format,
                            input=True,
                            input_device_index=self.device_index,
                            frames_per_buffer=self.chunk)

        try:
            while not self.stop_event.is_set():
                data = stream.read(self.chunk, exception_on_overflow=False)
                chunk_array = np.frombuffer(data, dtype=np.float32)
                self.audio_queue.put(chunk_array)
        finally:
            stream.stop_stream()
            stream.close()
            # 共有インスタンスのため terminate() しない(cleanup() で一度だけ)。

    def start_recording(self):
        self.stop_event.clear()
        self.recording_thread = threading.Thread(target=self.record_audio)
        self.recording_thread.start()

    def stop_recording(self):
        self.stop_event.set()
        if hasattr(self, "recording_thread"):
            self.recording_thread.join()

    def change_device(self, device_index):
        self.stop_recording()
        self.device_index = device_index
        self.overlap_buffer = []
        while not self.audio_queue.empty():
            try:
                self.audio_queue.get_nowait()
            except queue.Empty:
                break
        self.start_recording()

    def get_audio_chunk(self):
        audio_data = list(self.overlap_buffer)
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
                    is_speaking = True
                    consecutive_silence = 0
                else:
                    consecutive_silence += 1

                if is_speaking and consecutive_silence >= silence_chunks_needed:
                    if len(audio_data) >= min_chunks:
                        break

            except queue.Empty:
                if self.stop_event.is_set():
                    break

        if not audio_data:
            return None

        # 発話が一度も検出されなければ(全区間が無音)、ASR に渡さず破棄する。
        # 無音を渡すと特に Whisper が「ご視聴ありがとうございました」等を幻聴するため。
        # producer(record_audio_thread)は None をスキップする。
        if not is_speaking:
            return None

        if overlap_chunks > 0 and len(audio_data) > overlap_chunks:
            self.overlap_buffer = audio_data[-overlap_chunks:]

        return np.concatenate(audio_data)


recorder = None
recorder_mode = "fixed"


def list_input_devices():
    """利用可能な入力デバイス一覧を返す"""
    pa = get_pyaudio()
    devices = []
    # 列挙は録音スレッドの pa.open() と同じロックで直列化する。
    with _pa_lock:
        try:
            default_index = pa.get_default_input_device_info().get("index")
        except Exception:
            default_index = None
        for i in range(pa.get_device_count()):
            info = pa.get_device_info_by_index(i)
            if info.get("maxInputChannels", 0) > 0:
                devices.append({
                    "index": i,
                    "name": info.get("name", f"device {i}"),
                    "is_default": i == default_index,
                })
    return devices


def get_current_device():
    if recorder is None:
        return None
    return getattr(recorder, "device_index", None)


def switch_device(device_index):
    """実行中のレコーダーの入力デバイスを切り替える"""
    global recorder
    if recorder is None:
        return
    recorder.change_device(device_index)


def initialize_recorder(mode="fixed", device_index=None, **kwargs):
    global recorder, recorder_mode
    recorder_mode = mode

    if recorder is None:
        if mode == "dynamic":
            recorder = DynamicAudioRecorder(device_index=device_index, **kwargs)
        else:
            recorder = AudioRecorder(device_index=device_index)
        recorder.start_recording()


def record_audio():
    global recorder
    if recorder is None:
        initialize_recorder()
    return recorder.get_audio_chunk()


def cleanup():
    global recorder, _pa_instance
    if recorder is not None:
        recorder.stop_recording()
        recorder = None
    with _pa_lock:
        if _pa_instance is not None:
            _pa_instance.terminate()
            _pa_instance = None
