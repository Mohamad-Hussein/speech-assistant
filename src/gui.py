import os
from time import sleep
import subprocess
from multiprocessing import Event, Queue, Process, Pipe, Value
from threading import Thread
from tkinter.ttk import Combobox, Button
from tkinter import (
    Tk,
    Frame,
    Menu,
    Label,
    StringVar,
    DISABLED,
    NORMAL,
    LEFT,
    RIGHT,
    BooleanVar,
    Checkbutton,
)
import logging

from src import LOAD_MODEL_SIGNAL, UNLOAD_MODEL_SIGNAL, TERMINATE_SIGNAL
from src.utils.funcs import run_listener
from src.utils.voice_capturing import main_loop
from src.speech.processing import change_agent
from src.speech.asr import audio_processing_service
from src.config import get_from_config, update_config
from src.config import (
    WRITE,
    SAVE_AUDIO,
    HOTKEY,
    TASK,
    TASKS,
    SPEECH_MODELS,
    MODEL_ID,
    AGENT_MODELS,
    DEFAULT_AGENT,
)

# Setting logger
logger = logging.getLogger(__name__)


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
        # Choosing which task to do
        self.task_bool_value = Value("b", TASKS.index(TASK))
        # Choosing if agent should be used or not
        self.agent_bool_value = Value("b", DEFAULT_AGENT != "None")

        # Dictionary for synchronization to pass in process
        self.synch_dict = {
            "Audio Queue": self.sound_data_queue,
            "Model-GUI Pipe": self.child_pipe,
            "Start Event": self.start_event,
            "Model Event": self.model_event,
            "Terminate Event": self.terminate_event,
            "Model Index": self.model_index_value,
            "Task Bool": self.task_bool_value,
            "Agent Bool": self.agent_bool_value,
        }

        ## GUI ##
        self.option_window_open: bool = False

        # GUI parameters
        self.root = Tk()
        self.root.title("Speech-Assistant")
        # Calculate screen width and height
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()

        # Set window size based on screen resolution
        window_width = int(screen_width * 0.15)
        window_height = int(screen_height * 0.15)
        # Center the window
        window_position_x = (screen_width - window_width) // 2
        window_position_y = (screen_height - window_height) // 2

        self.window_size = f"{window_width}x{window_height}"
        self.root.geometry(
            f"{self.window_size}+{window_position_x}+{window_position_y}"
        )

        # self.root.geometry(self.window_size)
        self.root.resizable(True, True)
        self.is_running = True
        self.max_text_length = 35

        ## Menu
        self.menu = Menu(self.root, bg="white", font=("Consolas", 8))
        self.root.config(menu=self.menu)

        # File menu
        self.file_menu = Menu(self.menu, tearoff=0, bg="white", font=("Consolas", 8))
        self.menu.add_cascade(label="File", menu=self.file_menu)
        self.menu.add_command(label="Settings", command=self.open_options)
        self.file_menu.add_command(label="Exit", command=self.on_close)

        ## Text box
        self.text_info = Label(self.root, text="Press start to begin speech detection.")
        self.text_info.pack(pady=10)

        buttons_frame = Frame(self.root)
        buttons_frame.pack()

        ## Start button
        self.start_button = Button(
            buttons_frame, text="Start", command=self.start_detection
        )
        self.start_button.pack(side="left", padx=5, pady=10)

        ## Stop button
        self.stop_button = Button(
            buttons_frame,
            text="Stop",
            command=self.stop_detection,
            state=DISABLED,
        )
        self.stop_button.pack(side="right", padx=5, pady=10)

        ## GUI protocols
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        # Start the web server for the web interface
        webui_path = os.path.join(
            os.path.dirname(__file__), "assistant/assistant_ui.py"
        )
        self.webui_process = subprocess.Popen(
            ["python", webui_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=os.getcwd(),
        )

    def start_model_service(self):
        """Loads the ASR model and starts the model service."""
        ## Creating process for model as it takes the longest to load
        self.model_process = Process(
            target=audio_processing_service,
            args=(
                self.synch_dict,
                WRITE,
            ),
            name="WhisperModel",
        )
        self.model_process.start()

        # Waiting for model to load
        print(f"Waiting for model to load\n\nModel message: ", end="")
        while self.model_event.is_set():
            self.force_update()
            sleep(0.1)
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
            self.sound_data_queue.put(LOAD_MODEL_SIGNAL)

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
        self.child_pipe.send("Starting speech recognition processes...")
        self.force_update()

        # Initializing system
        self.init_system()

        # Button state change when model is loaded
        while self.model_event.is_set():
            self.force_update()
            sleep(0.1)
        self.stop_button.config(state=NORMAL)

    def stop_detection(self):
        """
        Stops the speech detection process by
        telling the model to unload and terminating
        parent and key listener processes.
        """
        # For model to unload from memory
        self.sound_data_queue.put(UNLOAD_MODEL_SIGNAL)

        # For parent process to terminate
        self.terminate_event.set()
        self.start_event.set()

        # Making sure processes are joined
        self.parent_process.join(timeout=10)
        self.key_listener_thread.join(timeout=10)
        # Checking if processes are still running
        if self.parent_process.is_alive() or self.key_listener_thread.is_alive():
            self.text_info.config(text="Processes not ended, please restart program!")
            logger.info("ERROR: Processes not ended")

        # Button state change
        self.start_button.config(state=NORMAL)
        self.stop_button.config(state=DISABLED)

        # Removes speech text
        self.text_info.config(text="Press start to begin speech detection.")

    def on_close(self):
        """Terminates all processes before closing"""

        # To tell model process to terminate
        self.sound_data_queue.put(TERMINATE_SIGNAL)

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
        if self.webui_process:
            self.webui_process.terminate()

        # Destroys all GUIs
        if self.option_window_open:
            self.options_window.destroy()
        # Destroys the GUI
        self.root.destroy()

        # Stops the main loop
        self.is_running = False

        # raise KeyboardInterrupt

    def run(self):
        """Runs the GUI"""
        while self.is_running:
            self.root.update()

            # Updates text
            self.force_update()
            sleep(0.1)

    def force_update(self):
        """Updates GUI when frozen"""
        # Updates text
        if self.parent_pipe.poll():
            text = self.parent_pipe.recv()

            # Handling
            if "ERROR:" in text:
                self.stop_detection()

            # Shortening text if too long
            if len(text) > self.max_text_length:
                text = text[: self.max_text_length] + "..."

            self.text_info.config(text=text)

        self.root.update()

    def open_options(self):
        """Opens the options window"""

        if self.option_window_open:
            self.options_window.focus_force()
            return

        self.option_window_open = True

        # Create a new Tkinter window
        self.options_window = Tk()
        self.options_window.title("Settings")
        self.options_window.geometry(self.window_size)

        # Label for settings
        label = Label(
            self.options_window,
            text="Change the speech model used \nand the assistant model.",
        )
        label.pack()

        ## Model selection for Speech-to-Text
        speech_model_var = StringVar()
        speech_model_label = Label(
            self.options_window, text="Select Speech-To-Text Model:"
        )
        speech_model_label.pack(pady=(20, 5))
        speech_model_combobox = Combobox(
            self.options_window,
            textvariable=speech_model_var,
            width=40,
            justify="center",
            state="readonly",
        )
        speech_model_combobox["values"] = SPEECH_MODELS
        speech_model_combobox.current(self.model_index_value.value)
        speech_model_combobox.pack(pady=5)

        def on_model_select(event):
            selected_model = speech_model_combobox.get()
            self.model_index_value.value = SPEECH_MODELS.index(selected_model)

            update_config("Default Model Index", self.model_index_value.value)
            print(f"\nASR model changed to {selected_model}\n")

        # Bind the on_model_select function to the <<ComboboxSelected>> event
        speech_model_combobox.bind("<<ComboboxSelected>>", on_model_select)

        ## Model selection Combobox
        model_var = StringVar()
        model_label = Label(self.options_window, text="Select Assistant Model:")
        model_label.pack(pady=5)
        model_combobox = Combobox(
            self.options_window,
            textvariable=model_var,
            width=40,
            justify="center",
            state="readonly",
        )
        # Showing info on first option
        user_models = get_from_config("User Models List")
        agent_models_options = AGENT_MODELS.copy() + user_models
        agent_models_options[0] = "None (Transcription only)"

        model_combobox["values"] = agent_models_options
        current_agent = get_from_config("Default Agent Model")

        model_combobox.current(agent_models_options.index(current_agent))
        model_combobox.pack(pady=5)

        def on_agent_select(event):
            selected_agent = model_combobox.get()
            selected_agent = (
                "None"
                if selected_agent == "None (Transcription only)"
                else selected_agent
            )

            # Update if agent should be used
            self.agent_bool_value.value = selected_agent != "None"
            # Update config for web ui
            update_config("Default Agent Model", selected_agent)

            # Change agent
            if selected_agent != "None":
                change_agent(selected_agent)

            print(f"\nAgent model changed to {selected_agent}\n")

        model_combobox.bind("<<ComboboxSelected>>", on_agent_select)

        ## Translate Speech Checkbox
        frame = Frame(self.options_window)
        frame.pack()

        # Create the text label
        text_label = Label(frame, text="Translate to English")
        text_label.pack(side=RIGHT)

        # Create the checkbox for translate speech
        translate_speech = BooleanVar(value=self.task_bool_value.value)
        # check_button = Checkbutton(frame, variable=translate_speech, command=on_checked)

        translate_speech_command = self.update_config_command(
            translate_speech, self.task_bool_value, "Translate Speech"
        )
        translate_speech_button = Checkbutton(
            frame,
            variable=translate_speech,
            command=translate_speech_command,
        )

        (
            translate_speech_button.select()
            if translate_speech.get()
            else translate_speech_button.deselect()
        )
        translate_speech_button.pack(side=LEFT)

        # TODO add a check for using local_files_only

        info_label = Label(self.options_window, text="(applicable to Whisper-Large)")
        info_label.pack()

        self.options_window.protocol("WM_DELETE_WINDOW", self.close_options)

    def close_options(self):
        self.option_window_open = False
        self.root.focus_set()
        self.options_window.destroy()

    def update_config_command(self, bool_var, val_to_change, config_name):
        """Returns a command to update command when checking a box

        Args:
            bool_var (BooleanVar): The boolean variable to check
            val_to_change (multiprocessing.Value): The Value to change
            config_name (str): The name of the config to change
        """
        command = lambda bool_var=bool_var, val_to_change=val_to_change: self.update_config_on_check(
            bool_var, val_to_change, config_name
        )

        return command

    def update_config_on_check(self, bool_var, val_to_change, config_name):
        """Update a boolean variable on check event"""
        bool_var.set(not bool_var.get())

        # Update the task
        val_to_change.value = bool_var.get()

        # Update the config file
        update_config(config_name, bool_var.get())
