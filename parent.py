from multiprocessing import Process, Event, Pipe
# from tkinter import messagebox

from key_listener import Listener
from record import start_audio
from model_inference import service


def run(child_pipe, start_event):
    a = Listener(child_pipe, start_event)
    a.run()

title = """
       _____                                _          
      / ____|                              | |         
     | (___    _ __     ___    ___    ___  | |__       
      \___ \  | '_ \   / _ \  / _ \  / __| | '_ \      
      ____) | | |_) | |  __/ |  __/ | (__  | | | |     
     |_____/  | .__/   \___| _\___|  \___| |_| |_| _   
     /\       | |       (_) | |                   | |  
    /  \     _|_|  ___   _  | |_    __ _   _ __   | |_ 
   / /\ \   / __| / __| | | | __|  / _` | | '_ \  | __|
  / ____ \  \__ \ \__ \ | | | |_  | (_| | | | | | | |_ 
 /_/    \_\ |___/ |___/ |_|  \__|  \__,_| |_| |_|  \__|
 """
title2 = (
    """

      ░██████╗██████╗░███████╗███████╗░█████╗░██╗░░██╗
      ██╔════╝██╔══██╗██╔════╝██╔════╝██╔══██╗██║░░██║
      ╚█████╗░██████╔╝█████╗░░█████╗░░██║░░╚═╝███████║
      ░╚═══██╗██╔═══╝░██╔══╝░░██╔══╝░░██║░░██╗██╔══██║
      ██████╔╝██║░░░░░███████╗███████╗╚█████╔╝██║░░██║
      ╚═════╝░╚═╝░░░░░╚══════╝╚══════╝░╚════╝░╚═╝░░╚═╝

░█████╗░░██████╗░██████╗██╗████████╗░█████╗░███╗░░██╗████████╗
██╔══██╗██╔════╝██╔════╝██║╚══██╔══╝██╔══██╗████╗░██║╚══██╔══╝
███████║╚█████╗░╚█████╗░██║░░░██║░░░███████║██╔██╗██║░░░██║░░░
██╔══██║░╚═══██╗░╚═══██╗██║░░░██║░░░██╔══██║██║╚████║░░░██║░░░
██║░░██║██████╔╝██████╔╝██║░░░██║░░░██║░░██║██║░╚███║░░░██║░░░
╚═╝░░╚═╝╚═════╝░╚═════╝░╚═╝░░░╚═╝░░░╚═╝░░╚═╝╚═╝░░╚══╝░░░╚═╝░░░
    """
)

print(title2)
del title, title2

if __name__ == "__main__":
    # Creating pipes just in case
    parent_pipe, child_pipe = Pipe(duplex=False)

    # Events for synchronization
    start_event = Event()
    stop_event = Event()
    model_event = Event()

    # Creating processes
    userinput_process = Process(target=run, args=(child_pipe, start_event))
    userinput_process.start()

    model_process = Process(target=service, args=(child_pipe, model_event))
    model_process.start()
    try:
        while 1:
            try:
                # Waiting for Start event
                print("Waiting now")
                start_event.wait()

                # Start recording process
                print("Recording")
                recording_process = Process(
                    target=start_audio, args=(stop_event,)
                )
                recording_process.start()

                # Waiting for Stop
                print("Waiting for stop")
                while start_event.is_set():
                    pass

                # Stopping recording
                stop_event.set()
                recording_process.join()

                # Inference
                print("Starting inference")
                model_event.set()
                while model_event.is_set():
                    pass

                # Clearing events
                stop_event.clear()
                start_event.clear()

                print("Finished inference")

            except Exception as e:
                print(e)
                break

    # To ensure that the processes are closed
    finally:
        userinput_process.join()
