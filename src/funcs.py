import io
import wave
import logging
from platform import system
import traceback

from pyaudio import PyAudio, paInt16

logger = logging.getLogger(__name__)


def get_audio():
    """Creates the audio stream for recording audio from the microphone."""

    audio = PyAudio()
    stream_input = audio.open(
        format=paInt16,
        channels=1,
        rate=44100,
        input=True,
        frames_per_buffer=1024,
    )

    return audio, stream_input


def create_sound_file(file_name="tmp.wav"):
    """Creates a sound file for writing"""
    # Copying soundbyte for debugging purposes
    sound_file = wave.open(file_name, "wb")
    sound_file.setnchannels(1)
    sound_file.setsampwidth(2)  # 2 bytes = 16 bits p
    sound_file.setframerate(44100)

    return sound_file


def pcm_to_wav(input_pcm):
    """
    Converts PCM bytes to WAV bytes so that the HuggingFace pipeline receives
    bytes that ffmpeg could interpret.

    Args:
        input_pcm (bytes): PCM bytes from pyaudio

    Returns:
        wav_data (bytes): WAV bytes
    """
    with io.BytesIO() as wav_file:
        wav_writer = wave.open(wav_file, "wb")

        try:
            wav_writer.setframerate(44100)
            wav_writer.setsampwidth(2)
            wav_writer.setnchannels(1)
            wav_writer.writeframes(input_pcm)
            wav_data = wav_file.getvalue()
        except Exception:
            logger.error(f"Exception on pcm_to_wav: {traceback.format_exc()}")
        finally:
            wav_writer.close()

    return wav_data


def run_listener(child_pipe, start_event, model_event):
    """
    Runs the key listener based on the OS.

    Args:
        child_pipe (multiprocessing.Pipe): Pipe for communication with the child process
        start_event (multiprocessing.Event): Event to tell the child process that the model is loaded
        model_event (multiprocessing.Event): Event to tell the child process that the model is loaded

    Returns:
        None
    """
    # Differentiate between windows and linux
    if system() == "Windows":
        from src.key_listener_win import Listener
    else:
        from src.key_listener import Listener

    a = Listener(child_pipe, start_event, model_event)
    a.run()


def find_gpu_config(logger):
    """
    Finds the GPU config and returns the device, device name and torch_dtype
    based on GPU platform and availability.

    Args:
        logger (logging.Logger): Logger instance to log messages onto model.log (for Windows)

    Returns:
        device (str): Device type, either cuda:0, cpu, or ...
        device_name (str): Device name
        torch_dtype (torch.dtype): Data type for torch, float16 for GPU, float32 for CPU

    """
    from torch import cuda
    from torch import float16, float32

    logger.debug("Checking for GPU config")

    # Assume, then check
    device = "cuda:0" if cuda.is_available() else "cpu"
    torch_dtype = float16 if cuda.is_available() else float32
    device_name = ""

    # CUDA
    if cuda.is_available():
        device = "cuda:0"
        device_name = cuda.get_device_name()

        logger.debug("GPU detected from cuda")
        logger.info(f"Device: {device}")
        logger.info(f"Device name: {cuda.get_device_name()}")
        logger.info(f"Device properties: {cuda.get_device_properties(device)}")
        logger.info(f"Device count: {cuda.device_count()}")
        logger.info(f"Device capability: {cuda.get_device_capability()}")
        logger.info(f"Current memory allocated: {cuda.mem_get_info()}")

    # AMD, change 0 to 1 if you have an AMD GPU
    elif 0:
        try:
            import torch_directml as dml
        except ImportError:
            print(
                f"Please install torch_directml to your environment to check if you have AMD GPU,\n"
                + "Use ` pip install torch-directml `."
                "If you don't and want to use CPU, although not recommended, "
                + "comment out this else statement."
            )
            logger.error(f"Package directml not found")
            exit(1)

        if dml.is_available():
            torch_dtype = float16
            device = dml.device()
            device_name = dml.device_name(dml.default_device())

            logger.debug("GPU detected from torch_directml")
            logger.info(f"Available: {dml.is_available()}")
            logger.info(f"Devices Available: {dml.device_count()}")
            logger.info(f"Device: {device}")
            logger.info(f"Default device: {dml.default_device()}")
            logger.info(f"Device name: {dml.device_name(0)}")
            logger.info(f"GPU memory: {dml.gpu_memory()}")

        else:
            torch_dtype = float32

            logger.debug("No GPU detected, using cpu")
            logger.warning(
                "Attention, using the CPU is not recommended! Computation time will be long."
            )

    logger.debug(
        f"GPU config -- device: {device}, device name: {device_name}, torch_dtype: {torch_dtype}"
    )
    return device, device_name, torch_dtype

def process_text(text : str):
    """
    Processes the text to not type dictation
    in which the user has not said anything

    Args:
        text (str): The text to be processed

    Returns:
        text (str): The processed text
    """
    processed = text

    if text.strip().lower() in "you're not.":
        processed = ""

    return processed