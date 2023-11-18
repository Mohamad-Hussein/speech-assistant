from keyboard import unhook_all, wait, is_pressed


class Listener:
    def __init__(self, pipe, start_event):
        self.pipe = pipe
        self.start_event = start_event
        self.hotkey_held = False

        # -- Hotkey --
        self.hotkey = "left windows + shift"
        # ------------

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
        print(f"Hotkey assigned: {self.hotkey}")
        # add_hotkey(' + '.join(self.hotkey), self.down)
        # on_release_key(self.hotkey, self.up)

        try:
            while 1:
                wait(self.hotkey)
                self.down()
                # Wait until it is not pressed anymore
                while is_pressed(self.hotkey):
                    pass
                self.up()

        finally:
            print("Ending hotkey listener")
            unhook_all()


if __name__ == "__main__":
    """This is for testing purposes"""
    from multiprocessing import Event, Pipe

    event = Event()
    pipe = Pipe()
    obj = Listener(pipe=Pipe, start_event=event)
    obj.run()
