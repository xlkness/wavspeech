import pyAudioKits.audio as ak
import pyAudioKits.algorithm as alg

audio = ak.read_Audio(direction = "wav/no1_174.wav")
vad_result = alg.VAD(audio, 0.05, 0.5, 400, frameDuration=0.03, overlapRate=0.7)    #对录音进行端点检测，设置较低的短时能量阈值为0.05、较高的短时能量阈值为0.5、短时过零率阈值为400
# vad_result.plot()
label=vad_result.label
audio=vad_result.input.retrieve()
step=vad_result.input.step

start=0
voiced_frames = []

print('sr:', audio.sr)
print('step:', step)
print('width:', audio)

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
        
print(voiced_frames)