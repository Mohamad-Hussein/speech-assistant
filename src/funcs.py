from pyaudio import PyAudio, paInt16
import logging
from platform import system


logger = logging.getLogger(__name__)


def get_audio():
    audio = PyAudio()
    stream_input = audio.open(
        format=paInt16,
        channels=1,
        rate=44100,
        input=True,
        frames_per_buffer=1024,
    )

    return audio, stream_input


def run_listener(child_pipe, start_event, model_event):
    # Differentiate between windows and linux
    if system() == "Windows":
        from src.key_listener_win import Listener
    else:
        from src.key_listener import Listener

    a = Listener(child_pipe, start_event, model_event)
    a.run()
