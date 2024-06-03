import asyncio
import os
import requests
from typing import Optional, Callable

from src.utils.funcs import copy_writing
from src.config import CHAINLIT_HOST, IGNORE, MIN_WORDS, AGENT_TRIGGER

LLM_WEBUI_OPENED: bool = False
SESSION_IDS: list[str] = []
CONNECTION_TIMEOUT = 10
READER_TIMEOUT = 30


def perform_request(text: str, write_method: Callable, use_agent: bool):
    """Performs the request of the user based on action and if agent is enabled.

    Args:
        text (str): The input text for the request
        write_method (Callable): A function to call to write the transcription

    Returns:
        str: The processed text
    """

    # Agent trigger
    if (use_agent or AGENT_TRIGGER in text.lower()) and len(text) > 0:

        webui_user_input(text, "SESSION_IDS[-1]")
        invoke_agent(text, "SESSION_IDS[-1]")

    else:
        # If the text is not English, then copy it
        if notAscii(text):
            write_method = copy_writing

        write_method(text)

    return text


def process_text(text: str, start_event, prev_text) -> str:
    """
    Processes the text to not type dictation
    in which the user has not said anything

    Args:
        text (str): The text to be processed
        start_event (multiprocessing.Event): Event to tell the child process
            that the model is loaded
        prev_text (str): The previous text

    Returns:
        text (str): The processed text
    """
    processed = text.strip()

    # if text.strip().lower() in "you're not.":

    # NOTE this is for sequential voice transcription
    # if start_event.is_set():
    #     index = text.find(prev_text)

    #     # Remove the common sequence (if found) and any leading/trailing whitespace
    #     if index != -1:
    #         processed = text[index + len(prev_text) :].strip()
    #     else:
    #         processed = text.strip()

    # Decide if its a valid transcription
    if any(
        True for ignore_str in IGNORE if ignore_str.startswith(processed)
    ) or MIN_WORDS > len(processed.strip().split(" ")):
        return ""

    else:
        return processed


def notAscii(s):
    return not s.isascii()


def invoke_agent(user_prompt: str, id: Optional[str] = "0000"):
    """Invokes the agent and updates the webui with the new agent status."""

    json_data = {
        "message": user_prompt,
    }
    print(f"Calling {CHAINLIT_HOST}/message/{id}")
    try:
        response = requests.post(
            f"{CHAINLIT_HOST}/message/{id}",
            json=json_data,
            timeout=(CONNECTION_TIMEOUT, READER_TIMEOUT),
        )
    except requests.exceptions.ReadTimeout as e:
        print("Request timed out: ", e)
    except Exception as e:
        print("Error: ", e)


def webui_user_input(user_input: str, id: Optional[str] = "0000"):
    """Updates the webui with the new user input."""

    json_data = {
        "message": user_input,
    }
    try:
        response = requests.post(
            f"{CHAINLIT_HOST}/user/{id}",
            json=json_data,
            timeout=(CONNECTION_TIMEOUT, READER_TIMEOUT),
        )
    except requests.exceptions.ReadTimeout as e:
        print("Request timed out: ", e)
    except Exception as e:
        print("Error: ", e)


def change_agent(model_name: str, id: Optional[str] = "0000"):
    """Updates the agent and webui name with the new agent model"""

    json_data = {
        "model": model_name,
    }

    response = requests.post(f"{CHAINLIT_HOST}/model/{model_name}/{id}", json=json_data)
