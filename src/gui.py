from time import sleep
from multiprocessing import Event, Queue, Process, Pipe, Value
from tkinter import Tk, Menu, Button, Label, StringVar, DISABLED, NORMAL
from tkinter.ttk import Combobox
from threading import Thread

from src.parent import main_loop
from src.funcs import run_listener, type_writing, copy_writing
from src.model_inference import service, SPEECH_MODELS, MODEL_ID


# Choosing which way to write text.
WRITE = copy_writing


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
        # This is for choosing speech model
        self.model_index_value = Value("i", SPEECH_MODELS.index(MODEL_ID))

        ## GUI ##
        self.option_window_open: bool = False

        # GUI parameters
        self.root = Tk()
        self.root.title("Speech-Assistant")
        self.root.geometry("300x200")
        self.root.resizable(False, False)
        self.is_running = True
        self.max_text_length = 30

        ## Menu
        self.menu = Menu(self.root, bg="white", font=("Consolas", 8))
        self.root.config(menu=self.menu)

        # File menu
        self.file_menu = Menu(self.menu, tearoff=0, bg="white", font=("Consolas", 8))
        self.menu.add_cascade(label="File", menu=self.file_menu)
        self.file_menu.add_command(label="Options", command=self.open_options)
        self.file_menu.add_command(label="Exit", command=self.on_close)

        ## Text box
        self.text_var = Label(self.root, text="Press start to begin speech detection.")
        self.text_var.pack(pady=10)
        ## Start button
        self.start_button = Button(
            self.root, text="Start", command=self.start_detection
        )
        # self.start_button.pack(side='top', padx=5, pady=10)
        self.start_button.place(x=100, y=50, anchor="center")

        ## Stop button
        self.stop_button = Button(
            self.root,
            text="Stop",
            command=self.stop_detection,
            state=DISABLED,
        )
        # self.stop_button.pack(side='top', padx=5, pady=10)
        self.stop_button.place(x=200, y=50, anchor="center")

        ## GUI protocols
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def start_model_service(self):
        """Loads the ASR model and starts the model service."""
        ## Creating process for model as it takes the longest to load
        self.model_process = Process(
            target=service,
            args=(
                self.sound_data_queue,
                self.child_pipe,
                self.model_event,
                self.start_event,
                WRITE,
                self.model_index_value,
            ),
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
            self.start_model_service()
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

        # Removes speech text
        self.text_var.config(text="Press start to begin speech detection.")

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

        # Destroys all GUIs
        if self.option_window_open:
            self.options_window.destroy()
        # Destroys the GUI
        self.root.destroy()

        # Stops the main loop
        self.is_running = False

    def run(self):
        """Runs the GUI"""
        while self.is_running:

            # Updates text
            if self.parent_pipe.poll():
                text = self.parent_pipe.recv()

                # Shortening text if too long
                if len(text) > self.max_text_length:
                    text = text[: self.max_text_length] + "..."

                self.text_var.config(text=text)

            self.root.update()
            sleep(0.1)

    def open_options(self):
        """Opens the options window"""

        if self.option_window_open:
            self.options_window.focus_force()
            return

        self.option_window_open = True

        # Create a new Tkinter window
        self.options_window = Tk()
        self.options_window.title("Settings")
        self.options_window.geometry("300x200")
        self.options_window.resizable(False, False)

        # Add your settings UI elements here
        # For example:
        label = Label(self.options_window, text="Settings will go here")
        label.pack()

        ## Model selection for Speech-to-Text
        speech_model_var = StringVar()
        speech_model_label = Label(
            self.options_window, text="Select Speech-To-Text Model:"
        )
        speech_model_label.pack(pady=(50, 5))
        speech_model_combobox = Combobox(
            self.options_window,
            textvariable=speech_model_var,
            width=40,
            justify="center",
            state="readonly",
        )
        speech_model_combobox["values"] = SPEECH_MODELS
        speech_model_combobox.current(1)
        speech_model_combobox.pack(pady=5)

        def on_model_select(event):
            selected_model = speech_model_combobox.get()
            self.model_index_value.value = SPEECH_MODELS.index(selected_model)

            print(f"\nASR model changed to {selected_model}\n")

        # Bind the on_model_select function to the <<ComboboxSelected>> event
        speech_model_combobox.bind("<<ComboboxSelected>>", on_model_select)

        ## Model selection Combobox
        model_var = StringVar()
        model_label = Label(self.options_window, text="Select Model:")
        model_label.pack(pady=5)
        model_combobox = Combobox(
            self.options_window,
            textvariable=model_var,
            width=40,
            justify="center",
            state="readonly",
        )
        model_combobox["values"] = ["ChatGPT-3.5 API"]  # Add your model names here
        model_combobox.current(0)  # Set default model selection
        model_combobox.pack(pady=5)

        self.options_window.protocol("WM_DELETE_WINDOW", self.close_options)

        # Run the Tkinter event loop for the new window
        self.options_window.mainloop()

    def close_options(self):
        self.option_window_open = False
        self.root.focus_set()
        self.options_window.destroy()
