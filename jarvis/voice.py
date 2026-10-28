"""Voice I/O: wake word / push-to-talk, faster-whisper STT, pyttsx3 or edge-tts TTS.

All imports are lazy so text mode works without any audio packages.
"""
from __future__ import annotations

import asyncio
import os
import tempfile

SAMPLE_RATE = 16000


class Speaker:
    def __init__(self, use_edge: bool = False):
        self.use_edge = use_edge
        self._engine = None

    def say(self, text: str) -> None:
        print(f"Jarvis: {text}")
        if not text:
            return
        try:
            if self.use_edge:
                self._edge(text)
            else:
                if self._engine is None:
                    import pyttsx3

                    self._engine = pyttsx3.init()
                self._engine.say(text)
                self._engine.runAndWait()
        except Exception as exc:  # audio is best-effort
            print(f"(tts unavailable: {exc})")

    def _edge(self, text: str) -> None:
        import edge_tts
        from playsound import playsound

        path = os.path.join(tempfile.gettempdir(), "jarvis_tts.mp3")
        asyncio.run(edge_tts.Communicate(text, "en-GB-RyanNeural").save(path))
        playsound(path)


class Listener:
    def __init__(self, whisper_model: str = "base.en"):
        from faster_whisper import WhisperModel

        self.model = WhisperModel(whisper_model, device="cpu", compute_type="int8")

    def record(self, seconds: float = 5.0):
        import sounddevice as sd

        audio = sd.rec(int(seconds * SAMPLE_RATE), samplerate=SAMPLE_RATE, channels=1, dtype="float32")
        sd.wait()
        return audio.flatten()

    def transcribe(self, audio) -> str:
        segments, _ = self.model.transcribe(audio, language="en", vad_filter=True)
        return " ".join(s.text for s in segments).strip()


def wait_for_hotkey(hotkey: str) -> None:
    import keyboard

    print(f"Press {hotkey} to talk...")
    keyboard.wait(hotkey)


def wait_for_wake_word(name: str = "hey_jarvis", threshold: float = 0.5) -> None:
    """Block until openWakeWord hears the wake word (pre-trained 'hey jarvis' model)."""
    import numpy as np
    import sounddevice as sd
    import openwakeword
    from openwakeword.model import Model

    openwakeword.utils.download_models([name])
    model = Model(wakeword_models=[name], inference_framework="onnx")
    print("Listening for 'Hey Jarvis'...")
    with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype="int16", blocksize=1280) as stream:
        while True:
            frame, _ = stream.read(1280)
            scores = model.predict(np.asarray(frame).flatten())
            if max(scores.values()) >= threshold:
                model.reset()
                return
