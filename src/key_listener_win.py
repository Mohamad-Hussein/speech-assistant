from keyboard import add_hotkey, unhook_all, on_press_key, on_release_key
from time import sleep
from multiprocessing import Event

class Listener:
    def __init__(self, pipe, start_event):
        self.pipe = pipe
        self.start_event = start_event
        self.hotkey_held = False

        # -- Hotkey --
        self.hotkey = "win", "shift"
        # ------------    

        add_hotkey('+'.join(self.hotkey), self.down)
        on_release_key(self.hotkey, self.up)
        

    def down(self):
        # print(f"Key {e.name}")
        if not self.hotkey_held and not self.start_event.is_set():
            self.start_event.set()
            self.hotkey_held = True

    def up(self, e):
        print(f"Key {e.name}")
        if self.hotkey_held and self.start_event.is_set():
            self.start_event.clear()
            self.hotkey_held = False

    def run(self):
        
        try:
            while 1:
                print(self.start_event)     
                sleep(1)
        except KeyboardInterrupt:
            print("Ending hotkey listener")
            unhook_all()

if __name__ == '__main__':
    event = Event()
    obj = Listener(pipe="Hi", start_event=event)
    obj.run()