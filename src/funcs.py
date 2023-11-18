from pyaudio import PyAudio, paInt16
from wave import open
from os.path import join
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

    stream_output = audio.open(
        format=paInt16,
        channels=1,
        rate=44100,
        output=True,
    )
    return audio, stream_input, stream_output


def get_effects(dir_name: str, sound_low_name: str, sound_high_name: str):
    file_low = open(join(dir_name, sound_low_name), "rb")
    file_high = open(join(dir_name, sound_high_name), "rb")
    sound_low = file_low.readframes(file_low.getnframes())
    sound_high = file_high.readframes(file_high.getnframes())
    file_low.close()
    file_high.close()
    return sound_low, sound_high


def run_listener(child_pipe, start_event):
    # Differentiate between windows and linux
    if system() == "Windows":
        from src.key_listener_win import Listener
    else:
        from src.key_listener import Listener

    a = Listener(child_pipe, start_event)
    a.run()
