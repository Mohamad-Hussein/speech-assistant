from src.utils.funcs import copy_writing


def perform_request(text: str, start_event, prev_text, write_method):
    """Performs the request of the user based on action

    Args:
        text (str): The input text for the request
        start_event (Event): The event that triggered the request
        prev_text (str): The previous text in the conversation, if applicable. Defaults to None.
        write_method (Callable): A function to call with the output text, if necessary. Defaults to None.

    Returns:
        str: The processed text
    """
    text = process_text(text, start_event, prev_text)

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
    processed = text
    if text.strip().lower() in "you're not.":
        return ""

    if start_event.is_set():
        index = text.find(prev_text)

        # Remove the common sequence (if found) and any leading/trailing whitespace
        if index != -1:
            processed = text[index + len(prev_text) :].strip()
        else:
            processed = text.strip()

    return processed


def notAscii(s):
    return not s.isascii()
