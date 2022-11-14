from pyannote.audio import Pipeline
import os, sys
import rich
import torchaudio

torchaudio.set_audio_backend("soundfile")
pipeline = Pipeline.from_pretrained("pyannote/speaker-diarization", use_auth_token="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")

def vad_annota(path, samples, rate):
    diarization = pipeline(path)

    dura = samples/(rate/1000)

    start_point = samples+1
    end_point = 0
    for turn, _, speaker in diarization.itertracks(yield_label=True):
        cur_start_ts = turn.start
        cur_end_ts = turn.end
        # print('speech {}-{} / {}'.format(cur_start_ts, cur_end_ts, dura))
        cur_start_point = int(samples * (cur_start_ts*1000/dura))
        cur_end_point = int(samples * (cur_end_ts*1000/dura))
        if start_point > cur_start_point:
            start_point = cur_start_point
        if end_point < cur_end_point:
            end_point = cur_end_point
        # print(f"start={turn.start:.1f}s stop={turn.end:.1f}s speaker_{speaker}")
    return [(start_point, end_point)]