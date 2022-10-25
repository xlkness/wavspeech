import collections
import contextlib
import sys
import wave

import webrtcvad


def read_wave(path):
    """Reads a .wav file.

    Takes the path, and returns (PCM audio data, sample rate).
    """
    with contextlib.closing(wave.open(path, 'rb')) as wf:
        num_channels = wf.getnchannels()
        assert num_channels == 1
        sample_width = wf.getsampwidth()
        # assert sample_width == 2
        sample_rate = wf.getframerate()
        # assert sample_rate in (8000, 16000, 32000, 48000)
        pcm_data = wf.readframes(wf.getnframes())
        return wf, pcm_data, sample_rate


def write_wave(path, audio, sample_rate, sample_width):
    """Writes a .wav file.

    Takes path, PCM audio data, and sample rate.
    """
    with contextlib.closing(wave.open(path, 'wb')) as wf:
        wf.setnchannels(1)
        wf.setsampwidth(sample_width)
        wf.setframerate(sample_rate)
        wf.writeframes(audio)


class Frame(object):
    """Represents a "frame" of audio data."""
    def __init__(self, bytes, timestamp, duration, section_len, offset):
        self.bytes = bytes
        self.timestamp = timestamp
        self.duration = duration
        self.section_len = section_len
        self.offset = offset


def frame_generator(frame_duration_ms, audio, sample_rate, sample_width):
    """Generates audio frames from PCM audio data.

    Takes the desired frame duration in milliseconds, the PCM data, and
    the sample rate.

    Yields Frames of the requested duration.
    """
    n = int(sample_rate * (frame_duration_ms / 1000.0) * sample_width)
    offset = 0
    timestamp = 0.0
    duration = (float(n) / sample_rate) / float(sample_width)
    while offset + n < len(audio):
        yield Frame(audio[offset:offset + n], timestamp, duration, n, offset)
        timestamp += duration
        offset += n


def vad_collector(sample_rate, frame_duration_ms,
                  padding_duration_ms, vad, frames):
    num_padding_frames = int(padding_duration_ms / frame_duration_ms)
    # We use a deque for our sliding window/ring buffer.
    ring_buffer = collections.deque(maxlen=num_padding_frames)
    # We have two states: TRIGGERED and NOTTRIGGERED. We start in the
    # NOTTRIGGERED state.
    triggered = False

    voiced_frames = []
    for frame in frames:
        is_speech = vad.is_speech(frame.bytes, sample_rate)

        # sys.stdout.write('1' if is_speech else '0')
        if not triggered:
            ring_buffer.append((frame, is_speech))
            num_voiced = len([f for f, speech in ring_buffer if speech])
            # If we're NOTTRIGGERED and more than 90% of the frames in
            # the ring buffer are voiced frames, then enter the
            # TRIGGERED state.
            if num_voiced > 0.9 * ring_buffer.maxlen:
                triggered = True
                # sys.stdout.write('+(%s)' % (ring_buffer[0][0].timestamp,))
                # We want to yield all the audio we see from now until
                # we are NOTTRIGGERED, but we have to start with the
                # audio that's already in the ring buffer.
                for f, s in ring_buffer:
                    voiced_frames.append(f)
                ring_buffer.clear()
        else:
            # We're in the TRIGGERED state, so collect the audio data
            # and add it to the ring buffer.
            voiced_frames.append(frame)
            ring_buffer.append((frame, is_speech))
            num_unvoiced = len([f for f, speech in ring_buffer if not speech])
            # If more than 90% of the frames in the ring buffer are
            # unvoiced, then enter NOTTRIGGERED and yield whatever
            # audio we've collected.
            if num_unvoiced > 0.9 * ring_buffer.maxlen:
                # sys.stdout.write('-(%s)' % (frame.timestamp + frame.duration))
                triggered = False
                yield [f for f in voiced_frames]
                ring_buffer.clear()
                voiced_frames = []
    if triggered:
        a = 1
        # sys.stdout.write('-(%s)' % (frame.timestamp + frame.duration))
    # sys.stdout.write('\n')
    # If we have any leftover voiced audio when we run out of input,
    # yield it.
    if voiced_frames:
        yield [f for f in voiced_frames]


def vad_collector1(sample_rate, sample_width, frame_duration_ms,
                  padding_duration_ms, vad, frames):
    triggered = False
    voiced_frames = []
    
    i = 0
    offset = 0
    for frame in frames:
        is_speech = vad.is_speech(frame.bytes, sample_rate)
        # print("is speech:", is_speech)
        if triggered != is_speech or i == 0:
            if triggered and not is_speech:
                # print("speech section:", tmp_start, tmp_end)
                tmp_end = offset + len(frame.bytes)
                voiced_frames.append((tmp_start, tmp_end))
            elif not triggered and is_speech:
                tmp_start = offset
            triggered = is_speech
        i += 1
        offset = offset + len(frame.bytes)
    return voiced_frames

def main(args):
    if len(args) != 2:
        sys.stderr.write(
            'Usage: example.py <aggressiveness> <path to wav file>\n')
        sys.exit(1)
    wav, raw_frames, sample_rate = read_wave(args[1])
    vad = webrtcvad.Vad(int(args[0]))
    frames = frame_generator(30, raw_frames, sample_rate, wav.getsampwidth())
    frames = list(frames)
    segments = vad_collector(sample_rate, 30, 300, vad, frames)
    for i, segment in enumerate(segments):
        # path = 'chunk-%002d.wav' % (i,)
        # print(' Writing %s' % (path,))
        print("seg len:", len(segment))
        print("seg:", segment[0])
        # write_wave(path, segment, sample_rate, wav.getsampwidth())


if __name__ == '__main__':
    main(sys.argv[1:])
