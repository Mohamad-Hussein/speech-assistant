from platform import system

# Differentiate between windows and linux
if system() == 'Windows':
    from src.key_listener_win import Listener
else:
    from src.key_listener import Listener

# from src.record import start_audio
from src.model_inference import service
from wave import open

from multiprocessing import Process, Event, Pipe

from pyaudio import PyAudio, paInt16

audio = PyAudio()

stream = audio.open(
    format=paInt16,
    channels=1,
    rate=44100,
    input=True,
    frames_per_buffer=1024,
)

def start_audio(start_event):
    # global audio, stream
    frames = []

    print("Started audio recording")
    try:
        while start_event.is_set():
            print("Capture")
            data = stream.read(1024)
            frames.append(data)
    except KeyboardInterrupt:
        print("Keyboard interrupt")
        pass
    
    # Sound file creation
    sound_file = open("recording.wav", "wb")
    sound_file.setnchannels(1)
    sound_file.setsampwidth(audio.get_sample_size(paInt16))
    sound_file.setframerate(44100)
    sound_file.writeframes(b"".join(frames))
    sound_file.close()
    print("Saved audio")

def run_listener(child_pipe, start_event):
    a = Listener(child_pipe, start_event)
    a.run()


def main():
    # Creating pipes just in case
    parent_pipe, child_pipe = Pipe(duplex=False)

    # Events for synchronization
    start_event = Event()
    stop_event = Event()
    model_event = Event()

    # Creating processes (model first)
    model_process = Process(target=service, args=(child_pipe, model_event))
    model_process.start()

    userinput_process = Process(target=run_listener, args=(child_pipe, start_event))
    userinput_process.start()
    
    try:
        while 1:
            try:
                # Waiting for Start event
                print("Waiting now")
                start_event.wait()

                # Start recording process
                print("Recording")

                # recording_process = Process(target=start_audio, args=(stop_event, audio, stream))
                # recording_process.start()
                start_audio(start_event)
                # Waiting for Stop
                print("Waiting for stop")
                while start_event.is_set():
                    pass
                
                # Stopping recording
                stop_event.set()

                # see a way to stop it

                # Inference
                print("Starting inference")
                model_event.set()
                while model_event.is_set():
                    pass

                # Clearing events
                stop_event.clear()
                start_event.clear()

                print("Finished inference")

            except Exception as e:
                print(e)
                break

    # To ensure that the processes are closed
    finally:
        userinput_process.join()
        stream.stop_stream()
        stream.close()
        audio.terminate()