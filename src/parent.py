from platform import system
from time import time
from os.path import join
import logging

# Differentiate between windows and linux
if system() == 'Windows':
    from src.key_listener_win import Listener
else:
    from src.key_listener import Listener

# from src.record import start_audio
from src.model_inference import service
from wave import open

from multiprocessing import Process, Event, Pipe

from pyaudio import PyAudio, paInt16

# Global variables
# -------------------------

# Configure the logging settings
logging.basicConfig(
    level=logging.DEBUG,  # Set the desired logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    format='%(asctime)s - %(levelname)s - %(message)s',  # Define the log message format
    filename='example.log',  # Specify the log file name
    filemode='w'  # 'w' for write, 'a' for append
)
# Create a logger instance
logger = logging.getLogger(__name__)

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

# Get sound data
file_low = open(join('effects', 'button-low.wav'), 'rb')
file_high = open(join('effects', 'button-high.wav'), 'rb')
sound_low = file_low.readframes(file_low.getnframes())
sound_high = file_high.readframes(file_high.getnframes())
file_low.close()
file_high.close()
# -------------------------

def start_audio(start_event):
    # This line to wake device from sleep state
    stream_output.write(sound_high)

    # stream_input.start_stream()
    logger.debug(f"stream is stopped: {stream_input.is_stopped()}")
    logger.debug(f"Get read: {stream_input.get_read_available()}")
    logger.debug(f"Is active: {stream_input.is_active()}")

    if not stream_input.is_active():
        print("Stream is not active")
        return
    

    frames = []

    print("Started audio recording")

    try:
        while start_event.is_set():
            print("Capture")
            data = stream_input.read(1024)
            frames.append(data)

        stream_output.write(sound_low)
        print("Capture FINISHED")
    
    except KeyboardInterrupt:
        print("Keyboard interrupt")
        return
    except Exception:
        print(f"\nCAPTURE UNSUCCESFUL!")
        return
    
    # Sound file creation
    sound_file = open("recording.wav", "wb")
    sound_file.setnchannels(1)
    sound_file.setsampwidth(audio.get_sample_size(paInt16))
    sound_file.setframerate(44100)
    sound_file.writeframes(b"".join(frames))
    sound_file.close()
    print("Saved audio")

def run_listener(child_pipe, start_event):
    a = Listener(child_pipe, start_event)
    a.run()


def main():
    # Input device
    print(f"This is the input device used: {audio.get_default_input_device_info()['name']}")
    # Creating pipes just in case
    parent_pipe, child_pipe = Pipe(duplex=False)

    # Events for synchronization
    start_event = Event()
    model_event = Event()

    # Creating processe for model as it takes the longest to load
    model_process = Process(target=service, args=(child_pipe, model_event), name='WhisperModel')
    model_process.start()

    # Waiting for model to load
    print(f"Waiting for model to load")
    model_event.wait()
    model_event.clear()
    print(f"Model loaded!\n\n")

    # Creating process for Key listener
    userinput_process = Process(target=run_listener, args=(child_pipe, start_event), name='SA-KeyListener')
    userinput_process.start()

    try:
        while 1:
            try:
                # Waiting for Start event
                print("Waiting for hotkey")
                start_event.wait()

                # Previously had seperate process running, however 3 concurrent runnnig is enough
                # recording_process = Process(target=start_audio, args=(stop_event, audio, stream))
                # recording_process.start()

                # Starting to Record
                print("Recording")
                if start_event.is_set():
                    start_audio(start_event)
                else:
                    print("Did not record properly")

                # Inference
                print("Starting inference")
                model_event.set()
                while model_event.is_set():
                    pass

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