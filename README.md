# speech-assistant


[![contributions welcome](https://img.shields.io/badge/contributions-welcome-brightgreen.svg?style=flat)](https://github.com/dwyl/esta/issues)
[![License badge](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/license/mit/)               

![Python](https://img.shields.io/badge/Python-3.11-3776AB.svg?style=flat&logo=python&logoColor=white)
[![pytorch](https://img.shields.io/badge/PyTorch-2.1.1-EE4C2C.svg?style=flat&logo=pytorch)](https://pytorch.org)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)


<!-- 
[![Mohamad-Hussein github](https://img.shields.io/badge/GitHub-Mohamad-Hussein.svg?style=flat&logo=github)](https://github.com/Mohamad-Hussein)
![Static Badge](https://img.shields.io/badge/any%20text-you%20like-blue) 
![GitHub repo size](https://img.shields.io/github/repo-size/:Mohamad-Hussein/:speech-assistant)
-->

### Table of Contents
- [Welcome](#Welcome)
- [How to Use](#How-to-Use)
  - [Nvidia GPU](#nvidia-gpu)
  - [AMD GPU](#amd-gpu)
- [Configurations](#Configurations)
- [Notes and Considerations](#notes-and-considerations)
- [Contributions](#future-contributions)
- [Acknowledgements](#acknowledgements)


# Welcome
**Welcome to Speech-Assistant!**

This is a project to implement a working desktop application on both Linux and Windows that provides a real-time, offline speech-to-text dictation program. It uses the distil-whisper models from HuggingFace which offers an accurate transcription of speech that is fully structured, complete with proper punctuation and syntax. Distil-whisper is based on OpenAI's Whisper model that is **6 times faster**, 49% smaller, and performs **within 1% word error rate** on speech it has never seen before. The research is based on this [repo](https://github.com/huggingface/distil-whisper).

The speech-to-text assistant writes down spoken words directly to the keyboard cursor. To use it is easy, hold down a hotkey combination of Windows key (Super) and Shift to begin, and let go to end the recording. Your speech will be transcribed in real time and the transcription is going to be typed in for you at the keyboard cursor. I made this program to enhance efficiency and add quality of life to the experience of PC users. Additionally, there isn't a reliable speech-to-text model used for transcription on Linux, however, do check out [nerd-dictation](https://github.com/ideasman42/nerd-dictation) for the implementation of speech-to-text for the vosk models.



https://github.com/Mohamad-Hussein/speech-assistant/assets/115669425/57975e07-af13-4582-95df-ae8c8e049bfe



Here is a longer [demo](https://youtu.be/rF8mtyhBZiM) of speech-assistant of a previous and slower version of the program.

# How to Use
![Linux](https://img.shields.io/badge/Linux-F2F2F2) ![Windows](https://img.shields.io/badge/Windows-17b3d2)

You can get started on any operating system you would like. The program was tested in Pop-os (Ubuntu 22.04), Windows 10 and 11. Here is Anaconda's installation [instructions](https://docs.anaconda.com/free/anaconda/install/). If you are on Windows make sure to have access to the conda command using the Anaconda **cmd** terminal, or to source it directly. Nvidia and AMD have different packages needed to run Pytorch, please follow accordingly to ensure smooth compatibility.

## Nvidia GPU
1. Navigate to the speech-assistant repo using the terminal (using the Anaconda CMD on windows).
1. Create a running environment from env-cuda.yml, this will take ~5-15 minutes depending on your internet connection. (Type ```y``` and press enter when asked to download packages)
```bash
conda env create -f env-cuda.yml
conda activate speech-assistant
```
3. Start running the program.
```bash
python main.py
```
4. And voila! The program is now ready to use!

## AMD GPU
Different steps are depending on your operating system.

### Windows
We will be using the [torch-directml](https://learn.microsoft.com/en-us/windows/ai/directml/dml-intro) API from Microsoft instead of CUDA.
1. Create a conda environment from env-amd-win.yml and activate it.
```bash
conda env create -f env-amd-win.yml -y
conda activate speech-assistant
```
2. Change [line](https://github.com/Mohamad-Hussein/speech-assistant/blob/main/src/funcs.py#L58) from ```elif 0:``` to ```elif 1:```
3. Start program.
```bash
python main.py
```
### Linux
To use AMD GPUs for PyTorch, we need to download the ROCm platform version of PyTorch.
1. Create a conda environment from env-amd-linux.yml and activate it.
```bash
conda env create -f env-amd-linux.yml -y
conda activate speech-assistant
```
2. Start the program
```bash
python main.py
```
# Configurations
The program will download the ```distil-whisper/distil-small.en``` model by default and cache it locally in a folder named 'model'. The model consumes ~600 MB of GPU memory, and to improve accuracy, you could choose a bigger model. Currently, you could change models [model_inference.py](https://github.com/Mohamad-Hussein/speech-assistant/blob/main/src/model_inference.py) by adjusting the MODEL_ID variable (GUI will be implemented later on). The available model choices are shown below. Please note that the listed models are English only, except for ```whisper-large```, which supports transcription capabilities of multiple languages.
| Model                                                                      | Params / M | Rel. Latency | Short-Form WER | Long-Form WER |
|----------------------------------------------------------------------------|------------|--------------|----------------|---------------|
| [whisper-tiny.en](https://huggingface.co/openai/whisper-tiny.en)         | 39       |          | [~15](https://arxiv.org/abs/2212.04356)        | [~15](https://arxiv.org/abs/2212.04356)          |
| [distil-small.en](https://huggingface.co/distil-whisper/distil-small.en)   | **166**    | 5.6          | 12.1           | 12.8          |
| [distil-medium.en](https://huggingface.co/distil-whisper/distil-medium.en) | 394    | **6.8**      | 11.1           | 12.4          |
| [distil-large-v2](https://huggingface.co/distil-whisper/distil-large-v2)   | 756        | 5.8          | 10.1           | **11.6**      |
| [whisper-large-v2](https://huggingface.co/openai/whisper-large-v2)         | 1550       | 1.0          | **9.1**        | 11.7          |
| [whisper-large-v3](https://huggingface.co/openai/whisper-large-v3)         | 1550       |           |         |           |

# Notes and Considerations
- Users with dedicated graphics cards will have a better experience running the big models.
- Make sure to locate your primary sound input device!
- There is a problem with using PowerShell, use cmd, and activate the conda environment.
- Installing with requirement.txt, package ffmpeg will be missing on model inference. This module can be downloaded with anaconda with ```conda install ffmpeg -c pytorch.```
- For transcribing on Windows you can use its built-in dictation service with left windows + h. However, the whisper models can be useful for formatting expressive punctuation, and the implementation allows for private and quick dictation.

# Future contributions
## Future features
- Add choice of direct connection to ChatGPT API, local LLM, or AutoGPT
- Add sequential inference, for transcription as you talk
  
## Needed features
- Add optimizations suggested by HuggingFace (added BetterTransformer)
- Add the option to use whatever key bind of the user's choosing (GUI)
- Add GUI
- Make Dockerfile for containers
  
## Issues to solve
- Current pressed values save capital letters (somewhat fixed, current pressed down var cleared once pressing hotkey)(key_listener.py)
- Fix this warning:
```
/home/mohamadhussein/anaconda3/envs/pytorch/lib/python3.11/site-packages/transformers/pipelines/base.py:1101: UserWarning: You seem to be using the pipelines sequentially on GPU. To maximize efficiency please use a dataset
  warnings.warn()
```

# Problems faced along the way
## Could not build wheels for PyGOObject
```bash
sudo apt install libgirepository1.0-dev
```
## If PyAudio doesn't work for your Linux installation
```bash
sudo apt-get install python3.11-dev
sudo apt install portaudio19-dev
python3 -m  pip install PyAudio
```
# Acknowledgements

Distil-whisper paper:

- **Title:** Distil-Whisper: Robust Knowledge Distillation via Large-Scale Pseudo Labelling
- **Authors:** Sanchit Gandhi, Patrick von Platen, Alexander M. Rush
- **Year:** 2023
- **Link:** [ArXiv](https://arxiv.org/abs/2311.00430)

Sound effect: [soundsforyou](https://pixabay.com/users/soundsforyou-4861230/) on pixabay
