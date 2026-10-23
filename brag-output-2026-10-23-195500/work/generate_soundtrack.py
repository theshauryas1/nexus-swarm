import math
import numpy as np
import scipy.io.wavfile as wavfile
import os

def create_soundtrack(output_path="soundtrack.wav", duration=20.0, sample_rate=48000):
    num_samples = int(duration * sample_rate)
    t = np.linspace(0, duration, num_samples, endpoint=False)
    left = np.zeros(num_samples, dtype=np.float32)
    right = np.zeros(num_samples, dtype=np.float32)

    bpm = 110.0
    beat_dur = 60.0 / bpm  # ~0.545s
    num_beats = int(duration / beat_dur)

    # 1. Sub-bass pulse (C2, Eb2, G2, Bb1)
    bass_freqs = [65.41, 77.78, 98.0, 58.27]
    for b in range(num_beats):
        beat_start = b * beat_dur
        beat_idx = int(beat_start * sample_rate)
        sub_len = int(beat_dur * 0.8 * sample_rate)
        if beat_idx + sub_len > num_samples:
            sub_len = num_samples - beat_idx
        
        freq = bass_freqs[(b // 4) % len(bass_freqs)]
        bt = np.linspace(0, sub_len / sample_rate, sub_len, endpoint=False)
        envelope = np.exp(-bt * 3.5)
        bass_wave = np.sin(2 * np.pi * freq * bt) * 0.28 * envelope
        
        left[beat_idx:beat_idx + sub_len] += bass_wave
        right[beat_idx:beat_idx + sub_len] += bass_wave

    # 2. Ambient minor chords pad (C minor: C3, Eb3, G3, Bb3)
    c_minor = [130.81, 155.56, 196.00, 233.08]
    eb_maj = [155.56, 196.00, 233.08, 293.66]
    ab_maj = [103.83, 130.81, 164.81, 207.65]
    bb_dom = [116.54, 146.83, 174.61, 233.08]
    chords = [c_minor, eb_maj, ab_maj, bb_dom]

    for bar in range(int(duration / (beat_dur * 4)) + 1):
        bar_start = bar * beat_dur * 4
        bar_idx = int(bar_start * sample_rate)
        bar_len = int(beat_dur * 4 * sample_rate)
        if bar_idx >= num_samples:
            break
        if bar_idx + bar_len > num_samples:
            bar_len = num_samples - bar_idx
            
        cur_chord = chords[bar % len(chords)]
        ct = np.linspace(0, bar_len / sample_rate, bar_len, endpoint=False)
        # Warm attack and release envelope
        env = np.sin(np.pi * ct / (bar_len / sample_rate)) ** 1.5 * 0.12
        
        for i, f in enumerate(cur_chord):
            detune_l = np.sin(2 * np.pi * (f - 0.4) * ct)
            detune_r = np.sin(2 * np.pi * (f + 0.4) * ct)
            left[bar_idx:bar_idx + bar_len] += detune_l * env * (0.8 + 0.2 * (i % 2))
            right[bar_idx:bar_idx + bar_len] += detune_r * env * (0.8 + 0.2 * ((i + 1) % 2))

    # 3. Micro hi-hats / interface tick groove on 8th notes
    for h in range(num_beats * 2):
        h_start = h * (beat_dur / 2.0)
        h_idx = int(h_start * sample_rate)
        h_len = int(0.025 * sample_rate)
        if h_idx + h_len > num_samples:
            break
        ht = np.linspace(0, 0.025, h_len, endpoint=False)
        noise = (np.random.rand(h_len) * 2 - 1) * np.exp(-ht * 120.0) * 0.035
        left[h_idx:h_idx + h_len] += noise * 0.8
        right[h_idx:h_idx + h_len] += noise * 1.0

    # 4. Integrated Sound Effects in Key:
    # A. 0.6s: Terminal key click
    def add_click(timestamp, gain=0.08):
        idx = int(timestamp * sample_rate)
        dur = int(0.015 * sample_rate)
        if idx + dur < num_samples:
            ct = np.linspace(0, 0.015, dur, endpoint=False)
            click = np.sin(2 * np.pi * 1800 * ct) * np.exp(-ct * 250) * gain
            left[idx:idx + dur] += click
            right[idx:idx + dur] += click

    # B. 4.5s: Swarm Division Fan-out Clicks (staggered)
    for i in range(6):
        add_click(4.6 + i * 0.08, gain=0.06)

    # C. 9.5s: Latency drop frequency glide (450Hz down to 65Hz sub drop)
    drop_idx = int(9.6 * sample_rate)
    drop_len = int(0.6 * sample_rate)
    if drop_idx + drop_len < num_samples:
        dt = np.linspace(0, 0.6, drop_len, endpoint=False)
        freq_curve = 400.0 * np.exp(-dt * 6.0) + 65.41
        phase = 2 * np.pi * np.cumsum(freq_curve) / sample_rate
        drop_wave = np.sin(phase) * np.exp(-dt * 3.5) * 0.22
        left[drop_idx:drop_idx + drop_len] += drop_wave
        right[drop_idx:drop_idx + drop_len] += drop_wave

    # D. 11.2s: AST Block alert tone (Eb chord dissonant sting)
    alert_idx = int(11.2 * sample_rate)
    alert_len = int(0.4 * sample_rate)
    if alert_idx + alert_len < num_samples:
        at = np.linspace(0, 0.4, alert_len, endpoint=False)
        a_wave = (np.sin(2 * np.pi * 311.13 * at) + np.sin(2 * np.pi * 466.16 * at)) * np.exp(-at * 7.0) * 0.12
        left[alert_idx:alert_idx + alert_len] += a_wave
        right[alert_idx:alert_idx + alert_len] += a_wave

    # E. 15.5s: QA Test Passing Chime (Pure C5 crystal sine, 523.25 Hz)
    chime_idx = int(15.5 * sample_rate)
    chime_len = int(1.8 * sample_rate)
    if chime_idx + chime_len < num_samples:
        cmt = np.linspace(0, 1.8, chime_len, endpoint=False)
        chime_wave = (np.sin(2 * np.pi * 523.25 * cmt) + 0.3 * np.sin(2 * np.pi * 1046.5 * cmt)) * np.exp(-cmt * 2.2) * 0.16
        left[chime_idx:chime_idx + chime_len] += chime_wave * 0.9
        right[chime_idx:chime_idx + chime_len] += chime_wave * 1.1

    # 5. Master fade-out over final 1.5 seconds
    fade_len = int(1.5 * sample_rate)
    fade_curve = np.linspace(1.0, 0.0, fade_len)
    left[-fade_len:] *= fade_curve
    right[-fade_len:] *= fade_curve

    # Peak normalization
    peak = max(np.max(np.abs(left)), np.max(np.abs(right)))
    if peak > 0:
        left = (left / peak) * 0.88
        right = (right / peak) * 0.88

    stereo = np.vstack((left, right)).T
    stereo_int16 = (stereo * 32767).astype(np.int16)

    wavfile.write(output_path, sample_rate, stereo_int16)
    print(f"Generated soundtrack: {output_path} ({duration}s, {sample_rate}Hz stereo)")

if __name__ == "__main__":
    out_dir = r"d:\hack\brag-output-2026-10-23-195500\work"
    wav_path = os.path.join(out_dir, "soundtrack.wav")
    create_soundtrack(wav_path, duration=20.0)
