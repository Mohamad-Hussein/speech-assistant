from sys import exit
from os.path import join, basename, realpath
import gc
from time import sleep, time
import logging
import traceback
from typing import Any, Callable, Dict

from src.config import SPEECH_MODELS, TASK, TASKS, MODEL_ID
from src.utils.funcs import find_gpu_config
from src.assistant.processing import perform_request, process_text

from transformers.pipelines import pipeline
from transformers import AutoModelForSpeechSeq2Seq, AutoProcessor
import torch

# from optimum.onnxruntime import ORTModelForSpeechSeq2Seq
# from optimum.nvidia.pipelines import pipeline
timeout = 10


def load_model(gui_pipe, model_event, model_index_value, task_value, logger):
    """Loads the ASR model using HuggingFace's Transformers library.

    Args:
        gui_pipe (Pipe): A Pipe object for communicating with the GUI process.
        model_event (threading.Event): An event to signal when the model is loaded.
        model_id_value (int): The ID of the model to load.
        logger (logging.Logger): A logger to log information about the loading process.

    Returns:
        ModelPipeline: The ASR model as a Transformers pipeline.
    """

    # Checking for GPU
    device, device_name, torch_dtype = find_gpu_config(logger)

    # Setting cache dir
    local_cache_dir = join(".", "model")

    # Getting model id
    model_id = SPEECH_MODELS[model_index_value.value]

    # Downloading the model from HuggingFace Hub
    gui_pipe.send(f"Downloading {basename(model_id)}...")
    logger.info(
        f"Downloading mode {basename(model_id)} into {realpath(local_cache_dir)}"
    )

    model = AutoModelForSpeechSeq2Seq.from_pretrained(
        model_id,
        torch_dtype=torch_dtype,
        low_cpu_mem_usage=True,
        use_safetensors=True,
        cache_dir=local_cache_dir,
        # local_files_only=True,
    )

    # Loading the model to device
    gui_pipe.send(
        f"Loading {basename(model_id)} to {device_name if device_name else 'CPU'}..."
    )
    model.to(device)

    # Making pipeline for inference
    processor = AutoProcessor.from_pretrained(
        model_id,
        cache_dir=local_cache_dir,
        # local_files_only=True
    )

    # Setting task
    generate_kwargs = {"task": TASKS[task_value.value]} if "-large" in model_id else {}
    logger.info(f"Setting task as {task_value.value}")

    model_pipe = pipeline(
        "automatic-speech-recognition",
        model=model,
        tokenizer=processor.tokenizer,
        feature_extractor=processor.feature_extractor,
        max_new_tokens=128,
        chunk_length_s=15,
        batch_size=16,
        torch_dtype=torch_dtype,
        device=device,
        generate_kwargs=generate_kwargs,
    )

    # Checking if GPU or CPU used
    if device_name:
        print(f"\n\n\033[1m{model_id}\033[0m loaded to {device_name}\n\n")
    else:
        print(
            f"\n\033[1m{model_id}\033[0m loaded to physical memory and CPU is used.\n"
            + "WARNING: Unfortunatly these models are not optimal to be computed on CPU!\n\n"
        )
    del device, torch_dtype, local_cache_dir, processor

    # Telling parent that model is loaded
    model_event.set()

    # To make sure event is cleared before model inference
    sleep(1)

    # Make sure event is cleared before then
    model_event.clear()

    return model_pipe


def run_model(synch_dict: Dict[str, Any], write_method: Callable, logger):
    """This is to run the model

    Args:
        synch_dict (dict): Dictionary containing all the synchronization variables
        write_method (str): Method to write the output of model
        logger (logging.Logger): Logger object to write logs

    """
    # Extracting synchronization variables from dictionary
    queue = synch_dict["Audio Queue"]
    gui_pipe = synch_dict["Model-GUI Pipe"]
    start_event = synch_dict["Start Event"]
    model_event = synch_dict["Model Event"]
    terminate_event = synch_dict["Terminate Event"]
    model_id_value = synch_dict["Model Index"]
    task_value = synch_dict["Task Bool"]
    use_agent_value = synch_dict["Agent Bool"]

    # Load the model
    model_pipe = load_model(gui_pipe, model_event, model_id_value, task_value, logger)
    gui_pipe.send("Model loaded. Hold hotkey to start")
    previous_text = ""

    while not terminate_event.is_set():

        # Get audio bytes from queue
        audio_bytes = queue.get(block=True)
        t0 = time()

        ## Synchronization control ##
        # This is for process to remove model from memory
        if audio_bytes is None:
            break
        # This is for process to terminate
        elif audio_bytes == "Terminate":
            raise KeyboardInterrupt

        ## Transcribing ##
        result = model_pipe(audio_bytes)
        logger.info(f"Time for inference: {time() - t0:.4f} seconds")

        # Process text
        processed_text = process_text(
            result["text"],
            start_event,
            previous_text,
        )
        gui_pipe.send(processed_text)

        # Action report
        speech_to_text_time = time() - t0
        print(
            f"\nPrinted text: {result['text']}\nSpeech-to-text time: {speech_to_text_time:.3f}s\n"
        )
        previous_text = result["text"]

        # LLM inference and actions taken
        perform_request(processed_text, write_method, use_agent_value.value)

        # Resetting
        logger.debug(f"Result: {result}")
        model_event.clear()

    ## Finally
    model_event.clear()

    # Clearing model from memory
    logger.info("Removing model from memory")
    del model_pipe

    # FIXME Clear as much memory as possible (not all memory is cleared)
    gc.collect()

    with torch.no_grad():
        torch.cuda.empty_cache()


def audio_processing_service(synch_dict, write_method):
    """This is to start the model service"""
    # Configure the logging settings
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(levelname)s - %(message)s",
        filename=join("logs", "model.log"),
        filemode="w",
    )
    logger = logging.getLogger(__name__)

    # Extracting synchronization variables
    queue = synch_dict["Audio Queue"]

    try:
        while True:

            # Load the ASR model
            run_model(
                synch_dict,
                write_method,
                logger,
            )

            # Signal to load model after stop
            queue.get(block=True)

    except KeyboardInterrupt:
        logger.info("KeyboardInterrupt hit on model_inference")
        print("\n\033[92m\033[4mmodel_inference.py\033[0m \033[92mprocess ended\033[0m")
    except Exception as e:
        logger.error(f"Exception hit: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        print("\n\033[91m\033[4mmodel_inference.py\033[0m \033[91mprocess ended\033[0m")
        exit(1)
    finally:
        pass
