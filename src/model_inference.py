from sys import exit
from os.path import join
import gc
from time import sleep, time
import logging
import traceback
import Xlib.threaded

from src.funcs import find_gpu_config, process_text

from transformers.pipelines import pipeline
from transformers import AutoModelForSpeechSeq2Seq, AutoProcessor
import torch

# from optimum.onnxruntime import ORTModelForSpeechSeq2Seq
# from optimum.nvidia.pipelines import pipeline

# MODEL_ID = "openai/whisper-tiny.en"  # ~400 MiB of GPU memory
MODEL_ID = "distil-whisper/distil-small.en"  # ~500-700 MiB of GPU memory
# MODEL_ID = "distil-whisper/distil-medium.en"  # ~900-1500 MiB of GPU memory
# MODEL_ID = "distil-whisper/distil-large-v2"  # ~1700-2000 MiB of GPU memory
# MODEL_ID = "openai/whisper-large-v3"  # ~4000 MiB of GPU memory
# MODEL_ID = "optimum/whisper-tiny.en"  # ~400 MiB of GPU memory


def load_model(queue, model_event, write_method, logger):
    # Checking for GPU
    device, device_name, torch_dtype = find_gpu_config(logger)

    # Setting cache dir
    local_cache_dir = join(".", "model")

    # Creating model
    model = AutoModelForSpeechSeq2Seq.from_pretrained(
        MODEL_ID,
        torch_dtype=torch_dtype,
        low_cpu_mem_usage=True,
        use_safetensors=True,
        cache_dir=local_cache_dir,
    )
    model.to(device)

    # Makes inference faster for transformers
    if "cuda" in device.type or "cpu" in device.type:
        from optimum.bettertransformer import BetterTransformer

        model = BetterTransformer.transform(model)

    # Making pipeline for inference
    processor = AutoProcessor.from_pretrained(MODEL_ID, cache_dir=local_cache_dir)

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
    )

    # Checking if GPU or CPU used
    if device_name:
        print(f"\n\n\033[1m{MODEL_ID}\033[0m loaded to {device_name}\n\n")
    else:
        print(
            f"\n\033[1m{MODEL_ID}\033[0m loaded to physical memory and CPU is used.\n"
            + "WARNING: Unfortunatly these models are not optimal to be computed on CPU!\n\n"
        )
    del device, torch_dtype, local_cache_dir, processor

    # Telling parent that model is loaded
    model_event.set()

    # To make sure event is cleared before model inference
    sleep(1)

    # Make sure event is cleared before then
    model_event.clear()

    while 1:

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
        processed_text = process_text(result["text"])

        # Write text
        write_method(processed_text)

        # Action report
        speech_to_text_time = time() - t0
        print(
            f"\nPrinted text: {result['text']}\nSpeech-to-text time: {speech_to_text_time:.3f}s\n"
        )

        # Resetting
        logger.debug(f"Result: {result}")
        model_event.clear()

    ## Finally
    model_event.clear()

    # Clearing model from memory
    logger.info("Removing model from memory")
    del model_pipe, model

    # FIXME Clear as much memory as possible (not all memory is cleared)
    gc.collect()

    with torch.no_grad():
        torch.cuda.empty_cache()


def service(queue, model_event, write_method):
    """This is to start the model service"""
    # Configure the logging settings
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(levelname)s - %(message)s",
        filename=join("logs", "model.log"),
        filemode="w",
    )
    logger = logging.getLogger(__name__)

    try:
        while True:

            # Load the ASR model
            load_model(queue, model_event, write_method, logger)

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
