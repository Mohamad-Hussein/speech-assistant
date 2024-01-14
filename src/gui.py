from multiprocessing import Event, Queue, Process, Pipe
from tkinter import Tk, Button, DISABLED, NORMAL
from threading import Thread

from src.parent import main_loop
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

        # GUI parameters
        self.root = Tk()
        self.root.title("Speech-Assistant")
        self.root.geometry("300x200")
        self.root.resizable(False, False)

        # Start button
        self.start_button = Button(
            self.root, text="Start Speech Detection", command=self.start_detection
        )
        self.start_button.pack(pady=10)
        # Stop button
        self.stop_button = Button(
            self.root,
            text="Stop Speech Detection",
            command=self.stop_detection,
            state=DISABLED,
        )
        self.stop_button.pack(pady=10)

        # GUI protocols
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

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
            args=(
                self.child_pipe,
                self.start_event,
                self.model_event,
                self.terminate_event,
            ),
            name="SA-KeyListener",
        )
        self.key_listener_thread.start()

        # Waiting for key listener to start
        self.start_event.wait()
        self.start_event.clear()

    def start_detection(self):
        """Starts the speech detection process"""
        # Button state change
        self.start_button.config(state=DISABLED)

        # Initializing system
        self.init_system()

        # Creating process for parent
        self.parent_process = Process(
            target=main_loop,
            args=(
                self.start_event,
                self.model_event,
                self.terminate_event,
                self.sound_data_queue,
            ),
            name="SA-Parent",
        )
        self.parent_process.start()

        # Button state change
        self.stop_button.config(state=NORMAL)

    def stop_detection(self):
        # For model process to terminate
        self.sound_data_queue.put(None)

        # For parent process to terminate
        self.terminate_event.set()
        self.start_event.set()

        self.parent_process.join()
        self.model_process.join()

        # Button state change
        self.start_button.config(state=NORMAL)
        self.stop_button.config(state=DISABLED)

    def on_close(self):
        # Terminates all processes before closing
        if self.stop_button["state"] == NORMAL:
            self.stop_detection()

        # Destroys the GUI
        self.root.destroy()

    def run(self):
        self.root.mainloop()
        self.parent_process.join()
        self.model_process.join()
        self.key_listener_thread.join()
