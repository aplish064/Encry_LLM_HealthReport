#!/usr/bin/env python3
"""
完整版后端 - 恢复所有原始功能
端口8082，使用UT_HAR数据集，集成智谱AI
"""
import os
import json
import time
import base64
import tempfile
from io import BytesIO
from typing import Dict, Any, Optional, List
from functools import lru_cache
import asyncio
from concurrent.futures import ThreadPoolExecutor
import numpy as np
import tenseal as ts
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

DATA_PATHS = {
    "UWB": os.path.join(BASE_DIR, "test_data", "uwb_from_utar.txt"),
    "IMU": os.path.join(BASE_DIR, "test_data", "imu_from_utar.txt"),
    "CSI": os.path.join(BASE_DIR, "test_data", "csi_from_utar.csv"),
}

ASSET_USER_DIR = os.path.join(BASE_DIR, "frontend", "assets", "user")
DEPTH_PNG_PATH = os.path.join(ASSET_USER_DIR, "deep2.png")
RGB_PNG_PATH = os.path.join(ASSET_USER_DIR, "RGB.png")

_DATA_CACHE: Dict[str, np.ndarray] = {}
_THUMBNAIL_CACHE: Dict[str, str] = {}  # Cache for generated thumbnails
MODALITY_CONFIG = {
    "Depth": {"enabled": True, "file": DEPTH_PNG_PATH},
    "UWB": {"enabled": True, "file": DATA_PATHS["UWB"]},
    "IMU": {"enabled": True, "file": DATA_PATHS["IMU"]},
    "CSI": {"enabled": True, "file": DATA_PATHS["CSI"]},
    "RGB": {"enabled": True, "file": RGB_PNG_PATH},
}

# Thread pool for parallel processing
executor = ThreadPoolExecutor(max_workers=4)

# 智谱AI配置
ZHIPU_API_KEY = "3e53672cccc548629e749d7436098975.yVFwqfG0ATQ69Ro4"
ZHIPU_API_URL = "https://open.bigmodel.cn/api/anthropic/v1/messages"

# 模型集群配置
CLUSTER_MODELS = [
    {"id": "ecg", "title": "ECG Arrhythmia", "subtitle": "CSI Heart Pattern"},
    {"id": "bp", "title": "Blood Pressure", "subtitle": "UWB Regression"},
    {"id": "sleep", "title": "Sleep Staging", "subtitle": "Depth-based Model"},
    {"id": "metabolic", "title": "Metabolic Score", "subtitle": "IMU Proxy"},
    {"id": "risk", "title": "Risk Assessment", "subtitle": "RGB Triage"},
]

app = FastAPI(title="Secure Multimodal HE + LLM Demo", version="3.1")

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

def generate_thumbnail(data: np.ndarray, modality_type: str, size=(64, 64)) -> str:
    """生成预览缩略图（带缓存）"""
    # 创建缓存键
    cache_key = f"{modality_type}_{data.shape}_{size}"

    # 检查缓存
    if cache_key in _THUMBNAIL_CACHE:
        return _THUMBNAIL_CACHE[cache_key]

    try:
        fig = plt.figure(figsize=(size[0]/100, size[1]/100), dpi=100)

        if modality_type == 'timeseries':
            # 时序数据：显示前50个点
            if data.ndim == 1:
                plt.plot(data[:50], linewidth=1, color='#3b82f6')
            else:
                plt.plot(data[:50, 0], linewidth=1, color='#3b82f6')
        elif modality_type == 'skeleton':
            # 骨骼数据：显示简单轮廓
            plt.scatter(data[::3], data[1::3], c='#3b82f6', s=10)
        elif modality_type in ['image', 'medical_image']:
            # 图像数据：调整大小显示
            from PIL import Image
            if data.ndim == 3:
                img = data[0] if data.shape[0] < 100 else data
            else:
                img = data
            img_pil = Image.fromarray((img * 255).astype(np.uint8))
            img_pil = img_pil.resize(size)
            plt.imshow(img_pil, cmap='gray')

        plt.axis('off')
        plt.tight_layout(pad=0)

        result = png_b64_from_plt(fig)

        # 缓存结果
        _THUMBNAIL_CACHE[cache_key] = result

        return result
    except Exception as e:
        print(f"缩略图生成失败: {e}")
        return ""

def png_b64_from_file(path: str) -> Optional[str]:
    """Load and convert image file to base64 with caching."""
    if path in _THUMBNAIL_CACHE:
        return _THUMBNAIL_CACHE[path]

    try:
        with open(path, "rb") as f:
            result = b64e(f.read())
            _THUMBNAIL_CACHE[path] = result
            return result
    except Exception:
        return None

@lru_cache(maxsize=1)
def load_modality_config() -> Dict[str, Any]:
    """Load modality configuration from modality_config.json or return default config.
    Uses LRU cache to avoid repeated file reads.
    """
    config_path = os.path.join(BASE_DIR, "backend", "modality_config.json")
    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
                # Convert from list format to dict format
                if "modalities" in config and isinstance(config["modalities"], list):
                    modality_dict = {}
                    for mod in config["modalities"]:
                        modality_dict[mod["name"]] = {
                            "enabled": True,
                            "type": mod.get("type", "sensor"),
                            "id": mod.get("id", ""),
                            "description": mod.get("description", ""),
                            "icon": mod.get("icon", "")
                        }
                    return modality_dict
                return config.get("modalities", MODALITY_CONFIG)
        except Exception as e:
            print(f"Warning: Failed to load config from {config_path}: {e}")
            return MODALITY_CONFIG
    return MODALITY_CONFIG

def _load_csv_matrix(path: str) -> np.ndarray:
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        first = f.readline().strip()
    if not first:
        return np.empty((0, 0), dtype=float)
    if "," in first:
        if first.startswith("t,") or "c0" in first:
            return np.loadtxt(path, delimiter=",", skiprows=1, dtype=float)
        return np.loadtxt(path, delimiter=",", dtype=float)
    return np.loadtxt(path, delimiter=None, dtype=float)

def get_data(name: str) -> np.ndarray:
    if name in _DATA_CACHE:
        return _DATA_CACHE[name]
    p = DATA_PATHS.get(name)
    if not p or not os.path.exists(p):
        raise FileNotFoundError(f"Missing data file for {name}: {p}")
    arr = _load_csv_matrix(p)

    # 处理特定数据格式的reshape
    if name == "UWB":
        # UWB: 600 -> (200, 3)
        if arr.ndim == 1:
            arr = arr.reshape(-1, 3)
    elif name == "IMU":
        # IMU: 1500 -> (250, 6)
        if arr.ndim == 1:
            arr = arr.reshape(-1, 6)
    elif name == "CSI":
        # CSI: (200, 9) -> (200, 8)，去除时间列
        if arr.ndim == 2 and arr.shape[1] > 8:
            arr = arr[:, 1:9]  # 取后8列

    _DATA_CACHE[name] = arr
    return arr

def bytes_preview(b: bytes, n: int = 160) -> str:
    """生成字节预览（十六进制）"""
    return b[:n].hex()

def excerpt_array(arr: np.ndarray, rows: int = 4, cols: int = 6) -> str:
    """生成数组摘要文本 - 原始风格"""
    if arr.ndim == 1:
        arr = arr.reshape(-1, 1)

    rows = min(rows, arr.shape[0])
    cols = min(cols, arr.shape[1])

    excerpt_parts = []
    for i in range(rows):
        row_vals = arr[i, :cols]
        row_str = "[" + ", ".join([f"{x:+.3f}" for x in row_vals]) + "]"
        excerpt_parts.append(row_str)

    if arr.shape[0] > rows:
        excerpt_parts.append("...")
    return "\n".join(excerpt_parts)

def plot_multichannel_preview(data: np.ndarray, title: str, max_channels: int = 6) -> str:
    """生成多通道预览图 - 完全重构版"""
    if data.ndim == 1:
        data = data.reshape(-1, 1)

    n_channels = min(data.shape[1], max_channels)

    # 根据通道数选择最优布局
    if n_channels <= 3:
        # 少量通道：叠加显示 + 统计信息
        fig, (ax_main, ax_stats) = plt.subplots(2, 1, figsize=(10, 5),
                                                    gridspec_kw={'height_ratios': [3, 1]})
        colors = ['#3b82f6', '#8b5cf6', '#ec4899']

        # 主图：多通道叠加
        for i in range(n_channels):
            channel = data[:, i]
            mean_val = np.mean(channel)
            ax_main.plot(channel, linewidth=1.5, color=colors[i], label=f'Ch{i+1}', alpha=0.8)
            ax_main.axhline(mean_val, color=colors[i], linestyle='--', linewidth=1, alpha=0.5)

        ax_main.set_title(title, fontsize=12, fontweight='bold')
        ax_main.set_xlabel("Time (frames)", fontsize=10)
        ax_main.set_ylabel("Amplitude", fontsize=10)
        ax_main.legend(fontsize=9, loc='upper right', framealpha=0.9)
        ax_main.grid(True, alpha=0.3, linestyle='--')

        # 统计图：条形图
        means = [np.mean(data[:, i]) for i in range(n_channels)]
        stds = [np.std(data[:, i]) for i in range(n_channels)]
        x_pos = np.arange(n_channels)

        bars = ax_stats.bar(x_pos, means, yerr=stds, capsize=5,
                          color=colors[:n_channels], alpha=0.7, edgecolor='black', linewidth=1)
        ax_stats.set_ylabel("Mean ± Std", fontsize=10)
        ax_stats.set_xticks(x_pos)
        ax_stats.set_xticklabels([f'Ch{i+1}' for i in range(n_channels)], fontsize=9)
        ax_stats.set_title("Statistical Summary", fontsize=10, fontweight='bold')
        ax_stats.grid(True, alpha=0.3, axis='y')

        # 添加数值标注
        for i, (bar, mean) in enumerate(zip(bars, means)):
            height = bar.get_height()
            ax_stats.text(bar.get_x() + bar.get_width()/2., height,
                        f'{mean:.2f}', ha='center', va='bottom', fontsize=8)

    elif n_channels <= 6:
        # 中等通道：子图网格布局
        n_rows = 2
        n_cols = 3
        fig, axes = plt.subplots(n_rows, n_cols, figsize=(14, 8))
        axes = axes.flatten()

        colors = ['#3b82f6', '#8b5cf6', '#ec4899', '#f59e0b', '#10b981', '#ef4444']

        for i in range(n_channels):
            ax = axes[i]
            channel = data[:, i]
            mean_val = np.mean(channel)
            std_val = np.std(channel)
            min_val = np.min(channel)
            max_val = np.max(channel)

            # 绘制数据
            ax.plot(channel, linewidth=1.5, color=colors[i], alpha=0.8, label=f'Ch{i+1}')
            ax.axhline(mean_val, color='red', linestyle='--', linewidth=1.5, alpha=0.6)

            # 填充区域（包络线）
            ax.fill_between(range(len(channel)), min_val, max_val, alpha=0.15, color=colors[i])

            # 统计信息
            stats_box = f'μ={mean_val:.2f}\nσ={std_val:.2f}\n[{min_val:.2f}, {max_val:.2f}]'
            ax.text(0.98, 0.02, stats_box, transform=ax.transAxes,
                   fontsize=9, verticalalignment='bottom', horizontalalignment='right',
                   bbox=dict(boxstyle='round', facecolor='white', alpha=0.8, edgecolor='gray'),
                   family='monospace')

            ax.set_title(f'Channel {i+1}', fontsize=10, fontweight='bold')
            ax.set_xlabel("Time", fontsize=8)
            ax.set_ylabel("Amplitude", fontsize=8)
            ax.grid(True, alpha=0.25, linestyle='--')
            ax.legend(fontsize=8, loc='upper right')

        fig.suptitle(title, fontsize=14, fontweight='bold', y=0.98)

    else:
        # 多通道：选择性显示 + 聚焦分析
        selected_channels = 6
        step = max(1, n_channels // selected_channels)
        selected_indices = list(range(0, n_channels, step))[:selected_channels]

        fig = plt.figure(figsize=(14, 8))
        gs = fig.add_gridspec(2, 2, hspace=0.3, wspace=0.3)

        # 主图：选择的通道
        ax_main = fig.add_subplot(gs[0, :])
        # 使用matplotlib的颜色映射而不是plt.cm
        colors = ['#3b82f6', '#8b5cf6', '#ec4899', '#f59e0b', '#10b981', '#ef4444']
        if len(selected_indices) > len(colors):
            # 如果选择的通道多于预定义颜色，使用viridis colormap
            import matplotlib.cm as cm
            colors = [cm.viridis(i / len(selected_indices)) for i in range(len(selected_indices))]

        for idx, i in enumerate(selected_indices):
            channel = data[:, i]
            mean_val = np.mean(channel)
            ax_main.plot(channel, linewidth=1.5, color=colors[idx], alpha=0.8,
                       label=f'Ch{i+1} (μ={mean_val:.2f})')

        ax_main.set_title(f"{title} (showing {len(selected_indices)} of {n_channels} channels)",
                        fontsize=12, fontweight='bold')
        ax_main.set_xlabel("Time (frames)", fontsize=10)
        ax_main.set_ylabel("Amplitude", fontsize=10)
        ax_main.legend(fontsize=9, loc='upper right', ncol=2, framealpha=0.9)
        ax_main.grid(True, alpha=0.3, linestyle='--')

        # 统计对比
        ax_stats = fig.add_subplot(gs[1, 0])
        means = [np.mean(data[:, i]) for i in selected_indices]
        stds = [np.std(data[:, i]) for i in selected_indices]
        x_pos = np.arange(len(selected_indices))

        # 为每个条形使用单独的颜色
        bar_colors = colors[:len(selected_indices)]
        ax_stats.bar(x_pos, means, yerr=stds, capsize=5,
                     color=bar_colors, alpha=0.7, edgecolor='black', linewidth=1)
        ax_stats.set_ylabel("Mean ± Std", fontsize=10)
        ax_stats.set_xticks(x_pos)
        ax_stats.set_xticklabels([f'Ch{i+1}' for i in selected_indices], fontsize=9)
        ax_stats.set_title("Statistical Comparison", fontsize=11, fontweight='bold')
        ax_stats.grid(True, alpha=0.3, axis='y')

        # 相关性热图
        ax_corr = fig.add_subplot(gs[1, 1])
        selected_data = data[:, selected_indices].T
        corr_matrix = np.corrcoef(selected_data)

        im = ax_corr.imshow(corr_matrix, cmap='RdBu_r', vmin=-1, vmax=1, aspect='auto')
        ax_corr.set_xticks(range(len(selected_indices)))
        ax_corr.set_yticks(range(len(selected_indices)))
        ax_corr.set_xticklabels([f'Ch{i+1}' for i in selected_indices], fontsize=8)
        ax_corr.set_yticklabels([f'Ch{i+1}' for i in selected_indices], fontsize=8)
        ax_corr.set_title("Channel Correlation", fontsize=11, fontweight='bold')

        # 添加相关系数标注
        for i in range(len(selected_indices)):
            for j in range(len(selected_indices)):
                val = corr_matrix[i, j]
                # 根据相关系数值选择文本颜色
                text_color = 'black' if abs(val) < 0.5 else 'white'
                text = ax_corr.text(j, i, f'{val:.2f}',
                                  ha="center", va="center", fontsize=7, color=text_color,
                                  fontweight='bold')

        plt.colorbar(im, ax=ax_corr, label='Correlation')

    plt.tight_layout()
    return png_b64_from_plt(fig)

def plot_fft_spectrum(data: np.ndarray, title: str, fs: float = 24.0, max_channels: int = 4) -> str:
    """绘制增强的FFT频谱图 - 添加交互式峰值标注"""
    if data.ndim == 1:
        data = data.reshape(-1, 1)

    n_channels = min(data.shape[1], max_channels)

    # 根据通道数选择布局
    if n_channels <= 3:
        # 少量通道：垂直排列 + 详细标注
        fig, axes = plt.subplots(n_channels, 1, figsize=(10, 3 * n_channels), sharex=True)

        if n_channels == 1:
            axes = [axes]

        colors = ['#3b82f6', '#8b5cf6', '#ec4899']

        for i in range(n_channels):
            ax = axes[i]
            signal = data[:, i]
            signal = signal - np.mean(signal)
            window = np.hanning(len(signal))
            signal_windowed = signal * window

            fft_result = np.fft.fft(signal_windowed)
            freqs = np.fft.fftfreq(len(signal), 1/fs)
            magnitude = np.abs(fft_result)[:len(freqs)//2]

            # 绘制频谱
            ax.plot(freqs[:len(freqs)//2], magnitude, linewidth=2, color=colors[i], alpha=0.8)
            ax.fill_between(freqs[:len(freqs)//2], 0, magnitude, alpha=0.3, color=colors[i])

            # 找峰值并标注
            peak_idx = np.argmax(magnitude)
            peak_freq = freqs[peak_idx]
            peak_mag = magnitude[peak_idx]

            ax.plot(peak_freq, peak_mag, 'ro', markersize=8, markeredgecolor='white', markeredgewidth=2)
            ax.annotate(f'Peak: {peak_freq:.2f}Hz\n({peak_mag:.1f})',
                       xy=(peak_freq, peak_mag), xytext=(10, 10),
                       textcoords='offset points', fontsize=9, fontweight='bold',
                       bbox=dict(boxstyle='round,pad=0.3', facecolor='yellow', alpha=0.7),
                       arrowprops=dict(arrowstyle='->', color='red', lw=1.5))

            # 添加频率范围标注
            ax.axvspan(0.5, 3.0, alpha=0.2, color='green', label='HR range')
            ax.axvspan(0.1, 0.6, alpha=0.2, color='blue', label='RR range')

            ax.set_ylabel(f"Ch{i+1} Magnitude", fontsize=10)
            ax.grid(True, alpha=0.3, linestyle='--')

        axes[-1].set_xlabel("Frequency (Hz)", fontsize=11, fontweight='bold')
        axes[0].legend(fontsize=8, loc='upper right')
        fig.suptitle(title, fontsize=13, fontweight='bold')

    else:
        # 多通道：网格布局 + 峰值标注
        n_rows = (n_channels + 1) // 2
        fig, axes = plt.subplots(n_rows, 2, figsize=(14, 3.5 * n_rows))
        axes = axes.flatten() if n_channels > 1 else [axes]

        colors = ['#3b82f6', '#8b5cf6', '#ec4899', '#f59e0b', '#10b981', '#ef4444']

        for i in range(n_channels):
            if i >= len(axes):
                break

            ax = axes[i]
            signal = data[:, i]
            signal = signal - np.mean(signal)
            window = np.hanning(len(signal))
            signal_windowed = signal * window

            fft_result = np.fft.fft(signal_windowed)
            freqs = np.fft.fftfreq(len(signal), 1/fs)
            magnitude = np.abs(fft_result)[:len(freqs)//2]

            # 绘制频谱
            ax.plot(freqs[:len(freqs)//2], magnitude, linewidth=1.5, color=colors[i % len(colors)], alpha=0.8)
            ax.fill_between(freqs[:len(freqs)//2], 0, magnitude, alpha=0.3, color=colors[i % len(colors)])

            # 找峰值并标注
            peak_idx = np.argmax(magnitude)
            peak_freq = freqs[peak_idx]
            peak_mag = magnitude[peak_idx]

            # 只标注显著峰值
            if peak_mag > np.mean(magnitude) + 2 * np.std(magnitude):
                ax.plot(peak_freq, peak_mag, 'ro', markersize=6, markeredgecolor='white', markeredgewidth=1.5)
                ax.text(peak_freq, peak_mag, f'{peak_freq:.1f}Hz',
                       fontsize=8, verticalalignment='bottom', horizontalalignment='center',
                       bbox=dict(boxstyle='round,pad=0.2', facecolor='white', alpha=0.8))

            # 添加频率范围背景
            ax.axvspan(0.8, 3.0, alpha=0.15, color='lightgreen')
            ax.axvspan(0.1, 0.6, alpha=0.15, color='lightblue')

            ax.set_title(f'Channel {i+1} Spectrum', fontsize=10, fontweight='bold')
            ax.set_ylabel("Magnitude", fontsize=8)
            ax.grid(True, alpha=0.25, linestyle='--')

            # 添加统计信息
            dom_freq = peak_freq if peak_mag > np.mean(magnitude) + 2 * np.std(magnitude) else 0
            ax.text(0.98, 0.98, f'Peak: {dom_freq:.1f}Hz',
                   transform=ax.transAxes, fontsize=8, verticalalignment='top',
                   horizontalalignment='right',
                   bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.7))

        # 隐藏多余的子图
        for i in range(n_channels, len(axes)):
            axes[i].set_visible(False)

        # 为最后一行的子图添加x轴标签
        for i in range(n_channels):
            row = (i) // 2
            col = (i) % 2
            if row == n_rows - 1:
                ax = axes[i]
                ax.set_xlabel("Frequency (Hz)", fontsize=9)

        fig.suptitle(f"{title} (Peak Detection + Frequency Bands)",
                    fontsize=13, fontweight='bold', y=0.98)

    plt.tight_layout()
    return png_b64_from_plt(fig)

def plot_spectrogram(data: np.ndarray, title: str) -> str:
    """绘制频谱图 - 为CSI数据添加"""
    if data.ndim == 1:
        data = data.reshape(-1, 1)

    # 使用第一个通道绘制频谱图
    signal = data[:, 0]

    fig, ax = plt.subplots(figsize=(10, 4))

    # 计算频谱图
    from scipy import signal as scipy_signal
    try:
        freqs, times, Sxx = scipy_signal.spectrogram(signal, fs=24.0)
        im = ax.pcolormesh(times, freqs, 10 * np.log10(Sxx), shading='gouraud', cmap='viridis')
        fig.colorbar(im, ax=ax, label='Power (dB)')
    except:
        # 如果scipy不可用，使用简单的FFT时频图
        ax.plot(signal, linewidth=0.5, alpha=0.7)
        ax.set_title(f"{title} (Time Domain)")

    ax.set_ylabel("Frequency (Hz)")
    ax.set_xlabel("Time (s)")
    ax.set_title(title, fontsize=10, fontweight="bold")

    fig.tight_layout()
    return png_b64_from_plt(fig)

def feat_from_series(data: np.ndarray) -> np.ndarray:
    """从时间序列提取8维特征"""
    if data.ndim == 1:
        data = data.reshape(-1, 1)

    features = []
    for col in range(min(data.shape[1], 8)):
        channel = data[:, col]
        stats = [
            np.mean(channel),
            np.std(channel),
            np.min(channel),
            np.max(channel),
            np.percentile(channel, 25),
            np.percentile(channel, 50),
            np.percentile(channel, 75),
            np.ptp(channel)
        ]
        features.extend(stats)

    return np.array(features[:8])

def setup_context() -> ts.Context:
    """设置CKKS加密上下文"""
    ctx = ts.context(
        ts.SCHEME_TYPE.CKKS,
        poly_modulus_degree=16384,
        coeff_mod_bit_sizes=[60, 40, 40, 40, 40, 40, 60]
    )
    ctx.global_scale = 2**40
    ctx.generate_galois_keys()
    return ctx

def _dominant_freq_hz(signal: np.ndarray, fs: float, freq_range: tuple) -> float:
    """计算主频率"""
    freqs = np.fft.fftfreq(len(signal), 1/fs)
    fft_result = np.fft.fft(signal - np.mean(signal))
    magnitude = np.abs(fft_result)

    mask = (freqs >= freq_range[0]) & (freqs <= freq_range[1])
    if not np.any(mask):
        return np.nan

    peak_idx = np.argmax(magnitude[mask])
    return freqs[mask][peak_idx]

def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))

def _sigmoid(x: float) -> float:
    return 1.0 / (1.0 + np.exp(-x))

def build_health_report(results: List[Dict], uwb_data: np.ndarray, imu_data: np.ndarray, csi_data: np.ndarray, seed: int = 42) -> Dict[str, Any]:
    """生成完整的健康报告 - 完全按照原始数据结构"""
    rng = np.random.default_rng(seed)
    fs = 24.0  # 采样率

    # 处理数据
    csi_series = csi_data[:, :min(csi_data.shape[1], 8)].mean(axis=1)
    imu_series = imu_data[:, 0] if imu_data.ndim == 2 else imu_data.ravel()
    uwb_series = uwb_data[:, :min(uwb_data.shape[1], 8)].mean(axis=1)

    # 提取生命体征
    try:
        hr_hz = _dominant_freq_hz(csi_series, fs, (0.8, 3.0))
        rr_hz = _dominant_freq_hz(csi_series, fs, (0.1, 0.55))
        hr_bpm = float("nan") if np.isnan(hr_hz) else hr_hz * 60.0
        rr_bpm = float("nan") if np.isnan(rr_hz) else rr_hz * 60.0
    except:
        hr_bpm, rr_bpm = 75.0, 16.0

    # 步频估计
    try:
        cad_hz = _dominant_freq_hz(imu_series, fs, (0.5, 3.0))
        cadence_spm = float("nan") if np.isnan(cad_hz) else cad_hz * 60.0
    except:
        cadence_spm = 110.0

    # 模型分数
    by_model = {r["model_id"]: r for r in results}
    score_ecg = float(by_model.get("ecg", {}).get("score", 75.0))
    score_bp = float(by_model.get("bp", {}).get("score", 120.0))
    score_sleep = float(by_model.get("sleep", {}).get("score", 85.0))
    score_met = float(by_model.get("metabolic", {}).get("score", 1600.0))
    score_risk = float(by_model.get("risk", {}).get("score", 0.3))

    # 计算风险组件
    def nrm(v: float, lo: float, hi: float) -> float:
        return _clamp((v - lo) / (hi - lo), 0.0, 1.0)

    cardio_r = nrm(score_ecg / 100, 0.5, 1.5)
    bp_r = nrm(score_bp / 140, 0.7, 1.3)
    sleep_r = nrm(score_sleep / 100, 0.6, 1.4)
    metab_r = nrm(score_met / 2000, 0.6, 1.4)

    # IMU变异性（步态稳定性）
    imu_std = np.std(imu_series) if len(imu_series) > 0 else 1.0
    imu_mean = np.abs(np.mean(imu_series)) if len(imu_series) > 0 else 1.0
    gait_var = _clamp(imu_std / (imu_mean + 1e-6), 0.0, 3.0)

    # UWB运动代理（稳定性/游走）
    uwb_drift = float(np.mean(np.abs(np.diff(uwb_series)))) if len(uwb_series) > 2 else 0.0

    mobility_r = _clamp(0.55 * nrm(gait_var, 0.1, 1.2) + 0.45 * nrm(uwb_drift, 0.0, 0.08), 0.0, 1.0)

    # 跌倒风险概率
    raw = (
        1.15 * mobility_r +
        0.35 * cardio_r +
        0.25 * bp_r +
        0.20 * sleep_r +
        0.15 * metab_r
    )
    fall_prob = _sigmoid((raw - 0.85) * 3.4)

    if fall_prob >= 0.70:
        fall_level = "High"
    elif fall_prob >= 0.40:
        fall_level = "Moderate"
    else:
        fall_level = "Low"

    # 临床指标转换
    sbp = float(118 + 28 * bp_r + rng.normal(0, 3.0))
    dbp = float(78 + 18 * bp_r + rng.normal(0, 2.0))
    sleep_eff = float(_clamp(90 - 22 * sleep_r + rng.normal(0, 1.8), 55, 98))
    spo2 = float(_clamp(98 - 4.5 * cardio_r + rng.normal(0, 0.6), 90, 100))

    # 活动混合
    activity_labels = ["Walk", "Stand", "Sit", "Sleep"]
    base = np.array([0.22, 0.18, 0.35, 0.25], dtype=float)
    tilt = np.array([0.06 * (1.0 - sleep_r), 0.04 * (1.0 - cardio_r), 0.05 * sleep_r, 0.05 * metab_r], dtype=float)
    mix = np.clip(base + tilt + rng.normal(0, 0.015, size=4), 0.05, 0.80)
    mix = mix / mix.sum()

    # 域雷达图
    radar_labels = ["Cardio", "BP", "Sleep", "Metabolic", "Recovery", "Safety"]
    radar_values = [
        float(100 * (1.0 - cardio_r)),
        float(100 * (1.0 - bp_r)),
        float(100 * (1.0 - sleep_r)),
        float(100 * (1.0 - metab_r)),
        float(100 * (1.0 - _clamp(0.6 * sleep_r + 0.4 * cardio_r, 0.0, 1.0))),
        float(100 * (1.0 - fall_prob))
    ]

    # 定义状态函数
    def status_by_range(v: float, lo: float, hi: float) -> str:
        if np.isnan(v):
            return "unknown"
        if v < lo:
            return "low"
        if v > hi:
            return "high"
        return "normal"

    # 指标卡片
    def metric(name: str, value: float, unit: str, ref: str, status: str, detail: str = "") -> Dict[str, Any]:
        return {
            "name": name,
            "value": None if np.isnan(value) else float(value),
            "unit": unit,
            "ref": ref,
            "status": status,
            "detail": detail,
        }

    metrics = [
        metric("Heart rate", hr_bpm, "bpm", "60–100", status_by_range(hr_bpm, 60, 100), "Derived from CSI rhythm band"),
        metric("Resp. rate", rr_bpm, "rpm", "12–20", status_by_range(rr_bpm, 12, 20), "Low-frequency CSI component"),
        metric("Blood pressure", sbp, "mmHg", "SBP 90–120", status_by_range(sbp, 90, 120), f"DBP ≈ {dbp:.0f} mmHg"),
        metric("SpO₂", spo2, "%", "95–100", status_by_range(spo2, 95, 100), "Cardio proxy + noise"),
        metric("Sleep efficiency", sleep_eff, "%", "≥ 85", "low" if sleep_eff < 85 else "normal", "Depth-based staging proxy"),
        metric("Cadence", cadence_spm, "spm", "90–130", status_by_range(cadence_spm, 90, 130), "IMU step-frequency proxy"),
    ]

    # 风险驱动因素
    drivers = []
    if mobility_r > 0.55:
        drivers.append("Increased gait instability / variability")
    if sleep_r > 0.55:
        drivers.append("Suboptimal sleep efficiency pattern")
    if cardio_r > 0.55:
        drivers.append("Elevated cardio rhythm irregularity proxy")
    if bp_r > 0.55:
        drivers.append("Elevated blood-pressure proxy")
    if not drivers:
        drivers.append("No dominant risk drivers detected in this demo cycle")

    # 建议
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

    # 整体状态
    overall = "Stable"
    if fall_level == "High" or any(m["status"] == "high" for m in metrics):
        overall = "Attention"
    elif fall_level == "Moderate" or any(m["status"] in ("low", "high") for m in metrics):
        overall = "Watch"

    # 叙述性报告
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
                    float(hr_bpm if not np.isnan(hr_bpm) else 75.0),
                    float(rr_bpm if not np.isnan(rr_bpm) else 16.0),
                    float(sbp),
                    float(spo2),
                    float(sleep_eff),
                    float(cadence_spm if not np.isnan(cadence_spm) else 110.0),
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

async def call_zhipu_llm(prompt: str, max_tokens: int = 1024) -> str:
    """调用智谱AI API"""
    try:
        headers = {
            "Authorization": f"Bearer {ZHIPU_API_KEY}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": "claude-3-5-sonnet-20241022",
            "max_tokens": max_tokens,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(ZHIPU_API_URL, headers=headers, json=payload)
            response.raise_for_status()
            result = response.json()

            if "content" in result and len(result["content"]) > 0:
                return result["content"][0]["text"]
            else:
                return "智谱AI调用成功但返回格式异常"

    except Exception as e:
        return f"智谱AI调用失败，使用默认报告: {str(e)}"

@app.get("/api/health")
async def health_check():
    """健康检查"""
    return {"status": "healthy", "version": "3.1-complete", "timestamp": time.time()}

@app.get("/api/modalities")
async def get_modalities():
    """获取所有可用的模态配置"""
    try:
        config_path = os.path.join(BASE_DIR, "backend", "modality_config.json")
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        return config
    except Exception as e:
        # 如果配置文件不存在，返回默认配置
        return {
            "modalities": [
                {"id": "depth", "name": "深度图像", "type": "image", "description": "睡眠姿态检测", "icon": "🛏️"},
                {"id": "uwb", "name": "UWB雷达", "type": "timeseries", "description": "心率、血压监测", "icon": "📡"},
                {"id": "imu", "name": "IMU传感器", "type": "timeseries", "description": "步态分析、代谢评估", "icon": "🏃"},
                {"id": "csi", "name": "CSI信号", "type": "timeseries", "description": "心率、呼吸监测", "icon": "📶"},
                {"id": "rgb", "name": "RGB图像", "type": "image", "description": "风险评分、跌倒检测", "icon": "📷"},
                {"id": "ntu", "name": "NTU骨骼", "type": "skeleton", "description": "动作识别、行为分析", "icon": "🦴"},
                {"id": "retina", "name": "视网膜图像", "type": "medical_image", "description": "心血管疾病早期预警", "icon": "👁️"},
                {"id": "chest", "name": "胸部X光", "type": "medical_image", "description": "肺部疾病筛查", "icon": "🫁"},
                {"id": "path", "name": "组织病理", "type": "medical_image", "description": "癌症筛查", "icon": "🔬"},
                {"id": "blood", "name": "血细胞", "type": "medical_image", "description": "血液疾病诊断", "icon": "🩸"}
            ]
        }

@app.get("/api/cycle")
async def run_cycle(selected_modalities: Optional[str] = None):
    """执行完整的数据处理周期 - 支持选择性模态加载

    Args:
        selected_modalities: Optional comma-separated list of modalities to load
                           Example: "UWB,IMU,CSI" or "Depth,RGB"
    """
    start_time = time.time()

    # Load modality configuration
    modality_config = load_modality_config()

    # Parse selected modalities if provided
    enabled_modalities = []
    if selected_modalities:
        requested = [m.strip() for m in selected_modalities.split(",")]
        for mod in requested:
            if mod in modality_config and modality_config[mod].get("enabled", True):
                enabled_modalities.append(mod)
            else:
                print(f"Warning: Modality {mod} not found or disabled")

        # Fallback: if no valid modalities, load all enabled
        if not enabled_modalities:
            print("No valid modalities provided, loading all enabled modalities")
            enabled_modalities = [mod for mod, cfg in modality_config.items() if cfg.get("enabled", True)]
    else:
        # Default: load all enabled modalities
        enabled_modalities = [mod for mod, cfg in modality_config.items() if cfg.get("enabled", True)]

    print(f"Enabled modalities for this cycle: {enabled_modalities}")

    # Step 1: 数据收集
    step1_start = time.time()
    try:
        # Only load selected modalities
        uwb_data = get_data("UWB") if "UWB" in enabled_modalities else None
        imu_data = get_data("IMU") if "IMU" in enabled_modalities else None
        csi_data = get_data("CSI") if "CSI" in enabled_modalities else None

        # 重塑数据 (only for loaded modalities)
        uwb_series = uwb_data.reshape(-1, 3) if uwb_data is not None else None
        imu_series = imu_data.reshape(-1, 6) if imu_data is not None else None
        csi_series = csi_data[:, 1:] if csi_data is not None else None

        # 生成增强的多通道预览图 (only for loaded modalities)
        uwb_preview = plot_multichannel_preview(uwb_series, "UWB Multichannel Analysis (3 Channels)", max_channels=3) if uwb_series is not None else ""
        imu_preview = plot_multichannel_preview(imu_series, "IMU Multichannel Analysis (6 Channels)", max_channels=6) if imu_series is not None else ""
        csi_preview = plot_multichannel_preview(csi_series, "CSI Multichannel Analysis (8 Channels)", max_channels=8) if csi_series is not None else ""

        # 生成增强的FFT频谱图 (only for loaded modalities)
        uwb_fft = plot_fft_spectrum(uwb_series, "UWB Frequency Spectrum Analysis", fs=24.0) if uwb_series is not None else ""
        imu_fft = plot_fft_spectrum(imu_series, "IMU Frequency Spectrum Analysis", fs=24.0) if imu_series is not None else ""
        csi_fft = plot_fft_spectrum(csi_series, "CSI Frequency Spectrum Analysis", fs=24.0) if csi_series is not None else ""

        # CSI暂时不生成spectrogram（可选）
        csi_spectrogram = ""

        # 生成Depth和RGB预览 (only if enabled)
        depth_png = png_b64_from_file(DEPTH_PNG_PATH) if "Depth" in enabled_modalities else ""
        rgb_png = png_b64_from_file(RGB_PNG_PATH) if "RGB" in enabled_modalities else ""

        step1_time = time.time() - step1_start

        # Build step1_data with only enabled modalities
        step1_modalities = {}

        if "Depth" in enabled_modalities:
            step1_modalities["Depth"] = {
                "kind": "image",
                "shape": "64×64",
                "preview_png": depth_png or "",
                "plaintext_excerpt": "Depth map for sleep posture detection"
            }

        if "UWB" in enabled_modalities and uwb_series is not None:
            step1_modalities["UWB"] = {
                "kind": "timeseries",
                "shape": f"{uwb_series.shape[0]}×{uwb_series.shape[1]}",
                "preview_png": uwb_preview,
                "plaintext_excerpt": excerpt_array(uwb_series, rows=4, cols=3),
                "fft_png": uwb_fft,
            }

        if "IMU" in enabled_modalities and imu_series is not None:
            step1_modalities["IMU"] = {
                "kind": "timeseries",
                "shape": f"{imu_series.shape[0]}×{imu_series.shape[1]}",
                "preview_png": imu_preview,
                "plaintext_excerpt": excerpt_array(imu_series, rows=4, cols=6),
                "fft_png": imu_fft,
            }

        if "CSI" in enabled_modalities and csi_series is not None:
            step1_modalities["CSI"] = {
                "kind": "timeseries",
                "shape": f"{csi_series.shape[0]}×{csi_series.shape[1]}",
                "preview_png": csi_preview,
                "plaintext_excerpt": excerpt_array(csi_series, rows=4, cols=4),
                "fft_png": csi_fft,
                "spectrogram_png": csi_spectrogram,
            }

        if "RGB" in enabled_modalities:
            step1_modalities["RGB"] = {
                "kind": "image",
                "shape": "64×64×3",
                "preview_png": rgb_png or "",
                "plaintext_excerpt": "RGB image for risk assessment"
            }

        step1_data = {
            "time_sec": step1_time,
            "modalities": step1_modalities,
            "enabled_modalities": enabled_modalities
        }
    except Exception as e:
        return {"error": f"Step 1 failed: {str(e)}"}

    # Step 2: 加密和推理
    step2_start = time.time()
    try:
        # 特征提取 (only for loaded modalities)
        uwb_feat = feat_from_series(uwb_series) if uwb_series is not None else np.zeros(8)
        imu_feat = feat_from_series(imu_series) if imu_series is not None else np.zeros(8)
        csi_feat = feat_from_series(csi_series) if csi_series is not None else np.zeros(8)

        ctx = setup_context()

        # 加密特征
        enc_uwb = ts.ckks_vector(ctx, uwb_feat.tolist())
        enc_imu = ts.ckks_vector(ctx, imu_feat.tolist())
        enc_csi = ts.ckks_vector(ctx, csi_feat.tolist())

        # 聚合密文
        agg_bytes = enc_uwb.serialize() + enc_imu.serialize()[:100]

        # LLM智能分配 (only for enabled modalities)
        assignments = []
        if "CSI" in enabled_modalities:
            assignments.append({"input_modality": "CSI", "model_id": "ecg", "tool": "secure_ecg_toolbox"})
        if "UWB" in enabled_modalities:
            assignments.append({"input_modality": "UWB", "model_id": "bp", "tool": "secure_bp_toolbox"})
        if "IMU" in enabled_modalities:
            assignments.append({"input_modality": "IMU", "model_id": "sleep", "tool": "secure_sleep_toolbox"})
            assignments.append({"input_modality": "IMU", "model_id": "metabolic", "tool": "secure_metabolic_toolbox"})
        if "RGB" in enabled_modalities:
            assignments.append({"input_modality": "RGB", "model_id": "risk", "tool": "secure_risk_toolbox"})

        # Fallback: if no modalities selected, use default assignment
        if not assignments:
            assignments = [
                {"input_modality": "CSI", "model_id": "ecg", "tool": "secure_ecg_toolbox"},
                {"input_modality": "UWB", "model_id": "bp", "tool": "secure_bp_toolbox"},
            ]

        # 模拟推理结果 - 使用正确的数据结构
        results = []
        for a in assignments:
            model_meta = next((m for m in CLUSTER_MODELS if m["id"] == a["model_id"]), None)
            model_title = model_meta["title"] if model_meta else a["model_id"]

            # 根据模型ID生成模拟分数
            if a["model_id"] == "ecg":
                score = 75.5
                status = "normal"
            elif a["model_id"] == "bp":
                score = 118.0
                status = "normal"
            elif a["model_id"] == "sleep":
                score = 85.2
                status = "good"
            elif a["model_id"] == "metabolic":
                score = 1650.0
                status = "normal"
            elif a["model_id"] == "risk":
                score = 0.25
                status = "low"
            else:
                score = 50.0
                status = "unknown"

            results.append({
                "model": model_title,
                "model_id": a["model_id"],
                "input_modality": a["input_modality"],
                "tool": a["tool"],
                "score": score,
                "status": status
            })

        # 工具执行时间（模拟）
        tool_times = [0.8, 1.2, 0.9, 1.1, 0.7]

        # LLM摘要
        summary = ", ".join([f"{a['input_modality']}→{a['tool']}" for a in assignments])

        step2_time = time.time() - step2_start

        step2_data = {
            "time_sec": step2_time,
            "llm_time_sec": 0.0,  # 暂时设为0，因为使用智谱AI
            "summary": summary,
            "cluster_models": CLUSTER_MODELS,
            "assignments": assignments,
            "tool_times": tool_times,
            "aggregate_cipher_preview": bytes_preview(agg_bytes, 160),
        }
    except Exception as e:
        return {"error": f"Step 2 failed: {str(e)}"}

    # Step 3: 解密和报告生成
    step3_start = time.time()
    try:
        # 生成完整健康报告 (use zero arrays for missing modalities)
        uwb_for_report = uwb_series if uwb_series is not None else np.zeros((100, 3))
        imu_for_report = imu_series if imu_series is not None else np.zeros((250, 6))
        csi_for_report = csi_series if csi_series is not None else np.zeros((200, 8))

        report = build_health_report(results, uwb_for_report, imu_for_report, csi_for_report)

        # 调用智谱AI增强结论
        activity_mix = report['charts']['activity_mix']
        radar_scores = report['charts']['radar']['values']

        llm_prompt = f"""你是一个健康监测分析专家，基于UT_HAR人体活动识别数据集的监测结果，请生成专业的健康评估结论。

【数据来源】UT_HAR人体活动识别数据集 - 通过多模态传感器(深度、UWB、IMU、CSI、RGB)采集

【整体评估】{report['overall']}
【跌倒风险】{report['fall_risk']['level']} (概率: {report['fall_risk']['probability']:.1%})

【核心生理指标】
- 心率: {report['metrics'][0]['value']} bpm (参考范围: {report['metrics'][0]['ref']}, 状态: {report['metrics'][0]['status']})
- 呼吸率: {report['metrics'][1]['value']} rpm (参考范围: {report['metrics'][1]['ref']}, 状态: {report['metrics'][1]['status']})
- 血压: {report['metrics'][2]['value']} mmHg (参考范围: {report['metrics'][2]['ref']}, 状态: {report['metrics'][2]['status']})
- 血氧饱和度: {report['metrics'][3]['value']}% (参考范围: {report['metrics'][3]['ref']}, 状态: {report['metrics'][3]['status']})
- 睡眠效率: {report['metrics'][4]['value']}% (参考范围: {report['metrics'][4]['ref']}, 状态: {report['metrics'][4]['status']})
- 步态频率: {report['metrics'][5]['value']} spm (参考范围: {report['metrics'][5]['ref']}, 状态: {report['metrics'][5]['status']})

【活动模式分析】
- 行走: {activity_mix['values'][0]:.1%}
- 站立: {activity_mix['values'][1]:.1%}
- 坐姿: {activity_mix['values'][2]:.1%}
- 睡眠: {activity_mix['values'][3]:.1%}

【功能评估】
- 心血管功能: {radar_scores[0]:.0f}/100
- 血压调节: {radar_scores[1]:.0f}/100
- 睡眠质量: {radar_scores[2]:.0f}/100
- 代谢水平: {radar_scores[3]:.0f}/100
- 恢复能力: {radar_scores[4]:.0f}/100
- 安全性: {radar_scores[5]:.0f}/100

【主要风险因素】
{chr(10).join([f"- {driver}" for driver in report['fall_risk']['drivers']])}

【技术特点】
✅ 使用CKKS同态加密保护数据隐私
✅ 5种模态传感器融合分析
✅ 6个健康预测模型并行推理

请提供：
1. 整体健康状况评估（1-2句话）
2. 主要发现和关注点（2-3句话）
3. 具体改善建议（2-3句话）

要求：专业、准确、实用性强的医学表述，避免过于技术性的术语。"""

        report_conclusion = await call_zhipu_llm(llm_prompt)

        step3_time = time.time() - step3_start

        step3_data = {
            "time_sec": step3_time,
            "results": results,
            "report_conclusion": report_conclusion,
            "report": report,  # 完整的报告对象
        }
    except Exception as e:
        return {"error": f"Step 3 failed: {str(e)}"}

    return {
        "schema": "he-multimodal-cycle/v1",
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "cycle_time_sec": time.time() - start_time,
        "step1": step1_data,
        "step2": step2_data,
        "step3": step3_data,
        "data_source": "UT_HAR dataset",
        "llm_provider": "ZhipuAI"
    }

if __name__ == "__main__":
    import uvicorn
    print("Starting complete backend server on port 8082...")
    print("Data source: UT_HAR dataset")
    print("Features: Full original visualization + ZhipuAI + Health charts")
    uvicorn.run(app, host="127.0.0.1", port=8082)