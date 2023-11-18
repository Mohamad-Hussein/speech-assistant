from pyaudio import PyAudio, paInt16
from wave import open
from os.path import join

def get_audio():
    audio = PyAudio()
    stream_input = audio.open(
    format=paInt16,
    channels=1,
    rate=44100,
    input=True,
    frames_per_buffer=1024,
    )

    stream_output = audio.open(
        format=paInt16,
        channels=1,
        rate=44100,
        output=True,
    )
    return audio, stream_input, stream_output

def get_effects(dir_name : str, sound_low_name : str, sound_high_name : str):
    file_low = open(join(dir_name, sound_low_name), 'rb')
    file_high = open(join(dir_name, sound_high_name), 'rb')
    sound_low = file_low.readframes(file_low.getnframes())
    sound_high = file_high.readframes(file_high.getnframes())
    file_low.close()
    file_high.close()
    return sound_low, sound_high

def start_audio(start_event, model_event):
    
    # This line to wake device from sleep state
    logger.info('sound-high played')

    stream_output.write(sound_high)

    # stream_input.start_stream()
    logger.debug(f"stream is stopped: {stream_input.is_stopped()}")
    logger.debug(f"Get read: {stream_input.get_read_available()}")
    logger.debug(f"Is active: {stream_input.is_active()}")

    if not stream_input.is_active():
        print("Stream is not active")
        return
    
    frames = []

    try:
        print("Capture STARTED")
        while start_event.is_set():
            data = stream_input.read(1024)
            frames.append(data)
        print("Capture FINISHED")
        stream_output.write(sound_low)
        logger.info('sound-low played')
    
    except KeyboardInterrupt:
        print("Keyboard interrupt")
        return
    except Exception:
        print(f"\nCAPTURE UNSUCCESFUL!")
        return
    
    # sound_file.
    sound_file = open("tmp.wav", "wb")
    sound_file.setnchannels(1)
    sound_file.setsampwidth(audio.get_sample_size(paInt16))
    sound_file.setframerate(44100)
    sound_file.writeframes(b"".join(frames))
    model_event.set()
    logger.debug(f"{sound_file.tell()}")
    logger.debug(f"Sound file size: {sound_file.getnframes() / sound_file.getframerate():.2f} seconds")
    print("Saved audio")
    sound_file.close()

if __name__ == "__main__":
    """
    To record a recording and test it 
    run this commandin terminal:
    python record.py
    """
    from multiprocessing import Event
    stop_event = Event()
    start_audio(stop_event)