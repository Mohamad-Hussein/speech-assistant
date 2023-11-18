from os.path import join
import logging
from shutil import copy


from src.funcs import get_effects, get_audio, run_listener
from src.model_inference import service
from wave import open

from multiprocessing import Process, Event, Pipe

from pyaudio import paInt16

# Global variables
# -------------------------

# Create a logger instance
logger = logging.getLogger(__name__)

# Getting audio inputs and outputs
audio, stream_input, stream_output = get_audio()

logger.info(f"Audio: Default input info: {audio.get_default_input_device_info()}")
logger.info(f"Audio: Default output info: {audio.get_default_output_device_info()}")
logger.info(f"Audio: Device count: {audio.get_device_count()}")

# No audio being recorded
stream_input.stop_stream()

# Get sound data, global to not load them in each time
sound_low, sound_high = get_effects("effects", "button-low.wav", "button-high.wav")


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

    # This line to wake device from sleep state
    stream_output.write(sound_high)

    stream_input.start_stream()
    logger.debug(f"Get read: {stream_input.get_read_available()}")
    
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
        logger.info("sound-low played")

    except KeyboardInterrupt:
        print("Keyboard interrupt")
        return
    except Exception:
        print(f"\nCAPTURE UNSUCCESFUL!")
        return

    stream_input.stop_stream()

    # Writing to file
    sound_file.writeframes(b"".join(frames))

    # Start model to be quicker
    model_event.set()
    logger.debug(f"{sound_file.tell()}")
    logger.debug(
        f"Sound file size: {sound_file.getnframes() / sound_file.getframerate():.2f}s"
    )
    print("Saved audio")
    sound_file.close()
    copy("tmp.wav", "recording.wav")


def main():
    ## Initial processes

    # Input device
    print(
        f"Input device detected: \033[94m{audio.get_default_input_device_info()['name']}\033[0m"
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
        target=run_listener, args=(child_pipe, start_event), name="SA-KeyListener"
    )
    userinput_process.start()

    start_event.wait()
    start_event.clear()

    ## Main loop
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
            print("Starting inference")
            while model_event.is_set():
                pass

            # Copying soundbyte for debugging purposes
            copy("tmp.wav", "recording.wav")

            # To reset sound file, remove to continuously add more sound bytes
            sound_file = create_sound_file()

            # Clearing events
            start_event.clear()

    except Exception as e:
        print(f"Exception on parent!\n\n")
        print(e)

    # To ensure that the processes are closed
    finally:
        userinput_process.join()
        stream_input.stop_stream()
        stream_output.stop_stream()
        stream_input.close()
        stream_output.close()
        audio.terminate()
        sound_file.close()
        logger.info("Program End")
        print(f"\n\nspeech-assistant ended\n\n")
