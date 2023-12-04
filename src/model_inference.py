from time import sleep, time
from pyautogui import typewrite
from os.path import join
from transformers import AutoModelForSpeechSeq2Seq, AutoProcessor, pipeline
import logging
from sys import exit

from src.funcs import find_gpu_config

# MODEL_ID = "openai/whisper-tiny"  # ~400 MiB of GPU memory
MODEL_ID = "distil-whisper/distil-medium.en"  # ~900-1500 MiB of GPU memory
# MODEL_ID = "distil-whisper/distil-large-v2"  # ~1700-2000 MiB of GPU memory
# MODEL_ID = "openai/whisper-large-v3"  # ~4000 MiB of GPU memory

def service(pipe, event):
    # Configure the logging settings
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(levelname)s - %(message)s",
        filename=join("logs", "model.log"),
        filemode="w",
    )
    logger = logging.getLogger(__name__)

    
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
        print(f"\nModel loaded to {device_name}\n\n")
    else:
        print(f"\nModel loaded to physical memory and CPU is used.\n"+
              "WARNING: Unfortunatly these models are not optimal to be computed on CPU!\n\n")

    del device, torch_dtype, local_cache_dir, processor

    # Telling parent that model is loaded
    event.set()
    # To make sure event is cleared before model inference
    sleep(1)

    # Waits in standy for inference
    file_path = "tmp.wav"

    # Make sure event is cleared before then
    try:
        while 1:
            event.wait()
            t0 = time()
            result = model_pipe(file_path)
            logger.info(f"Time for inference: {time() - t0:.4f} seconds")
            typewrite(result["text"])
            print(
                f"\nPrinted text: {result['text']}\nSpeech-to-text time: {time() - t0:.3f}s\n"
            )
            logger.debug(f"Result: {result}")
            event.clear()
    except KeyboardInterrupt:
        print("\n\033[92m\033[4mmodel_inference.py\033[0m \033[92mprocess ended\033[0m")
    except Exception as e:
        logger.error(f"Exception hit: {e}")
        print("\n\033[91m\033[4mmodel_inference.py\033[0m \033[91mprocess ended\033[0m")
        exit(1)
    finally:
        pass