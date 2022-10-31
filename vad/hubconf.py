dependencies = ['torch', 'torchaudio']
import torch
import json
from silerovad_utils import (init_jit_model,
                       get_speech_timestamps,
                       get_number_ts,
                       get_language,
                       get_language_and_group,
                       save_audio,
                       read_audio,
                       VADIterator,
                       collect_chunks,
                       drop_chunks,
                       Validator,
                       OnnxWrapper)
import os, sys
from pathlib import Path
import time

rootPath = os.path.dirname(os.path.realpath(sys.argv[0]))

def silero_vad(onnx=False, force_onnx_cpu=False):
    # hub_dir = torch.hub.get_dir()
    if onnx:
        model = OnnxWrapper(f'{rootPath}/vad/silero_vad.onnx', force_onnx_cpu)
    else:
        jitPath = os.path.join(os.path.join(rootPath, 'vad'), 'silero_vad.jit')
        if not Path(jitPath).is_file():
            print("没有找到jit文件，请将silero_vad.jit放置在当前vad目录下")
            os._exit(1)
        # model = init_jit_model(model_path=f'{hub_dir}/snakers4_silero-vad_master/files/silero_vad.jit')
        model = init_jit_model(model_path=jitPath)
    utils = (get_speech_timestamps,
             save_audio,
             read_audio,
             VADIterator,
             collect_chunks)

    return model, utils


def silero_number_detector(onnx=False, force_onnx_cpu=False):
    if onnx:
        url = 'https://models.silero.ai/vad_models/number_detector.onnx'
    else:
        url = 'https://models.silero.ai/vad_models/number_detector.jit'
    model = Validator(url, force_onnx_cpu)
    utils = (get_number_ts,
             save_audio,
             read_audio,
             collect_chunks,
             drop_chunks)

    return model, utils


def silero_lang_detector(onnx=False, force_onnx_cpu=False):
    if onnx:
        url = 'https://models.silero.ai/vad_models/number_detector.onnx'
    else:
        url = 'https://models.silero.ai/vad_models/number_detector.jit'
    model = Validator(url, force_onnx_cpu)
    utils = (get_language,
             read_audio)

    return model, utils


def silero_lang_detector_95(onnx=False, force_onnx_cpu=False):
    hub_dir = torch.hub.get_dir()
    if onnx:
        url = 'https://models.silero.ai/vad_models/lang_classifier_95.onnx'
    else:
        url = 'https://models.silero.ai/vad_models/lang_classifier_95.jit'
    model = Validator(url, force_onnx_cpu)

    with open(f'{hub_dir}/silero_resources/lang_dict_95.json', 'r') as f:
        lang_dict = json.load(f)

    with open(f'{hub_dir}/silero_resources/lang_group_dict_95.json', 'r') as f:
        lang_group_dict = json.load(f)

    utils = (get_language_and_group, read_audio)

    return model, lang_dict, lang_group_dict, utils
