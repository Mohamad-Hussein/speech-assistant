import asyncio
import os
import requests
from typing import Optional

from src.utils.funcs import copy_writing
from src.config import IGNORE, MIN_WORDS, AGENT_TRIGGER

LLM_WEBUI_OPENED: bool = False
SESSION_IDS: list[str] = []


def perform_request(text: str, write_method):
    """Performs the request of the user based on action

    Args:
        text (str): The input text for the request
        start_event (Event): The event that triggered the request
        prev_text (str): The previous text in the conversation, if applicable. Defaults to None.
        write_method (Callable): A function to call with the output text, if necessary. Defaults to None.

    Returns:
        str: The processed text
    """

    # Agent trigger
    if AGENT_TRIGGER in text.lower() or 1 == 1 and len(text) > 0:

        webui_user_input(text, "SESSION_IDS[-1]")
        invoke_agent(text, "SESSION_IDS[-1]")

        # asyncio.run(prompt_agent(processed))

    else:
        # If the text is not English, then copy it
        if notAscii(text):
            write_method = copy_writing

        write_method(text)

    return text


def invoke_agent(user_prompt: str, id: Optional[str] = "0000"):
    """Invokes the agent and updates the webui with the new agent status."""

    json_data = {
        "message": user_prompt,
    }
    response = requests.post(f"http://localhost:8000/message/{id}", json=json_data)


def webui_user_input(user_input: str, id: Optional[str] = "0000"):
    """Updates the webui with the new user input."""
    
    json_data = {
        "message": user_input,
    }

    response = requests.post(f"http://localhost:8000/user/{id}", json=json_data)


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
    processed = text

    # if text.strip().lower() in "you're not.":

    if start_event.is_set():
        index = text.find(prev_text)

        # Remove the common sequence (if found) and any leading/trailing whitespace
        if index != -1:
            processed = text[index + len(prev_text) :].strip()
        else:
            processed = text.strip()

    # Decide if its a valid transcription
    if any(
        True for ignore_str in IGNORE if ignore_str.startswith(processed)
    ) or MIN_WORDS > len(processed.strip().split(" ")):
        return ""

    else:
        return processed


def notAscii(s):
    return not s.isascii()
