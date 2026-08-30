import io
import threading
import wave

import numpy as np
import pyaudio
import webrtcvad
from loguru import logger

from common.concurrent.abs_runnable import ThreadRunnable
from common.io.file_type import AudioFileType
from event.event_data import DeviceMicrophoneVADEvent
from event.event_emitter import emitter


class SmartMicrophone(ThreadRunnable):
    def __init__(self, enable_vad: bool=False, vad_mode=3, frame_duration=30, rms_threshold: float = 100.0):
        """
        初始化智能麦克风类
        :param vad_mode: Optionally, set its aggressiveness mode, which is an integer between 0 and 3.
                         0 is the least aggressive about filtering out non-speech, 3 is the most aggressive.
        :param frame_duration: A frame must be either 10, 20, or 30 ms in duration.
        """
        super().__init__()
        self._enable_vad = enable_vad
        self._rms_threshold = rms_threshold
        if frame_duration not in [10, 20, 30]:
            raise ValueError(f"A frame must be either 10, 20, or 30 ms in duration!")

        # Audio parameters
        self._format = pyaudio.paInt16
        self._channels = 1
        self._sample_rate = 16000
        self._chunk_size = int(self._sample_rate * frame_duration / 1000)  # Bytes

        # Initialize microphone
        self._audio = pyaudio.PyAudio()
        self._vad = webrtcvad.Vad(vad_mode)
        self._stream = self._audio.open(format=self._format,
                                        channels=self._channels,
                                        rate=self._sample_rate,
                                        input=True,
                                        frames_per_buffer=self._chunk_size)

        self._audio_frames = []
        self._is_speaking = False
        self._silence_frames = 0
        # Number of consecutive non-speech frames before ending speech segment
        # 30 frames * 30ms = 900ms of silence to end speech
        self._silence_threshold = 30

        # self._pause_event = threading.Event()
        self._stop_flag = False

        # 初始默认麦克风 off
        if self._stream.is_active():
            self._stream.stop_stream()

        self._talk_enabled_event = threading.Event()
        self._talk_enabled_event.clear()

        # 外部环境可用的锁
        self._recording_lock = threading.Lock()

    @property
    def is_recording(self):
        # return self._pause_event.is_set() and (not self._stop_flag) and self._stream.is_active()
        return self._talk_enabled_event.is_set() and (not self._stop_flag) and self._stream.is_active()

    def start(self):
        super().start()
        # self._pause_event.set()
        self._stop_flag = False
        try:
            i = 0
            while not self._stop_flag:
                # self._pause_event.wait()
                self._talk_enabled_event.wait()

                with self._recording_lock:
                    if not self._talk_enabled_event.is_set():
                        continue
                    self._stream_update()

                    if self._stop_flag:
                        break

                    data = self._stream.read(self._chunk_size, exception_on_overflow=False)
                    if i % 100 == 0:
                        rms = float(np.sqrt(np.mean(np.frombuffer(data, dtype=np.int16).astype(np.float32) ** 2)))
                        logger.debug(f"Mic reading: active={self._stream.is_active()}, "
                                     f"rms={rms:.1f}, is_speech={self._vad.is_speech(data, self._sample_rate)}")
                    i += 1
                    self._vad_record(data)

        except Exception as e:
            logger.exception(e)
        finally:
            # Stop and close the microphone stream
            self._stream.stop_stream()
            self._stream.close()
            self._audio.terminate()

    def _vad_record(self, data: bytes):
        if self._enable_vad:
            is_speech = self._vad.is_speech(data, self._sample_rate)
            if is_speech:
                self._silence_frames = 0
                if not self._is_speaking:
                    rms = float(np.sqrt(np.mean(np.frombuffer(data, dtype=np.int16).astype(np.float32) ** 2)))
                    if rms >= self._rms_threshold:
                        logger.info(f"Voice detected: Beginning. (rms={rms:.1f})")
                        self._is_speaking = True
                    else:
                        return  # Noise below threshold, ignore
                self._audio_frames.append(data)
            else:
                if self._is_speaking:
                    self._silence_frames += 1
                    self._audio_frames.append(data)  # Keep frames during debounce
                    if self._silence_frames >= self._silence_threshold:
                        logger.info("Voice detected: Ending.")
                        self._is_speaking = False
                        self._silence_frames = 0
                        self._emit_event()
                        self._audio_frames = []
        else:
            if not self._is_speaking:
                self._is_speaking = True
            self._audio_frames.append(data)

    def _emit_event(self):
        if self._audio_frames:
            # 创建一个BytesIO对象来存储WAV文件
            file = io.BytesIO()
            with wave.open(file, 'wb') as wf:
                wf.setnchannels(self._channels)
                wf.setsampwidth(self._audio.get_sample_size(self._format))
                wf.setframerate(self._sample_rate)
                wf.writeframes(b''.join(self._audio_frames))

            # 将BytesIO对象的指针移到开始位置
            file.seek(0)
            emitter.emit(DeviceMicrophoneVADEvent(
                speech=file.read(),
                audio_type=AudioFileType.WAV,
                channels=self._channels,
                sample_rate=self._sample_rate,
            ))

    def _stream_update(self):
        if self._talk_enabled_event.is_set():
            if not self._stream.is_active():
                self._stream.start_stream()
        else:
            if self._stream.is_active():
                self._stream.stop_stream()

    def pause(self):
        # self._pause_event.clear()
        self._talk_enabled_event.clear()
        logger.info("Paused smart microphone.")

    def resume(self):
        # self._pause_event.set()
        self._talk_enabled_event.set()
        logger.info("Resumed smart microphone.")

    def stop(self):
        self._stop_flag = True
        # self._pause_event.set()
        # self._talk_enabled_event.clear()
        # Fix: Set it to true to avoid the deadlock!
        self._talk_enabled_event.set()
        logger.info("Stopped smart microphone.")

    def close(self):
        try:
            if self._stream.is_active():
                self._stream.stop_stream()
            self._stream.close()
        except Exception:
            pass
        try:
            self._audio.terminate()
        except Exception:
            pass
        logger.info("Closed smart microphone resources.")

    def name(self):
        return "SmartMicrophone"
    
    def is_set_talk_enabled_event(self):
        return self._talk_enabled_event.is_set()
    
    def set_talk_enabled_event(self):
        self._talk_enabled_event.set()

    def unset_talk_enabled_event(self):
        self._talk_enabled_event.clear()

    def force_commit(self, is_emit=False):
        with self._recording_lock:
            if self._is_speaking and self._audio_frames and is_emit:
                self._is_speaking = False
                self._silence_frames = 0
                self._emit_event()
            self._is_speaking = False
            self._silence_frames = 0
            self._audio_frames = []