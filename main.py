#!/usr/bin/env python3
from os.path import exists, join
from os import makedirs, system
import logging

from src.gui import SpeechDetectionGUI

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
title2 = """
                        Welcome to

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

if __name__ == "__main__":
    # Welcome message
    print(title2)
    del title, title2

    system("")  # Enable ANSI colors
    print(
        "Hold \033[37;42m Hotkey \033[0m for dictation or "
        + "Press \033[37;41m Ctrl + c \033[0m to end the program."
    )
    print("--------------------------------------------------------------------")
    # Creates logs directory if it doesn't exist
    if not exists("logs"):
        makedirs("logs")

    # Configure the logging settings
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(levelname)s - %(message)s",
        filename=join("logs", "speech-assistant.log"),
        filemode="w",
    )
    logger = logging.getLogger(__name__)
    logger.info("Program started")

    try:
        gui = SpeechDetectionGUI()

        gui.run()

        print("GUI closed")
    except KeyboardInterrupt:
        pass
    except Exception as e:
        logger.error(f"Exception hit: {e}")
        pass
    finally:
        print("\n\n\033[30;47m Thank you for using speech-assistant! \033[0m")
        logger.info("Exited main.py")
