#!/usr/bin/env python2

# Captures all keyboard and mouse events, including modifiers
# Adapted from http://stackoverflow.com/questions/22367358/
# Adapted from users CasualDemon and o9000 on stackoverflow
# Requires python-xlib
import logging
from os.path import join

from Xlib.display import Display
from Xlib import X, XK
from Xlib.ext import record
from Xlib.protocol import rq


class Listener:
    def __init__(self, pipe, start_event, model_event):
        self.disp = None
        self.keys_down = set()
        self.pipe = pipe
        self.start_event = start_event
        self.model_event = model_event
        self.hotkey_held = False

        # -- Hotkey --
        self.hotkey = {"Super", "Shift"}
        # ------------

        # Configure the logging settings
        logging.basicConfig(
            level=logging.DEBUG,
            format="%(asctime)s - %(levelname)s - %(message)s",
            filename=join("logs", "key_listener.log"),
            filemode="w",
        )
        self.logger = logging.getLogger(__name__)
        self.logger.info("Key listener for Linux started")

    def keycode_to_key(self, keycode, state):
        i = 0
        if state & X.ShiftMask:
            i += 1
        if state & X.Mod1Mask:
            i += 2
        return self.disp.keycode_to_keysym(keycode, i)

    def key_to_string(self, key):
        keys = []
        for name in dir(XK):
            if name.startswith("XK_") and getattr(XK, name) == key:
                keys.append(name.lstrip("XK_").replace("_L", "").replace("_R", ""))
        if keys:
            return " or ".join(keys)
        return "[%d]" % key

    def keycode_to_string(self, keycode, state):
        return self.key_to_string(self.keycode_to_key(keycode, state))

    def mouse_to_string(self, code):
        if code == X.Button1:
            return "Button1"
        elif code == X.Button2:
            return "Button2"
        elif code == X.Button3:
            return "Button3"
        elif code == X.Button4:
            return "Button4"
        elif code == X.Button5:
            return "Button5"
        else:
            return "{%d}" % code

    def down(self, key):
        # print(f"Key added: {key}")
        self.keys_down.add(key)
        # self.print_keys()

    def up(self, key):
        if key in self.keys_down:
            self.keys_down.remove(key)
            # self.print_keys()

        # Removing shift key on up
        elif key == "[0]" and "Shift" in self.keys_down:
            self.keys_down.remove("Shift")
            # self.print_keys()

    def print_keys(self):
        keys = list(self.keys_down)
        print("Currently pressed:", ", ".join(keys))

    def event_handler(self, reply):
        data = reply.data
        while data:
            event, data = rq.EventField(None).parse_binary_value(
                data, self.disp.display, None, None
            )

            if event.type == X.KeyPress:
                self.down(self.keycode_to_string(event.detail, event.state))

                ## Hotkey
                if self.hotkey.issubset(self.keys_down) and not self.hotkey_held:
                    self.pipe.send("Start")
                    print(f"\nHOTKEY PRESSED")
                    self.start_event.set()
                    self.hotkey_held = True

            elif event.type == X.KeyRelease:
                self.up(self.keycode_to_string(event.detail, event.state))

                if (
                    self.hotkey.issubset(self.keys_down) == False
                    and self.hotkey_held == True
                ):
                    self.pipe.send("Stop")
                    self.hotkey_held = False
                    self.start_event.clear()
                    # To remove sticky keys to not interfere with hotkey
                    self.keys_down.clear()

            elif event.type == X.ButtonPress:
                self.down(self.mouse_to_string(event.detail))
            elif event.type == X.ButtonRelease:
                self.up(self.mouse_to_string(event.detail))

    def run(self):
        try:
            self.disp = Display()
            XK.load_keysym_group("xf86")
            root = self.disp.screen().root

            print(f"Hotkey assigned: {' + '.join(self.hotkey)}")
            # To signal to parent that it is ready
            self.start_event.set()

            ctx = self.disp.record_create_context(
                0,
                [record.AllClients],
                [
                    {
                        "core_requests": (0, 0),
                        "core_replies": (0, 0),
                        "ext_requests": (0, 0, 0, 0),
                        "ext_replies": (0, 0, 0, 0),
                        "delivered_events": (0, 0),
                        "device_events": (X.KeyReleaseMask, X.ButtonReleaseMask),
                        "errors": (0, 0),
                        "client_started": False,
                        "client_died": False,
                    }
                ],
            )
            self.disp.record_enable_context(
                ctx, lambda reply: self.event_handler(reply)
            )
            self.disp.record_free_context(ctx)
            while True:
                event = root.display.next_event()
        except KeyboardInterrupt:
            self.logger.info("Keyboard Interrupt")
            print(
                "\n\033[92m\033[4mkey_listener.py\033[0m \033[92mprocess ended\033[0m"
            )
        except Exception as e:
            self.logger.error(f"Exception occured: {e}")
            print(
                "\n\033[91m\033[4mkey_listener.py\033[0m \033[91mprocess ended\033[0m"
            )
        finally:
            self.disp.close()
            


if __name__ == "__main__":
    Listener("test pipe", "test event").run()
