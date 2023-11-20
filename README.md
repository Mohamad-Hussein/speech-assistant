# speech-assistant
[![contributions welcome](https://img.shields.io/badge/contributions-welcome-brightgreen.svg?style=flat)](https://github.com/dwyl/esta/issues)  ![GitHub repo size](https://img.shields.io/github/repo-size/:Mohamad-Hussein/:speech-assistant)  [![Anaconda-Server Badge](https://anaconda.org/fastai/fastai/badges/latest_release_date.svg)](https://anaconda.org/fastai/fastai)
![Linux](https://img.shields.io/badge/Linux-F2F2F2) ![Windows](https://img.shields.io/badge/Windows-17b3d2) 


<!-- ![Static Badge](https://img.shields.io/badge/any%20text-you%20like-blue) -->
Welcome to Speech-Assistant! 

This is a project to implement a working desktop application on both Linux and Windows that provides a real-time, offline speech-to-text dictation program. It uses the distil-whisper models from HuggingFace, based on this [repo](https://github.com/huggingface/distil-whisper). The speech-to-text assistant writes down spoken words directly to the keyboard cursor. To use it is easy, hold down a hotkey combination of Windows key (Super) and Shift to begin, and let go to end the recording. Your speech will be transcribed in real time and the transcription is going to be typed in for you at the keyboard cursor. I made this program to enhance efficiency and add quality of life to the experience of PC users. Additionally, there isn't a reliable speech-to-text model used for transcription on Linux, however, do check out [nerd-dictation](https://github.com/ideasman42/nerd-dictation) for the implementation of speech-to-text for the vosk models.

Here is a quick [demo](https://youtu.be/rF8mtyhBZiM) of speech-assistant.

# Getting Started

You can get started on any operating system you would like. The program was tested in Pop-Os (Ubuntu22.04), Windows 10 and 11. Here is Anaconda's installation [instructions](https://docs.anaconda.com/free/anaconda/install/). If you are on Windows make sure to have access to the conda command using the Anaconda **cmd** terminal, or to source it directly (time-consuming). Nvidia and AMD have different packages needed to run Pytorch, please follow accordingly to ensure smooth compatibility.

## Nvidia GPU
1. Create a running environment from env-cuda.yml, this will take ~5-15 minutes depending on your internet connection
```
conda env create -f env-cuda.yml -y
conda activate speech-assistant
```
2. Start running the program. The program will download the distil-whisper/distil-medium.en model by default and cache it locally in a folder named 'model'.  It is ~800 MB and you can choose the bigger models if you would like, however, the smaller model is very accurate and the quickest. The different choices are in this [configuration](#configurations). You can change this in [model_inference.py](https://github.com/Mohamad-Hussein/speech-assistant/blob/main/src/model_inference.py).
```
python main.py
```
3. Hold the default hotkey Super + Shift to start recording your microphone
4. Release the hotkey to stop the recording
5. And voila! The model will output the transcription on your text cursor!

## AMD GPU
Different steps are depending on your operating system.

### Windows
We will be using the [torch-directml](https://learn.microsoft.com/en-us/windows/ai/directml/dml-intro) API from Microsoft instead of CUDA.
1. Create a conda environment from env-amd-win.yml and activate it.
```
conda env create -f env-amd-win.yml -y
conda activate speech-assistant
```
2. Change [line](https://github.com/Mohamad-Hussein/speech-assistant/blob/main/src/funcs.py#L58) from ```elif 0:``` to ```elif 1:```
3. Start program.
```
python main.py
```
### Linux
To use AMD GPUs for PyTorch, we need to download the ROCm platform version of PyTorch.
1. Create a conda environment from env-amd-linux.yml and activate it.
```
conda env create -f env-amd-linux.yml -y
conda activate speech-assistant
```
2. Start the program
```
python main.py
```
# Notes and Considerations
- Make sure to locate your primary sound input device!
- There is a problem with using PowerShell, use cmd, and activate the conda environment.
- Installing with requirement.txt, package ffmpeg will be missing on model inference. This module can be downloaded with anaconda with ```conda install ffmpeg -c pytorch.```
- Users with dedicated graphics cards will have a better experience running the big models.
- For transcribing on Windows you can use its built-in dictation service with left windows + h. However, the whisper models can be useful for formatting expressive punctuation, and the implementation allows for private and quick dictation.
## Configurations

| Model                                                                      | Params / M | Rel. Latency | Short-Form WER | Long-Form WER |
|----------------------------------------------------------------------------|------------|--------------|----------------|---------------|
| [whisper-large-v2](https://huggingface.co/openai/whisper-large-v2)         | 1550       | 1.0          | **9.1**        | 11.7          |
| [distil-large-v2](https://huggingface.co/distil-whisper/distil-large-v2)   | 756        | 5.8          | 10.1           | **11.6**      |
| [distil-medium.en](https://huggingface.co/distil-whisper/distil-medium.en) | **394**    | **6.8**      | 11.1           | 12.4          |

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

# Future contributions
## Issues to solve
- Current pressed values save capital letters (somewhat fixed, current pressed down var cleared once pressing hotkey)(key_listener.py)
- Fix this warning:
```
/home/mohamadhussein/anaconda3/envs/pytorch/lib/python3.11/site-packages/transformers/pipelines/base.py:1101: UserWarning: You seem to be using the pipelines sequentially on GPU. To maximize efficiency please use a dataset
  warnings.warn()
```

## Needed features
- Add optimizations suggested by HuggingFace
- Add capability for AMD GPUs
- Add the option to use whatever key bind of the user's choosing (GUI)
- Add GUI
- Stress tests to make reliable
- Make Dockerfile

# Acknowledgements

Distil-whisper paper:

- **Title:** Distil-Whisper: Robust Knowledge Distillation via Large-Scale Pseudo Labelling
- **Authors:** Sanchit Gandhi, Patrick von Platen, Alexander M. Rush
- **Year:** 2023
- **Link:** [ArXiv](https://arxiv.org/abs/2311.00430)

Sound effect: [soundsforyou](https://pixabay.com/users/soundsforyou-4861230/) on pixabay
