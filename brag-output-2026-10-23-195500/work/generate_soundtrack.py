import math
import numpy as np
import scipy.io.wavfile as wavfile
import os

def create_soundtrack(output_path="soundtrack.wav", duration=52.0, sample_rate=48000):
    num_samples = int(duration * sample_rate)
    left = np.zeros(num_samples, dtype=np.float32)
    right = np.zeros(num_samples, dtype=np.float32)

    bpm = 110.0
    beat_dur = 60.0 / bpm  # ~0.54545s
    num_beats = int(duration / beat_dur)

    # 1. Driving Sub-Bass Progression in C minor (C2, Eb2, Ab1, Bb1)
    bass_freqs = [65.41, 77.78, 51.91, 58.27]  # C2, Eb2, Ab1, Bb1
    for b in range(num_beats):
        beat_start = b * beat_dur
        beat_idx = int(beat_start * sample_rate)
        sub_len = int(beat_dur * 0.85 * sample_rate)
        if beat_idx + sub_len > num_samples:
            sub_len = num_samples - beat_idx
        if sub_len <= 0:
            break
        
        freq = bass_freqs[(b // 4) % len(bass_freqs)]
        bt = np.linspace(0, sub_len / sample_rate, sub_len, endpoint=False)
        envelope = np.exp(-bt * 3.2)
        
        # Fundamental + slight 2nd harmonic for warmth
        bass_wave = (np.sin(2 * np.pi * freq * bt) + 0.3 * np.sin(2 * np.pi * freq * 2 * bt)) * 0.26 * envelope
        
        left[beat_idx:beat_idx + sub_len] += bass_wave
        right[beat_idx:beat_idx + sub_len] += bass_wave

    # 2. Rich Synth Chords / Pads (C minor, Eb major, Ab major, Bb dominant)
    c_minor = [130.81, 155.56, 196.00, 233.08] # C3, Eb3, G3, Bb3
    eb_maj = [155.56, 196.00, 233.08, 293.66]  # Eb3, G3, Bb3, D4
    ab_maj = [103.83, 130.81, 164.81, 207.65]  # Ab2, C3, Eb3, Ab3
    bb_dom = [116.54, 146.83, 174.61, 233.08]  # Bb2, D3, F3, Bb3
    chords = [c_minor, eb_maj, ab_maj, bb_dom]

    bar_dur = beat_dur * 4 # ~2.18s per bar
    num_bars = int(duration / bar_dur) + 1
    for bar in range(num_bars):
        bar_start = bar * bar_dur
        bar_idx = int(bar_start * sample_rate)
        bar_len = int(bar_dur * sample_rate)
        if bar_idx >= num_samples:
            break
        if bar_idx + bar_len > num_samples:
            bar_len = num_samples - bar_idx
            
        cur_chord = chords[bar % len(chords)]
        ct = np.linspace(0, bar_len / sample_rate, bar_len, endpoint=False)
        # Smooth trapezoidal / sine envelope
        env = (np.sin(np.pi * ct / (bar_len / sample_rate)) ** 1.3) * 0.11
        
        for i, f in enumerate(cur_chord):
            detune_l = np.sin(2 * np.pi * (f - 0.35) * ct)
            detune_r = np.sin(2 * np.pi * (f + 0.35) * ct)
            # Add subtle octave overtone
            oct_l = 0.25 * np.sin(2 * np.pi * (f * 2 - 0.2) * ct)
            oct_r = 0.25 * np.sin(2 * np.pi * (f * 2 + 0.2) * ct)
            left[bar_idx:bar_idx + bar_len] += (detune_l + oct_l) * env * (0.8 + 0.2 * (i % 2))
            right[bar_idx:bar_idx + bar_len] += (detune_r + oct_r) * env * (0.8 + 0.2 * ((i + 1) % 2))

    # 3. Dynamic Rhythmic Pulse & Hi-Hats
    for h in range(num_beats * 2):
        h_start = h * (beat_dur / 2.0)
        h_idx = int(h_start * sample_rate)
        h_len = int(0.028 * sample_rate)
        if h_idx + h_len > num_samples:
            break
        ht = np.linspace(0, 0.028, h_len, endpoint=False)
        accent = 1.3 if (h % 4 == 2) else 0.8
        noise = (np.random.rand(h_len) * 2 - 1) * np.exp(-ht * 110.0) * (0.028 * accent)
        left[h_idx:h_idx + h_len] += noise * 0.85
        right[h_idx:h_idx + h_len] += noise * 1.05

    # 4. Melodic Arpeggio Sequence (C minor scale: C4, Eb4, G4, Bb4, C5)
    arp_notes = [261.63, 311.13, 392.00, 466.16, 523.25, 466.16, 392.00, 311.13]
    for a in range(num_beats * 4):
        a_start = a * (beat_dur / 4.0)
        # Enable arpeggios after intro bar (from t >= 4.0s to 48.0s)
        if a_start < 4.0 or a_start > 48.0:
            continue
        a_idx = int(a_start * sample_rate)
        a_len = int(0.12 * sample_rate)
        if a_idx + a_len > num_samples:
            break
        at = np.linspace(0, 0.12, a_len, endpoint=False)
        note_freq = arp_notes[a % len(arp_notes)]
        arp_wave = np.sin(2 * np.pi * note_freq * at) * np.exp(-at * 22.0) * 0.045
        pan = 0.5 + 0.4 * np.sin(a * 0.5)
        left[a_idx:a_idx + a_len] += arp_wave * (1.0 - pan)
        right[a_idx:a_idx + a_len] += arp_wave * pan

    # 5. Specialized Scene Transition SFX & Cues:
    def add_hit(timestamp, freq=180.0, decay=8.0, gain=0.18):
        idx = int(timestamp * sample_rate)
        dur = int(0.5 * sample_rate)
        if idx + dur < num_samples:
            ht = np.linspace(0, 0.5, dur, endpoint=False)
            wave = np.sin(2 * np.pi * freq * ht) * np.exp(-ht * decay) * gain
            left[idx:idx + dur] += wave
            right[idx:idx + dur] += wave

    def add_glide(timestamp, start_f=420.0, end_f=65.0, dur_s=0.7, gain=0.22):
        idx = int(timestamp * sample_rate)
        dur = int(dur_s * sample_rate)
        if idx + dur < num_samples:
            gt = np.linspace(0, dur_s, dur, endpoint=False)
            freq_curve = (start_f - end_f) * np.exp(-gt * 5.0) + end_f
            phase = 2 * np.pi * np.cumsum(freq_curve) / sample_rate
            glide = np.sin(phase) * np.exp(-gt * 3.0) * gain
            left[idx:idx + dur] += glide
            right[idx:idx + dur] += glide

    def add_crystal_chime(timestamp, freq=523.25, gain=0.15):
        idx = int(timestamp * sample_rate)
        dur = int(1.6 * sample_rate)
        if idx + dur < num_samples:
            ct = np.linspace(0, 1.6, dur, endpoint=False)
            chime = (np.sin(2 * np.pi * freq * ct) + 0.3 * np.sin(2 * np.pi * freq * 2 * ct)) * np.exp(-ct * 2.5) * gain
            left[idx:idx + dur] += chime * 0.95
            right[idx:idx + dur] += chime * 1.05

    # Synchronized scene cues:
    add_hit(0.2, freq=120.0, gain=0.22)        # Scene 1: Opening impact
    add_hit(7.4, freq=150.0, gain=0.18)        # Scene 2: Hierarchy fan-out
    add_glide(14.8, start_f=500.0, end_f=70.0) # Scene 3: Latency drop / Model Router
    add_hit(22.2, freq=90.0, gain=0.20)        # Scene 4: Memory Pyramid & Vector DB
    add_hit(29.6, freq=280.0, decay=12.0)      # Scene 5: AST Guardrail alert cue
    add_crystal_chime(35.2, freq=659.25)       # Scene 5: Self-healing QA repair pass chime (E5)
    add_hit(37.0, freq=110.0, gain=0.24)       # Scene 6: Benchmark impact hit
    add_crystal_chime(44.4, freq=523.25)       # Scene 7: Production Cloud Run resolve (C5)

    # 6. Master fade-out over final 2.0 seconds
    fade_len = int(2.0 * sample_rate)
    fade_curve = np.linspace(1.0, 0.0, fade_len)
    left[-fade_len:] *= fade_curve
    right[-fade_len:] *= fade_curve

    # Peak normalization to -1.0 dB
    peak = max(np.max(np.abs(left)), np.max(np.abs(right)))
    if peak > 0:
        left = (left / peak) * 0.89
        right = (right / peak) * 0.89

    stereo = np.vstack((left, right)).T
    stereo_int16 = (stereo * 32767).astype(np.int16)

    wavfile.write(output_path, sample_rate, stereo_int16)
    print(f"Generated 52s soundtrack: {output_path} ({duration}s, {sample_rate}Hz stereo)")

if __name__ == "__main__":
    out_dir = r"d:\hack\brag-output-2026-10-23-195500\work"
    wav_path = os.path.join(out_dir, "soundtrack.wav")
    create_soundtrack(wav_path, duration=52.0)
