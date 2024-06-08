from time import time, sleep
from os.path import join
import logging
import traceback
from threading import Thread

from src.config import SAVE_AUDIO
from src.utils.funcs import get_audio, create_sound_file, pcm_to_wav

from playsound import playsound

# Global variables
# -------------------------

# Create a logger instance
logger = logging.getLogger(__name__)

# -------------------------


def start_recording(start_event, model_event, queue):
    logger.info("sound-high played")
    t0 = time()

    # This line to wake device from sleep state
    # Huge performance gain from Threading and playsound
    sound1 = Thread(
        target=playsound, args=(join("effects", "button-high.wav"),), name="play-sound1"
    )
    sound2 = Thread(
        target=playsound, args=(join("effects", "button-low.wav"),), name="play-sound2"
    )

    # Start stream
    stream_input.start_stream()
    logger.debug(f"Get read: {stream_input.get_read_available()}")

    if not stream_input.is_active():
        print("Stream is not active")
        return

    # Capturing audio
    frames = []
    try:
        # Playing start sound
        sound1.start()
        logger.info(f"From start to capture: {time() - t0:.2f}s")

        # Capturing audio
        print("Capture STARTED")
        while start_event.is_set():
            data = stream_input.read(1024)
            frames.append(data)
        print("Capture FINISHED")

        # Converting to wav
        sound_byte_wav = pcm_to_wav(b"".join(frames))

        # Sending sound to model for inference
        queue.put({"message": sound_byte_wav, "do_action": True})

        # Checking extreme case
        if model_event.is_set():
            print("!!Already doing inference!!")
            logger.error("Already doing inference, too quick")
            return
        # Start model to be quicker
        model_event.set()

        # Playing end sound
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

    # Saving audio
    if SAVE_AUDIO:
        # This wav file is for resetting the audio byte
        sound_file = create_sound_file("recording.wav")

        # Writing to file
        sound_file.writeframes(b"".join(frames))

        # Logging
        logger.debug(f"Sound file tell: {sound_file.tell()}")
        logger.debug(
            f"Sound file size: {sound_file.getnframes() / sound_file.getframerate():.2f}s"
        )

        sound_file.close()
        print("Saved audio")

    return


def main_loop(
    start_event,
    model_event,
    terminate_event,
    sound_data_queue,
):
    ## Initial processes ##

    # Getting audio inputs
    global audio, stream_input
    audio, stream_input = get_audio()

    # No audio being recorded
    stream_input.stop_stream()

    logger.info(f"Audio: Default input info: {audio.get_default_input_device_info()}")
    logger.info(f"Audio: Default output info: {audio.get_default_output_device_info()}")
    logger.info(f"Audio: Device count: {audio.get_device_count()}")
    logger.info(f"Audio: Host API count: {audio.get_host_api_count()}")

    # Input device
    print(
        f"Input device detected: \033[94m{audio.get_default_input_device_info()['name']} \033[0m"
    )

    # Waiting for model to be loaded
    model_event.wait()

    ## Main loop ##
    try:
        # Init
        while 1:
            # Waiting for Start event
            print("Waiting for hotkey")
            start_event.wait()

            # To terminate process
            if terminate_event.is_set():
                raise KeyboardInterrupt

            # Starting to Record
            print("Recording...\n")
            if start_event.is_set():
                start_recording(start_event, model_event, sound_data_queue)
            else:
                print("Did not record properly")
                continue

            # Waiting for inference to complete
            while model_event.is_set():
                sleep(0.01)

            # Clearing events
            start_event.clear()

    except KeyboardInterrupt:
        logger.info("Keyboard Interrupt from parent")
        print("\n\033[92m\033[4mparent.py\033[0m \033[92mprocess ended\033[0m")

    except Exception as e:
        logger.error(f"Exception on parent: {traceback.format_exc()}")
        print("\n\033[91m\033[4mparent.py\033[0m \033[91mprocess ended\033[0m")

    finally:
        # Audio
        stream_input.stop_stream()
        stream_input.close()
        audio.terminate()
        # Logging
        logger.info("Program End")
