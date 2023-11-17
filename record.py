import pyaudio
import wave


def start_audio(stop_event):
    audio = pyaudio.PyAudio()

    stream = audio.open(
        format=pyaudio.paInt16,
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

    sound_file = wave.open("recording.wav", "wb")
    sound_file.setnchannels(1)
    sound_file.setsampwidth(audio.get_sample_size(pyaudio.paInt16))
    sound_file.setframerate(44100)
    sound_file.writeframes(b"".join(frames))
    sound_file.close()
    print("Saved audio")


# if __name__ == "__main__":

#     key_thread = threading.Thread(target=key_input)
#     key_thread.daemon = True
#     audio_thread = threading.Thread(save_audio)

#     audio_thread.start()
#     key_thread.start()

#     key_thread.join()
#     audio_thread.join()
