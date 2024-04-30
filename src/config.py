from datetime import datetime
import os
import json

from src.utils.funcs import type_writing


# Global variables
# -----------------------------------

## Default values
# Choosing which way to write text.
WRITE = type_writing

# Deciding whether to save audio file or not.
SAVE_AUDIO = False

# Hotkey for the listener.
# HOTKEY = {"Super", "Shift"}
HOTKEY = {"Alt", "F9"}
AGENT_TRIGGER = "assistant"

# Available models for ASR
SPEECH_MODELS = [
    "openai/whisper-tiny.en",  # ~400 MiB of GPU memory
    "distil-whisper/distil-small.en",  # ~500-700 MiB of GPU memory
    "distil-whisper/distil-medium.en",  # ~900-1500 MiB of GPU memory
    "distil-whisper/distil-large-v2",  # ~1700-2000 MiB of GPU memory
    "openai/whisper-large-v2",  # ~4000 MiB of GPU memory
    "openai/whisper-large-v3",  # ~4000 MiB of GPU memory
    # "optimum/whisper-tiny.en",  # ~400 MiB of GPU memory
]

# Available tasks for ASR
TASKS = ["transcribe", "translate"]

DEFAULT_MODEL_ID = 1
DEFAULT_TRANSLATE_SPEECH = False

# Words to ignore when you haven't said anything
IGNORE = ["you know.", "you're not."]

# Minimum number of words to be considered a valid transcription
MIN_WORDS = 2
# -----------------------------------


def get_from_config(key: str, filename="config.json"):
    """
    Gets the model index from the config file.

    Returns:
        model_id_idx (int): The index of the model in the config file
    """

    # Looks for config file
    if os.path.exists(filename):
        # If the file exists, load its contents
        with open(filename, "r") as file:
            data = json.load(file)
        # Extract the value from the loaded data
        value = data.get(key, DEFAULT_MODEL_ID)

        return value

    # If the file doesn't exist, set the value to the default value
    model_id_idx = DEFAULT_MODEL_ID
    translate_speech = DEFAULT_TRANSLATE_SPEECH

    # Save the value to the JSON file
    data = {
        "Default Model Index": model_id_idx,
        "Date Created": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "Translate Speech": translate_speech,
    }

    with open(filename, "w") as file:
        json.dump(data, file, indent=4)

    return data[key]


def save_to_config(model_id_idx: int, translate_speech: bool, filename="config.json"):
    """
    Saves the model index to the config file.

    Args:
        model_id_idx (int): The index of the model in the config file
    """

    # Looks for config file
    if os.path.exists(filename):
        # If the file exists, load its contents
        with open(filename, "r") as file:
            data = json.load(file)
    else:
        # If the file doesn't exist, create a new dictionary
        data = {}

    # Update the dictionary with the new value
    data["Default Model Index"] = model_id_idx
    data["Translate Speech"] = translate_speech
    data["Date Modified"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Save the dictionary to the JSON file
    with open(filename, "w") as file:
        json.dump(data, file, indent=4)


def update_config(key: str, value, filename="config.json"):
    """
    Updates a key in the config file

    Args:
        key (str): The key to be updated
        value : The new value for the key
        filename (str, optional): The name of the config file
            Defaults to "config.json".

    """
    # Read the existing config
    with open(filename, "r") as file:
        config = json.load(file)

    # Update the value for the specified key
    config[key] = value
    config["Date Modified"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Write the updated config back to the file
    with open(filename, "w") as file:
        json.dump(config, file, indent=4)


# Choosing default model
model_id_idx = get_from_config("Default Model Index")
MODEL_ID = SPEECH_MODELS[model_id_idx]

# Tasks available
translate_speech = get_from_config("Translate Speech")
TASK = TASKS[translate_speech]
