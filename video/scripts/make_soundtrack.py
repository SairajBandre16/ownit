#!/usr/bin/env python3
"""Synthesize the OwnIt intro soundtrack from src/timeline.json.

Everything comes from oscillators and filtered noise (no samples, no models), so the track is
license-free and every hit lands on the same beat grid the video uses. Scene cuts, pops, dings
and whooshes are read from the "cues" in the timeline, so moving a cue there moves its sound too.

Output: public/soundtrack.wav (48 kHz, 16-bit stereo).
Needs: numpy, scipy.
"""

from __future__ import annotations

import json
import wave
from pathlib import Path

import numpy as np
from scipy.signal import butter, fftconvolve, sosfilt

ROOT = Path(__file__).resolve().parents[1]
TL = json.loads((ROOT / "src" / "timeline.json").read_text(encoding="utf-8"))
OUT = ROOT / "public" / "soundtrack.wav"

SR = 48000
BEAT = TL["beatFrames"] / TL["fps"]  # seconds per beat (18 frames at 30 fps = 100 BPM)
TOTAL_BEATS = TL["durationBeats"]
N = int(round(TOTAL_BEATS * BEAT * SR))
rng = np.random.default_rng(7)

# Bus levels. Tune the mix here.
LEVEL = {
    "kick": 0.80,
    "clap": 0.55,
    "hat": 0.17,
    "snare": 0.40,
    "crash": 0.16,
    "bass": 0.36,
    "pad": 0.55,
    "arp": 0.20,
    "sfx": 1.0,
    "reverb": 0.38,
}

# Per-cue sound levels.
SFX_GAIN = {
    "pop": 0.30,
    "tick": 0.24,
    "swap": 0.28,
    "ding": 0.20,
    "roll": 0.16,
    "type": 0.17,
    "type_soft": 0.10,
    "whoosh": 0.30,
    "whoosh_small": 0.20,
    "riser": 0.30,
    "swell": 0.14,
    "swell_short": 0.12,
    "thud": 0.75,
    "impact": 0.85,
    "impact_big": 0.95,
    "unlock": 0.30,
    "stab": 0.30,
    "bell": 0.26,
    "bell_hi": 0.28,
}

# Chords as (pad voicing, bass root), MIDI note numbers.
CHORDS = {
    "F": ([53, 57, 60, 64], 41),
    "G": ([55, 59, 62, 64], 43),
    "Am": ([57, 60, 64, 67], 45),
    "Em": ([52, 55, 59, 62], 40),
    "Dm": ([50, 53, 57, 60], 38),
    "C": ([48, 52, 55, 59, 62], 36),
}
SCENES = {s["id"]: s for s in TL["scenes"]}


def start(scene: str) -> float:
    return float(SCENES[scene]["start"])


def end(scene: str) -> float:
    return float(SCENES[scene]["start"] + SCENES[scene]["beats"])


def cue_beat(scene: str, name: str) -> float:
    return start(scene) + TL["cues"][scene][name][0]


# One chord per scene, or the scene split evenly between its chords, so harmony moves on the cuts.
CHORD_PLAN: list[tuple[float, float, str]] = []
for _s in TL["scenes"]:
    _part = _s["beats"] / len(_s["chords"])
    for _k, _name in enumerate(_s["chords"]):
        CHORD_PLAN.append((_s["start"] + _k * _part, _s["start"] + (_k + 1) * _part, _name))

# Music drops out for half a beat before the two big hits.
GAPS = [(cue_beat("hook", "blackout"), start("brand")), (cue_beat("badges", "gap"), start("end"))]


# ----------------------------------------------------------------------------- helpers


def sec(beat: float) -> float:
    return beat * BEAT


def ns(seconds: float) -> int:
    return int(round(seconds * SR))


def tt(dur: float) -> np.ndarray:
    return np.arange(ns(dur)) / SR


def noise(dur: float) -> np.ndarray:
    return rng.uniform(-1.0, 1.0, ns(dur))


def mtof(m: float) -> float:
    return 440.0 * 2 ** ((m - 69) / 12)


def filt(x: np.ndarray, kind: str, f: float | list[float], order: int = 2) -> np.ndarray:
    sos = butter(order, f, btype=kind, fs=SR, output="sos")
    return sosfilt(sos, x, axis=-1)


def env(dur: float, a: float, d: float, sus: float, r: float) -> tuple[np.ndarray, np.ndarray]:
    """Attack / exponential decay to sustain while held for `dur`, then exponential release."""
    t = tt(dur + 5 * r)
    on = np.minimum(1.0, t / max(a, 1e-4)) * (sus + (1 - sus) * np.exp(-np.maximum(t - a, 0) / max(d, 1e-4)))
    held = on[min(ns(dur), len(on) - 1)]
    off = held * np.exp(-(t - dur) / r)
    return t, np.where(t < dur, on, off)


def saw(f: float, t: np.ndarray, phase: float) -> np.ndarray:
    return 2.0 * ((f * t + phase) % 1.0) - 1.0


def svf_band(x: np.ndarray, fc: np.ndarray, q: float = 1.2) -> np.ndarray:
    """State-variable band-pass with a time-varying centre frequency (for whooshes and risers)."""
    out = np.empty_like(x)
    low = band = 0.0
    damp = 1.0 / q
    coef = 2.0 * np.sin(np.pi * np.minimum(fc, 7000.0) / SR)
    for i in range(len(x)):
        f = coef[i]
        low += f * band
        high = x[i] - low - damp * band
        band += f * high
        out[i] = band
    return out


def pan_st(x: np.ndarray, pan: float | np.ndarray) -> np.ndarray:
    a = (np.asarray(pan) + 1.0) * np.pi / 4.0
    return np.vstack([x * np.cos(a), x * np.sin(a)]) * np.sqrt(2.0)


class Bus:
    def __init__(self) -> None:
        self.x = np.zeros((2, N))

    def add(self, sig: np.ndarray, at: float, gain: float = 1.0, pan: float = 0.0) -> None:
        st = sig if sig.ndim == 2 else pan_st(sig, pan)
        i0 = ns(at)
        j0 = max(0, -i0)
        i0 = max(0, i0)
        length = min(st.shape[1] - j0, N - i0)
        if length > 0:
            self.x[:, i0 : i0 + length] += gain * st[:, j0 : j0 + length]


# ----------------------------------------------------------------------------- instruments


def kick(dur: float = 0.5) -> np.ndarray:
    t = tt(dur)
    f = 44 + 120 * np.exp(-t * 32)
    body = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 6.5)
    click = filt(noise(0.006), "highpass", 2000) * np.exp(-tt(0.006) * 600)
    body[: len(click)] += 0.35 * click
    return np.tanh(1.6 * body) / np.tanh(1.6)


def clap() -> np.ndarray:
    t = tt(0.4)
    e = np.zeros_like(t)
    for off in (0.0, 0.011, 0.022):
        m = t >= off
        e[m] += 0.8 * np.exp(-(t[m] - off) * 180)
    m = t >= 0.03
    e[m] += 0.7 * np.exp(-(t[m] - 0.03) * 15)
    return filt(noise(0.4) * e, "bandpass", [900, 3600])


def hat(decay: float = 40.0) -> np.ndarray:
    t = tt(0.3)
    return filt(noise(0.3), "highpass", 7000) * np.exp(-t * decay)


def snare() -> np.ndarray:
    t = tt(0.25)
    tone = np.sin(2 * np.pi * 190 * t) * np.exp(-t * 30)
    nz = filt(noise(0.25), "bandpass", [1500, 7500]) * np.exp(-t * 22)
    return 0.5 * tone + 0.8 * nz


def crash() -> np.ndarray:
    t = tt(2.4)
    x = filt(noise(2.4), "highpass", 4500) * np.exp(-t * 2.0)
    ring = sum(np.sin(2 * np.pi * f * t) for f in (3150.0, 4410.0, 5230.0, 6620.0)) * np.exp(-t * 3.0)
    return x + 0.05 * ring


def bass(m: float, dur: float) -> np.ndarray:
    t, e = env(dur, 0.004, 0.25, 0.7, 0.03)
    f = mtof(m)
    x = np.sin(2 * np.pi * f * t) + 0.3 * np.sin(4 * np.pi * f * t) + 0.08 * np.sin(6 * np.pi * f * t)
    return np.tanh(1.4 * x * e)


def pad_chord(notes: list[int], dur: float, attack: float, release: float = 0.35) -> np.ndarray:
    t, e = env(dur, attack, 1.2, 0.85, release)
    out = np.zeros((2, len(t)))
    for m in notes:
        f = mtof(m)
        for det, pan in ((-0.09, -0.75), (0.0, 0.0), (0.08, 0.75)):
            v = saw(f * 2 ** (det / 12), t, float(rng.random()))
            out += pan_st(v, pan) * 0.5
    return out * e / (len(notes) * 1.6)


def pluck(m: float, dur: float = 0.55) -> np.ndarray:
    t = tt(dur)
    f = mtof(m)
    x = (
        np.sin(2 * np.pi * f * t)
        + 0.22 * np.sin(4 * np.pi * f * t) * np.exp(-t * 18)
        + 0.10 * np.sin(6 * np.pi * f * t) * np.exp(-t * 28)
    )
    return x * np.exp(-t * 9) * np.minimum(1.0, t / 0.002)


def bell(m: float, dur: float = 2.8) -> np.ndarray:
    """Electric-piano style FM tone: soft body plus a short metallic tine."""
    t = tt(dur)
    f = mtof(m)
    idx = 1.6 * np.exp(-t * 2.5)
    body = np.sin(2 * np.pi * f * t + idx * np.sin(2 * np.pi * f * t))
    tine = np.sin(2 * np.pi * f * t + 0.6 * np.exp(-t * 25) * np.sin(2 * np.pi * f * 7 * t))
    x = 0.7 * body + 0.3 * tine
    return x * np.exp(-t * 1.6) * np.minimum(1.0, t / 0.002)


# ----------------------------------------------------------------------------- sound effects


def sfx_pop(step: int) -> np.ndarray:
    t = tt(0.14)
    k = 2 ** ([0, 2, 4, 7, 9, 12][step % 6] / 12)
    f = (900 * np.exp(-t * 18) + 440) * k
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 32)


def sfx_tick(step: int = 0, f0: float = 2400.0) -> np.ndarray:
    t = tt(0.06)
    f = f0 * 2 ** ([0, 2, 4, 7, 9][step % 5] / 12)
    return np.sin(2 * np.pi * f * t) * np.exp(-t * 110) + 0.3 * filt(noise(0.06), "highpass", 5000) * np.exp(-t * 300)


def sfx_swap(step: int) -> np.ndarray:
    out = np.zeros(ns(0.3))
    a = sfx_tick(step, 1800.0)
    b = sfx_tick(step, 2700.0)
    out[: len(a)] += a
    out[ns(0.06) : ns(0.06) + len(b)] += 0.8 * b
    w = filt(noise(0.18), "bandpass", [2000, 6000]) * np.sin(np.pi * tt(0.18) / 0.18) ** 2
    out[: len(w)] += 0.25 * w
    return out


def sfx_ding(m1: float = 91, m2: float = 98) -> np.ndarray:
    t = tt(1.2)
    x = np.sin(2 * np.pi * mtof(m1) * t) + 0.6 * np.sin(2 * np.pi * mtof(m2) * t) + 0.15 * np.sin(2 * np.pi * mtof(m1) * 2 * t)
    return x * np.exp(-t * 3.5) * np.minimum(1.0, t / 0.002)


def sfx_roll(dur: float = 0.6) -> np.ndarray:
    out = np.zeros(ns(dur + 0.1))
    k = 0
    for at in np.arange(0, dur, 0.034):
        tk = sfx_tick(0, 2100 + 900 * at / dur) * (0.7 - 0.5 * at / dur)
        i = ns(at)
        out[i : i + len(tk)] += tk[: len(out) - i]
        k += 1
    return out


def sfx_type(dur: float) -> np.ndarray:
    out = np.zeros(ns(dur + 0.1))
    at = 0.0
    while at < dur:
        t = tt(0.03)
        click = filt(noise(0.03), "bandpass", [1800, 6500]) * np.exp(-t * 380)
        thock = np.sin(2 * np.pi * 320 * t) * np.exp(-t * 160)
        c = (0.8 * click + 0.4 * thock) * rng.uniform(0.5, 1.0)
        i = ns(at)
        out[i : i + len(c)] += c[: len(out) - i]
        at += rng.uniform(0.045, 0.085)
    return out


def sfx_whoosh(rise: float, fall: float = 0.35) -> np.ndarray:
    """Band-passed noise swept up then down, panned across the stereo field; peaks at `rise`."""
    dur = rise + fall
    t = tt(dur)
    fc = np.where(t < rise, 300 * (2600 / 300) ** (t / rise), 2600 * (700 / 2600) ** ((t - rise) / fall))
    e = np.where(t < rise, (t / rise) ** 2, np.exp(-(t - rise) * 9))
    x = svf_band(noise(dur), fc, 1.4) * e
    return pan_st(x / (np.max(np.abs(x)) + 1e-9), np.linspace(-0.6, 0.6, len(t)))


def sfx_riser(dur: float) -> np.ndarray:
    t = tt(dur)
    fc = 400 * (6000 / 400) ** (t / dur)
    e = (t / dur) ** 1.6
    x = svf_band(noise(dur), fc, 2.0)
    x = x / (np.max(np.abs(x)) + 1e-9)
    f = 180 * (1100 / 180) ** (t / dur) * (1 + 0.01 * np.sin(2 * np.pi * 6 * t))
    tone = np.sin(2 * np.pi * np.cumsum(f) / SR)
    return (0.8 * x + 0.25 * tone) * e


def sfx_swell(dur: float = 2.2, rise: float = 0.8) -> np.ndarray:
    t = tt(dur)
    e = np.where(t < rise, np.sin(0.5 * np.pi * t / rise) ** 2, np.exp(-(t - rise) * 1.6))
    return filt(noise(dur), "bandpass", [500, 2600]) * e


def sfx_shimmer() -> np.ndarray:
    t = tt(0.9)
    e = np.sin(np.pi * np.minimum(t / 0.9, 1.0)) ** 2
    tones = sum(np.sin(2 * np.pi * mtof(m) * t) * (1 + 0.4 * np.sin(2 * np.pi * 11 * t + m)) for m in (84, 88, 91, 95))
    air = filt(noise(0.9), "highpass", 6000)
    return (0.25 * tones + 0.6 * air) * e


def sfx_thud(dur: float = 0.7) -> np.ndarray:
    t = tt(dur)
    f = 50 + 70 * np.exp(-t * 20)
    body = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 5)
    hit = filt(noise(dur), "lowpass", 1800) * np.exp(-t * 40)
    return np.tanh(1.5 * (body + 0.5 * hit))


def sfx_impact(big: bool = False) -> np.ndarray:
    dur = 3.0 if big else 2.0
    t = tt(dur)
    f = 38 + 90 * np.exp(-t * 14)
    boom = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * (1.4 if big else 2.2))
    burst = filt(noise(dur), "lowpass", 3500) * np.exp(-t * 9)
    x = np.tanh(1.8 * (boom + 0.45 * burst))
    if big:
        c = crash()[: len(x)]
        x[: len(c)] += 0.35 * c
    return x


def sfx_unlock() -> np.ndarray:
    out = np.zeros(ns(1.3))
    for at in (0.0, 0.07):
        t = tt(0.05)
        c = filt(noise(0.05), "bandpass", [3000, 8000]) * np.exp(-t * 300) + 0.5 * np.sin(2 * np.pi * 3200 * t) * np.exp(-t * 90)
        i = ns(at)
        out[i : i + len(c)] += c
    d = sfx_ding(96, 103)
    i = ns(0.12)
    out[i : i + len(d)] += 0.8 * d[: len(out) - i]
    return out


def sfx_stab(chord: str) -> np.ndarray:
    notes = [m + 12 for m in CHORDS[chord][0]]
    st = pad_chord(notes, 0.16, 0.003, 0.09)
    st = filt(st, "lowpass", 3200)
    hit = snare()
    st[:, : len(hit)] += 0.35 * hit
    return st


# ----------------------------------------------------------------------------- arrangement


def chord_at(beat: float) -> str:
    for a, b, name in CHORD_PLAN:
        if a <= beat < b:
            return name
    return CHORD_PLAN[-1][2]


def scene_of(beat: float) -> str:
    current = TL["scenes"][0]["id"]
    for s in TL["scenes"]:
        if beat >= s["start"]:
            current = s["id"]
    return current


GROOVE = ("humanize", "walkthrough", "mine", "doctor", "export")


def build() -> np.ndarray:
    kick_bus, drum_bus, bass_bus, pad_bus, arp_bus = Bus(), Bus(), Bus(), Bus(), Bus()
    sfx_bus, send = Bus(), Bus()
    kick_times: list[float] = []

    def k(beat: float, gain: float = 1.0) -> None:
        kick_bus.add(kick(), sec(beat), gain)
        kick_times.append(sec(beat))

    blackout = cue_beat("hook", "blackout")
    gap = cue_beat("badges", "gap")

    # Drums
    for b in range(TOTAL_BEATS):
        sc = scene_of(b)
        local = b - start(sc)
        groove = sc in GROOVE
        build_up = sc == "badges" and b < gap
        if sc == "hook" and b in (0, 2):
            k(b, 0.45)  # soft heartbeat under the hook
        if sc == "brand" or groove or build_up:
            k(b)
        if sc == "viva" and local % 2 == 0:
            k(b)  # half-time "exam hall" feel
        if b == start("end"):
            k(b)
        if (groove or build_up) and local % 2 == 1:
            drum_bus.add(clap(), sec(b), LEVEL["clap"])
            send.add(clap(), sec(b), 0.12)
        if sc == "viva" and local % 4 == 2:
            drum_bus.add(clap(), sec(b), LEVEL["clap"])
        # hats
        if sc == "hook" and 2 <= b < blackout:
            for h in (0.0, 0.5):
                if b + h < blackout:
                    ramp = (b + h - 2) / (blackout - 2)
                    drum_bus.add(hat(55), sec(b + h), LEVEL["hat"] * (0.25 + 0.5 * ramp), pan=0.3)
        if sc == "brand":
            drum_bus.add(hat(), sec(b + 0.5), LEVEL["hat"], pan=0.3)
        if groove:
            drum_bus.add(hat(), sec(b + 0.5), LEVEL["hat"], pan=0.3)
            for h in (0.25, 0.75):
                drum_bus.add(hat(70), sec(b + h), LEVEL["hat"] * 0.4, pan=0.4)
            if local % 2 == 1:
                drum_bus.add(hat(12), sec(b + 0.5), LEVEL["hat"] * 0.5, pan=-0.2)
        if sc == "viva":
            drum_bus.add(hat(60), sec(b + 0.5), LEVEL["hat"] * 0.35, pan=0.3)
        if build_up:
            for h in (0.0, 0.25, 0.5, 0.75):
                if b + h < gap:
                    drum_bus.add(hat(60), sec(b + h), LEVEL["hat"] * 0.6, pan=0.3)
    # Snare roll into the end card: 8ths, then 16ths for the last two beats.
    b0 = start("badges")
    roll = list(np.arange(b0, gap - 2, 0.5)) + list(np.arange(gap - 2, gap, 0.25))
    for i, rb in enumerate(roll):
        drum_bus.add(snare(), sec(rb), LEVEL["snare"] * (0.2 + 0.8 * i / (len(roll) - 1)), pan=-0.1)
    for cb in (start("humanize"), start("doctor")):
        drum_bus.add(crash(), sec(cb), LEVEL["crash"], pan=-0.3)

    # Bass
    for b in range(TOTAL_BEATS):
        sc = scene_of(b)
        local = b - start(sc)
        root = CHORDS[chord_at(b)][1]
        if sc == "brand" or sc in GROOVE or (sc == "badges" and b + 0.5 < gap - 0.5):
            bass_bus.add(bass(root + (12 if local % 4 == 3 else 0), 0.2), sec(b + 0.5), LEVEL["bass"])
            if local % 4 == 0:
                bass_bus.add(bass(root, 0.14), sec(b), LEVEL["bass"] * 0.8)
        if sc == "viva" and local % 2 == 0:
            bass_bus.add(bass(root, sec(1.8)), sec(b), LEVEL["bass"])
    bass_bus.add(bass(CHORDS["C"][1], sec(3.5)), sec(start("end")), LEVEL["bass"] * 1.1)

    # Pad: one chord per CHORD_PLAN segment; the last one rings out under the end card.
    for i, (a, b, name) in enumerate(CHORD_PLAN):
        last = i == len(CHORD_PLAN) - 1
        attack = 0.9 if i == 0 else 0.03
        dur = sec(b - a) - (0.8 if last else 0.0)
        pad_bus.add(pad_chord(CHORDS[name][0], dur, attack, 1.4 if last else 0.35), sec(a), LEVEL["pad"])

    # Arp: 8ths from Humanize on, 16ths in the build before the end card.
    pattern = [0, 2, 1, 3, 2, 1, 3, 2]
    for b in range(int(start("humanize")), int(np.ceil(gap))):
        sc = scene_of(b)
        notes = CHORDS[chord_at(b)][0]
        steps = (0.0, 0.25, 0.5, 0.75) if sc == "badges" else (0.0, 0.5)
        for j, h in enumerate(steps):
            if b + h >= gap:
                continue
            idx = pattern[(b * len(steps) + j) % len(pattern)]
            m = notes[idx % len(notes)] + 12
            g = LEVEL["arp"] * (0.65 if sc == "viva" else 1.0)
            pan = -0.35 if (j % 2 == 0) else 0.35
            arp_bus.add(pluck(m), sec(b + h), g, pan)
            send.add(pluck(m), sec(b + h), g * 0.8, pan)

    # Cued sound effects
    end_bells = {"tagline1": 76, "tagline2": 79, "tagline3": 84}
    starts = {sid: start(sid) for sid in SCENES}
    placed: list[tuple[float, str, str]] = []
    for scene, cues in TL["cues"].items():
        step = 0
        for name, (cb, kind) in cues.items():
            if not kind:
                continue
            at = sec(starts[scene] + cb)
            g = SFX_GAIN[kind]
            placed.append((starts[scene] + cb, scene, f"{name}:{kind}"))
            if kind == "pop":
                s = sfx_pop(step)
                step += 1
                pan = -0.3 + 0.2 * step
                sfx_bus.add(s, at, g, pan)
                send.add(s, at, g * 0.5, pan)
            elif kind == "tick":
                s = sfx_tick(step)
                step += 1
                sfx_bus.add(s, at, g, 0.15)
                send.add(s, at, g * 0.4)
            elif kind == "swap":
                s = sfx_swap(step)
                step += 1
                sfx_bus.add(s, at, g, 0.2)
                send.add(s, at, g * 0.3)
            elif kind == "ding":
                sfx_bus.add(sfx_ding(), at, g)
                send.add(sfx_ding(), at, g * 0.6)
            elif kind == "roll":
                sfx_bus.add(sfx_roll(), at, g, 0.1)
            elif kind in ("type", "type_soft"):
                sfx_bus.add(sfx_type(sec(1.4)), at, g, -0.1)
            elif kind == "whoosh":
                w = sfx_whoosh(sec(0.5))
                sfx_bus.add(w, at, g)
                send.add(w, at, g * 0.4)
            elif kind == "whoosh_small":
                sfx_bus.add(sfx_whoosh(0.12, 0.22), at, g)
            elif kind == "riser":
                length = sec(blackout - (starts[scene] + cb))
                sfx_bus.add(sfx_riser(length), at, g)
                send.add(sfx_riser(length), at, g * 0.3)
            elif kind == "swell":
                sfx_bus.add(sfx_swell(), at, g)
                send.add(sfx_swell(), at, g)
            elif kind == "swell_short":
                sfx_bus.add(sfx_shimmer(), at, g)
                send.add(sfx_shimmer(), at, g * 0.8)
            elif kind == "thud":
                sfx_bus.add(sfx_thud(), at, g)
                send.add(sfx_thud(), at, g * 0.25)
            elif kind in ("impact", "impact_big"):
                s = sfx_impact(kind == "impact_big")
                sfx_bus.add(s, at, g)
                send.add(s, at, g * 0.45)
            elif kind == "unlock":
                sfx_bus.add(sfx_unlock(), at, g)
                send.add(sfx_unlock(), at, g * 0.5)
            elif kind == "stab":
                s = sfx_stab(chord_at(starts[scene] + cb))
                sfx_bus.add(s, at, g)
                send.add(s, at, g * 0.5)
            elif kind in ("bell", "bell_hi"):
                s = bell(end_bells.get(name, 79))
                sfx_bus.add(s, at, g, {"tagline1": -0.4, "tagline2": 0.4}.get(name, 0.0))
                send.add(s, at, g * 0.9)
            else:
                raise ValueError(f"unknown sound {kind!r} for cue {scene}.{name}")

    # Pad brightness automation: cross-fade a dark and a bright low-pass of the same pad.
    auto_pts = [(0, 0.05), (cue_beat("hook", "riser"), 0.35), (blackout, 0.7), (start("brand"), 0.55),
                (start("humanize"), 0.75), (start("viva") - 0.1, 0.8), (start("viva"), 0.15), (end("viva") - 0.5, 0.3),
                (start("doctor"), 0.8), (start("badges"), 0.7), (gap, 1.0), (start("end"), 1.0), (TOTAL_BEATS, 0.35)]
    tb = np.arange(N) / SR / BEAT
    bright = np.interp(tb, [p[0] for p in auto_pts], [p[1] for p in auto_pts])
    pad = filt(pad_bus.x, "lowpass", 520) * (1 - bright) + filt(pad_bus.x, "lowpass", 2800) * bright
    send.x += pad * 0.6

    # Sidechain: pad, bass and arp duck under each kick.
    sc = np.ones(N)
    t = np.arange(N) / SR
    for kt in kick_times:
        i = ns(kt)
        seg = t[i : i + ns(0.6)] - kt
        duck = 1 - 0.55 * np.exp(-seg / 0.13) * np.minimum(1.0, seg / 0.004 + 0.2)
        sc[i : i + len(seg)] = np.minimum(sc[i : i + len(seg)], duck)

    music = kick_bus.x * LEVEL["kick"] + drum_bus.x + (bass_bus.x + pad + arp_bus.x) * sc

    # Reverb: stereo decaying-noise impulse response.
    ir_t = tt(2.2)
    decay = np.exp(-6.9 * ir_t / 1.7)
    ir = np.vstack([noise(2.2) * decay, noise(2.2) * decay])
    ir = filt(ir, "lowpass", 5200)
    ir = np.concatenate([np.zeros((2, ns(0.018))), ir], axis=1)
    ir /= np.sqrt(np.sum(ir**2, axis=1, keepdims=True))
    wet = np.vstack([fftconvolve(send.x[c], ir[c])[:N] for c in range(2)])
    wet = filt(wet, "highpass", 180)

    gate = np.ones(N)
    for a, b in GAPS:
        i0, i1 = ns(sec(a)), ns(sec(b))
        ramp = ns(0.006)
        gate[i0:i1] = 0.0
        gate[i0 : i0 + ramp] = np.linspace(1, 0, ramp)
    music *= gate
    mix = music + sfx_bus.x * LEVEL["sfx"] + wet * LEVEL["reverb"] * (0.35 + 0.65 * gate)

    # Master: high-pass, glue, soft clip, fades, -1 dBFS peak.
    mix = filt(mix, "highpass", 28)
    mix /= np.max(np.abs(mix)) + 1e-9
    mix = np.tanh(1.4 * mix) / np.tanh(1.4)
    fade_in = np.minimum(1.0, t / 0.01)
    fade_out = np.clip((t[-1] - t) / 1.1, 0.0, 1.0) ** 1.5
    mix *= fade_in * fade_out
    mix *= 0.891 / (np.max(np.abs(mix)) + 1e-9)

    print("cues placed:")
    for b, scene, label in sorted(placed):
        print(f"  beat {b:5.1f}  frame {b * TL['beatFrames']:6.1f}  {scene:12s} {label}")
    for name, x in (("kick", kick_bus.x * LEVEL["kick"]), ("drums", drum_bus.x), ("bass", bass_bus.x),
                    ("pad", pad), ("arp", arp_bus.x), ("sfx", sfx_bus.x), ("wet", wet * LEVEL["reverb"])):
        rms = np.sqrt(np.mean(x**2)) + 1e-12
        print(f"  bus {name:6s} rms {20 * np.log10(rms):6.1f} dBFS  peak {20 * np.log10(np.max(np.abs(x)) + 1e-12):6.1f} dBFS")
    return mix


def main() -> None:
    mix = build()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    pcm = (np.clip(mix, -1, 1).T * 32767).astype("<i2")
    with wave.open(str(OUT), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())
    rms = np.sqrt(np.mean(mix**2))
    print(f"wrote {OUT.relative_to(ROOT)}: {mix.shape[1] / SR:.2f} s, master rms {20 * np.log10(rms):.1f} dBFS")


if __name__ == "__main__":
    main()
