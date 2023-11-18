from pyaudio import PyAudio, paInt16
from wave import open


def start_audio(stop_event):
    audio = PyAudio()

    stream = audio.open(
        format=paInt16,
        channels=1,
        rate=44100,
        input=True,
        frames_per_buffer=1024,
    )

    frames = []

    print("Started audio recording")
    try:
        while not stop_event.is_set():
            print("Capture")
            data = stream.read(1024)
            frames.append(data)
    except KeyboardInterrupt:
        print("Keyboard interrupt")
        pass

    stream.stop_stream()
    stream.close()
    audio.terminate()

    sound_file = open("recording.wav", "wb")
    sound_file.setnchannels(1)
    sound_file.setsampwidth(audio.get_sample_size(paInt16))
    sound_file.setframerate(44100)
    sound_file.writeframes(b"".join(frames))
    sound_file.close()
    print("Saved audio")

if __name__ == "__main__":
    """
    To record a recording and test it 
    run this commandin terminal:
    python record.py
    """
    from multiprocessing import Event
    stop_event = Event()
    start_audio(stop_event)