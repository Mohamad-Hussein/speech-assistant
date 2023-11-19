from os.path import join
from keyboard import wait, is_pressed
from time import sleep
import logging


class Listener:
    def __init__(self, pipe, start_event, model_event):
        self.pipe = pipe
        self.start_event = start_event
        self.model_event = model_event
        self.hotkey_held = False

        # -- Hotkey --
        self.hotkey = "left windows + shift"
        # ------------

        # Configure the logging settings
        logging.basicConfig(
            level=logging.DEBUG,
            format="%(asctime)s - %(levelname)s - %(message)s",
            filename=join("logs", "key_listener.log"),
            filemode="w",
        )
        self.logger = logging.getLogger(__name__)
        self.logger.info("Key listener started")

    def down(self):
        print(f"\nHOTKEY PRESSED")
        if not self.hotkey_held and not self.start_event.is_set():
            print(f"{self.hotkey} is held")
            self.start_event.set()
            self.hotkey_held = True

    def up(self, e=None):
        # print(f"Key {e.name}")
        if self.hotkey_held and self.start_event.is_set():
            # print(f"{self.hotkey} is released")
            self.start_event.clear()
            self.hotkey_held = False

    def run(self):
        # This is to start program once listener is set
        print(f"Hotkey assigned: {self.hotkey}")
        self.start_event.set()

        try:
            while 1:
                wait(self.hotkey)
                # So model can finish its inference first before continuing
                if self.model_event.is_set():
                    self.logger.warn("Hotkey pressed while inference is happening")
                    continue

                self.down()
                # Wait until it is not pressed anymore
                while is_pressed(self.hotkey):
                    pass
                self.up()

                # To make sure inference happens first
                sleep(1)
        except KeyboardInterrupt:
            pass
        finally:
            print(
                "\n\033[92m\033[4mkey_listener_win.py\033[0m \033[92mprocess ended\033[0m"
            )


if __name__ == "__main__":
    """This is for testing purposes"""
    from multiprocessing import Event, Pipe

    event = Event()
    pipe = Pipe()
    obj = Listener(pipe=Pipe, start_event=event)
    obj.run()
