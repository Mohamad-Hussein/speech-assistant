from os.path import join
import logging
from shutil import copy

from time import time, sleep
from src.funcs import get_audio, run_listener
from src.model_inference import service
from wave import open

from multiprocessing import Process, Event, Pipe
from threading import Thread

from pyaudio import paInt16
from playsound import playsound

# Global variables
# -------------------------

# Create a logger instance
logger = logging.getLogger(__name__)

# Getting audio inputs
audio, stream_input = get_audio()

# No audio being recorded
stream_input.stop_stream()


# -------------------------
def create_sound_file():
    # Copying soundbyte for debugging purposes
    sound_file = open("tmp.wav", "wb")
    sound_file.setnchannels(1)
    sound_file.setsampwidth(audio.get_sample_size(paInt16))
    sound_file.setframerate(44100)
    return sound_file


def start_recording(start_event, model_event, sound_file):
    logger.info("sound-high played")
    t0 = time()

    # This line to wake device from sleep state
    # Huge performance gain from Threading and playsound
    sound1 = Thread(target=playsound, args=(join('effects', 'button-high.wav'),), name='play-sound1')
    sound2 = Thread(target=playsound, args=(join('effects', 'button-low.wav'),), name='play-sound2')

    # Start stream
    stream_input.start_stream()
    logger.debug(f"Get read: {stream_input.get_read_available()}")

    if not stream_input.is_active():
        print("Stream is not active")
        return

    # Capturing audio
    frames = []
    try:
        sound1.start()
        logger.info(f"From start to capture: {time() - t0:.2f}s")

        print("Capture STARTED")
        while start_event.is_set():
            data = stream_input.read(1024)
            frames.append(data)
        print("Capture FINISHED")

        sound2.start()
        logger.info("sound-low played")

    except KeyboardInterrupt:
        print("Keyboard interrupt")
        return
    except Exception:
        print(f"\nCAPTURE UNSUCCESFUL!")
        return
    finally:
        sound1.join()
        sound2.join()

    # Stop stream
    stream_input.stop_stream()

    # Checking extreme case
    if model_event.is_set():
        print("!!Already doing inference!!")
        logger.error("Already doing inference, too quick")
        return
    
    # Writing to file
    sound_file.writeframes(b"".join(frames))

    # Start model to be quicker
    model_event.set()

    # Logging
    logger.debug(f"Sound file tell: {sound_file.tell()}")
    logger.debug(
        f"Sound file size: {sound_file.getnframes() / sound_file.getframerate():.2f}s"
    )

    # Sound file saving and copying
    sound_file.close()
    print("Saved audio")
    copy("tmp.wav", "recording.wav")


def main():
    ## Initial processes ##
    logger.info(f"Audio: Default input info: {audio.get_default_input_device_info()}")
    logger.info(f"Audio: Default output info: {audio.get_default_output_device_info()}")
    logger.info(f"Audio: Device count: {audio.get_device_count()}")
    logger.info(f"Audio: Host API count: {audio.get_host_api_count()}")

    # Input device
    print(
        f"Input device detected: \033[94m{audio.get_default_input_device_info()['name']} \033[0m"
    )

    # Creating pipes just in case
    parent_pipe, child_pipe = Pipe(duplex=False)

    # Events for synchronization
    start_event = Event()
    model_event = Event()

    # Creating processe for model as it takes the longest to load
    model_process = Process(
        target=service, args=(child_pipe, model_event), name="WhisperModel"
    )
    model_process.start()

    # Waiting for model to load
    print(f"Waiting for model to load\n\nModel message: ", end="")
    model_event.wait()
    model_event.clear()

    # Creating process for Key listener
    userinput_process = Process(
        target=run_listener, args=(child_pipe, start_event, model_event), name="SA-KeyListener"
    )
    userinput_process.start()

    # Waiting for key listener to start
    start_event.wait()
    start_event.clear()

    ## Main loop ##
    try:
        sound_file = create_sound_file()
        while 1:
            # Waiting for Start event
            print("Waiting for hotkey")
            start_event.wait()

            # Starting to Record
            print("Recording...\n")
            if start_event.is_set():
                start_recording(start_event, model_event, sound_file)
            else:
                print("Did not record properly")
                continue

            # Inference
            print("\n--Starting inference--")
            while model_event.is_set():
                pass

            # Copying soundbyte for debugging purposes
            copy("tmp.wav", "recording.wav")

            # To reset sound file, remove to continuously add more sound bytes
            sound_file = create_sound_file()

            # Clearing events
            start_event.clear()
    except KeyboardInterrupt:
        print("\n\033[92m\033[4mparent.py\033[0m \033[92mprocess ended\033[0m")
    except Exception as e:
        logger.error(f"Exception on parent: {e}")
        print("\n\033[91m\033[4mparent.py\033[0m \033[91mprocess ended\033[0m")


    finally:
        # Processes
        model_process.join()
        userinput_process.join()
        # Audio
        stream_input.stop_stream()
        stream_input.close()
        audio.terminate()
        sound_file.close()
        # Logging
        logger.info("Program End")

