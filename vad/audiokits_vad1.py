from pyAudioKits.analyse.timeDomainAnalyse import energyCal, overzeroCal
import numpy as np
import matplotlib.pyplot as plt
import pyAudioKits.audio as ak
import pyAudioKits.algorithm as alg
from . import webrtcvad_utils
import aifc

class VADNoZeroCrossing:

    def __init__(self,input,energyThresLow,frameDuration = 0.03,overlapRate=0.5):
        """Speech endpoint detection based on double threshold. 
        input: An Audio object. 
        energyThresLow: A lower threshold of energy for distinguish between silence and voice.
        frameDuration: A float object for the duration of each frame (seconds) or a int object for the length of each fram (sample points). 
        overlapRate: A float object in [0,1) for the overlapping rate of the frame.
        return: A VAD object.  
        """
        input = input.framing(frameDuration, overlapRate)
        flatten=input.samples
        energys=energyCal(flatten)

        voice_begins, voice_ends = self.__distinguish(0, len(energys), energys, energyThresLow)

        labels = np.zeros_like(energys)
        for i in range(len(voice_begins)):
            labels[voice_begins[i]:voice_ends[i]] = 1

        self.label=labels
        self.input=input
    
    def __distinguish(self, b, e, energys, energyThres):
        clip1=energyThres
        voice_begins = []
        voice_ends = []
        if energys[b] >= clip1:
            voice_begins.append(b)
        for i in range(b+1,e):
            if (energys[i] >= clip1) and (energys[i-1] < clip1):
                voice_begins.append(i)
            elif (energys[i] <= clip1) and (energys[i-1] > clip1):
                voice_ends.append(i)
        if len(voice_begins) - 1 == len(voice_ends):
            voice_ends.append(e)
        assert len(voice_begins) == len(voice_ends)

        return voice_begins, voice_ends


def vad(path):
    audio = ak.read_Audio(direction = path)
    # vad_result = alg.VAD(audio, 0.0005, 0.5, 300, frameDuration=0.03, overlapRate=0.7)    #对录音进行端点检测，设置较低的短时能量阈值为0.05、较高的短时能量阈值为0.5、短时过零率阈值为400
    vad_result = VADNoZeroCrossing(audio, 0.002, frameDuration=0.03, overlapRate=0.7)    #对录音进行端点检测，设置较低的短时能量阈值为0.05、较高的短时能量阈值为0.5、短时过零率阈值为400
    # vad_result.plot()
    label=vad_result.label
    audio=vad_result.input.retrieve()
    step=vad_result.input.step

    voiced_frames = []
    triggered = False
    tmp_start = 0
    tmp_end = 0
    for i in range(0,len(label)):
        is_speech = (label[i]!=0)
        # start*step/audio.sr:(i+1)*step/audio.sr
        if is_speech != triggered or i == 0:
            if triggered and not is_speech:
                tmp_end = i - 1
                voiced_frames.append((tmp_start * step, tmp_end * step))
            elif not triggered and is_speech:
                tmp_start = i
            triggered = is_speech

    # print(voiced_frames)

    audio1, raw_frames, sample_rate = webrtcvad_utils.read_wave(path)

    return voiced_frames, int(float(len(raw_frames)) / float(audio1.getsampwidth())), sample_rate , int(audio1.getsampwidth()), raw_frames, ''