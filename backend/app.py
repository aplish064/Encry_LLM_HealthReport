
import os
import json
import time
import re
import base64
import tempfile
from io import BytesIO
from typing import Dict, Any, Optional, List

import numpy as np
import tenseal as ts

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.image as mpimg

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import sys
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from openai import AsyncOpenAI

SERVER_PY = os.path.join(os.path.dirname(__file__), "server.py")

# project root (contains HAR_train.txt / imu_walk.txt / uwb_walk.txt)
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

DATA_PATHS = {
    "UWB": os.path.join(BASE_DIR, "test_data", "uwb_from_utar.txt"),
    "IMU": os.path.join(BASE_DIR, "test_data", "imu_from_utar.txt"),
    "CSI": os.path.join(BASE_DIR, "test_data", "csi_from_utar.csv"),
}

# user-provided (or auto-generated) images
ASSET_USER_DIR = os.path.join(BASE_DIR, "frontend", "assets", "user")
DEPTH_PNG_PATH = os.path.join(ASSET_USER_DIR, "deep2.png")
RGB_PNG_PATH = os.path.join(ASSET_USER_DIR, "RGB.png")

_DATA_CACHE: Dict[str, np.ndarray] = {}

app = FastAPI(title="Secure Multimodal HE + LLM Demo", version="2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def b64e(b: bytes) -> str:
    return base64.b64encode(b).decode("ascii")

def png_b64_from_plt(fig, pad_inches: float = 0.06) -> str:
    bio = BytesIO()
    fig.savefig(bio, format="png", dpi=160, bbox_inches="tight", pad_inches=pad_inches)
    plt.close(fig)
    return b64e(bio.getvalue())

def png_b64_from_file(path: str) -> Optional[str]:
    try:
        with open(path, "rb") as f:
            return b64e(f.read())
    except Exception:
        return None

def _load_csv_matrix(path: str) -> np.ndarray:
    # Robust numeric loader for txt/csv. We auto-detect comma vs whitespace.
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        first = f.readline().strip()
    if not first:
        return np.empty((0, 0), dtype=float)
    if "," in first:
        return np.loadtxt(path, delimiter=",", dtype=float)
    return np.loadtxt(path, delimiter=None, dtype=float)

def get_data(name: str) -> np.ndarray:
    if name in _DATA_CACHE:
        return _DATA_CACHE[name]
    p = DATA_PATHS.get(name)
    if not p or not os.path.exists(p):
        raise FileNotFoundError(f"Missing data file for {name}: {p}")
    arr = _load_csv_matrix(p)
    _DATA_CACHE[name] = arr
    return arr

def _llm_client_from_env() -> Optional[AsyncOpenAI]:
    api_key = os.getenv("DEEPSEEK_API_KEY") or os.getenv("LLM_API_KEY")
    base_url = os.getenv("DEEPSEEK_BASE_URL") or os.getenv("LLM_BASE_URL")
    if not api_key or not base_url:
        return None
    return AsyncOpenAI(api_key=api_key, base_url=base_url)

def setup_context() -> ts.Context:
    ctx = ts.context(
        ts.SCHEME_TYPE.CKKS,
        poly_modulus_degree=16384,
        coeff_mod_bit_sizes=[60, 40, 40, 40, 40, 40, 60],
    )
    ctx.global_scale = 2 ** 40
    ctx.generate_galois_keys()
    return ctx

def make_public_context_bytes(ctx: ts.Context) -> bytes:
    pub = ctx.copy()
    pub.make_context_public()
    return pub.serialize()

def bytes_preview(b: bytes, n: int = 80) -> str:
    return b[:n].hex()

# -----------------------------
# Simulation (5 modalities)
# -----------------------------
def sim_timeseries(frames: int, dims: int, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    t = np.linspace(0, 10, frames)
    base = np.sin(2 * np.pi * 0.35 * t) + 0.35 * np.sin(2 * np.pi * 0.09 * t + 0.7)
    drift = 0.015 * t
    X = []
    for i in range(dims):
        noise = rng.normal(0, 0.06 + 0.01 * i, size=frames)
        comp = (1.0 + 0.05 * i) * (base + 0.2 * np.sin(2 * np.pi * (0.18 + 0.02 * i) * t + 0.25 * i) + drift) + noise
        X.append(comp)
    return np.stack(X, axis=1)

def sim_depth(seed: int, h: int = 64, w: int = 64) -> np.ndarray:
    rng = np.random.default_rng(seed)
    y, x = np.mgrid[0:h, 0:w]
    cx, cy = w * 0.5 + rng.normal(0, 2.0), h * 0.5 + rng.normal(0, 2.0)
    r = np.sqrt((x - cx) ** 2 + (y - cy) ** 2)
    depth = np.exp(-(r ** 2) / (2 * (w * 0.22) ** 2)) + 0.15 * rng.normal(0, 1, size=(h, w))
    depth = np.clip(depth, 0, 1)
    return depth

def sim_rgb(seed: int, h: int = 64, w: int = 64) -> np.ndarray:
    rng = np.random.default_rng(seed)
    base = rng.uniform(0.15, 0.9, size=(h, w, 3))
    y, x = np.mgrid[0:h, 0:w]
    cx, cy = w * 0.55 + rng.normal(0, 3.0), h * 0.45 + rng.normal(0, 3.0)
    r2 = (x - cx) ** 2 + (y - cy) ** 2
    blob = np.exp(-r2 / (2 * (w * 0.18) ** 2))
    base[..., 0] = np.clip(base[..., 0] + 0.35 * blob, 0, 1)
    base[..., 1] = np.clip(base[..., 1] + 0.15 * blob, 0, 1)
    return base

def plot_har(har_vec: np.ndarray, title: str) -> str:
    """Render HAR feature vector as a small heatmap."""
    v = np.asarray(har_vec, dtype=float).ravel()
    # take first 576 values and reshape to 24x24 (pad if needed)
    n = 24 * 24
    if v.size < n:
        v = np.pad(v, (0, n - v.size))
    v = v[:n]
    # normalize for display
    vv = v - np.nanmin(v)
    denom = np.nanmax(vv) - np.nanmin(vv)
    if denom > 1e-9:
        vv = vv / denom
    img = vv.reshape(24, 24)

    fig = plt.figure(figsize=(3.2, 2.4))
    ax = fig.add_subplot(111)
    ax.imshow(img, cmap="magma")
    ax.set_title(title, fontsize=11, fontweight="bold")
    ax.axis("off")
    fig.tight_layout()
    return png_b64_from_plt(fig)

def feat_from_har(v: np.ndarray) -> np.ndarray:
    vv = np.asarray(v, dtype=float).ravel()
    feats = np.array([
        float(np.mean(vv)),
        float(np.std(vv)),
        float(np.min(vv)),
        float(np.max(vv)),
        float(np.mean(np.abs(vv))),
        float(np.percentile(vv, 90)),
        float(np.percentile(vv, 10)),
        float(np.mean(np.square(vv))),
    ])
    return feats

def plot_line(series: np.ndarray, title: str) -> str:
    fig = plt.figure(figsize=(4.6, 2.4))
    ax = fig.add_subplot(111)
    ax.plot(series)
    ax.set_title(title, fontsize=11, fontweight="bold")
    ax.set_xlabel("frame index / time", fontsize=9)
    ax.set_ylabel("value", fontsize=9)
    ax.grid(True, alpha=0.25)
    fig.tight_layout()
    return png_b64_from_plt(fig)

def plot_sparkline(series: np.ndarray) -> str:
    """Line-only preview: no axes, no ticks, no labels, no title."""
    fig = plt.figure(figsize=(4.6, 2.0))
    ax = fig.add_subplot(111)
    ax.plot(series, linewidth=1.4)
    ax.set_axis_off()
    for sp in ax.spines.values():
        sp.set_visible(False)
    ax.margins(x=0.0, y=0.08)
    fig.subplots_adjust(left=0, right=1, top=1, bottom=0)
    return png_b64_from_plt(fig, pad_inches=0.0)

def plot_fft_spectrum(data: np.ndarray, title: str, fs: float = 24.0, max_channels: int = 4) -> str:
    """Plot FFT spectrum for time series data."""
    if data.ndim == 1:
        data = data.reshape(-1, 1)

    n_channels = min(data.shape[1], max_channels)
    fig, axes = plt.subplots(n_channels, 1, figsize=(8, 1.6 * n_channels), sharex=True)

    if n_channels == 1:
        axes = [axes]

    for i in range(n_channels):
        signal = data[:, i]
        # Remove mean and apply window
        signal = signal - np.mean(signal)
        window = np.hanning(len(signal))
        signal_windowed = signal * window

        # Compute FFT
        fft_vals = np.fft.rfft(signal_windowed)
        fft_mag = np.abs(fft_vals)
        freqs = np.fft.rfftfreq(len(signal), d=1.0/fs)

        # Plot
        ax = axes[i]
        ax.plot(freqs, fft_mag, linewidth=1.2, color=f'C{i}')
        ax.fill_between(freqs, fft_mag, alpha=0.3, color=f'C{i}')
        ax.grid(True, alpha=0.3, linestyle='--')
        ax.set_ylabel(f'Ch{i} Mag', fontsize=9, fontweight='bold')
        ax.tick_params(labelsize=8)

        # Mark dominant frequency
        if len(fft_mag) > 1:
            peak_idx = np.argmax(fft_mag[1:]) + 1  # Skip DC component
            peak_freq = freqs[peak_idx]
            ax.axvline(peak_freq, color='red', linestyle='--', linewidth=1, alpha=0.6)
            ax.text(peak_freq, max(fft_mag) * 0.9, f'{peak_freq:.2f} Hz',
                   fontsize=8, color='red', ha='left')

    axes[-1].set_xlabel('Frequency (Hz)', fontsize=9)
    axes[-1].set_xlim(0, fs / 2)
    fig.suptitle(title, fontsize=12, fontweight='bold', y=0.995)
    fig.tight_layout()
    return png_b64_from_plt(fig)

def plot_spectrogram(data: np.ndarray, title: str, fs: float = 24.0) -> str:
    """Plot spectrogram for a single channel."""
    if data.ndim > 1:
        data = data[:, 0]  # Use first channel

    fig = plt.figure(figsize=(8, 3.5))
    ax = fig.add_subplot(111)

    # Compute spectrogram
    from matplotlib import mlab
    nperseg = min(64, len(data) // 4)
    spec, freqs, t = mlab.specgram(data, NFFT=nperseg, Fs=fs,
                                    noverlap=nperseg//2, window=np.hanning(nperseg))

    # Plot
    im = ax.pcolormesh(t, freqs, 10 * np.log10(spec + 1e-10), shading='auto', cmap='viridis')
    ax.set_ylabel('Frequency (Hz)', fontsize=10)
    ax.set_xlabel('Time (s)', fontsize=10)
    ax.set_title(title, fontsize=12, fontweight='bold')

    # Add colorbar
    cbar = fig.colorbar(im, ax=ax)
    cbar.set_label('Power (dB)', fontsize=9)

    fig.tight_layout()
    return png_b64_from_plt(fig)


def plot_byte_heatmap(payload: bytes, side: int = 64) -> str:
    """Render a byte-level heatmap preview (used as 'encrypted packet' visualization)."""
    n = side * side
    arr = np.frombuffer(payload[:n], dtype=np.uint8)
    if arr.size < n:
        arr = np.pad(arr, (0, n - arr.size), mode="constant")
    mat = arr.reshape(side, side)

    fig = plt.figure(figsize=(4.6, 2.0))
    ax = fig.add_subplot(111)
    ax.imshow(mat, aspect="auto")
    ax.set_axis_off()
    for sp in ax.spines.values():
        sp.set_visible(False)
    fig.subplots_adjust(left=0, right=1, top=1, bottom=0)

    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=140, bbox_inches="tight", pad_inches=0)
    plt.close(fig)
    return base64.b64encode(buf.getvalue()).decode("utf-8")

def plot_depth(depth: np.ndarray, title: str) -> str:
    fig = plt.figure(figsize=(3.2, 2.4))
    ax = fig.add_subplot(111)
    ax.imshow(depth, cmap="viridis")
    ax.set_title(title, fontsize=11, fontweight="bold")
    ax.axis("off")
    fig.tight_layout()
    return png_b64_from_plt(fig)

def plot_rgb(rgb: np.ndarray, title: str) -> str:
    fig = plt.figure(figsize=(3.2, 2.4))
    ax = fig.add_subplot(111)
    ax.imshow(rgb)
    ax.set_title(title, fontsize=11, fontweight="bold")
    ax.axis("off")
    fig.tight_layout()
    return png_b64_from_plt(fig)

# -----------------------------
# Health report synthesis (demo)
# -----------------------------
def _sigmoid(x: float) -> float:
    return float(1.0 / (1.0 + np.exp(-x)))

def _clamp(x: float, lo: float, hi: float) -> float:
    return float(max(lo, min(hi, x)))

def _dominant_freq_hz(
    series: np.ndarray,
    fs_hz: float,
    band: tuple[float, float],
) -> float:
    """Dominant frequency (Hz) in a band using FFT magnitude."""
    x = np.asarray(series, dtype=float).ravel()
    if x.size < 8 or not np.isfinite(x).all():
        return float("nan")
    x = x - np.mean(x)
    # taper to reduce spectral leakage
    w = np.hanning(x.size)
    xw = x * w
    spec = np.abs(np.fft.rfft(xw))
    freqs = np.fft.rfftfreq(xw.size, d=1.0 / fs_hz)
    lo, hi = band
    m = (freqs >= lo) & (freqs <= hi)
    if not np.any(m):
        return float("nan")
    idx = np.argmax(spec[m])
    return float(freqs[m][idx])

def _series_stats(x: np.ndarray) -> Dict[str, float]:
    v = np.asarray(x, dtype=float).ravel()
    v = v[np.isfinite(v)]
    if v.size == 0:
        return {"mean": float("nan"), "std": float("nan"), "p95": float("nan"), "p05": float("nan")}
    return {
        "mean": float(np.mean(v)),
        "std": float(np.std(v)),
        "p95": float(np.percentile(v, 95)),
        "p05": float(np.percentile(v, 5)),
    }

def build_health_report(
    *,
    results: List[Dict[str, Any]],
    uwb: np.ndarray,
    imu: np.ndarray,
    csi: np.ndarray,
    depth: np.ndarray,
    rgb: np.ndarray,
    seed: int,
) -> Dict[str, Any]:
    """Create a richer, chart-friendly health report (demo output)."""
    rng = np.random.default_rng(seed)

    # Sampling rate assumptions (demo): 240 frames ~ 10s in the simulator -> 24 Hz
    fs = 24.0

    # Representative 1D signals
    csi_series = np.asarray(csi[:, : min(csi.shape[1], 8)].mean(axis=1), dtype=float)
    imu_series = np.asarray(imu[:, 0], dtype=float) if imu.ndim == 2 and imu.shape[1] else np.asarray(imu, dtype=float).ravel()
    uwb_series = np.asarray(uwb[:, : min(uwb.shape[1], 8)].mean(axis=1), dtype=float)

    # Extract vitals (rough demo estimators)
    hr_hz = _dominant_freq_hz(csi_series, fs, (0.8, 3.0))
    rr_hz = _dominant_freq_hz(csi_series, fs, (0.1, 0.55))
    hr_bpm = float("nan") if np.isnan(hr_hz) else hr_hz * 60.0
    rr_bpm = float("nan") if np.isnan(rr_hz) else rr_hz * 60.0

    # IMU cadence proxy
    cad_hz = _dominant_freq_hz(imu_series, fs, (0.5, 3.0))
    cadence_spm = float("nan") if np.isnan(cad_hz) else cad_hz * 60.0
    imu_stats = _series_stats(imu_series)
    gait_var = _clamp(imu_stats["std"] / (abs(imu_stats["mean"]) + 1e-6), 0.0, 3.0)

    # UWB motion proxy (stability / wander)
    uwb_stats = _series_stats(uwb_series)
    uwb_drift = float(np.mean(np.abs(np.diff(uwb_series)))) if uwb_series.size > 2 else 0.0

    # Model scores (from HE tools)
    by_model = {r["model_id"]: r for r in results}
    score_ecg = float(by_model.get("ecg", {}).get("score", 1.0))
    score_bp = float(by_model.get("bp", {}).get("score", 1.0))
    score_sleep = float(by_model.get("sleep", {}).get("score", 1.0))
    score_met = float(by_model.get("metabolic", {}).get("score", 1.0))
    score_risk = float(by_model.get("risk", {}).get("score", 1.0))

    # Map tool scores into 0..1 “risk components” (demo)
    def nrm(v: float, lo: float, hi: float) -> float:
        return _clamp((v - lo) / (hi - lo), 0.0, 1.0)

    cardio_r = nrm(score_ecg, 0.8, 2.2)
    bp_r = nrm(score_bp, 0.8, 2.2)
    sleep_r = nrm(score_sleep, 0.8, 2.2)
    metab_r = nrm(score_met, 0.8, 2.2)
    triage_r = nrm(score_risk, 0.8, 2.2)

    mobility_r = _clamp(0.55 * nrm(gait_var, 0.1, 1.2) + 0.45 * nrm(uwb_drift, 0.0, 0.08), 0.0, 1.0)

    # Fall risk probability (demo)
    raw = (
        1.15 * mobility_r +
        0.55 * triage_r +
        0.35 * cardio_r +
        0.25 * sleep_r +
        0.20 * bp_r
    )
    fall_prob = _sigmoid((raw - 0.85) * 3.4)

    if fall_prob >= 0.70:
        fall_level = "High"
    elif fall_prob >= 0.40:
        fall_level = "Moderate"
    else:
        fall_level = "Low"

    # Convert to demo “clinical-ish” numbers
    # Blood pressure proxy (mmHg): center around 120/80, scale w/ bp_r
    sbp = float(118 + 28 * bp_r + rng.normal(0, 3.0))
    dbp = float(78 + 18 * bp_r + rng.normal(0, 2.0))

    # Sleep efficiency (%): lower if sleep_r higher
    sleep_eff = float(_clamp(90 - 22 * sleep_r + rng.normal(0, 1.8), 55, 98))

    # SpO2 (%): lightly penalize cardio_r (demo)
    spo2 = float(_clamp(98 - 4.5 * cardio_r + rng.normal(0, 0.6), 90, 100))

    # Simple “mobility score” 0..100
    mobility_score = float(_clamp(100 * (1.0 - mobility_r), 0, 100))

    # Small distribution charts (demo)
    # Activity mix (percent) — NOT fall-specific
    activity_labels = ["Walk", "Stand", "Sit", "Sleep"]
    # Create a stable-ish mix influenced by sleep/cardio/metabolic proxies
    base = np.array([0.22, 0.18, 0.35, 0.25], dtype=float)
    tilt = np.array([0.06 * (1.0 - sleep_r), 0.04 * (1.0 - cardio_r), 0.05 * sleep_r, 0.05 * metab_r], dtype=float)
    mix = np.clip(base + tilt + rng.normal(0, 0.015, size=4), 0.05, 0.80)
    mix = mix / mix.sum()

    # Domain radar

    radar_labels = ["Cardio", "BP", "Sleep", "Metabolic", "Recovery", "Safety"]
    radar_values = [
        float(100 * (1.0 - cardio_r)),
        float(100 * (1.0 - bp_r)),
        float(100 * (1.0 - sleep_r)),
        float(100 * (1.0 - metab_r)),
        float(100 * (1.0 - _clamp(0.6 * sleep_r + 0.4 * cardio_r, 0.0, 1.0))),
        float(100 * (1.0 - triage_r)),
    ]

    # Metrics cards
    def metric(name: str, value: float, unit: str, ref: str, status: str, detail: str = "") -> Dict[str, Any]:
        return {
            "name": name,
            "value": None if np.isnan(value) else float(value),
            "unit": unit,
            "ref": ref,
            "status": status,
            "detail": detail,
        }

    def status_by_range(v: float, lo: float, hi: float) -> str:
        if np.isnan(v):
            return "unknown"
        if v < lo:
            return "low"
        if v > hi:
            return "high"
        return "normal"

    metrics = [
        metric("Heart rate", hr_bpm, "bpm", "60–100", status_by_range(hr_bpm, 60, 100), "Derived from CSI rhythm band"),
        metric("Resp. rate", rr_bpm, "rpm", "12–20", status_by_range(rr_bpm, 12, 20), "Low-frequency CSI component"),
        metric("Blood pressure", sbp, "mmHg", "SBP 90–120", status_by_range(sbp, 90, 120), f"DBP ≈ {dbp:.0f} mmHg"),
        metric("SpO₂", spo2, "%", "95–100", status_by_range(spo2, 95, 100), "Cardio proxy + noise"),
        metric("Sleep efficiency", sleep_eff, "%", "≥ 85", "low" if sleep_eff < 85 else "normal", "Depth-based staging proxy"),
        metric("Cadence", cadence_spm, "spm", "90–130", status_by_range(cadence_spm, 90, 130), "IMU step-frequency proxy"),
    ]

    # Alerts (top drivers)
    drivers = []
    if mobility_r > 0.55:
        drivers.append("Increased gait instability / variability")
    if sleep_r > 0.55:
        drivers.append("Suboptimal sleep efficiency pattern")
    if cardio_r > 0.55:
        drivers.append("Elevated cardio rhythm irregularity proxy")
    if bp_r > 0.55:
        drivers.append("Elevated blood-pressure proxy")
    if triage_r > 0.55:
        drivers.append("Higher triage risk score")
    if not drivers:
        drivers.append("No dominant risk drivers detected in this demo cycle")

    # Recommendations (demo)
    recos = [
        "If dizziness or recent falls are present, consider supervised ambulation and a home safety check.",
        "Aim for consistent sleep timing; reduce late caffeine and screen exposure.",
        "Hydration and gradual warm-up may reduce transient gait instability.",
        "This demo report is not medical advice; consult a clinician for interpretation.",
    ]
    if fall_level == "High":
        recos.insert(0, "Fall risk appears high in this demo cycle—prioritize assistive support and remove trip hazards.")
    elif fall_level == "Moderate":
        recos.insert(0, "Fall risk appears moderate—monitor gait stability and consider balance exercises.")

    overall = "Stable"
    if fall_level == "High" or any(m["status"] == "high" for m in metrics):
        overall = "Attention"
    elif fall_level == "Moderate" or any(m["status"] in ("low", "high") for m in metrics):
        overall = "Watch"

    narrative = (
        f"Overall status: {overall}. Fall risk estimate: {fall_level} (p={fall_prob:.2f}).\n"
        f"Key drivers: " + "; ".join(drivers[:3]) + ".\n"
        "\n"
        "Interpretation (demo): Sensor-derived proxies suggest current mobility and physiologic state. "
        "Values are illustrative and should not be used for diagnosis."
    )

    return {
        "overall": overall,
        "disclaimer": "Demo output only — not for medical use.",
        "fall_risk": {
            "probability": float(fall_prob),
            "level": fall_level,
            "drivers": drivers[:4],
        },
        "metrics": metrics,
        "recommendations": recos,
        "narrative": narrative,
        "charts": {
            "activity_mix": {"labels": activity_labels, "values": [float(x) for x in mix.tolist()]},
            "radar": {"labels": radar_labels, "values": [float(x) for x in radar_values]},
            "sparklines": {
                "uwb": [float(x) for x in uwb_series[:120].tolist()],
                "imu": [float(x) for x in imu_series[:120].tolist()],
                "csi": [float(x) for x in csi_series[:120].tolist()],
            },
            "vitals": {
                "labels": ["HR", "RR", "SBP", "SpO₂", "SleepEff", "Cadence"],
                "values": [
                    float(hr_bpm if not np.isnan(hr_bpm) else 0.0),
                    float(rr_bpm if not np.isnan(rr_bpm) else 0.0),
                    float(sbp),
                    float(spo2),
                    float(sleep_eff),
                    float(cadence_spm if not np.isnan(cadence_spm) else 0.0),
                ],
                "ranges": {
                    "HR": [60, 100],
                    "RR": [12, 20],
                    "SBP": [90, 120],
                    "SpO2": [95, 100],
                    "SleepEff": [85, 100],
                    "Cadence": [90, 130],
                },
            },
        },
    }

def excerpt_array(arr: np.ndarray, rows: int = 4, cols: int = 4) -> str:
    sl = arr[:rows, :cols]
    return "\n".join(["[" + ", ".join([f"{x:+.3f}" for x in row]) + "]" for row in sl])

def feat_from_series(X: np.ndarray) -> np.ndarray:
    m = X.mean(axis=0)
    s = X.std(axis=0)
    mn = X.min(axis=0)
    mx = X.max(axis=0)
    feats = np.array([
        float(m.mean()),
        float(s.mean()),
        float(mn.mean()),
        float(mx.mean()),
        float(np.mean(np.abs(X))),
        float(np.mean(np.diff(X[:, 0]))),
        float(np.mean(np.square(X))),
        float(np.percentile(X, 90)),
    ])
    return feats

def feat_from_depth(D: np.ndarray) -> np.ndarray:
    gx, gy = np.gradient(D)
    feats = np.array([
        float(D.mean()),
        float(D.std()),
        float(D.min()),
        float(D.max()),
        float(np.mean(np.abs(gx))),
        float(np.mean(np.abs(gy))),
        float(np.percentile(D, 90)),
        float(np.percentile(D, 10)),
    ])
    return feats

def feat_from_rgb(R: np.ndarray) -> np.ndarray:
    ch_mean = R.reshape(-1, 3).mean(axis=0)
    ch_std = R.reshape(-1, 3).std(axis=0)
    feats = np.array([
        float(ch_mean[0]), float(ch_mean[1]), float(ch_mean[2]),
        float(ch_std[0]), float(ch_std[1]),
        float(R.min()), float(R.max()),
        float(np.percentile(R, 90)),
    ])
    return feats

CLUSTER_MODELS = [
    {"id": "ecg", "title": "ECG Arrhythmia", "subtitle": "CSI Heart Pattern"},
    {"id": "bp", "title": "Blood Pressure", "subtitle": "UWB Regression"},
    {"id": "sleep", "title": "Sleep Staging", "subtitle": "Depth-based Model"},
    {"id": "metabolic", "title": "Metabolic Score", "subtitle": "IMU Proxy"},
    {"id": "risk", "title": "Risk Assessment", "subtitle": "RGB Triage"},
    {"id": "anomaly", "title": "Anomaly Check", "subtitle": "Cross-modality"},
]

DEFAULT_ASSIGNMENTS = [
    {"input_modality": "CSI", "model_id": "ecg", "tool": "secure_ecg_toolbox"},
    {"input_modality": "UWB", "model_id": "bp", "tool": "secure_bp_toolbox"},
    {"input_modality": "Depth", "model_id": "sleep", "tool": "secure_sleep_toolbox"},
    {"input_modality": "IMU", "model_id": "metabolic", "tool": "secure_metabolic_toolbox"},
    {"input_modality": "RGB", "model_id": "risk", "tool": "secure_risk_toolbox"},
]

async def llm_dispatch_plan(llm: AsyncOpenAI, model_name: str) -> List[Dict[str, str]]:
    system = "You are a scheduler. Return a JSON array assigning each modality to one model/tool. No extra text."
    user = {
        "modalities": ["Depth", "UWB", "IMU", "CSI", "RGB"],
        "cluster_models": CLUSTER_MODELS,
        "available_tools": [
            "secure_ecg_toolbox",
            "secure_bp_toolbox",
            "secure_sleep_toolbox",
            "secure_metabolic_toolbox",
            "secure_risk_toolbox",
            "secure_anomaly_toolbox",
        ],
        "constraints": "Use exactly five assignments (one per modality). Prefer intuitive mapping.",
        "output_schema": [{"input_modality": "Depth", "model_id": "sleep", "tool": "secure_sleep_toolbox"}],
    }
    resp = await llm.chat.completions.create(
        model=model_name,
        messages=[{"role": "system", "content": system}, {"role": "user", "content": json.dumps(user)}],
        temperature=0.2,
    )
    txt = resp.choices[0].message.content or ""
    try:
        arr = json.loads(txt)
        if isinstance(arr, list):
            out = []
            seen = set()
            for it in arr:
                if not isinstance(it, dict):
                    continue
                mod = str(it.get("input_modality", "")).strip()
                tool = str(it.get("tool", "")).strip()
                mid = str(it.get("model_id", "")).strip()
                if mod and tool and mid and mod not in seen:
                    seen.add(mod)
                    out.append({"input_modality": mod, "model_id": mid, "tool": tool})
            if len(out) == 5:
                return out
    except Exception:
        pass
    return DEFAULT_ASSIGNMENTS

async def run_mcp_inference(pub_ctx_path: str, enc_inputs: Dict[str, str], assignments: List[Dict[str, str]]) -> Dict[str, Any]:
    server_params = StdioServerParameters(command=sys.executable, args=[SERVER_PY], env=None)
    t0 = time.perf_counter()

    outputs: Dict[str, str] = {}
    tool_times: List[Dict[str, Any]] = []

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            for a in assignments:
                tool = a["tool"]
                modality = a["input_modality"]
                enc_in = enc_inputs[modality]
                out_path = os.path.join(tempfile.gettempdir(), f"he_out_{modality}_{int(time.time()*1000)}.bin")

                args = {"context_path": pub_ctx_path, "data_path": enc_in, "output_path": out_path}

                tt0 = time.perf_counter()
                await session.call_tool(tool, arguments=args)
                tt1 = time.perf_counter()

                outputs[modality] = out_path
                tool_times.append({"tool": tool, "input_modality": modality, "time_sec": (tt1 - tt0)})

    t1 = time.perf_counter()
    return {"outputs": outputs, "tool_times": tool_times, "time_sec": (t1 - t0)}


def _strip_markdown(s: str) -> str:
    # remove common markdown emphasis / code markers
    s = s.replace("**", "").replace("*", "")
    s = s.replace("`", "")
    # remove markdown headings and list markers
    lines = []
    for ln in s.splitlines():
        ln2 = re.sub(r"^\s{0,3}#{1,6}\s*", "", ln)           # headings
        ln2 = re.sub(r"^\s*[-•*+]\s+", "", ln2)             # bullets
        ln2 = ln2.strip()
        if ln2:
            lines.append(ln2)
    return "\n".join(lines).strip()

def _extract_conclusion(text: str) -> str:
    t = _strip_markdown(text)
    if not t:
        return "—"
    # try to extract content after a 'Conclusion' marker
    lines = t.splitlines()
    for i, ln in enumerate(lines):
        if re.search(r"(?i)\bconclusion\b", ln):
            # if 'Conclusion: ...' in same line, keep after colon
            after = re.split(r"(?i)\bconclusion\b\s*[:：]?", ln, maxsplit=1)
            chunk = after[1].strip() if len(after) > 1 else ""
            tail = []
            if chunk:
                tail.append(chunk)
            # also include following non-empty lines until a section-like line
            for j in range(i + 1, len(lines)):
                if re.search(r"(?i)\b(summary|assessment|recommendation|impression)\b\s*[:：]?", lines[j]):
                    break
                tail.append(lines[j])
                if len(" ".join(tail)) > 420:
                    break
            out = " ".join(tail).strip()
            return out if out else "—"
    # fallback: last 1-2 lines as a concluding statement
    tail = lines[-2:] if len(lines) >= 2 else lines[-1:]
    return " ".join(tail).strip() or "—"

async def generate_report_conclusion(llm: Optional[AsyncOpenAI], model_name: str, results: List[Dict[str, Any]]) -> str:
    # Return ONLY a plain-text conclusion (no markdown markers), for UI display.
    if llm is None:
        highs = [r for r in results if r.get("status") == "high"]
        elevs = [r for r in results if r.get("status") == "elevated"]
        if not highs and not elevs:
            return "Overall indicators appear within normal ranges in this demo cycle. This output is for demonstration only and not for medical use."
        focus = []
        for r in (highs + elevs)[:3]:
            focus.append(f"{r['model']} ({r['input_modality']}: {r['status']}, score {r['score']:.2f})")
        return "Overall risk appears elevated in some modalities: " + "; ".join(focus) + ". This output is for demonstration only and not for medical use."

    system = "Write ONLY the Conclusion section of a medical report in plain text. No markdown, no bullets, no headings. 1-3 sentences."
    user = {"results": results, "notes": "Demo only. Do not claim diagnosis with certainty. Use cautious language."}
    resp = await llm.chat.completions.create(
        model=model_name,
        messages=[{"role": "system", "content": system}, {"role": "user", "content": json.dumps(user)}],
        temperature=0.3,
    )
    raw = (resp.choices[0].message.content or "").strip()
    return _extract_conclusion(raw)
@app.get("/api/health")
def health():
    return {"ok": True}

@app.get("/api/cycle")
async def api_cycle():
    cycle_seed = int(time.time())
    t_cycle0 = time.perf_counter()

    # Step 1
    t1_0 = time.perf_counter()
    frames = 240

    # Real data (from txt) + user images
    uwb_raw = get_data("UWB")
    imu_raw = get_data("IMU")

    # slice windows (wrap via cycle_seed to vary slightly across refreshes)
    def _window(mat: np.ndarray, n: int, cols: Optional[int] = None) -> np.ndarray:
        if mat.ndim == 1:
            mat2 = mat.reshape(-1, 1)
        else:
            mat2 = mat
        r = mat2.shape[0]
        if r <= n:
            out = mat2
        else:
            start = (cycle_seed % (r - n))
            out = mat2[start:start + n]
        if cols is not None and out.shape[1] > cols:
            out = out[:, :cols]
        return out

    uwb = _window(uwb_raw, frames)
    imu = _window(imu_raw, frames)

    # Load real CSI data from FL-Datasets-for-HAR
    try:
        csi_raw = get_data("CSI")
        csi = _window(csi_raw, frames, cols=8)  # Limit to 8 columns for compatibility
    except Exception as e:
        print(f"Warning: Could not load CSI data, falling back to simulation: {e}")
        csi = sim_timeseries(frames, 8, seed=cycle_seed + 33)

    # Prefer user-provided deep2.png / RGB.png (or pre-generated placeholders)
    depth_preview_b64 = png_b64_from_file(DEPTH_PNG_PATH)
    rgb_preview_b64 = png_b64_from_file(RGB_PNG_PATH)
    if depth_preview_b64 is None:
        depth = sim_depth(seed=cycle_seed + 44)
        depth_preview_b64 = plot_depth(depth, "Depth (plaintext)")
    else:
        # for feature extraction, synthesize a depth matrix from the preview image
        depth_img = mpimg.imread(DEPTH_PNG_PATH)
        if depth_img.ndim == 3:
            depth = depth_img[..., 0]
        else:
            depth = depth_img

    if rgb_preview_b64 is None:
        rgb = sim_rgb(seed=cycle_seed + 55)
        rgb_preview_b64 = plot_rgb(rgb, "RGB (plaintext)")
    else:
        rgb = mpimg.imread(RGB_PNG_PATH)
        if rgb.ndim == 2:
            rgb = np.stack([rgb, rgb, rgb], axis=-1)
        rgb = np.clip(rgb[..., :3], 0, 1)

    # For UWB/IMU, plot an aggregate single-channel signal for quick preview.
    uwb_series = uwb[:, : min(uwb.shape[1], 8)].mean(axis=1)
    imu_series = imu[:, 0] if imu.shape[1] else imu[:, 0]

    
    # Byte-level 'encrypted packet' visualization (demo): XOR float32 bytes with a random mask
    rng_local = np.random.default_rng(cycle_seed + 777)
    raw_bytes = np.asarray(csi, dtype=np.float32).tobytes()
    mask = rng_local.integers(0, 256, size=min(len(raw_bytes), 4096), dtype=np.uint8)
    enc_bytes = (np.frombuffer(raw_bytes[:mask.size], dtype=np.uint8) ^ mask).tobytes()
    enc_preview_b64 = plot_byte_heatmap(enc_bytes, side=64)

    # Generate FFT spectrum plots only (no time-series)
    uwb_fft_png = plot_fft_spectrum(uwb, "UWB Frequency Spectrum", fs=24.0)
    imu_fft_png = plot_fft_spectrum(imu, "IMU Frequency Spectrum", fs=24.0)
    csi_fft_png = plot_fft_spectrum(csi, "CSI Frequency Spectrum", fs=24.0)
    csi_spectrogram_png = plot_spectrogram(csi, "CSI Spectrogram", fs=24.0)

    step1_modalities = {
            "Depth": {
                "kind": "image",
                "shape": str(getattr(depth, "shape", "image")),
                "preview_png": depth_preview_b64,
                "plaintext_excerpt": f"mean={float(np.mean(depth)):.3f}, std={float(np.std(depth)):.3f}, min={float(np.min(depth)):.3f}, max={float(np.max(depth)):.3f}",
            },
            "UWB": {
                "kind": "timeseries",
                "shape": f"{uwb.shape[0]}x{uwb.shape[1]}",
                "preview_png": plot_sparkline(uwb_series),
                "plaintext_excerpt": excerpt_array(uwb, rows=4, cols=min(6, uwb.shape[1])),
                "fft_png": uwb_fft_png,
            },
            "IMU": {
                "kind": "timeseries",
                "shape": f"{imu.shape[0]}x{imu.shape[1]}",
                "preview_png": plot_sparkline(imu_series),
                "plaintext_excerpt": excerpt_array(imu, rows=4, cols=min(6, imu.shape[1])),
                "fft_png": imu_fft_png,
            },
            "CSI": {
                "kind": "timeseries",
                "shape": f"{csi.shape[0]}x{csi.shape[1]}",
                "preview_png": plot_sparkline(csi),
                "plaintext_excerpt": excerpt_array(csi, rows=4, cols=min(4, csi.shape[1])),
                "fft_png": csi_fft_png,
                "spectrogram_png": csi_spectrogram_png,
            },
            "Encrypted": {
                "kind": "cipher/bytes",
                "shape": "64x64 bytes",
                "preview_png": enc_preview_b64,
                "plaintext_excerpt": "Encrypted packet visualization (byte heatmap)",
            },
            "RGB": {
                "kind": "image",
                "shape": str(getattr(rgb, "shape", "image")),
                "preview_png": rgb_preview_b64,
                "plaintext_excerpt": f"mean={float(np.mean(rgb)):.3f}, std={float(np.std(rgb)):.3f}, min={float(np.min(rgb)):.3f}, max={float(np.max(rgb)):.3f}",
            },
        }
    
    t1_1 = time.perf_counter()
    step1_time = t1_1 - t1_0

    # Step 2
    t2_0 = time.perf_counter()
    ctx = setup_context()
    pub_ctx_path = os.path.join(tempfile.gettempdir(), f"he_pub_{int(time.time()*1000)}.bin")
    with open(pub_ctx_path, "wb") as f:
        f.write(make_public_context_bytes(ctx))

    feats = {
        "Depth": feat_from_depth(depth),
        "UWB": feat_from_series(uwb),
        "IMU": feat_from_series(imu),
        "CSI": feat_from_series(csi),
        "RGB": feat_from_rgb(rgb),
    }

    enc_inputs: Dict[str, str] = {}
    for mod, vec in feats.items():
        enc = ts.ckks_vector(ctx, vec.tolist())
        p = os.path.join(tempfile.gettempdir(), f"he_in_{mod}_{int(time.time()*1000)}.bin")
        with open(p, "wb") as f:
            f.write(enc.serialize())
        enc_inputs[mod] = p


    # Step 1 UI: add a tiny ciphertext snippet per modality (feature-vector ciphertext)
    for mod, pth in enc_inputs.items():
        try:
            with open(pth, "rb") as f:
                ct_head = f.read(32)  # small excerpt only
            if mod in step1_modalities:
                step1_modalities[mod]["ciphertext_excerpt"] = bytes_preview(ct_head, 32)
        except Exception:
            if mod in step1_modalities:
                step1_modalities[mod]["ciphertext_excerpt"] = "—"

    llm = _llm_client_from_env()
    model_name = os.getenv("DEEPSEEK_MODEL") or os.getenv("LLM_MODEL") or "deepseek-chat"
    llm_time = 0.0
    assignments = DEFAULT_ASSIGNMENTS

    if llm is not None:
        t_llm0 = time.perf_counter()
        assignments = await llm_dispatch_plan(llm, model_name)
        t_llm1 = time.perf_counter()
        llm_time = t_llm1 - t_llm0

    infer = await run_mcp_inference(pub_ctx_path, enc_inputs, assignments)

    agg_bytes = b""
    for _, out_path in infer["outputs"].items():
        with open(out_path, "rb") as f:
            agg_bytes += f.read(64)

    t2_1 = time.perf_counter()
    step2_time = t2_1 - t2_0

    # Step 3
    t3_0 = time.perf_counter()
    results = []

    for a in assignments:
        mod = a["input_modality"]
        out_path = infer["outputs"][mod]
        with open(out_path, "rb") as f:
            out_ct = ts.ckks_vector_from(ctx, f.read())
        val = float(out_ct.decrypt()[0])

        status = "normal"
        if val > 1.2:
            status = "elevated"
        if val > 1.8:
            status = "high"

        model_meta = next((m for m in CLUSTER_MODELS if m["id"] == a["model_id"]), None)
        ui_name = model_meta["title"] if model_meta else a["model_id"]

        results.append({
            "model_id": a["model_id"],
            "model": ui_name,
            "input_modality": mod,
            "tool": a["tool"],
            "score": val,
            "status": status,
        })

    report_conclusion = await generate_report_conclusion(llm, model_name, results)

    # Rich report payload for the UI (charts + metrics). This is synthetic/demo output.
    report = build_health_report(
        results=results,
        uwb=uwb,
        imu=imu,
        csi=csi,
        depth=depth,
        rgb=rgb,
        seed=cycle_seed,
    )

    t3_1 = time.perf_counter()
    step3_time = t3_1 - t3_0

    t_cycle1 = time.perf_counter()

    summary = ", ".join([f"{a['input_modality']}→{a['tool']}" for a in assignments])

    return {
        "schema": "he-multimodal-cycle/v1",
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "cycle_time_sec": (t_cycle1 - t_cycle0),
        "step1": {"time_sec": step1_time, "modalities": step1_modalities},
        "step2": {
            "time_sec": step2_time,
            "llm_time_sec": llm_time,
            "summary": summary,
            "cluster_models": CLUSTER_MODELS,
            "assignments": assignments,
            "tool_times": infer["tool_times"],
            "aggregate_cipher_preview": bytes_preview(agg_bytes, 160),
        },
        "step3": {
            "time_sec": step3_time,
            "results": results,
            "report_conclusion": report_conclusion,
            "report": report,
        },
    }
