from torch.cuda import is_available
from torch import float16, float32
from pyautogui import typewrite
from os.path import join
from transformers import AutoModelForSpeechSeq2Seq, AutoProcessor, pipeline

MODEL_ID = "distil-whisper/distil-large-v2"  # ~1700-2000 MiB of GPU memory


def service(pipe, event):
    device = "cuda:0" if is_available() else "cpu"
    torch_dtype = float16 if is_available() else float32
    local_cache_dir = join(".", "model")

    model = AutoModelForSpeechSeq2Seq.from_pretrained(
        MODEL_ID,
        torch_dtype=torch_dtype,
        low_cpu_mem_usage=True,
        use_safetensors=True,
        cache_dir=local_cache_dir,
    )

    model.to(device)

    processor = AutoProcessor.from_pretrained(MODEL_ID, cache_dir=local_cache_dir)

    pipe = pipeline(
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

    # Clearing memory
    del device, torch_dtype, local_cache_dir, processor


    # Waits in standy for inference
    file_path = "recording.wav"
    try:
        while 1:
            event.wait()
            print("Inference event set")
            result = pipe(file_path)
            print(result["text"])
            typewrite(result["text"])
            event.clear()

    finally:
        print("Closing model")
        del model
