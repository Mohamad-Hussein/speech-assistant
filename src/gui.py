from tkinter import *
from multiprocessing import Event, Queue, Process, Pipe
from threading import Thread

from src.parent import main_loop, logger
from src.funcs import run_listener

from src.model_inference import service



class SpeechDetectionGUI:
    def __init__(self):
        # Concurrency construct
        self.key_listener_thread = None
        self.model_process = None
        self.parent_process = None

        # Concurrency variables
        self.start_event = None
        self.model_event = None
        self.terminate_event = None
        self.sound_data_queue = None
        self.parent_pipe = None
        self.child_pipe = None

        self.root = Tk()
        self.root.title("Speech Detection GUI")

        self.start_button = Button(self.root, text="Start Speech Detection", command=self.start_detection)
        self.start_button.pack(pady=10)

        self.stop_button = Button(self.root, text="Stop Speech Detection", command=self.stop_detection, state=DISABLED)
        self.stop_button.pack(pady=10)

    def init_system(self):
        """
        Initializes the system by creating the necessary concurrency constructs
        and starting the processes.
        """

        # Creating pipes for sending audio bytes
        self.parent_pipe, self.child_pipe = Pipe()
        # model_recv_pipe, model_send_pipe = Pipe() # duplex=True is faster than False

        # Events for synchronization
        self.start_event = Event()
        self.model_event = Event()
        self.terminate_event = Event()

        # Slower than Pipe however it could handle more data
        self.sound_data_queue = Queue()

        # Creating process for model as it takes the longest to load
        self.model_process = Process(
            target=service,
            args=(
                self.sound_data_queue,
                self.model_event,
            ),
            name="WhisperModel",
        )
        self.model_process.start()

        # Waiting for model to load
        print(f"Waiting for model to load\n\nModel message: ", end="")
        self.model_event.wait()
        self.model_event.clear()

        # Creating process for Key listener
        self.key_listener_thread = Thread(
            target=run_listener,
            args=(self.child_pipe, self.start_event, self.model_event, self.terminate_event),
            name="SA-KeyListener",
        )
        self.key_listener_thread.start()

        # Waiting for key listener to start
        self.start_event.wait()
        self.start_event.clear()

    def start_detection(self):
        self.start_button.config(state=DISABLED)

        self.init_system()
        self.parent_process = Process(
            target=main_loop,
            args=(
                self.model_process,
                self.key_listener_thread,
                self.start_event,
                self.model_event,
                self.terminate_event,
                self.sound_data_queue,
            ),
            name="SA-Parent",
        )
        self.parent_process.start()

        self.stop_button.config(state=NORMAL)

        
    def stop_detection(self):
        # self.key_listener_thread.
        # For model process to terminate
        self.sound_data_queue.put(None)
        
        # For parent process to terminate
        self.terminate_event.set()
        self.start_event.set()

        self.parent_process.join()
        self.model_process.join()

        self.start_button.config(state=NORMAL)
        self.stop_button.config(state=DISABLED)


    def run(self):
        self.root.mainloop()
        self.parent_process.join()
        self.model_process.join()
        self.key_listener_thread.join()


if __name__ == "__main__":
    start_event = Event()
    model_event = Event()
    sound_data_queue = Queue()

    gui = SpeechDetectionGUI(start_event, model_event, sound_data_queue)

    gui.run()

    print("GUI closed")