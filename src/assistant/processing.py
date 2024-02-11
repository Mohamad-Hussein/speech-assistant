
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