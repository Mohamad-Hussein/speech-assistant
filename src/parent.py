from platform import system
from time import time
from os.path import join
import logging
from shutil import copy


# Differentiate between windows and linux
if system() == 'Windows':
    from src.key_listener_win import Listener
else:
    from src.key_listener import Listener

from src.record import get_effects, get_audio
from src.model_inference import service
from wave import open

from multiprocessing import Process, Event, Pipe

from pyaudio import paInt16

# Global variables
# -------------------------

# Configure the logging settings
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename=join('logs','speech-assistant.log'),
    filemode='w'
)
# Create a logger instance
logger = logging.getLogger(__name__)

# Getting audio inputs and outputs
audio, stream_input, stream_output = get_audio()
stream_input.stop_stream()

# Get sound data
sound_low, sound_high = get_effects("effects", "button-low.wav", "button-high.wav")

logger.info(f"Audio: Default input info: {audio.get_default_input_device_info()}")
logger.info(f"Audio: Default output info: {audio.get_default_output_device_info()}")
logger.info(f"Audio: Device count: {audio.get_device_count()}")


# Sound file creation
sound_file = open("tmp.wav", "wb")
sound_file.setnchannels(1)
sound_file.setsampwidth(audio.get_sample_size(paInt16))
sound_file.setframerate(44100)


# -------------------------

def start_audio(start_event, model_event):
    # This line to wake device from sleep state
    logger.info('sound-high played')

    stream_output.write(sound_high)

    # stream_input.start_stream()
    logger.debug(f"stream is stopped: {stream_input.is_stopped()}")
    logger.debug(f"Get read: {stream_input.get_read_available()}")
    logger.debug(f"Is active: {stream_input.is_active()}")

    stream_input.start_stream()
    if not stream_input.is_active():
        print("Stream is not active")
        return
    
    frames = []
    try:
        print("Capture STARTED")
        while start_event.is_set():
            data = stream_input.read(1024)
            frames.append(data)
        print("Capture FINISHED")
        stream_output.write(sound_low)
        logger.info('sound-low played')

    except KeyboardInterrupt:
        print("Keyboard interrupt")
        return
    except Exception:
        print(f"\nCAPTURE UNSUCCESFUL!")
        return

    stream_input.stop_stream()    
    # sound_file.
    sound_file.writeframes(b"".join(frames))
    model_event.set()
    logger.debug(f"{sound_file.tell()}")
    logger.debug(f"Sound file size: {sound_file.getnframes() / sound_file.getframerate():.2f} seconds")
    print("Saved audio")
    sound_file.close()
    copy("tmp.wav", "recording.wav")

def run_listener(child_pipe, start_event):
    a = Listener(child_pipe, start_event)
    a.run()

def reset_sound_file():
    global sound_file
    # Copying soundbyte for debugging purposes
    copy("tmp.wav", "recording.wav")
    sound_file = open("tmp.wav", "wb")
    sound_file.setnchannels(1)
    sound_file.setsampwidth(audio.get_sample_size(paInt16))
    sound_file.setframerate(44100)

def main():
    # Input device
    print(f"Input device detected: \033[94m{audio.get_default_input_device_info()['name']}\033[0m")
    # Creating pipes just in case
    parent_pipe, child_pipe = Pipe(duplex=False)

    # Events for synchronization
    start_event = Event()
    model_event = Event()

    # Creating processe for model as it takes the longest to load
    model_process = Process(target=service, args=(child_pipe, model_event), name='WhisperModel')
    model_process.start()

    # Waiting for model to load
    print(f"Waiting for model to load\n\nModel message: ", end='')
    model_event.wait()
    model_event.clear()
    print(f"\nModel loaded!\n\n")

    # Creating process for Key listener
    userinput_process = Process(target=run_listener, args=(child_pipe, start_event), name='SA-KeyListener')
    userinput_process.start()

    try:
        while 1:
            try:
                # Waiting for Start event
                print("Waiting for hotkey")
                start_event.wait()

                # Starting to Record
                print("Recording")
                if start_event.is_set():
                    start_audio(start_event, model_event)
                else:
                    print("Did not record properly")
                    continue

                # Inference
                print("Starting inference")
                while model_event.is_set():
                    pass

                # To reset sound file, remove to continuously add more sound bytes
                reset_sound_file()

                # Clearing events
                start_event.clear()

            except Exception as e:
                print(f"Exception on parent!\n\n")
                print(e)
                break

    # To ensure that the processes are closed
    finally:
        userinput_process.join()
        stream_input.stop_stream()
        stream_output.stop_stream()
        stream_input.close()
        stream_output.close()
        audio.terminate()
        # sound_file.close()
        logger.info('Program End')
        print(f"\n\nspeech-assistant ended\n\n")