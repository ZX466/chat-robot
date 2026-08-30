import threading
from enum import Enum
from pathlib import Path
from queue import Queue

import pygame

from common.concurrent.abs_runnable import ThreadRunnable
from common.concurrent.killable_thread import KillableThread
from event.event_data import DeviceSpeakerPlayEvent
from event.event_emitter import emitter

_mixer_initialized = False
_system_sound = False


def _ensure_mixer_init():
    global _mixer_initialized
    if not _mixer_initialized:
        pygame.mixer.init()
        _mixer_initialized = True


class SystemSoundEnum(str, Enum):
    warn: str = "warn.wav"
    error: str = "error.wav"
    start: str = "start.wav"
    exit: str = "exit.wav"
    enable_func: str = "microphone-recoding.wav"
    disable_func: str = "microphone-stopped.wav"
    filtered: str = "filtered.wav"


class Speaker(ThreadRunnable):

    def name(self):
        return 'Speaker'

    def __init__(self):
        super().__init__()
        _ensure_mixer_init()
        self._stop_flag = False
        self._semaphore = threading.Event()
        self._speaker_thread = KillableThread(target=self._run)
        self.audio_clips: Queue[Path] = Queue()

    def start(self):
        super().start()
        self._stop_flag = False
        self._semaphore.set()
        self._speaker_thread.start()

    def stop(self):
        super().stop()
        self._stop_flag = True
        self._semaphore.set()
        self._speaker_thread.kill()
        self.close()

    def close(self):
        global _mixer_initialized
        if _mixer_initialized:
            try:
                pygame.mixer.stop()
                pygame.mixer.quit()
                _mixer_initialized = False
            except Exception:
                pass

    def _run(self):
        while not self._stop_flag:
            if self.audio_clips.empty():
                self._semaphore.clear()
            self._semaphore.wait()
            if self._stop_flag:
                break
            try:
                audio_clip = self.audio_clips.get_nowait()
            except Exception:
                continue
            emitter.emit(DeviceSpeakerPlayEvent(audio_path=audio_clip))
            self.playsound(audio_clip, block=True)

    def enqueue_sound(self, path_or_data: Path):
        self.activate_check()
        self.audio_clips.put(path_or_data)
        self._semaphore.set()

    def stop_now(self):
        pygame.mixer.stop()
        self.audio_clips = Queue()

    @staticmethod
    def playsound(path: Path, block: bool = True):
        if block:
            Speaker._sync_playsound(path)
        else:
            Speaker._async_playsound(path)

    @staticmethod
    def _sync_playsound(path: Path):
        pygame.mixer.music.load(path)
        pygame.mixer.music.play()
        Speaker.wait()

    @staticmethod
    def wait():
        import time
        while pygame.mixer.music.get_busy():
            time.sleep(0.1)

    @staticmethod
    def _async_playsound(path: Path):
        sound = pygame.mixer.Sound(path)
        pygame.mixer.Sound.play(sound)

    def __del__(self):
        self.close()
