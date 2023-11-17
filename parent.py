# from test import MyPollingDelayTimeoutClass
from multiprocessing import Process, Event, Pipe
from tkinter import messagebox

from key_listener import Listener
import record
from model_inference import service


def run(child_pipe, start_event):
    a = Listener(child_pipe, start_event)
    a.run()


print(f"Event and Process created")

if __name__ == "__main__":
    # Parent can recv only and child can send only
    # TODO might not need pipe
    parent_pipe, child_pipe = Pipe(duplex=False)

    start_event = Event()
    stop_event = Event()
    model_event = Event()

    userinput_process = Process(target=run, args=(child_pipe, start_event))
    userinput_process.start()

    model_process = Process(target=service, args=(child_pipe, model_event))
    model_process.start()

    while 1:
        try:
            # Waiting for Start event
            print("Waiting now")
            start_event.wait()

            # Start recording process
            print("Recording")
            recording_process = Process(target=record.start_audio, args=(stop_event,))
            recording_process.start()

            # Waiting for Stop
            print("Waiting for stop")
            while start_event.is_set():
                pass

            # start_event.wait()
            stop_event.set()
            recording_process.join()

            # Inference
            print("Starting inference")
            model_event.set()
            while model_event.is_set():
                pass

            # Clearing events
            stop_event.clear()
            start_event.clear()

            print("Poll done")
            print("Works!!!")
            
        except Exception as e:
            print(e)
            break

    userinput_process.join()
