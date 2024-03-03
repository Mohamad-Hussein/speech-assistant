from src.utils.funcs import type_writing, copy_writing, get_from_config

# Global variables
# -----------------------------------

# Choosing which way to write text.
WRITE = type_writing

# Deciding whether to save audio file or not.
SAVE_AUDIO = False

# Hotkey for the listener.
HOTKEY = {"Super", "Shift"}

# Task for ASR model (applies only to whisper-large)
TASK: str = "translate"

# Getting the model ID from json file
SPEECH_MODELS = [
    "openai/whisper-tiny.en",  # ~400 MiB of GPU memory
    "distil-whisper/distil-small.en",  # ~500-700 MiB of GPU memory
    "distil-whisper/distil-medium.en",  # ~900-1500 MiB of GPU memory
    "distil-whisper/distil-large-v2",  # ~1700-2000 MiB of GPU memory
    "openai/whisper-large-v2",  # ~4000 MiB of GPU memory
    "openai/whisper-large-v3",  # ~4000 MiB of GPU memory
    # "optimum/whisper-tiny.en",  # ~400 MiB of GPU memory
]

# Choosing default model
model_id_idx = get_from_config()
MODEL_ID = SPEECH_MODELS[model_id_idx]

# Tasks available
TASKS = ["transcribe", "translate"]
TASK = TASKS[0]
# -----------------------------------