import pyaudio
import wave
import threading
import key_input

def save_audio():

    audio = pyaudio.PyAudio()

    stream = audio.open(
        format=pyaudio.paInt16, 
        channels=1, 
        rate=44100,
        input=True,
        frames_per_buffer=1024
    )

    frames = []
    
    try:
        while True:
            data = stream.read(1024)
            frames.append(data)
    except KeyboardInterrupt:
            print("Keyboard interrupt")
            pass

    key_thread.join()

    stream.stop_stream()
    stream.close()
    audio.terminate()

    sound_file = wave.open("recording.wav", "wb")
    sound_file.setnchannels(1)
    sound_file.setsampwidth(audio.get_sample_size(pyaudio.paInt16))
    sound_file.setframerate(44100)
    sound_file.writeframes(b''.join(frames))
    sound_file.close()

if __name__ == "__main__":
     
    key_thread = threading.Thread(key_input)
    audio_thread = threading.Thread(save_audio)

    audio_thread.start()
    key_thread.start()
    
    key_thread.join()
    audio_thread.join()
