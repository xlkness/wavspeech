import torch
import torchaudio
torch.set_num_threads(1)
SAMPLING_RATE = 16000
USE_ONNX = False

torchaudio.set_audio_backend("soundfile")
torch.hub.download_url_to_file('https://models.silero.ai/vad_models/en.wav', 'en_example.wav')

model, utils = torch.hub.load(repo_or_dir='snakers4/silero-vad',
model='silero_vad',
force_reload=True,
onnx=USE_ONNX)

(get_speech_timestamps,
 save_audio,
 read_audio,
 VADIterator,
 collect_chunks) = utils

wav = read_audio('en_example.wav')
speech_timestamps = get_speech_timestamps(wav, model, sampling_rate=SAMPLING_RATE, min_speech_duration_ms=100, visualize_probs=False)

print(speech_timestamps)