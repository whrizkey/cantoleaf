import math

import numpy as np


def generate_heading_chime(sample_rate: int = 24000) -> np.ndarray:
    """
    Soft two-note fifth interval (440 Hz -> 659.25 Hz) with exponential decay
    signaling chapter and section transitions without spoken clutter.
    """
    dur_note1 = 0.08
    dur_note2 = 0.12
    t1 = np.linspace(0, dur_note1, int(sample_rate * dur_note1), endpoint=False, dtype=np.float32)
    t2 = np.linspace(0, dur_note2, int(sample_rate * dur_note2), endpoint=False, dtype=np.float32)

    note1 = 0.15 * np.sin(2 * math.pi * 440.0 * t1) * np.exp(-t1 * 25.0)
    note2 = 0.15 * np.sin(2 * math.pi * 659.25 * t2) * np.exp(-t2 * 18.0)

    return np.concatenate([note1, note2]).astype(np.float32)


def generate_quote_pluck(sample_rate: int = 24000) -> np.ndarray:
    """Subtle 90ms warm resonant pluck signaling entry or exit of a blockquote."""
    dur = 0.09
    t = np.linspace(0, dur, int(sample_rate * dur), endpoint=False, dtype=np.float32)
    pluck = (0.12 * np.sin(2 * math.pi * 330.0 * t) * np.exp(-t * 35.0)).astype(np.float32)
    return np.asarray(pluck, dtype=np.float32)


def generate_figure_card_chime(sample_rate: int = 24000) -> np.ndarray:
    """Soft triad arpeggio (220ms) marking the start of a narrated Table or Chart."""
    dur = 0.07
    tones: list[np.ndarray] = []
    freqs = (392.0, 523.25, 659.25)  # G4, C5, E5
    for f in freqs:
        t = np.linspace(0, dur, int(sample_rate * dur), endpoint=False, dtype=np.float32)
        tones.append(0.12 * np.sin(2 * math.pi * f * t) * np.exp(-t * 22.0))
    return np.concatenate(tones).astype(np.float32)


def generate_recall_tick(sample_rate: int = 24000) -> np.ndarray:
    """Gentle 1-second pulse for the Socratic Memory Lock thinking pause."""
    dur = 1.0
    t = np.linspace(0, dur, int(sample_rate * dur), endpoint=False, dtype=np.float32)
    # 40ms soft tick at start of each second
    tick_dur = 0.04
    tick_samples = int(sample_rate * tick_dur)
    signal = np.zeros_like(t)
    t_tick = t[:tick_samples]
    signal[:tick_samples] = 0.08 * np.sin(2 * math.pi * 880.0 * t_tick) * np.exp(-t_tick * 80.0)
    return signal.astype(np.float32)
