from multiprocessing import Event, Queue, Process, Pipe
from tkinter import Tk, Button, DISABLED, NORMAL
from threading import Thread

from src.parent import main_loop
from src.funcs import run_listener, type_writing, copy_writing
from src.model_inference import service


# Choosing which way to write text.
WRITE = type_writing


class SpeechDetectionGUI:
    def __init__(self):
        # Concurrency construct
        self.key_listener_thread = None
        self.model_process = None
        self.parent_process = None

        ## Concurrency variables
        # Events for synchronization
        self.start_event = Event()
        self.model_event = Event()
        self.terminate_event = Event()

        # Queue for audio data
        self.sound_data_queue = Queue()

        # Pipes for communication (not used yet)
        self.parent_pipe, self.child_pipe = Pipe()

        ## GUI ##
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

    def load_model(self):
        """Loads the ASR model and starts the model service."""
        ## Creating process for model as it takes the longest to load
        self.model_process = Process(
            target=service,
            args=(self.sound_data_queue, self.model_event, WRITE),
            name="WhisperModel",
        )
        self.model_process.start()

        # Waiting for model to load
        print(f"Waiting for model to load\n\nModel message: ", end="")
        self.model_event.wait()
        self.model_event.clear()

    def init_system(self):
        """
        Initializes the system by creating the necessary
        concurrency constructs and starting the processes.
        """

        # Clearing events
        self.model_event.clear()
        self.start_event.clear()
        self.terminate_event.clear()

        ## Loading model depending on the case
        if not self.model_process:
            self.load_model()
        else:
            self.sound_data_queue.put("Load model")

        ## Creating process for Key listener
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

        ## Creating process for parent
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

    def start_detection(self):
        """Starts the speech detection process"""
        # Button state change
        self.start_button.config(state=DISABLED)

        # Initializing system
        self.init_system()

        # Button state change
        self.stop_button.config(state=NORMAL)

    def stop_detection(self):
        """
        Stops the speech detection process by
        telling the model to unload and terminating
        parent and key listener processes.
        """
        # For model to unload from memory
        self.sound_data_queue.put(None)

        # For parent process to terminate
        self.terminate_event.set()
        self.start_event.set()

        # Making sure processes are joined
        self.parent_process.join()
        self.key_listener_thread.join()

        # Button state change
        self.start_button.config(state=NORMAL)
        self.stop_button.config(state=DISABLED)

    def on_close(self):
        """Terminates all processes before closing"""

        # To tell model process to terminate
        self.sound_data_queue.put("Terminate")

        # For parent process to terminate
        self.terminate_event.set()
        self.start_event.set()

        # Terminate processes and joining threads
        if self.model_process:
            self.model_process.terminate()
            self.model_process.join()
        if self.parent_process:
            self.parent_process.terminate()
            self.parent_process.join()
        if self.key_listener_thread:
            self.key_listener_thread.join()

        # Destroys the GUI
        self.root.destroy()

    def run(self):
        self.root.mainloop()
