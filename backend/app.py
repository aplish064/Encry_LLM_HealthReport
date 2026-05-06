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
import random
import uuid
from io import BytesIO
from typing import Dict, Any, Optional, List
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

from privacy_shuffle import (
    build_anonymous_database,
    build_distribution_summary,
    build_protected_llm_summary,
    build_real_data_record,
    generate_synthetic_database,
)

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

DATA_PATHS = {
    "UWB": os.path.join(BASE_DIR, "test_data", "uwb_sample.txt"),
    "IMU": os.path.join(BASE_DIR, "test_data", "imu_sample.txt"),
    "CSI": os.path.join(BASE_DIR, "test_data", "csi_sample.csv"),
    "NTU": os.path.join(BASE_DIR, "test_data", "ntu_sample.txt"),
    "Retina": os.path.join(BASE_DIR, "test_data", "retina_sample.npz"),
    "Chest": os.path.join(BASE_DIR, "test_data", "chest_sample.npz"),
    "Path": os.path.join(BASE_DIR, "test_data", "path_sample.npz"),
    "Blood": os.path.join(BASE_DIR, "test_data", "blood_sample.npz"),
}

ASSET_USER_DIR = os.path.join(BASE_DIR, "frontend", "assets", "user")
DEPTH_PNG_PATH = os.path.join(ASSET_USER_DIR, "deep2.png")
RGB_PNG_PATH = os.path.join(ASSET_USER_DIR, "RGB.png")

_DATA_CACHE: Dict[str, np.ndarray] = {}
_THUMBNAIL_CACHE: Dict[str, str] = {}  # Cache for generated thumbnails - 清空缓存以重新生成缩略图
_STAGED_SESSIONS: Dict[str, Dict[str, Any]] = {}
MODALITY_CONFIG = {
    "Depth": {"enabled": True, "file": DEPTH_PNG_PATH},
    "UWB": {"enabled": True, "file": DATA_PATHS["UWB"]},
    "IMU": {"enabled": True, "file": DATA_PATHS["IMU"]},
    "CSI": {"enabled": True, "file": DATA_PATHS["CSI"]},
    "RGB": {"enabled": True, "file": RGB_PNG_PATH},
}

# Thread pool for parallel processing
executor = ThreadPoolExecutor(max_workers=4)

# 模态名称映射：完整名称 -> 简化名称
MODALITY_NAME_MAP = {
    "Depth Camera": "Depth",
    "UWB Radar": "UWB",
    "IMU Sensor": "IMU",
    "WiFi CSI": "CSI",
    "RGB Camera": "RGB",
    "NTU": "NTU",
    "Retina Image": "Retina",
    "Chest X-ray": "Chest",
    "Pathology Image": "Path",
    "Blood Cell Image": "Blood",
    # 前端使用的名称（中文 + 英文）
    "Depth": "Depth",
    "UWB": "UWB",
    "IMU": "IMU",
    "CSI": "CSI",
    "RGB": "RGB",
    "Retina": "Retina",
    "Chest": "Chest",
    "Pathology": "Path",
    "Blood": "Blood",
    "深度图像": "Depth",
    "UWB雷达": "UWB",
    "IMU传感器": "IMU",
    "WiFi CSI": "CSI",
    "RGB摄像头": "RGB",
    "视网膜": "Retina",
    "胸部X光": "Chest",
    "组织病理": "Path",
    "血细胞": "Blood"
}

def normalize_modality_name(name: str) -> str:
    """将模态完整名称转换为后端get_data函数期望的简化名称"""
    return MODALITY_NAME_MAP.get(name, name)

# 智谱AI配置
ZHIPU_API_KEY = os.getenv("ZHIPU_API_KEY", "")
ZHIPU_API_URL = os.getenv("ZHIPU_API_URL", "https://open.bigmodel.cn/api/anthropic/v1/messages")
ZHIPU_MODEL = os.getenv("ZHIPU_MODEL", "claude-3-5-sonnet-20241022")

# 本地编码器配置
CLUSTER_MODELS = [
    {"id": "ecg", "title": "ECG Arrhythmia", "subtitle": "CSI Heart Pattern"},
    {"id": "bp", "title": "Blood Pressure", "subtitle": "UWB Regression"},
    {"id": "sleep", "title": "Sleep Staging", "subtitle": "Depth-based Model"},
    {"id": "metabolic", "title": "Metabolic Score", "subtitle": "IMU Proxy"},
    {"id": "risk", "title": "Risk Assessment", "subtitle": "RGB Triage"},
    {"id": "action", "title": "Action Recognition", "subtitle": "Skeleton Model"},
    {"id": "cardio", "title": "Cardiovascular", "subtitle": "Retina Analysis"},
    {"id": "lung", "title": "Lung Screening", "subtitle": "X-ray Analysis"},
    {"id": "cancer", "title": "Cancer Detection", "subtitle": "Pathology Model"},
    {"id": "blood", "title": "Blood Analysis", "subtitle": "Hematology Model"},
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
    try:
        bio = BytesIO()
        fig.savefig(bio, format="png", dpi=160, bbox_inches="tight", pad_inches=pad_inches)
        plt.close(fig)
        result = b64e(bio.getvalue())
        print(f"✅ png_b64_from_plt: Generated {len(result)} bytes")
        return result
    except Exception as e:
        print(f"❌ png_b64_from_plt failed: {e}")
        plt.close(fig)
        return ""

def generate_thumbnail(data: np.ndarray, modality_type: str, size=(200, 150)) -> str:
    """生成高质量预览缩略图（带缓存）"""
    # 创建缓存键
    cache_key = f"{modality_type}_{data.shape}_{size[0]}x{size[1]}"

    # 检查缓存
    if cache_key in _THUMBNAIL_CACHE:
        print(f"✅ Using cached thumbnail for {modality_type}")
        return _THUMBNAIL_CACHE[cache_key]

    print(f"🎨 Generating NEW thumbnail for {modality_type}, data shape: {data.shape}")

    try:
        # 创建更大的图形以获得更好的质量
        fig, ax = plt.subplots(figsize=(size[0]/100, size[1]/100), dpi=150)

        if modality_type == 'timeseries':
            # 时序数据：多通道可视化
            display_points = min(100, data.shape[0])
            colors = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899']

            if data.ndim == 1:
                # 单通道
                ax.plot(data[:display_points], linewidth=1.5, color=colors[0], alpha=0.8)
                ax.fill_between(range(display_points), data[:display_points], alpha=0.2, color=colors[0])
            else:
                # 多通道：显示前3个通道
                num_channels = min(3, data.shape[1])
                for i in range(num_channels):
                    ax.plot(data[:display_points, i], linewidth=1.2,
                           color=colors[i % len(colors)], alpha=0.7,
                           label=f'Ch{i+1}')

            ax.set_facecolor('#f8fafc')
            ax.grid(True, alpha=0.3, linewidth=0.5)
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)

        elif modality_type == 'skeleton':
            # 骨骼数据：绘制简化的2D火柴人
            plt.close(fig)  # 关闭之前创建的fig
            fig, ax = plt.subplots(figsize=(size[0]/100, size[1]/100), dpi=150)

            # 重塑数据为 (N, 3)
            if data.ndim == 1:
                n_points = len(data) // 3
                points = data[:n_points*3].reshape(n_points, 3)
            elif data.ndim == 2 and data.shape[1] >= 3:
                points = data[:, :3]
            else:
                points = data.flatten()[:75].reshape(25, 3)  # NTU标准：25个关节点

            # 归一化到画布坐标
            x = points[:, 0]
            y = -points[:, 1]  # 翻转y轴

            # 绘制关节点（只画主要的15个点）
            main_joints = [0, 1, 20, 2, 5, 3, 6, 4, 7, 8, 11, 9, 12, 10, 13]
            for idx in main_joints:
                if idx < len(points):
                    ax.scatter(x[idx], y[idx], s=30, c='#ef4444', zorder=3, edgecolors='white', linewidths=0.5)

            # 绘制骨骼连接线
            bones = [
                (0, 1), (1, 20), (21, 20), (21, 2), (21, 5),
                (2, 3), (3, 4), (5, 6), (6, 7),
                (0, 8), (0, 11), (8, 9), (9, 10), (11, 12), (12, 13)
            ]

            for i, j in bones:
                if i < len(points) and j < len(points):
                    ax.plot([x[i], x[j]], [y[i], y[j]], 'o-', c='#ef4444', linewidth=1.5, markersize=3, alpha=0.7)

            ax.set_facecolor('#f8fafc')
            ax.set_xlim(-1, 1)
            ax.set_ylim(-1, 1)
            ax.set_xticks([])
            ax.set_yticks([])
            ax.set_aspect('equal')

        elif modality_type in ['image', 'medical_image']:
            # 图像数据：高质量显示
            from PIL import Image

            # 标准化数据到0-255
            if data.dtype == np.float64 or data.dtype == np.float32:
                data = np.clip(data, 0, 1)

            # 处理不同维度的图像
            if data.ndim == 3:
                if data.shape[0] <= 4:  # 通道在前
                    data = np.moveaxis(data, 0, -1)
                if data.shape[-1] == 1:  # 单通道
                    data = data[:, :, 0]
                    ax.imshow(data, cmap='viridis')
                elif data.shape[-1] == 3:  # RGB
                    ax.imshow(data)
                else:  # 多通道，取前3个
                    ax.imshow(data[:, :, :3])
            else:
                # 2D图像
                if data.max() <= 1.0:
                    display_data = (data * 255).astype(np.uint8)
                else:
                    display_data = data.astype(np.uint8)
                ax.imshow(display_data, cmap='viridis')

            ax.axis('off')

        # 通用设置
        if modality_type != 'skeleton':
            ax.set_xticks([])
            ax.set_yticks([])

        plt.tight_layout(pad=0)
        plt.margins(x=0, y=0)

        result = png_b64_from_plt(fig, pad_inches=0)
        plt.close(fig)

        # 缓存结果
        _THUMBNAIL_CACHE[cache_key] = result

        return result

    except Exception as e:
        print(f"❌ 缩略图生成失败 ({modality_type}): {e}")
        print(f"   Data shape: {data.shape}, dtype: {data.dtype}")
        print(f"   Data range: min={data.min():.4f}, max={data.max():.4f}")
        import traceback
        traceback.print_exc()
        return None

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


def build_modality_alias_map(modality_config: Dict[str, Any]) -> Dict[str, str]:
    """Map request aliases to the canonical modality name from the config."""
    alias_map: Dict[str, str] = {}
    for canonical_name, mod_config in modality_config.items():
        aliases = {
            canonical_name,
            mod_config.get("id", ""),
            normalize_modality_name(canonical_name),
        }
        for alias in aliases:
            if alias:
                alias_map[str(alias).strip().lower()] = canonical_name
    return alias_map


def resolve_enabled_modalities(selected_modalities: Optional[str], modality_config: Dict[str, Any]) -> List[str]:
    """Resolve request ids/names to canonical config names while preserving order."""
    enabled_by_default = [name for name, cfg in modality_config.items() if cfg.get("enabled", True)]
    if not selected_modalities:
        return enabled_by_default

    alias_map = build_modality_alias_map(modality_config)
    resolved: List[str] = []
    for raw_name in selected_modalities.split(","):
        alias = raw_name.strip()
        if not alias:
            continue
        canonical_name = alias_map.get(alias.lower())
        if canonical_name and modality_config[canonical_name].get("enabled", True):
            if canonical_name not in resolved:
                resolved.append(canonical_name)
            continue
        print(f"Warning: Modality {alias} not found or disabled")

    if resolved:
        return resolved

    print("No valid modalities provided, loading all enabled modalities")
    return enabled_by_default


def find_selected_modality(enabled_modalities: List[str], short_name: str) -> Optional[str]:
    """Return the canonical selected modality name for a short alias."""
    for canonical_name in enabled_modalities:
        normalized_name = normalize_modality_name(canonical_name)
        if canonical_name == short_name or normalized_name == short_name:
            return canonical_name
    return None

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
    """加载模态数据，支持真实数据和模拟数据"""
    if name in _DATA_CACHE:
        return _DATA_CACHE[name]

    # 首先尝试从DATA_PATHS加载真实数据
    p = DATA_PATHS.get(name)
    if p and os.path.exists(p):
        try:
            arr = _load_csv_matrix(p)

            # 处理特定数据格式的reshape
            if name == "UWB":
                if arr.ndim == 1:
                    arr = arr.reshape(-1, 3)
            elif name == "IMU":
                if arr.ndim == 1:
                    arr = arr.reshape(-1, 6)
            elif name == "CSI":
                if arr.ndim == 2 and arr.shape[1] > 8:
                    arr = arr[:, 1:9]

            _DATA_CACHE[name] = arr
            return arr
        except Exception as e:
            print(f"Warning: Failed to load data from {p}: {e}")

    # 对于医学图像数据集，生成模拟数据
    if name in ["Retina", "Chest", "Path", "Blood", "NTU"]:
        arr = _generate_medical_image_sample(name)
        _DATA_CACHE[name] = arr
        return arr

    # 对于Depth和RGB，尝试从文件加载
    if name == "Depth" and os.path.exists(DEPTH_PNG_PATH):
        from PIL import Image
        img = Image.open(DEPTH_PNG_PATH)
        arr = np.array(img)
        _DATA_CACHE[name] = arr
        return arr

    if name == "RGB" and os.path.exists(RGB_PNG_PATH):
        from PIL import Image
        img = Image.open(RGB_PNG_PATH)
        arr = np.array(img)
        _DATA_CACHE[name] = arr
        return arr

    raise FileNotFoundError(f"Missing data file for {name}: {p}")

def _generate_medical_image_sample(modality: str) -> np.ndarray:
    """为医学图像模态生成模拟样本数据"""
    np.random.seed(42)  # 固定随机种子以获得一致的结果

    if modality == "Retina":
        # 视网膜图像：模拟眼底照片，圆形特征
        size = 128
        img = np.zeros((size, size, 3))
        center = size // 2

        # 创建径向渐变
        y, x = np.ogrid[:size, :size]
        mask = (x - center)**2 + (y - center)**2 <= (center - 5)**2

        # 添加血管结构
        for angle in np.linspace(0, 2*np.pi, 8):
            x_vessel = center + (center-10) * np.cos(angle)
            y_vessel = center + (center-10) * np.sin(angle)
            for r in range(5, center-5):
                x_pos = int(center + r * np.cos(angle))
                y_pos = int(center + r * np.sin(angle))
                if 0 <= x_pos < size and 0 <= y_pos < size:
                    img[y_pos-1:y_pos+2, x_pos-1:x_pos+2, 0] = np.random.uniform(0.6, 0.8)

        # 应用圆形遮罩
        for c in range(3):
            img[:, :, c] *= mask
            img[:, :, c] += np.random.normal(0, 0.05, (size, size))

        return np.clip(img, 0, 1)

    elif modality == "Chest":
        # 胸部X光：模拟肺部结构
        size = 128
        img = np.random.normal(0.3, 0.05, (size, size, 3))

        # 创建肺部形状（两个暗色区域）
        y, x = np.ogrid[:size, :size]

        # 左肺
        left_lung = ((x - size*0.3)**2 / 30**2 + (y - size*0.45)**2 / 35**2) <= 1
        # 右肺
        right_lung = ((x - size*0.7)**2 / 30**2 + (y - size*0.45)**2 / 35**2) <= 1

        for c in range(3):
            img[left_lung, c] = np.random.normal(0.15, 0.03, left_lung.sum())
            img[right_lung, c] = np.random.normal(0.15, 0.03, right_lung.sum())

        # 添加心脏阴影
        heart = ((x - size*0.5)**2 / 15**2 + (y - size*0.55)**2 / 20**2) <= 1
        for c in range(3):
            img[heart, c] = np.random.normal(0.4, 0.05, heart.sum())

        return np.clip(img, 0, 1)

    elif modality == "Path":
        # 病理图像：模拟组织细胞结构
        size = 128
        img = np.random.normal(0.5, 0.1, (size, size, 3))

        # 添加细胞核（小圆点）
        num_cells = 200
        for _ in range(num_cells):
            cx, cy = np.random.randint(10, size-10, 2)
            radius = np.random.randint(2, 6)

            y, x = np.ogrid[:size, :size]
            mask = (x - cx)**2 + (y - cy)**2 <= radius**2

            color = np.random.uniform(0.4, 0.7)
            for c in range(3):
                img[mask, c] = color + np.random.normal(0, 0.05, mask.sum())

        return np.clip(img, 0, 1)

    elif modality == "Blood":
        # 血液图像：模拟血细胞
        size = 128
        img = np.ones((size, size, 3)) * 0.95  # 浅色背景

        # 添加红细胞（红色圆圈）
        num_cells = 50
        for _ in range(num_cells):
            cx, cy = np.random.randint(10, size-10, 2)
            radius = np.random.randint(4, 8)

            y, x = np.ogrid[:size, :size]
            mask = (x - cx)**2 + (y - cy)**2 <= radius**2

            # 红色通道高，其他通道低
            img[mask, 0] = np.random.uniform(0.7, 0.9, mask.sum())  # R
            img[mask, 1] = np.random.uniform(0.1, 0.2, mask.sum())  # G
            img[mask, 2] = np.random.uniform(0.1, 0.2, mask.sum())  # B

        # 添加几个白细胞
        for _ in range(5):
            cx, cy = np.random.randint(15, size-15, 2)
            radius = np.random.randint(8, 12)

            y, x = np.ogrid[:size, :size]
            mask = (x - cx)**2 + (y - cy)**2 <= radius**2

            img[mask, 0] = np.random.uniform(0.8, 1.0, mask.sum())  # 亮色
            img[mask, 1] = np.random.uniform(0.8, 1.0, mask.sum())
            img[mask, 2] = np.random.uniform(0.8, 1.0, mask.sum())

        return np.clip(img, 0, 1)

    elif modality == "NTU":
        # NTU骨骼数据：模拟3D骨架关键点
        # 生成25个关键点的3D坐标
        num_joints = 25
        joints = np.random.randn(num_joints, 3) * 0.2

        # 添加一些结构（类似人体的骨骼结构）
        # 躯干中心
        joints[0] = [0.5, 0.5, 0.5]
        # 头部
        joints[1] = [0.5, 0.7, 0.5]
        # 左臂
        joints[2:5] = [[0.3, 0.6, 0.5], [0.2, 0.5, 0.5], [0.15, 0.4, 0.5]]
        # 右臂
        joints[5:8] = [[0.7, 0.6, 0.5], [0.8, 0.5, 0.5], [0.85, 0.4, 0.5]]
        # 左腿
        joints[8:12] = [[0.45, 0.35, 0.5], [0.4, 0.2, 0.5], [0.38, 0.1, 0.5], [0.4, 0.05, 0.5]]
        # 右腿
        joints[12:16] = [[0.55, 0.35, 0.5], [0.6, 0.2, 0.5], [0.62, 0.1, 0.5], [0.6, 0.05, 0.5]]

        # 添加一些随机噪声使其更真实
        joints += np.random.randn(*joints.shape) * 0.02

        return joints.flatten()

    else:
        # 默认：返回随机图像
        return np.random.rand(64, 64, 3)

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

def build_health_report(
    results: List[Dict],
    uwb_data: np.ndarray,
    imu_data: np.ndarray,
    csi_data: np.ndarray,
    seed: int = 42,
    selected_modalities: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """生成完整的健康报告 - 完全按照原始数据结构"""
    rng = np.random.default_rng(seed)
    selected_modality_ids = [
        str(item).strip().lower()
        for item in (selected_modalities or [])
        if str(item).strip()
    ]
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

    theme_order = ["integrated_risk", "mobility", "vitals", "sleep", "activity", "medical_screening"]
    theme_definitions = {
        "mobility": {
            "title": "Mobility & Fall Stability",
            "modalities": ["imu", "uwb", "rgb", "ntu"],
            "chart_type": "stability",
        },
        "vitals": {
            "title": "Cardiorespiratory Vitals",
            "modalities": ["csi", "uwb"],
            "chart_type": "reference_bars",
        },
        "sleep": {
            "title": "Sleep & Recovery",
            "modalities": ["depth", "csi"],
            "chart_type": "recovery_bars",
        },
        "activity": {
            "title": "Activity Pattern",
            "modalities": ["imu", "uwb", "rgb", "ntu"],
            "chart_type": "stacked_mix",
        },
        "medical_screening": {
            "title": "Medical Image Screening",
            "modalities": ["retina", "chest", "path", "blood"],
            "chart_type": "risk_tiles",
        },
        "integrated_risk": {
            "title": "Integrated Risk Summary",
            "modalities": selected_modality_ids,
            "chart_type": "radar",
        },
    }

    metric_by_name = {item["name"].lower(): item for item in metrics}

    def selected_sources(theme_id: str) -> List[str]:
        if theme_id == "integrated_risk":
            return selected_modality_ids if len(selected_modality_ids) >= 2 else []
        supported = theme_definitions[theme_id]["modalities"]
        return [item for item in selected_modality_ids if item in supported]

    def metric_pick(*names: str) -> List[Dict[str, Any]]:
        picked = []
        for name in names:
            metric_item = metric_by_name.get(name.lower())
            if metric_item:
                picked.append(metric_item)
        return picked

    def section_status(section_metrics: List[Dict[str, Any]], default_status: str = "stable") -> str:
        statuses = {str(item.get("status", "")).lower() for item in section_metrics}
        if "high" in statuses or "low" in statuses:
            return "attention"
        if "watch" in statuses or "moderate" in statuses:
            return "watch"
        return default_status

    def abnormality_score(section_metrics: List[Dict[str, Any]]) -> int:
        score = 0
        for item in section_metrics:
            status = str(item.get("status", "")).lower()
            if status in ("high", "low", "attention"):
                score += 30
            elif status in ("moderate", "watch"):
                score += 18
            elif status == "normal":
                score += 5
        return score

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

    # 健康指数（跌倒概率的反向映射）
    health_index = 1 - fall_prob
    if health_index >= 0.7:
        health_level = "High"
    elif health_index >= 0.4:
        health_level = "Moderate"
    else:
        health_level = "Low"

    # 建议
    recos = [
        "If dizziness or recent falls are present, consider supervised ambulation and a home safety check.",
        "Aim for consistent sleep timing; reduce late caffeine and screen exposure.",
        "Hydration and gradual warm-up may reduce transient gait instability.",
        "This demo report is not medical advice; consult a clinician for interpretation.",
    ]
    if health_level == "Low":
        recos.insert(0, "Health index appears low in this demo cycle—prioritize assistive support and remove trip hazards.")
    elif health_level == "Moderate":
        recos.insert(0, "Health index appears reduced—monitor gait stability and consider balance exercises.")

    # 整体状态
    overall = "Stable"
    if fall_level == "High" or any(m["status"] == "high" for m in metrics):
        overall = "Attention"
    elif fall_level == "Moderate" or any(m["status"] in ("low", "high") for m in metrics):
        overall = "Watch"

    # 动态主题区块
    sections = []

    if len(selected_modality_ids) >= 2:
        sections.append({
            "id": "integrated_risk",
            "title": theme_definitions["integrated_risk"]["title"],
            "status": overall.lower(),
            "priority": 85 + min(10, len(selected_modality_ids)),
            "source_modalities": selected_sources("integrated_risk"),
            "chart_type": "radar",
            "chart": {"labels": radar_labels, "values": [float(x) for x in radar_values]},
            "metrics": [
                metric(
                    "Health index",
                    health_index * 100,
                    "%",
                    "70-100",
                    "normal" if health_index >= 0.7 else "low"
                ),
                metric("Data coverage", len(selected_modality_ids), "modalities", "2+", "normal"),
            ],
            "insight": "Cross-modal evidence is summarized into a single protected health profile.",
        })

    mobility_metrics = metric_pick("Cadence")
    if selected_sources("mobility"):
        sections.append({
            "id": "mobility",
            "title": theme_definitions["mobility"]["title"],
            "status": "attention" if mobility_r > 0.55 else "stable",
            "priority": abnormality_score(mobility_metrics) + int(mobility_r * 60) + 20,
            "source_modalities": selected_sources("mobility"),
            "chart_type": "stability",
            "chart": {
                "score": float(1.0 - mobility_r),
                "trend": [float(x) for x in np.clip(np.linspace(1.0 - mobility_r * 0.7, 1.0 - mobility_r, 8), 0, 1).tolist()],
                "drift": float(uwb_drift),
                "gait_variability": float(gait_var),
            },
            "metrics": mobility_metrics + [
                metric("Movement drift", uwb_drift, "", "<0.08", "high" if uwb_drift > 0.08 else "normal"),
            ],
            "insight": "Movement stability is estimated from gait variability and radar motion drift.",
        })

    vitals_metrics = metric_pick("Heart rate", "Resp. rate", "Blood pressure", "SpO₂")
    if selected_sources("vitals"):
        sections.append({
            "id": "vitals",
            "title": theme_definitions["vitals"]["title"],
            "status": section_status(vitals_metrics),
            "priority": abnormality_score(vitals_metrics) + int(cardio_r * 30) + int(bp_r * 30),
            "source_modalities": selected_sources("vitals"),
            "chart_type": "reference_bars",
            "chart": {
                "labels": ["HR", "RR", "SBP", "SpO2"],
                "values": [float(hr_bpm if not np.isnan(hr_bpm) else 75.0), float(rr_bpm if not np.isnan(rr_bpm) else 16.0), float(sbp), float(spo2)],
                "ranges": {"HR": [60, 100], "RR": [12, 20], "SBP": [90, 120], "SpO2": [95, 100]},
            },
            "metrics": vitals_metrics[:4],
            "insight": "Cardiorespiratory proxies are compared against demo reference bands.",
        })

    sleep_metrics = metric_pick("Sleep efficiency", "Resp. rate")
    if selected_sources("sleep"):
        sections.append({
            "id": "sleep",
            "title": theme_definitions["sleep"]["title"],
            "status": "attention" if sleep_eff < 85 else "stable",
            "priority": abnormality_score(sleep_metrics) + int(sleep_r * 55),
            "source_modalities": selected_sources("sleep"),
            "chart_type": "recovery_bars",
            "chart": {
                "labels": ["Sleep efficiency", "Recovery", "Resp. regularity"],
                "values": [float(sleep_eff), float(100 * (1.0 - sleep_r)), float(100 * (1.0 - cardio_r * 0.4))],
            },
            "metrics": sleep_metrics,
            "insight": "Sleep and recovery are estimated from depth posture and respiratory rhythm signals.",
        })

    if selected_sources("activity"):
        sections.append({
            "id": "activity",
            "title": theme_definitions["activity"]["title"],
            "status": "stable",
            "priority": 35 + int((mix[0] + mix[1]) * 30),
            "source_modalities": selected_sources("activity"),
            "chart_type": "stacked_mix",
            "chart": {"labels": activity_labels, "values": [float(x) for x in mix.tolist()]},
            "metrics": [
                metric("Walk share", float(mix[0] * 100), "%", "demo mix", "normal"),
                metric("Rest share", float((mix[2] + mix[3]) * 100), "%", "demo mix", "normal"),
            ],
            "insight": "Activity mix summarizes the selected motion and visual behavior signals.",
        })

    medical_sources = selected_sources("medical_screening")
    if medical_sources:
        image_results = [item for item in results if str(item.get("model_id", "")).lower() in {"retina", "chest", "path", "blood"}]
        sections.append({
            "id": "medical_screening",
            "title": theme_definitions["medical_screening"]["title"],
            "status": "watch" if any(str(item.get("status", "")).lower() != "normal" for item in image_results) else "stable",
            "priority": 40 + 10 * len(image_results),
            "source_modalities": medical_sources,
            "chart_type": "risk_tiles",
            "chart": {
                "tiles": [
                    {"label": item.get("model", item.get("model_id", "Image")), "score": item.get("score"), "status": item.get("status", "normal")}
                    for item in image_results
                ],
            },
            "metrics": [
                metric("Image sources", len(medical_sources), "modalities", "1+", "normal"),
            ],
            "insight": "Medical imaging signals are summarized as demo screening tiles.",
        })

    order_index = {theme_id: index for index, theme_id in enumerate(theme_order)}
    sections.sort(key=lambda item: (-int(item.get("priority", 0)), order_index.get(item["id"], 99)))
    expanded_ids = {item["id"] for item in sections[:3]}
    expanded_sections = [{**item, "expanded": item["id"] in expanded_ids} for item in sections[:3]]
    compact_sections = [{**item, "expanded": False} for item in sections[3:]]

    missing_signals = []
    for theme_id in theme_order:
        if theme_id == "integrated_risk":
            if len(selected_modality_ids) < 2:
                missing_signals.append({
                    "theme_id": theme_id,
                    "title": theme_definitions[theme_id]["title"],
                    "missing_modalities": [],
                    "message": "Select at least two modalities to unlock integrated cross-modal risk summary.",
                })
            continue
        if selected_sources(theme_id):
            continue
        missing_signals.append({
            "theme_id": theme_id,
            "title": theme_definitions[theme_id]["title"],
            "missing_modalities": theme_definitions[theme_id]["modalities"],
            "message": f"Add {', '.join(theme_definitions[theme_id]['modalities'])} to unlock {theme_definitions[theme_id]['title']}.",
        })

    # 叙述性报告
    narrative = (
        f"Overall status: {overall}. Health index estimate: {health_level} (score={health_index:.2f}).\n"
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
        "summary": {
            "title": "Integrated Summary",
            "health_index": float(health_index),
            "overall": overall,
            "drivers": drivers[:4],
            "coverage": {
                "selected_modalities": selected_modality_ids,
                "available_theme_count": len(sections),
                "total_theme_count": len(theme_order),
            },
        },
        "missing_signals": missing_signals,
        "sections": expanded_sections,
        "compact_sections": compact_sections,
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
    if not ZHIPU_API_KEY:
        return "ZhipuAI is not configured. Returning a fallback protected conclusion."
    try:
        headers = {
            "Authorization": f"Bearer {ZHIPU_API_KEY}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": ZHIPU_MODEL,
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
                return "ZhipuAI returned success, but response format was unexpected."

    except Exception as e:
        return f"ZhipuAI call failed, using fallback protected conclusion: {str(e)}"

@app.get("/api/health")
async def health_check():
    """健康检查"""
    return {"status": "healthy", "version": "3.1-complete", "timestamp": time.time()}

@app.get("/api/modalities")
async def get_modalities():
    """获取所有可用的模态配置，包括文件信息"""
    try:
        config_path = os.path.join(BASE_DIR, "backend", "modality_config.json")
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)

        # 添加文件信息到每个模态
        test_data_dir = os.path.join(BASE_DIR, "test_data")

        for modality in config.get("modalities", []):
            modality_id = modality["id"]
            file_info = get_modality_file_info(modality_id, test_data_dir)
            modality["files"] = file_info

        return config

    except Exception as e:
        # 如果配置文件不存在，返回默认配置
        default_config = {
            "modalities": [
                {"id": "depth", "name": "Depth Camera", "type": "image", "description": "Sleep posture detection", "icon": "🛏️"},
                {"id": "uwb", "name": "UWB Radar", "type": "timeseries", "description": "Heart rate and blood pressure monitoring", "icon": "📡"},
                {"id": "imu", "name": "IMU Sensor", "type": "timeseries", "description": "Gait and metabolic assessment", "icon": "🏃"},
                {"id": "csi", "name": "WiFi CSI", "type": "timeseries", "description": "Heart rate and respiration monitoring", "icon": "📶"},
                {"id": "rgb", "name": "RGB Camera", "type": "image", "description": "Risk scoring and activity assessment", "icon": "📷"},
                {"id": "ntu", "name": "NTU Skeleton", "type": "skeleton", "description": "Action recognition and behavior analysis", "icon": "🦴"},
                {"id": "retina", "name": "Retina Image", "type": "medical_image", "description": "Early cardiovascular risk screening", "icon": "👁️"},
                {"id": "chest", "name": "Chest X-ray", "type": "medical_image", "description": "Lung condition screening", "icon": "🫁"},
                {"id": "path", "name": "Pathology Image", "type": "medical_image", "description": "Cancer screening", "icon": "🔬"},
                {"id": "blood", "name": "Blood Cell Image", "type": "medical_image", "description": "Hematology screening", "icon": "🩸"}
            ]
        }

        # 添加文件信息
        test_data_dir = os.path.join(BASE_DIR, "test_data")
        for modality in default_config["modalities"]:
            modality_id = modality["id"]
            file_info = get_modality_file_info(modality_id, test_data_dir)
            modality["files"] = file_info

        return default_config

def get_modality_file_info(modality_id: str, test_data_dir: str) -> list:
    """获取指定模态的可用文件列表"""
    file_mapping = {
        "uwb": ["uwb_sample.txt"],
        "imu": ["imu_sample.txt"],
        "csi": ["csi_sample.csv"],
        "ntu": ["ntu_sample.txt"],
        "retina": ["retina_sample.npz"],
        "chest": ["chest_sample.npz"],
        "path": ["path_sample.npz"],
        "blood": ["blood_sample.npz"],
        "depth": ["depth_sample.png"],
        "rgb": ["rgb_sample.png"]
    }

    files = file_mapping.get(modality_id, [])
    file_info_list = []

    for filename in files:
        filepath = os.path.join(test_data_dir, filename)
        if os.path.exists(filepath):
            size = os.path.getsize(filepath)
            file_info_list.append({
                "name": filename,
                "path": filepath,
                "size": size,
                "size_human": format_size(size)
            })

    return file_info_list

def format_size(size_bytes: int) -> str:
    """格式化文件大小为人类可读格式"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} TB"

@app.get("/api/modality_thumbnail")
async def get_modality_thumbnail(modality: str):
    """获取指定模态的缩略图预览 - 返回原始数据供前端Canvas绘制"""
    try:
        # 标准化模态名称
        normalized_name = normalize_modality_name(modality)
        print(f"Thumbnail request: {modality} -> {normalized_name}")

        # 加载模态数据
        try:
            data = get_data(normalized_name)
        except FileNotFoundError as e:
            print(f"Data file not found for {normalized_name}: {e}")
            return {"thumbnail": None, "error": f"Data not found for {modality}"}

        if data is None:
            return {"thumbnail": None, "error": "Modality not found"}

        # 确定数据类型
        if normalized_name in ["Depth", "RGB"]:
            data_type = "image"
        elif normalized_name in ["Retina", "Chest", "Path", "Blood"]:
            data_type = "medical_image"
        elif normalized_name == "NTU":
            data_type = "skeleton"
        else:
            data_type = "timeseries"

        print(f"📊 Modality: {modality} -> {normalized_name}, data_type: {data_type}")

        # 🎨 返回原始数据，前端用Canvas绘制
        result = {
            "modality": modality,
            "type": data_type,
            "data": None,
            "shape": None,
            "channels": None
        }

        if data_type == "timeseries":
            # 时序数据：返回原始数据数组
            result["data"] = data.T.tolist() if data.ndim > 1 else data.tolist()
            result["shape"] = list(data.shape)
            result["channels"] = data.shape[1] if data.ndim > 1 else 1
            print(f"   Timeseries data: {data.shape} -> {len(result['data'])} channels x {len(result['data'][0])} samples")

        elif data_type == "skeleton":
            # 骨架数据：返回关键点
            result["data"] = data.tolist() if isinstance(data, np.ndarray) else data
            result["shape"] = list(data.shape) if isinstance(data, np.ndarray) else [25, 3]
            print(f"   Skeleton data: {result['shape']}")

        elif data_type in ["image", "medical_image"]:
            # 图像数据：读取PNG文件
            if normalized_name == "Depth":
                img_path = DEPTH_PNG_PATH
            elif normalized_name == "RGB":
                img_path = RGB_PNG_PATH
            else:
                # 医学图像从npz文件加载
                img_path = os.path.join(BASE_DIR, "test_data", f"{normalized_name.lower()}_sample.npz")

            # 读取PNG或NPZ文件并转换为base64
            if img_path.endswith('.png'):
                with open(img_path, 'rb') as f:
                    img_data = f.read()
                    result["thumbnail"] = b64e(img_data)
                    print(f"   Image thumbnail: {len(img_data)} bytes")
            else:
                # NPZ文件 - 加载第一张图像
                npz_data = np.load(img_path)
                if 'train_images' in npz_data:
                    img = npz_data['train_images'][0]
                elif 'images' in npz_data:
                    img = npz_data['images'][0]
                else:
                    # 直接使用image字段（可能只有一张图像）
                    img = npz_data[list(npz_data.keys())[0]]
                    # 如果img是3D的(N,H,W)且N=1，取第一张
                    if img.ndim == 3 and img.shape[0] == 1:
                        img = img[0]
                    # 如果img是4D的(N,H,W,C)，取第一张
                    elif img.ndim == 4:
                        img = img[0]

                # 转换为PNG
                import io
                from PIL import Image
                # 归一化到0-255范围
                img_array = (img * 255).astype(np.uint8) if img.max() <= 1 else img.astype(np.uint8)
                # 处理不同格式的图像数据
                if img_array.ndim == 3 and img_array.shape[-1] == 1:
                    img_array = img_array.squeeze(-1)  # 移除单通道维度
                elif img_array.ndim == 2:
                    pass  # 已经是灰度图
                elif img_array.ndim == 3:
                    pass  # RGB图像

                # 确定图像模式
                if img_array.ndim == 2:
                    img_pil = Image.fromarray(img_array, mode='L')
                else:
                    img_pil = Image.fromarray(img_array)

                img_bytes = io.BytesIO()
                img_pil.save(img_bytes, format='PNG')
                result["thumbnail"] = b64e(img_bytes.getvalue())
                print(f"   Medical image thumbnail generated: {img_array.shape} -> {len(img_bytes.getvalue())} bytes")

        return result

    except Exception as e:
        print(f"生成缩略图失败 ({modality}): {e}")
        import traceback
        traceback.print_exc()
        return {"thumbnail": None, "error": str(e)}

def _selected_flags(selected_modalities: Optional[str]) -> Dict[str, Any]:
    modality_config = load_modality_config()
    enabled_modalities = resolve_enabled_modalities(selected_modalities, modality_config)
    return {
        "enabled_modalities": enabled_modalities,
        "depth": find_selected_modality(enabled_modalities, "Depth"),
        "uwb": find_selected_modality(enabled_modalities, "UWB"),
        "imu": find_selected_modality(enabled_modalities, "IMU"),
        "csi": find_selected_modality(enabled_modalities, "CSI"),
        "rgb": find_selected_modality(enabled_modalities, "RGB"),
        "ntu": find_selected_modality(enabled_modalities, "NTU"),
        "retina": find_selected_modality(enabled_modalities, "Retina"),
        "chest": find_selected_modality(enabled_modalities, "Chest"),
        "path": find_selected_modality(enabled_modalities, "Path"),
        "blood": find_selected_modality(enabled_modalities, "Blood"),
    }

def _build_step1(flags: Dict[str, Any]) -> Dict[str, Any]:
    step_start = time.time()
    uwb_data = get_data("UWB") if flags["uwb"] else None
    imu_data = get_data("IMU") if flags["imu"] else None
    csi_data = get_data("CSI") if flags["csi"] else None

    uwb_series = uwb_data.reshape(-1, 3) if uwb_data is not None else None
    imu_series = imu_data.reshape(-1, 6) if imu_data is not None else None
    csi_series = csi_data[:, 1:] if csi_data is not None else None
    modalities = {}

    if flags["depth"]:
        modalities["Depth"] = {
            "kind": "image",
            "type": "image",
            "shape": "64×64",
            "preview_png": png_b64_from_file(DEPTH_PNG_PATH) or "",
            "plaintext_excerpt": "Depth map for sleep posture detection",
        }
    if flags["uwb"] and uwb_series is not None:
        modalities["UWB"] = {
            "kind": "timeseries",
            "type": "timeseries",
            "shape": f"{uwb_series.shape[0]}×{uwb_series.shape[1]}",
            "channels": uwb_series.shape[1],
            "preview_png": plot_multichannel_preview(uwb_series, "UWB Multichannel Analysis (3 Channels)", max_channels=3),
            "plaintext_excerpt": excerpt_array(uwb_series, rows=4, cols=3),
            "fft_png": "",
            "raw_data": uwb_series.T.tolist(),
        }
    if flags["imu"] and imu_series is not None:
        modalities["IMU"] = {
            "kind": "timeseries",
            "type": "timeseries",
            "shape": f"{imu_series.shape[0]}×{imu_series.shape[1]}",
            "channels": imu_series.shape[1],
            "preview_png": plot_multichannel_preview(imu_series, "IMU Multichannel Analysis (6 Channels)", max_channels=6),
            "plaintext_excerpt": excerpt_array(imu_series, rows=4, cols=6),
            "fft_png": "",
            "raw_data": imu_series.T.tolist(),
        }
    if flags["csi"] and csi_series is not None:
        modalities["CSI"] = {
            "kind": "timeseries",
            "type": "timeseries",
            "shape": f"{csi_series.shape[0]}×{csi_series.shape[1]}",
            "channels": csi_series.shape[1],
            "preview_png": plot_multichannel_preview(csi_series, "CSI Multichannel Analysis (8 Channels)", max_channels=8),
            "plaintext_excerpt": excerpt_array(csi_series, rows=4, cols=4),
            "fft_png": "",
            "spectrogram_png": "",
            "raw_data": csi_series.T.tolist(),
        }
    if flags["rgb"]:
        modalities["RGB"] = {
            "kind": "image",
            "type": "image",
            "shape": "64×64×3",
            "preview_png": png_b64_from_file(RGB_PNG_PATH) or "",
            "plaintext_excerpt": "RGB image for risk assessment",
        }
    for flag_name, modality_name, kind, excerpt in [
        ("ntu", "NTU", "skeleton", "Skeleton data for action recognition"),
        ("retina", "Retina", "medical_image", "Retinal fundus image for cardiovascular screening"),
        ("chest", "Chest", "medical_image", "Chest X-ray for lung disease screening"),
        ("path", "Path", "medical_image", "Pathology image for cancer detection"),
        ("blood", "Blood", "medical_image", "Blood cell image for hematology analysis"),
    ]:
        if flags[flag_name]:
            sample = _generate_medical_image_sample(modality_name)
            item = {
                "kind": "skeleton" if kind == "skeleton" else "image",
                "type": "skeleton" if kind == "skeleton" else "image",
                "shape": "25×3" if kind == "skeleton" else "224×224×3",
                "preview_png": generate_thumbnail(sample, kind),
                "plaintext_excerpt": excerpt,
            }
            if kind == "skeleton":
                item["keypoints"] = sample.reshape(25, 3).tolist()
            modalities[modality_name] = item

    return {
        "step1": {
            "time_sec": time.time() - step_start,
            "modalities": modalities,
            "enabled_modalities": flags["enabled_modalities"],
        },
        "series": {
            "uwb": uwb_series,
            "imu": imu_series,
            "csi": csi_series,
        },
    }

def _build_assignments(flags: Dict[str, Any]) -> List[Dict[str, str]]:
    pairs = [
        ("csi", "ecg", "secure_ecg_toolbox"),
        ("uwb", "bp", "secure_bp_toolbox"),
        ("depth", "sleep", "secure_sleep_toolbox"),
        ("imu", "metabolic", "secure_metabolic_toolbox"),
        ("rgb", "risk", "secure_risk_toolbox"),
        ("ntu", "action", "secure_action_toolbox"),
        ("retina", "cardio", "secure_cardio_toolbox"),
        ("chest", "lung", "secure_lung_toolbox"),
        ("path", "cancer", "secure_cancer_toolbox"),
        ("blood", "blood", "secure_blood_toolbox"),
    ]
    assignments = [
        {"input_modality": flags[key], "model_id": model_id, "tool": tool}
        for key, model_id, tool in pairs
        if flags[key]
    ]
    return assignments or [
        {"input_modality": "WiFi CSI", "model_id": "ecg", "tool": "secure_ecg_toolbox"},
        {"input_modality": "UWB Radar", "model_id": "bp", "tool": "secure_bp_toolbox"},
    ]

def _score_for_model(model_id: str) -> Dict[str, Any]:
    scores = {
        "ecg": (75.5, "normal"),
        "bp": (118.0, "normal"),
        "sleep": (85.2, "good"),
        "metabolic": (1650.0, "normal"),
        "risk": (0.25, "low"),
        "action": (92.5, "good"),
        "cardio": (88.0, "normal"),
        "lung": (94.2, "good"),
        "cancer": (15.8, "low"),
        "blood": (91.5, "normal"),
    }
    score, status = scores.get(model_id, (50.0, "unknown"))
    return {"score": score, "status": status}

def _build_step2(flags: Dict[str, Any], series: Dict[str, Optional[np.ndarray]]) -> Dict[str, Any]:
    step_start = time.time()
    uwb_series = series["uwb"]
    imu_series = series["imu"]
    csi_series = series["csi"]
    uwb_feat = feat_from_series(uwb_series) if uwb_series is not None else np.zeros(8)
    imu_feat = feat_from_series(imu_series) if imu_series is not None else np.zeros(8)
    csi_feat = feat_from_series(csi_series) if csi_series is not None else np.zeros(8)

    ctx = setup_context()
    enc_uwb = ts.ckks_vector(ctx, uwb_feat.tolist())
    enc_imu = ts.ckks_vector(ctx, imu_feat.tolist())
    _ = ts.ckks_vector(ctx, csi_feat.tolist())
    agg_bytes = enc_uwb.serialize() + enc_imu.serialize()[:100]

    assignments = _build_assignments(flags)
    results = []
    for assignment in assignments:
        model_meta = next((m for m in CLUSTER_MODELS if m["id"] == assignment["model_id"]), None)
        scored = _score_for_model(assignment["model_id"])
        results.append({
            "model": model_meta["title"] if model_meta else assignment["model_id"],
            "model_id": assignment["model_id"],
            "input_modality": assignment["input_modality"],
            "tool": assignment["tool"],
            "score": scored["score"],
            "status": scored["status"],
        })

    return {
        "step2": {
            "time_sec": time.time() - step_start,
            "llm_time_sec": 0.0,
            "summary": ", ".join([f"{a['input_modality']}→{a['tool']}" for a in assignments]),
            "cluster_models": CLUSTER_MODELS,
            "assignments": assignments,
            "tool_times": [0.8, 1.2, 0.9, 1.1, 0.7],
            "aggregate_cipher_preview": bytes_preview(agg_bytes, 160),
        },
        "raw_results": results,
    }


def _build_bucketed_section_prompt_summary(raw_report: Dict[str, Any]) -> List[Dict[str, Any]]:
    preferred_order = [
        "integrated_risk",
        "mobility",
        "vitals",
        "sleep",
        "activity",
        "medical_screening",
    ]
    order_index = {section_id: index for index, section_id in enumerate(preferred_order)}

    section_summaries = []
    seen_ids = set()
    section_candidates = list(raw_report.get("sections") or [])
    section_candidates.extend(raw_report.get("compact_sections") or [])

    def _section_id(section: Dict[str, Any]) -> str:
        if not isinstance(section, dict):
            return ""
        return str(section.get("id", ""))

    ordered_sections = sorted(
        [section for section in section_candidates if isinstance(section, dict)],
        key=lambda section: (
            order_index.get(_section_id(section), len(preferred_order) + 1),
            section.get("priority", 0),
        ),
    )

    deduped_sections = []
    for section in ordered_sections:
        section_id = _section_id(section)
        if section_id in seen_ids:
            continue
        seen_ids.add(section_id)
        deduped_sections.append(section)

    for section in deduped_sections[:3]:
        if not isinstance(section, dict):
            continue
        metrics = section.get("metrics") or []
        metric_names = []
        for metric in metrics:
            if isinstance(metric, dict) and metric.get("name"):
                metric_names.append(metric.get("name"))
        section_summaries.append({
            "title": section.get("title"),
            "status": section.get("status"),
            "sources": section.get("source_modalities"),
            "metric_names": metric_names,
        })
    return section_summaries


def _build_bucketed_llm_prompt(
    protected_llm_summary: Dict[str, Any],
    raw_report: Optional[Dict[str, Any]] = None,
) -> str:
    section_summary = _build_bucketed_section_prompt_summary(raw_report) if raw_report else []
    return (
        "You are a health monitoring analysis expert. "
        "The external model can only see a bucketed privacy-preserving summary. "
        f"Record: {protected_llm_summary['record']}; "
        f"Overall status: {protected_llm_summary['risk_profile']['overall']}; "
        f"Health index bucket: {protected_llm_summary['risk_profile']['fall_probability_bucket']}; "
        f"Metric summary: {protected_llm_summary['metrics']}; "
        f"Section summary: {section_summary}; "
        f"Model summary: {protected_llm_summary['model_results'][:3]}. "
        "Generate a concise and cautious health conclusion."
    )


def _build_synthetic_database_privacy(
    raw_results: List[Dict[str, Any]],
    raw_report: Dict[str, Any],
    rng: random.Random,
) -> Dict[str, Any]:
    real_record = build_real_data_record(raw_results, raw_report)
    synthetic_records = generate_synthetic_database(real_record, database_size=100, rng=rng)
    anonymous_bundle = build_anonymous_database(real_record, synthetic_records, rng=rng)
    protected_llm_summary = build_protected_llm_summary(anonymous_bundle["selected_record"])
    distribution_summary = build_distribution_summary(anonymous_bundle)
    return {
        "protected_llm_summary": protected_llm_summary,
        "privacy_protection": {
            "enabled": True,
            "method": "synthetic_database_shuffle",
            "database_size": len(anonymous_bundle["anonymous_database"]),
            "synthetic_record_count": distribution_summary["synthetic_record_count"],
            "distribution_summary": {
                "risk_buckets": distribution_summary["risk_buckets"],
                "scatter_points": distribution_summary["scatter_points"],
                "target_point": distribution_summary["target_point"],
                "axes": distribution_summary["axes"],
            },
            "token_flow": distribution_summary["token_flow"],
            "anonymous_database_preview": anonymous_bundle["anonymous_database_preview"],
            "shuffle_order_preview": anonymous_bundle["shuffle_order_preview"],
            "selected_record_label": anonymous_bundle["selected_record_label"],
            "selected_record_index": anonymous_bundle["selected_record_index"],
            "llm_summary_mode": "bucketed_non_trusted",
            "protected_llm_summary_preview": protected_llm_summary,
            "generation_policy": {
                "distribution": "risk-bucket conditioned",
                "constraints": [
                    "physiological range",
                    "cross-model consistency",
                    "activity mix normalization",
                ],
            },
            "summary": (
                "Synthetic database masks the real inference record before a bucketed summary "
                "is sent to the non-trusted LLM."
            ),
        },
    }


async def _build_privacy_and_report(session: Dict[str, Any]) -> Dict[str, Any]:
    step_start = time.time()
    series = session["series"]
    raw_results = session["raw_results"]
    uwb_for_report = series["uwb"] if series["uwb"] is not None else np.zeros((100, 3))
    imu_for_report = series["imu"] if series["imu"] is not None else np.zeros((250, 6))
    csi_for_report = series["csi"] if series["csi"] is not None else np.zeros((200, 8))
    session_modalities = session.get("selected_modalities")
    selected_modality_ids = [
        str(item).strip().lower()
        for item in (
            session_modalities
            if isinstance(session_modalities, (list, tuple))
            else (str(session_modalities).split(",") if session_modalities else [])
        )
        if str(item).strip()
    ]
    if not selected_modality_ids:
        session_modalities = (
            session.get("step1", {}).get("enabled_modalities", [])
            if isinstance(session.get("step1"), dict)
            else []
        )
        selected_modality_ids = [
            str(item).strip().lower()
            for item in (session_modalities if isinstance(session_modalities, (list, tuple)) else [session_modalities])
            if str(item).strip()
        ]

    selected_modality_ids = [normalize_modality_name(item).strip().lower() for item in selected_modality_ids]

    raw_report = build_health_report(
        raw_results,
        uwb_for_report,
        imu_for_report,
        csi_for_report,
        selected_modalities=selected_modality_ids,
    )
    rng = random.Random(session["seed"])
    privacy_bundle = _build_synthetic_database_privacy(raw_results, raw_report, rng)
    prompt = _build_bucketed_llm_prompt(
        privacy_bundle["protected_llm_summary"],
        raw_report=raw_report,
    )
    report_conclusion = await call_zhipu_llm(prompt)
    return {
        "step3": {
            "time_sec": time.time() - step_start,
            "results": raw_results,
            "report_conclusion": report_conclusion,
            "plaintext_prompt": prompt,
            "report": raw_report,
        },
        "privacy_protection": privacy_bundle["privacy_protection"],
    }

@app.get("/api/dispatch")
async def run_dispatch(selected_modalities: Optional[str] = None):
    start_time = time.time()
    session_seed = time.time_ns()
    flags = _selected_flags(selected_modalities)
    step1_bundle = _build_step1(flags)
    step2_bundle = _build_step2(flags, step1_bundle["series"])
    session_id = uuid.uuid4().hex
    _STAGED_SESSIONS[session_id] = {
        "seed": session_seed,
        "selected_modalities": selected_modalities,
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "step1": step1_bundle["step1"],
        "step2": step2_bundle["step2"],
        "series": step1_bundle["series"],
        "raw_results": step2_bundle["raw_results"],
    }
    return {
        "schema": "he-multimodal-dispatch/v1",
        "session_id": session_id,
        "generated_at": _STAGED_SESSIONS[session_id]["generated_at"],
        "step1": step1_bundle["step1"],
        "step2": step2_bundle["step2"],
        "data_source": "UT_HAR dataset",
        "llm_provider": "ZhipuAI",
    }

@app.get("/api/privacy_shuffle")
async def run_privacy_shuffle(session_id: str):
    session = _STAGED_SESSIONS.get(session_id)
    if not session:
        return {"error": "Unknown or expired session_id"}
    if "privacy_protection" not in session or "step3" not in session:
        session.update(await _build_privacy_and_report(session))
    plaintext_prompt = session.get("step3", {}).get("plaintext_prompt") or session.get("step3", {}).get("llm_prompt")
    return {
        "schema": "he-multimodal-privacy/v1",
        "session_id": session_id,
        "privacy_protection": session["privacy_protection"],
        "plaintext_prompt": plaintext_prompt,
    }

@app.get("/api/report")
async def run_report(session_id: str):
    session = _STAGED_SESSIONS.get(session_id)
    if not session:
        return {"error": "Unknown or expired session_id"}
    if "privacy_protection" not in session or "step3" not in session:
        session.update(await _build_privacy_and_report(session))
    return {
        "schema": "he-multimodal-report/v1",
        "session_id": session_id,
        "generated_at": session["generated_at"],
        "step3": session["step3"],
        "privacy_protection": session["privacy_protection"],
        "data_source": "UT_HAR dataset",
        "llm_provider": "ZhipuAI",
    }

@app.get("/api/cycle")
async def run_cycle(selected_modalities: Optional[str] = None):
    """执行完整的数据处理周期 - 支持选择性模态加载

    Args:
        selected_modalities: Optional comma-separated list of modalities to load
                           Example: "UWB,IMU,CSI" or "Depth,RGB"
    """
    start_time = time.time()
    cycle_seed = time.time_ns()

    # Load modality configuration
    modality_config = load_modality_config()
    enabled_modalities = resolve_enabled_modalities(selected_modalities, modality_config)
    selected_modality_ids = [
        normalize_modality_name(name).strip().lower()
        for name in enabled_modalities
        if normalize_modality_name(name).strip()
    ]

    selected_depth = find_selected_modality(enabled_modalities, "Depth")
    selected_uwb = find_selected_modality(enabled_modalities, "UWB")
    selected_imu = find_selected_modality(enabled_modalities, "IMU")
    selected_csi = find_selected_modality(enabled_modalities, "CSI")
    selected_rgb = find_selected_modality(enabled_modalities, "RGB")
    selected_ntu = find_selected_modality(enabled_modalities, "NTU")
    selected_retina = find_selected_modality(enabled_modalities, "Retina")
    selected_chest = find_selected_modality(enabled_modalities, "Chest")
    selected_path = find_selected_modality(enabled_modalities, "Path")
    selected_blood = find_selected_modality(enabled_modalities, "Blood")

    print(f"Enabled modalities for this cycle: {enabled_modalities}")

    # Step 1: 数据收集
    step1_start = time.time()
    try:
        # Only load selected modalities.
        uwb_data = get_data("UWB") if selected_uwb else None
        imu_data = get_data("IMU") if selected_imu else None
        csi_data = get_data("CSI") if selected_csi else None

        # 重塑数据 (only for loaded modalities)
        uwb_series = uwb_data.reshape(-1, 3) if uwb_data is not None else None
        imu_series = imu_data.reshape(-1, 6) if imu_data is not None else None
        csi_series = csi_data[:, 1:] if csi_data is not None else None

        # 生成增强的多通道预览图 (only for loaded modalities)
        uwb_preview = plot_multichannel_preview(uwb_series, "UWB Multichannel Analysis (3 Channels)", max_channels=3) if uwb_series is not None else ""
        imu_preview = plot_multichannel_preview(imu_series, "IMU Multichannel Analysis (6 Channels)", max_channels=6) if imu_series is not None else ""
        csi_preview = plot_multichannel_preview(csi_series, "CSI Multichannel Analysis (8 Channels)", max_channels=8) if csi_series is not None else ""

        # 生成增强的FFT频谱图 (only for loaded modalities)
        # 不生成FFT频谱图，简化处理
        uwb_fft = ""
        imu_fft = ""
        csi_fft = ""

        # CSI暂时不生成spectrogram（可选）
        csi_spectrogram = ""

        # 生成Depth和RGB预览 (only if enabled)
        depth_png = png_b64_from_file(DEPTH_PNG_PATH) if selected_depth else ""
        rgb_png = png_b64_from_file(RGB_PNG_PATH) if selected_rgb else ""

        step1_time = time.time() - step1_start

        # Build step1_data with only enabled modalities
        step1_modalities = {}

        if selected_depth:
            step1_modalities["Depth"] = {
                "kind": "image",
                "type": "image",
                "shape": "64×64",
                "preview_png": depth_png or "",
                "plaintext_excerpt": "Depth map for sleep posture detection"
            }

        if selected_uwb and uwb_series is not None:
            # 转置数据：从 (samples, channels) 到 (channels, samples)
            uwb_raw = uwb_series.T.tolist()  # 现在是 [3][samples]
            step1_modalities["UWB"] = {
                "kind": "timeseries",
                "type": "timeseries",
                "shape": f"{uwb_series.shape[0]}×{uwb_series.shape[1]}",
                "channels": uwb_series.shape[1],
                "preview_png": uwb_preview,
                "plaintext_excerpt": excerpt_array(uwb_series, rows=4, cols=3),
                "fft_png": uwb_fft,
                "raw_data": uwb_raw  # 新增：原始数据，格式为 [channels][samples]
            }

        if selected_imu and imu_series is not None:
            # 转置数据：从 (samples, channels) 到 (channels, samples)
            imu_raw = imu_series.T.tolist()  # 现在是 [6][samples]
            step1_modalities["IMU"] = {
                "kind": "timeseries",
                "type": "timeseries",
                "shape": f"{imu_series.shape[0]}×{imu_series.shape[1]}",
                "channels": imu_series.shape[1],
                "preview_png": imu_preview,
                "plaintext_excerpt": excerpt_array(imu_series, rows=4, cols=6),
                "fft_png": imu_fft,
                "raw_data": imu_raw  # 新增：原始数据，格式为 [channels][samples]
            }

        if selected_csi and csi_series is not None:
            # 转置数据：从 (samples, channels) 到 (channels, samples)
            csi_raw = csi_series.T.tolist()  # 现在是 [8][samples]
            step1_modalities["CSI"] = {
                "kind": "timeseries",
                "type": "timeseries",
                "shape": f"{csi_series.shape[0]}×{csi_series.shape[1]}",
                "channels": csi_series.shape[1],
                "preview_png": csi_preview,
                "plaintext_excerpt": excerpt_array(csi_series, rows=4, cols=4),
                "fft_png": csi_fft,
                "spectrogram_png": csi_spectrogram,
                "raw_data": csi_raw  # 新增：原始数据，格式为 [channels][samples]
            }

        if selected_rgb:
            step1_modalities["RGB"] = {
                "kind": "image",
                "type": "image",
                "shape": "64×64×3",
                "preview_png": rgb_png or "",
                "plaintext_excerpt": "RGB image for risk assessment"
            }

        # 新增的5种医学图像模态
        if selected_ntu:
            # 生成骨架关键点数据
            ntu_skeleton = _generate_medical_image_sample("NTU").reshape(25, 3)  # 25个关节点，每个3维
            step1_modalities["NTU"] = {
                "kind": "skeleton",
                "type": "skeleton",
                "shape": "25×3",
                "preview_png": generate_thumbnail(_generate_medical_image_sample("NTU"), "skeleton"),
                "plaintext_excerpt": "Skeleton data for action recognition",
                "keypoints": ntu_skeleton.tolist()  # 新增：25个关节点的3D坐标
            }

        if selected_retina:
            step1_modalities["Retina"] = {
                "kind": "image",
                "type": "image",
                "shape": "224×224×3",
                "preview_png": generate_thumbnail(_generate_medical_image_sample("Retina"), "medical_image"),
                "plaintext_excerpt": "Retinal fundus image for cardiovascular screening"
            }

        if selected_chest:
            step1_modalities["Chest"] = {
                "kind": "image",
                "type": "image",
                "shape": "224×224×3",
                "preview_png": generate_thumbnail(_generate_medical_image_sample("Chest"), "medical_image"),
                "plaintext_excerpt": "Chest X-ray for lung disease screening"
            }

        if selected_path:
            step1_modalities["Path"] = {
                "kind": "image",
                "type": "image",
                "shape": "224×224×3",
                "preview_png": generate_thumbnail(_generate_medical_image_sample("Path"), "medical_image"),
                "plaintext_excerpt": "Pathology image for cancer detection"
            }

        if selected_blood:
            step1_modalities["Blood"] = {
                "kind": "image",
                "type": "image",
                "shape": "224×224×3",
                "preview_png": generate_thumbnail(_generate_medical_image_sample("Blood"), "medical_image"),
                "plaintext_excerpt": "Blood cell image for hematology analysis"
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

        # LLM智能分配 (支持所有10种模态，使用完整模态名称)
        assignments = []
        if selected_csi:
            assignments.append({"input_modality": selected_csi, "model_id": "ecg", "tool": "secure_ecg_toolbox"})
        if selected_uwb:
            assignments.append({"input_modality": selected_uwb, "model_id": "bp", "tool": "secure_bp_toolbox"})
        if selected_depth:
            assignments.append({"input_modality": selected_depth, "model_id": "sleep", "tool": "secure_sleep_toolbox"})
        if selected_imu:
            assignments.append({"input_modality": selected_imu, "model_id": "metabolic", "tool": "secure_metabolic_toolbox"})
        if selected_rgb:
            assignments.append({"input_modality": selected_rgb, "model_id": "risk", "tool": "secure_risk_toolbox"})
        if selected_ntu:
            assignments.append({"input_modality": selected_ntu, "model_id": "action", "tool": "secure_action_toolbox"})
        if selected_retina:
            assignments.append({"input_modality": selected_retina, "model_id": "cardio", "tool": "secure_cardio_toolbox"})
        if selected_chest:
            assignments.append({"input_modality": selected_chest, "model_id": "lung", "tool": "secure_lung_toolbox"})
        if selected_path:
            assignments.append({"input_modality": selected_path, "model_id": "cancer", "tool": "secure_cancer_toolbox"})
        if selected_blood:
            assignments.append({"input_modality": selected_blood, "model_id": "blood", "tool": "secure_blood_toolbox"})

        # Fallback: if no modalities selected, use default assignment
        if not assignments:
            assignments = [
                {"input_modality": "WiFi CSI", "model_id": "ecg", "tool": "secure_ecg_toolbox"},
                {"input_modality": "UWB Radar", "model_id": "bp", "tool": "secure_bp_toolbox"},
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
            elif a["model_id"] == "action":
                score = 92.5
                status = "good"
            elif a["model_id"] == "cardio":
                score = 88.0
                status = "normal"
            elif a["model_id"] == "lung":
                score = 94.2
                status = "good"
            elif a["model_id"] == "cancer":
                score = 15.8
                status = "low"
            elif a["model_id"] == "blood":
                score = 91.5
                status = "normal"
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

        raw_results = results
        raw_report = build_health_report(
            raw_results,
            uwb_for_report,
            imu_for_report,
            csi_for_report,
            selected_modalities=selected_modality_ids,
        )
        rng = random.Random(cycle_seed)
        privacy_bundle = _build_synthetic_database_privacy(raw_results, raw_report, rng)
        llm_prompt = _build_bucketed_llm_prompt(
            privacy_bundle["protected_llm_summary"],
            raw_report=raw_report,
        )
        report_conclusion = await call_zhipu_llm(llm_prompt)

        step3_time = time.time() - step3_start

        step3_data = {
            "time_sec": step3_time,
            "results": raw_results,
            "report_conclusion": report_conclusion,
            "plaintext_prompt": llm_prompt,
            "report": raw_report,  # 完整的报告对象
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
        "privacy_protection": privacy_bundle["privacy_protection"],
        "data_source": "UT_HAR dataset",
        "llm_provider": "ZhipuAI"
    }

if __name__ == "__main__":
    import uvicorn
    print("Starting complete backend server on port 8082...")
    print("Data source: UT_HAR dataset")
    print("Features: Full original visualization + ZhipuAI + Health charts")
    uvicorn.run(app, host="127.0.0.1", port=8082)
