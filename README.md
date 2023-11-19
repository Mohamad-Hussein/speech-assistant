# speech-assistant
[![contributions welcome](https://img.shields.io/badge/contributions-welcome-brightgreen.svg?style=flat)](https://github.com/dwyl/esta/issues)

Welcome to Speech-Assistant! 

This is a project to implement a working desktop application on both Linux and Windows that provides a real-time, offline speech-to-text dictation program. It uses the distil-whisper models from HuggingFace, based on this [repo](https://github.com/huggingface/distil-whisper). The speech-to-text assistant writes down spoken words directly to the keyboard cursor. To use it is easy, hold down a hotkey combination of Windows key (Super) and Shift to begin, and let go to end the recording. Your speech will be transcribed in real time and the transcription is going to be typed in for you at the keyboard cursor. I made this program to enhance efficiency  and add quality of life to the experience of PC users. Additionally, there isn't a reliable speech-to-text model used for transcription on Linux, however, do check out [nerd-dictation](https://github.com/ideasman42/nerd-dictation) for the implementation of speech-to-text for the vosk models.

Here is a [demo](https://youtu.be/p9-QpG0p9yQ) of speech-assistant.

# Getting Started
## Linux/Windows
### Anaconda
To get started you can get started on any operating system you would like. The program was tested in Pop-Os (Ubuntu22.04), Windows 10 and 11. Here is Anaconda's installation [instructions](https://docs.anaconda.com/free/anaconda/install/). If you are on Windows make sure to have access to the conda command using the Anaconda **cmd** terminal, or to source it directly (time-consuming).

1. Create a running environment from env.yml, this will take ~5-15 minutes depending on your internet connection
```
conda env create -f env.yml
conda activate speech-assistant
```
2. Start running the program. The program will download the distil-whisper/distil-medium.en model by default and cache it locally in a folder named 'model'.  It is ~800 MB and you can choose the bigger models if you would like, however, the smaller model is very accurate and the best choice. The different choices are in this [configuration](#configurations). You can change this in [model_inference.py](https://github.com/Mohamad-Hussein/speech-assistant/blob/main/src/model_inference.py).
```
python main.py
```
3. Hold the default hotkey Super + Shift to start recording your microphone
4. Release hotkey to stop the recording
5. And voila! The model will output the transcription on your text cursor!
## Notes and Considerations
- Make sure to locate your primary sound input device!
- There is a problem with using powershell, use cmd and activate conda env.
- Installing with requirement.txt, package ffmpeg will be missing on model inference. This module can be downloaded with anaconda with -c pytorch.
- Users with dedicated graphics cards will have a better experience running the big models.
- For transcribing on windows you can use its built in dictation service with left windows + h. The whisper models can be useful for formatting expressive punctuation.
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


## Issues to solve
- Current pressed values saves capital letters (somewhat fixed, current pressed down var cleared once pressing hotkey)(key_listener.py)
- Fix this warning:
```
/home/mohamadhussein/anaconda3/envs/pytorch/lib/python3.11/site-packages/transformers/pipelines/base.py:1101: UserWarning: You seem to be using the pipelines sequentially on GPU. In order to maximize efficiency please use a dataset
  warnings.warn()
```

## Needed features
- Add optimizations suggested by HuggingFace
- Add capability for AMD GPUs
- Add option to use whatever keybind of user's choosing
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
