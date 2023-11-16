#!/usr/bin/env python2

# Captures all keyboard and mouse events, including modifiers
# Adapted from http://stackoverflow.com/questions/22367358/
# Requires python-xlib

from Xlib.display import Display
from Xlib import X, XK
from Xlib.ext import record
from Xlib.protocol import rq
from multiprocessing import Pipe


class Listener:
    def __init__(self, pipe: Pipe):
        self.disp = None
        self.keys_down = set()
        self.pipe = pipe

        self.hotkey = {"grave or quoteleft", "Control"}
        self.hotkey_held = False

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
        self.print_keys()

    def up(self, key):
        if key in self.keys_down:
            self.keys_down.remove(key)
            self.print_keys()
        # Removing shift key on up
        elif key == "[0]" and "Shift" in self.keys_down:
            self.keys_down.remove("Shift")
            self.print_keys()

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
                if self.hotkey.issubset(self.keys_down) and not self.hotkey_held:
                    self.pipe.send("Start")
                    self.hotkey_held = True

            elif event.type == X.KeyRelease:
                self.up(self.keycode_to_string(event.detail, event.state))
                if (self.hotkey.issubset(self.keys_down) == False and self.hotkey_held == True):
                    print("Hit\n\n")
                    self.pipe.send("Stop")
                    self.hotkey_held = False

            elif event.type == X.ButtonPress:
                self.down(self.mouse_to_string(event.detail))
            elif event.type == X.ButtonRelease:
                self.up(self.mouse_to_string(event.detail))

    def run(self):
        self.disp = Display()
        XK.load_keysym_group("xf86")
        root = self.disp.screen().root
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
        self.disp.record_enable_context(ctx, lambda reply: self.event_handler(reply))
        self.disp.record_free_context(ctx)
        while True:
            event = root.display.next_event()


if __name__ == "__main__":
    Listener().run()
