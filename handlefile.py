import sys,os
parentdir = os.path.dirname(os.path.abspath(__file__))#跨目录调用
sys.path.append(parentdir)

import collections, queue
import numpy as np
import pyaudio
import webrtcvad
from halo import Halo
import torch
import torchaudio
from IPython.display import Audio

# torch.set_num_threads(1)

import vad.silerovad_utils as silerovad_utils
import vad.silerovad as silerovad
import vad.webrtcvad_utils as webrtcvad_utils
import time
from wavvad import  skip_record 
from global_val import log
import copy

try:
    # torch.set_num_threads(1)
    torchaudio.set_audio_backend("soundfile")
    # model, utils = torch.hub.load(repo_or_dir='snakers4/silero-vad',
    #                                             model='silero_vad',
    #                                             force_reload=True,
    #                                             onnx=False)
    # model, utils = torch.hub.load(repo_or_dir='snakers4/silero-vad',model='silero_vad', onnx=USE_ONNX)
except Exception as LoadErr:
    print('加载数据集报错：', LoadErr)
    os._exit(1)



def vad_webrtc(path): 
    vad_frame_dura = 20 # vad算法检测一次的帧持续时长
    vad_mode = 0 # vad模式，数字越大越严格，最大3

    vad = webrtcvad.Vad()
    vad.set_mode(vad_mode)
    audio, raw_frames, sample_rate = webrtcvad_utils.read_wave(path)
    if sample_rate not in [8000, 16000]:
        return None, int(float(len(raw_frames)) / float(audio.getsampwidth())), sample_rate , int(audio.getsampwidth()), raw_frames, '采样率目前只支持8000/16000'

    cut_frames = webrtcvad_utils.frame_generator(vad_frame_dura, raw_frames, sample_rate, audio.getsampwidth())
    cut_frames = list(cut_frames)
    segments = webrtcvad_utils.vad_collector1(sample_rate, audio.getsampwidth(), vad_frame_dura, 300, vad, cut_frames)
    # segments = webrtcvad_utils.vad_collector(sample_rate, vad_frame_dura, 300, vad, cut_frames)
    total_dura = float(len(raw_frames))/float(audio.getsampwidth()) / (float(sample_rate)/1000)

    speech_points = []
    # for i, l in enumerate(segments):
    #     for seg in l:
    #         start_point = seg.offset / 2
    #         end_point = start_point+seg.section_len/2
    #         start_ms = int(float(start_point)/float(len(raw_frames)) * total_dura)
    #         end_ms = int(float(end_point)/float(len(raw_frames)) * total_dura)
    #         print("[{}ms-{}ms] {}:{}".format(start_ms, end_ms, start_point/2, end_point/2))
    #         speech_points.append((int(start_point/audio.getsampwidth()), int(end_point/audio.getsampwidth())))
    
    for seg in segments:
        (start_point, end_point) = seg
        # (start_point, end_point) = seg
        # log.debug("wrv seg:", start_point/2, end_point/2)
        start_ms = int(float(start_point)/float(len(raw_frames)) * total_dura)
        end_ms = int(float(end_point)/float(len(raw_frames)) * total_dura)
        # print("[{}ms-{}ms] {}:{}".format(start_ms, end_ms, start_point/2, end_point/2))
        speech_points.append((int(start_point/audio.getsampwidth()), int(end_point/audio.getsampwidth())))
    
    return speech_points, int(float(len(raw_frames)) / float(audio.getsampwidth())), sample_rate , int(audio.getsampwidth()), raw_frames, ''


def vad_silero(path):
    USE_ONNX = False

    # get speech timestamps from full audio file
    model, utils = torch.hub.load(repo_or_dir='vad',model='silero_vad',source='local', onnx=False)
    # model1 = copy.deepcopy(model)
    model1 = model
    (get_speech_timestamps, save_audio, read_audio, VADIterator, collect_chunks) = utils

    wav, raw_frames, sample_rate = read_audio(path)

    speech_timestamps = get_speech_timestamps(raw_frames, model1, sampling_rate=sample_rate, min_speech_duration_ms=100) #, min_speech_duration_ms=100, window_size_samples=int(1024/(16000/sample_rate)))

    speech_points = []
    for seg in speech_timestamps:
        # log.debug("speech seg:", seg['start'], seg['end'])
        speech_points.append((seg['start'], seg['end']))
    
    return speech_points

# 标记人声段
def handle_file_extract_speech(path):
    # 走webrtc算法提取出有效声音 [(point1, point2), (point3, point4)]
    speech_sections1, sample_points, sample_rate, sample_width, raw_frames, err_msg = vad_webrtc(path)

    logRecord = handleLogRecord(path, raw_frames, sample_points, sample_rate, sample_width)
    logRecord.addProcessVad(processWebrtcVadLogRecord(speech_sections1))
    
    start_point = 0
    end_point = 0
    start_ts = 0
    end_ts = 0
    return_tuple = (raw_frames, sample_points, sample_rate, sample_width, start_point, end_point, start_ts, end_ts)

    if err_msg != '':
        return logRecord, err_msg

    # 走silero机器学习计算有效人声段 [(point1, point2)]
    speech_sections2 = vad_silero(path)

    if len(speech_sections2) <= 0:
        err_msg = '机器学习算法没有提取到有效人声'
        return logRecord, err_msg

    if len(speech_sections1) <= 0:
        err_msg = '机器学习算法提取到有效人声，但是webrtc vad算法没有检测到有效声音端点'
        return logRecord, err_msg

    # 查找到silero的开始点如果处于webrtcvad的某个有效声音段，则认为webrtcvad提取的这整个段都是人声
    # 因为silero提取有效声段在临界点有一点缺失，重新用webrtcvad提取的段覆盖初始或者结束
    start_point = speech_sections2[0][0]
    end_point = speech_sections2[-1][1]
    
    origin_start_point = start_point
    origin_end_point = end_point

    i = 0
    while i < len(speech_sections1):
        (webrtc_seg_start, webrtc_seg_end) = speech_sections1[i]
        if start_point > webrtc_seg_start and start_point < webrtc_seg_end:
            # 修正机器学习算法找到的人声区间，与webrtcvad保持一致，机器学习找前段会乱分割
            start_point = webrtc_seg_start
            break
        i += 1
    i = 0
    while i < len(speech_sections1):
        (webrtc_seg_start, webrtc_seg_end) = speech_sections1[i]
        if end_point > webrtc_seg_start and end_point < webrtc_seg_end:
            # start_point = webrtc_seg_start
            # 修正webrtcvad算法找到的人声区间，与机器学习保持一致，webrtcvad算法找到的后段比较长
            tmp_speech_sections1 = []
            j = 0
            while j < len(speech_sections1):
                if i == j:
                    tmp_speech_sections1.append((speech_sections1[j][0], end_point))
                    tmp_speech_sections1.append((end_point+1, webrtc_seg_end))
                else:
                    tmp_speech_sections1.append(speech_sections1[j])
                j += 1
            speech_sections1 = tmp_speech_sections1
            # end_point = webrtc_seg_end
            break
        i += 1

    processExtractSpeech = processSilerovadSpeechLogRecord(speech_sections2, origin_start_point, origin_end_point, start_point, end_point)
    logRecord.addExtractSpeech(processExtractSpeech)

    dura_ms = float(sample_points)/float(sample_rate/1000)

    start_ts = int(float(start_point)/float(sample_points) * dura_ms)
    end_ts = int(float(end_point)/float(sample_points) * dura_ms)

    # print("silero speech:", start_point, end_point)

    return_tuple = (raw_frames, sample_points, sample_rate, sample_width, start_point, end_point, start_ts, end_ts)
    # print("speech dura:{}ms - {}ms".format(start_ts, end_ts))

    return logRecord, ''

# 标记噪声段
def handle_file_extract_noise_point(start_point, end_point, speech_sections1):
    noise_sections = [] # 人声段之外的噪音
    for seg in speech_sections1:
        (tmp_start, tmp_end) = seg
        if tmp_end < start_point :
            # 当前段处于人声段之前，标记噪音
            noise_sections.append(seg)
        if tmp_start > end_point:
            # 当前段处于人声段之后，标记噪音
            noise_sections.append(seg)
    return noise_sections

# 去掉噪点
def handle_file_denoise(raw_frames, sample_points, sample_rate, sample_width, start_point, end_point, noise_sections):
    new_frames = []
    record_noise_points = 0 # 记录噪音段删除的点数量，用于新语音计算长度
    record_pre_noise_points = 0 # 记录噪音前段删除的点数量，用于人声段在新语音中的位置

    # 删除噪音段
    i = 0
    cut_end_point = 0
    while i < len(noise_sections):
        (noise_sp, noise_ep) = noise_sections[i]
        new_frames.extend(raw_frames[cut_end_point*sample_width:noise_sp*sample_width])
        cut_end_point = noise_ep
        record_noise_points += noise_ep - noise_sp
        if noise_ep < start_point:
            record_pre_noise_points += noise_ep - noise_sp
        i += 1
    new_frames.extend(raw_frames[cut_end_point*sample_width:])
 
    new_total_sample_points = sample_points - record_noise_points
    new_start_point = start_point - record_pre_noise_points # 删除了多少个噪音点就往左偏移多少个
    new_end_point = end_point - record_pre_noise_points

    return new_frames, new_start_point, new_end_point

# 处理前、后段填充静音段
def handle_file_full_common_mute(sample_rate, sample_width, mute_points, prefer_select_template_frames1, prefer_select_template_frames2):
    full_seconds = 2
    total_need_full_points = sample_rate*full_seconds
    
    need_full_frames = []
    if mute_points < total_need_full_points:
        # 需要补足
        template_frames = []
        if len(prefer_select_template_frames1) > 0:
            template_frames = prefer_select_template_frames1
        elif len(prefer_select_template_frames2) > 0:
            template_frames = prefer_select_template_frames2
        else:
            err_msg = '人声段前后都找不到静音段补充'
            return None, 0, err_msg
        
        need_points_count = total_need_full_points - mute_points

        while need_points_count > 0:
            template_length = int(len(template_frames)/sample_width)
            if need_points_count <= template_length:
                need_full_frames.extend(template_frames[:need_points_count*sample_width].copy())
                need_points_count = 0
            else:
                need_full_frames.extend(template_frames[:template_length*sample_width].copy())
                need_points_count -= template_length
    
    return need_full_frames, int(len(need_full_frames)/sample_width), ''

# 人声段前后填充xx秒的静音段
def handle_file_full_mute(raw_frames, sample_points, sample_rate, sample_width, start_point, end_point):
    need_full_pre_frames, full_points, err_msg = \
        handle_file_full_common_mute(sample_rate, sample_width, start_point, raw_frames[:start_point*sample_width], raw_frames[end_point*sample_width:])
    if err_msg != '':
        return None, 0, 0, err_msg
    

    need_full_post_frames, _, err_msg = \
        handle_file_full_common_mute(sample_rate, sample_width, sample_points - end_point, raw_frames[end_point*sample_width:], raw_frames[:start_point*sample_width])
    if err_msg != '':
        return None, 0, 0, err_msg

    need_full_pre_frames.extend(raw_frames)
    raw_frames = need_full_pre_frames
    raw_frames.extend(need_full_post_frames)

    return raw_frames, start_point+full_points, end_point+full_points, ''

# 处理人声段前后多余的静音段，保留xx毫秒
def handle_file_cut_more_mute(raw_frames, sample_points, sample_rate, sample_width, start_point, end_point):
    keep_mute_ms = 650
    keep_mute_points = sample_rate/1000.0*keep_mute_ms
    raw_frames = raw_frames[int((start_point-keep_mute_points)*sample_width):]
    end_point = end_point - (start_point-keep_mute_points)
    start_point = keep_mute_points
    sample_points = int(len(raw_frames)/sample_width)
    raw_frames = raw_frames[:int(end_point+keep_mute_points)*sample_width]

    return raw_frames, start_point, end_point

class processWebrtcVadLogRecord:
    voicedlist = []
    def __init__(self, voicedlist):
        self.voicedlist = voicedlist

class processSilerovadSpeechLogRecord:
    speechlist = []
    origin_start_point = 0
    origin_end_point = 0
    correct_start_point = 0
    correct_end_point = 0
    def __init__(self, speechlist, origin_start_point, origin_end_point, correct_start_point, correct_end_point):
        self.speechlist = speechlist
        self.origin_start_point = origin_start_point
        self.origin_end_point = origin_end_point
        self.correct_start_point = correct_start_point
        self.correct_end_point = correct_end_point

class handleLogRecord:
    def __init__(self, name, raw_frames, sample_points, sample_rate, sample_width):
        self.name = name
        self.raw_frames = raw_frames
        self.sample_points = sample_points
        self.sample_rate = sample_rate
        self.sample_width = sample_width
    def addProcessVad(self, processVad):
        self.processVad = processVad
    def addExtractSpeech(self, processExtractSpeech):
        self.processExtractSpeech = processExtractSpeech

# 开始处理一个文件
def handle_file(no, count, path, srcpath, outpath):
    (filename, ext) = os.path.splitext(os.path.basename(path))

    start_time = time.time()
    
    # 计算有效人声段
    logRecord, err_msg = handle_file_extract_speech(path)
    raw_frames, sample_points, sample_rate, sample_width = logRecord.raw_frames, logRecord.sample_points, logRecord.sample_rate, logRecord.sample_width
    if err_msg != '':
        msg = "[{}] 采样点：{}，帧率：{}，位宽：{}，遇到错误跳过：{}".format(path, sample_points, sample_rate, sample_width, err_msg)
        print(msg)
        skip_record.write(path + '：' + msg + '\n')
        return msg

    start_point, end_point = logRecord.processExtractSpeech.correct_start_point, logRecord.processExtractSpeech.correct_end_point
    # (start_point, end_point, start_ts, end_ts), active_voicd_sections, err_msg = handle_file_extract_speech(path)
    if err_msg != '':
        msg = "[{}] 采样点：{}，帧率：{}，位宽：{}，遇到错误跳过：{}".format(path, sample_points, sample_rate, sample_width, err_msg)
        print(msg)
        skip_record.write(path + '：' + msg + '\n')
        return msg

    # webrtcvad_utils.write_wave(outpath+"/"+filename+"-speech-0"+ext, bytes(raw_frames[start_point*sample_width:end_point*sample_width]), sample_rate, sample_width)

    # 计算人声段之外的噪音段
    noise_sections = handle_file_extract_noise_point(start_point, end_point, logRecord.processVad.voicedlist)

    # 去掉噪音段
    new_raw_frames, new_start_point, new_end_point = handle_file_denoise(raw_frames, sample_points, sample_rate, sample_width, start_point, end_point, noise_sections)

    # webrtcvad_utils.write_wave(outpath+"/"+filename+"-denoise-1"+ext, bytes(new_raw_frames), sample_rate, sample_width)

    # print("原始采样点数：", sample_points)
    # print("去掉噪音后采样点数：", len(new_raw_frames)/sample_width)
    # print("新人声起点：", new_start_point)
    # print("新人声终点：", new_end_point)

    # 人声段之外填充静音段
    new_raw_frames, new_start_point, new_end_point, err_msg = \
        handle_file_full_mute(new_raw_frames, int(len(new_raw_frames)/sample_width), sample_rate, sample_width, new_start_point, new_end_point)
    if err_msg != '':
        msg = "[{}] 采样点：{}，帧率：{}，位宽：{}，遇到错误跳过：{}".format(path, sample_points, sample_rate, sample_width, err_msg)
        print(msg)
        skip_record.write(path + '：' + msg + '\n')
        return msg

    # webrtcvad_utils.write_wave(outpath+"/"+filename+"-denoise-2"+ext, bytes(new_raw_frames), sample_rate, sample_width)
    # print("填充后采样点数：", len(new_raw_frames)/sample_width)

    new_raw_frames, new_start_point, new_end_point = \
        handle_file_cut_more_mute(new_raw_frames, int(len(new_raw_frames)/sample_width), sample_rate, sample_width, new_start_point, new_end_point)

    # print("保留0.6秒人声段：", new_start_point, new_end_point)
    # print("保留0.6秒静音后采样点数：", len(new_raw_frames)/sample_width)
   
    # frame_duration_ms = 30
    # n = int(sample_rate * (frame_duration_ms / 1000.0) * sample_width)
    # offset = 0
    # duration = (float(n) / sample_rate) / float(sample_width)

    # outFileName = filename+ext
    relative_path_name = os.path.relpath(path, srcpath)
    fullOutPath = os.path.join(outpath, relative_path_name)
    # print("原始文件：", path)
    # print("源目录：", srcpath)
    # print("输出目录：", outpath)
    # print("相对路径：", relative_path_name)
    # print("输出文件：", fullOutPath)
    try:
        os.makedirs(os.path.dirname(fullOutPath))
    except OSError:
        pass
    webrtcvad_utils.write_wave(fullOutPath, bytes(new_raw_frames), sample_rate, sample_width)

    noiseSegs = ''
    for noiseSeg in logRecord.processVad.voicedlist:
        noiseSegs += '{}-{},'.format(noiseSeg[0], noiseSeg[1])

    # log.debug('[{}] 噪声检测段：{}'.format(logRecord.name, noiseSegs))
    # log.debug('[{}] 人声段：{}-{}，修正人声段：{}-{}'.format(logRecord.name, \
    #     logRecord.processExtractSpeech.origin_start_point, logRecord.processExtractSpeech.origin_end_point, \
    #     logRecord.processExtractSpeech.correct_start_point, logRecord.processExtractSpeech.correct_end_point))
    log().info('[%d/%d][%s] 采样点：%d，帧率：%d*%d，噪声检测段：%s，人声段：%d-%d，修正人声段：%d-%d，输出到：%s', \
        no, count, logRecord.name, logRecord.sample_points, logRecord.sample_rate, logRecord.sample_width, \
        noiseSegs, logRecord.processExtractSpeech.origin_start_point, logRecord.processExtractSpeech.origin_end_point, \
        logRecord.processExtractSpeech.correct_start_point, logRecord.processExtractSpeech.correct_end_point, fullOutPath)
    # while offset + n < len(new_raw_frames):
    #     frame = bytes(new_raw_frames[offset:offset + n])
    #     # print("offset:", offset, offset+n)
    #     offset += n

#     print("[{}] 采样点：{}，帧率：{}，位宽：{}，有效人声段：[{}ms,{}ms]， \
# 抠除噪音段：{}个，抠除噪音点：{}个，总噪音时长：{}ms，前段补充点：{}个，后段补充点：{}个，新音频采样点：{}, 新音频时长：{}ms，耗时：{:.2f}秒". \
#       format(path, sample_points, sample_rate, sample_width, start_ts, end_ts, \
#         len(noise_sections), record_noise_points, noise_dura, need_pre_full_points, need_post_full_points, \
#             new_sample_points, new_dura, end_time - start_time))

    return ''

 