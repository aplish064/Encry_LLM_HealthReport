#!/usr/bin/env python3
"""
增强的多通道可视化函数 - 简化版
"""
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from io import BytesIO
import base64

def b64e(fig):
    """将图表转换为base64"""
    bio = BytesIO()
    fig.savefig(bio, format="png", dpi=120, bbox_inches="tight")
    plt.close(fig)
    return base64.b64encode(bio.getvalue()).decode("ascii")

def plot_multichannel_enhanced(data: np.ndarray, title: str, max_channels: int = 6) -> str:
    """生成增强的多通道预览图 - 简化版"""
    if data.ndim == 1:
        data = data.reshape(-1, 1)

    n_channels = min(data.shape[1], max_channels)

    # 根据通道数选择布局
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
            stats_text = f'μ={mean_val:.2f}\nσ={std_val:.2f}\n[{min_val:.2f}, {max_val:.2f}]'
            ax.text(0.98, 0.02, stats_text, transform=ax.transAxes,
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
        colors = ['#3b82f6', '#8b5cf6', '#ec4899', '#f59e0b', '#10b981', '#ef4444']

        for idx, i in enumerate(selected_indices):
            channel = data[:, i]
            mean_val = np.mean(channel)
            ax_main.plot(channel, linewidth=1.5, color=colors[idx % len(colors)], alpha=0.8,
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

        bar_colors = [colors[i % len(colors)] for i in range(len(selected_indices))]
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
                color = 'black' if abs(val) < 0.5 else 'white'
                ax_corr.text(j, i, f'{val:.2f}',
                          ha="center", va="center", fontsize=7, color=color)

        plt.colorbar(im, ax=ax_corr, label='Correlation')

    plt.tight_layout()
    return b64e(fig)

# 测试
if __name__ == "__main__":
    # 创建测试数据
    test_uwb = np.random.randn(200, 3)
    test_imu = np.random.randn(250, 6)
    test_csi = np.random.randn(200, 8) + 15

    print("🧪 测试增强的多通道可视化...")
    result_uwb = plot_multichannel_enhanced(test_uwb, "UWB Test", max_channels=3)
    print(f"✅ UWB图表生成成功，大小: {len(result_uwb)} 字符")

    result_imu = plot_multichannel_enhanced(test_imu, "IMU Test", max_channels=6)
    print(f"✅ IMU图表生成成功，大小: {len(result_imu)} 字符")

    result_csi = plot_multichannel_enhanced(test_csi, "CSI Test", max_channels=8)
    print(f"✅ CSI图表生成成功，大小: {len(result_csi)} 字符")
