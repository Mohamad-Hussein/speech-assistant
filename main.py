from src.parent import main
from os.path import exists, join
from os import makedirs
import logging

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
        main()
    except Exception as e:
        pass
    finally:
        logger.info("Exited main.py")
