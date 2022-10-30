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

rootPath = os.path.dirname(os.path.realpath(sys.argv[0]))

def versiontuple(v):
    return tuple(map(int, (v.split('+')[0].split("."))))


def silero_vad(onnx=False, force_onnx_cpu=False):
    if not onnx:
        installed_version = torch.__version__
        supported_version = '1.12.0'
        if versiontuple(installed_version) < versiontuple(supported_version):
            raise Exception(f'Please install torch {supported_version} or greater ({installed_version} installed)')

    # hub_dir = torch.hub.get_dir()
    if onnx:
        model = OnnxWrapper(f'{hub_dir}/snakers4_silero-vad_master/files/silero_vad.onnx', force_onnx_cpu)
    else:
        jitPath = os.path.join(os.path.join(rootPath, 'vad'), 'silero_vad.jit')
        model = init_jit_model(model_path=jitPath)
        # model = init_jit_model(model_path=f'{hub_dir}/snakers4_silero-vad_master/files/silero_vad.jit')
        # model = init_jit_model(model_path=f'{hub_dir}/snakers4_silero-vad_master/files/silero_vad.jit')
    utils = (get_speech_timestamps,
             save_audio,
             read_audio,
             VADIterator,
             collect_chunks)

    return model, utils


def silero_number_detector(onnx=False, force_onnx_cpu=False):
    """Silero Number Detector
    Returns a model with a set of utils
    Please see https://github.com/snakers4/silero-vad for usage examples
    """
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
    """Silero Language Classifier
    Returns a model with a set of utils
    Please see https://github.com/snakers4/silero-vad for usage examples
    """
    if onnx:
        url = 'https://models.silero.ai/vad_models/number_detector.onnx'
    else:
        url = 'https://models.silero.ai/vad_models/number_detector.jit'
    model = Validator(url, force_onnx_cpu)
    utils = (get_language,
             read_audio)

    return model, utils


def silero_lang_detector_95(onnx=False, force_onnx_cpu=False):
    """Silero Language Classifier (95 languages)
    Returns a model with a set of utils
    Please see https://github.com/snakers4/silero-vad for usage examples
    """

    hub_dir = torch.hub.get_dir()
    if onnx:
        url = 'https://models.silero.ai/vad_models/lang_classifier_95.onnx'
    else:
        url = 'https://models.silero.ai/vad_models/lang_classifier_95.jit'
    model = Validator(url, force_onnx_cpu)

    with open(f'{hub_dir}/snakers4_silero-vad_master/files/lang_dict_95.json', 'r') as f:
        lang_dict = json.load(f)

    with open(f'{hub_dir}/snakers4_silero-vad_master/files/lang_group_dict_95.json', 'r') as f:
        lang_group_dict = json.load(f)

    utils = (get_language_and_group, read_audio)

    return model, lang_dict, lang_group_dict, utils