/**
 * 模态卡片可视化组件
 * 支持10种模态的交互式预览
 */

// ========== 配置 ==========

const MODALITY_COLORS = {
  // 时序类
  'UWB': '#14b8a6',      // 青绿色 (Cyan-Green)
  'IMU': '#3b82f6',      // 蓝色 (Blue)
  'CSI': '#f97316',      // 橙色 (Orange)

  // 骨架类
  'NTU': '#ef4444',      // 红

  // 图像类
  'Retina': '#ec4899',   // 粉
  'Chest': '#6366f1',    // 靛蓝
  'Pathology': '#14b8a6',// 青
  'Blood': '#f43f5e',    // 玫红
  'Depth': '#3b82f6',    // 蓝
  'RGB': '#8b5cf6'       // 紫
};

const MODALITY_CONFIG = {
  'uwb': {
    id: 'uwb',
    name: 'UWB Radar',
    type: 'timeseries',
    channels: 3,
    icon: '📡',
    description: 'Blood pressure and motion monitoring',
    color: MODALITY_COLORS.UWB
  },
  'imu': {
    id: 'imu',
    name: 'IMU Sensor',
    type: 'timeseries',
    channels: 6,
    icon: '🏃',
    description: 'Gait analysis and metabolic assessment',
    color: MODALITY_COLORS.IMU
  },
  'csi': {
    id: 'csi',
    name: 'WiFi CSI',
    type: 'timeseries',
    channels: 8,
    icon: '📶',
    description: 'Heart rate and respiratory monitoring',
    color: MODALITY_COLORS.CSI
  },
  'ntu': {
    id: 'ntu',
    name: 'NTU',
    type: 'skeleton',
    icon: '🦴',
    description: 'Action recognition from skeleton data',
    color: MODALITY_COLORS.NTU
  },
  'retina': {
    id: 'retina',
    name: 'Retina',
    type: 'image',
    icon: '👁️',
    description: 'Retinal disease classification',
    color: MODALITY_COLORS.Retina
  },
  'chest': {
    id: 'chest',
    name: 'Chest',
    type: 'image',
    icon: '🫁',
    description: 'Thoracic disease classification',
    color: MODALITY_COLORS.Chest
  },
  'path': {
    id: 'path',
    name: 'Pathology',
    type: 'image',
    icon: '🔬',
    description: 'Pathology image classification',
    color: MODALITY_COLORS.Pathology
  },
  'blood': {
    id: 'blood',
    name: 'Blood',
    type: 'image',
    icon: '🩸',
    description: 'Blood cell classification',
    color: MODALITY_COLORS.Blood
  },
  'depth': {
    id: 'depth',
    name: 'Depth Camera',
    type: 'image',
    icon: '📷',
    description: 'Sleep posture detection',
    color: MODALITY_COLORS.Depth
  },
  'rgb': {
    id: 'rgb',
    name: 'RGB Camera',
    type: 'image',
    icon: '📷',
    description: 'Risk assessment and activity recognition',
    color: MODALITY_COLORS.RGB
  }
};

// 存储卡片状态（当前选中的通道等）
const cardStates = {};

// ========== 时序类：绘制真正的3D多通道时序线图 ==========

// ========== 时序类：绘制多通道波形图（2D简洁版） ==========

function drawTimeSeriesCard(canvasId, data, config) {
  const canvas = document.getElementById(canvasId);
  if (!canvas || !data) return null;

  const ctx = canvas.getContext('2d');
  const width = canvas.width = canvas.offsetWidth * 2;
  const height = canvas.height = 140 * 2;
  ctx.scale(2, 2);

  const displayWidth = width / 2;
  const displayHeight = height / 2;

  // 清空画布
  ctx.clearRect(0, 0, displayWidth, displayHeight);

  // ========== 数据格式说明 ==========
  // (传感器类型, 通道号, 采样点索引, 数值)
  // 例如：("UWB", 0, 10, 0.556) 表示UWB第1通道第11个采样点的值为0.556

  const numChannels = config.channels;
  const padding = { left: 45, right: 15, top: 15, bottom: 25 };
  const chartWidth = displayWidth - padding.left - padding.right;
  const chartHeight = displayHeight - padding.top - padding.bottom;

  // 计算每个通道的高度和间距
  const channelHeight = chartHeight / numChannels;
  const channelGap = 4;
  const waveHeight = channelHeight - channelGap * 2;

  // 计算全局数据范围
  let globalMin = Infinity;
  let globalMax = -Infinity;

  for (let ch = 0; ch < numChannels; ch++) {
    const channelData = data[ch] || [];
    if (channelData.length > 0) {
      globalMin = Math.min(globalMin, ...channelData);
      globalMax = Math.max(globalMax, ...channelData);
    }
  }

  const dataRange = globalMax - globalMin || 1;

  // 绘制每个通道
  for (let ch = 0; ch < numChannels; ch++) {
    const channelData = data[ch] || [];

    if (channelData.length > 1) {
      // 计算该通道的Y位置
      const channelTop = padding.top + ch * channelHeight;
      const waveTop = channelTop + channelGap;
      const waveBottom = waveTop + waveHeight;

      // 绘制通道背景区域
      ctx.fillStyle = ch % 2 === 0 ? '#f9f9f9' : '#ffffff';
      ctx.fillRect(padding.left, channelTop, chartWidth, channelHeight);

      // 绘制通道分隔线
      ctx.strokeStyle = '#e0e0e0';
      ctx.lineWidth = 0.5;
      ctx.beginPath();
      ctx.moveTo(padding.left, waveBottom);
      ctx.lineTo(displayWidth - padding.right, waveBottom);
      ctx.stroke();

      // 绘制通道标签
      ctx.font = 'bold 10px sans-serif';
      ctx.fillStyle = config.color;
      ctx.textAlign = 'right';
      ctx.textBaseline = 'middle';
      ctx.fillText(`Ch${ch + 1}`, padding.left - 8, waveTop + waveHeight / 2);

      // 绘制波形线
      ctx.beginPath();
      ctx.strokeStyle = config.color;
      ctx.lineWidth = 1.5;
      ctx.lineCap = 'round';
      ctx.lineJoin = 'round';

      const maxSamples = 100;
      const step = Math.max(1, Math.floor(channelData.length / maxSamples));

      let firstPoint = true;
      for (let i = 0; i < channelData.length; i += step) {
        // X坐标：采样点索引
        const x = padding.left + (i / (channelData.length - 1)) * chartWidth;

        // Y坐标：数值（归一化后翻转，因为Canvas Y轴向下）
        const normalizedVal = (channelData[i] - globalMin) / dataRange;
        const y = waveBottom - (normalizedVal * waveHeight);

        if (firstPoint) {
          ctx.moveTo(x, y);
          firstPoint = false;
        } else {
          ctx.lineTo(x, y);
        }
      }

      ctx.stroke();

      // 绘制参考线（中位数）
      const midY = waveTop + waveHeight / 2;
      ctx.strokeStyle = 'rgba(128, 128, 128, 0.3)';
      ctx.lineWidth = 1;
      ctx.setLineDash([4, 4]);
      ctx.beginPath();
      ctx.moveTo(padding.left, midY);
      ctx.lineTo(displayWidth - padding.right, midY);
      ctx.stroke();
      ctx.setLineDash([]);

      // 绘制最小值和最大值标签
      if (ch === 0) {
        ctx.font = '9px sans-serif';
        ctx.fillStyle = '#999';
        ctx.textAlign = 'left';
        ctx.fillText(globalMax.toFixed(2), padding.left + 5, padding.top + 10);
        ctx.fillText(globalMin.toFixed(2), padding.left + 5, displayHeight - padding.bottom - 5);
      }
    }
  }

  // 绘制X轴标签（采样点索引）
  ctx.font = '9px sans-serif';
  ctx.fillStyle = '#666';
  ctx.textAlign = 'center';
  ctx.fillText('Sample index ->', padding.left + chartWidth / 2, displayHeight - 8);

  return null;
}

// 辅助函数：将hex颜色转换为rgba
function hexToRgba(hex, alpha) {
  const r = parseInt(hex.slice(1, 3), 16);
  const g = parseInt(hex.slice(3, 5), 16);
  const b = parseInt(hex.slice(5, 7), 16);
  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

// ========== 骨架类：绘制火柴人 ==========

function drawSkeletonCard(canvasId, keypoints) {
  const canvas = document.getElementById(canvasId);
  if (!canvas || !keypoints) return null;

  const ctx = canvas.getContext('2d');
  const width = canvas.width = canvas.offsetWidth * 2;
  const height = canvas.height = 100 * 2;
  ctx.scale(2, 2);

  const displayWidth = width / 2;
  const displayHeight = height / 2;

  ctx.clearRect(0, 0, displayWidth, displayHeight);

  // NTU 25个关节点，简化为15个主要点
  // 映射：选择主要的关节点
  const mainJoints = [
    0,   // 0: base of spine
    1,   // 1: middle of spine
    20,  // 20: head
    2,   // 2: left shoulder
    5,   // 5: right shoulder
    3,   // 3: left elbow
    6,   // 6: right elbow
    4,   // 4: left wrist
    7,   // 7: right wrist
    8,   // 8: left hip
    11,  // 11: right hip
    9,   // 9: left knee
    12,  // 12: right knee
    10,  // 10: left ankle
    13,  // 13: right ankle
    21,  // 21: neck (between spine and head)
    22   // 22: left hand (optional, can skip)
  ];

  // 骨骼连接关系
  const bones = [
    [0, 1],     // spine base to middle
    [1, 21],    // middle to neck
    [21, 20],   // neck to head
    [21, 2],    // neck to left shoulder
    [21, 5],    // neck to right shoulder
    [2, 3],     // left shoulder to elbow
    [3, 4],     // left elbow to wrist
    [5, 6],     // right shoulder to elbow
    [6, 7],     // right elbow to wrist
    [0, 8],     // spine base to left hip
    [0, 11],    // spine base to right hip
    [8, 9],     // left hip to knee
    [9, 10],    // left knee to ankle
    [11, 12],   // right hip to knee
    [12, 13]    // right knee to ankle
  ];

  // 计算实际坐标范围并归一化到画布
  const allX = keypoints.map(pt => pt[0]);
  const allY = keypoints.map(pt => pt[1]);
  const minX = Math.min(...allX), maxX = Math.max(...allX);
  const minY = Math.min(...allY), maxY = Math.max(...allY);

  const rangeX = maxX - minX || 1;
  const rangeY = maxY - minY || 1;

  // 添加padding，确保图形不会贴边
  const padding = 15;
  const scaleX = (displayWidth - padding * 2) / rangeX;
  const scaleY = (displayHeight - padding * 2) / rangeY;
  const scale = Math.min(scaleX, scaleY) * 1.8; // 放大1.8倍，让点间距更大

  // 计算居中偏移
  const scaledWidth = rangeX * scale;
  const scaledHeight = rangeY * scale;
  const offsetX = (displayWidth - scaledWidth) / 2 - minX * scale;
  const offsetY = (displayHeight - scaledHeight) / 2 - minY * scale;

  const points = keypoints.map(pt => {
    const x = pt[0] * scale + offsetX;
    const y = displayHeight - (pt[1] * scale + offsetY); // y轴翻转
    return [x, y];
  });

  // 绘制骨骼连接线
  ctx.strokeStyle = MODALITY_COLORS.NTU;
  ctx.lineWidth = 2;
  ctx.lineCap = 'round';

  bones.forEach(([i, j]) => {
    if (i < mainJoints.length && j < mainJoints.length) {
      const pt1 = points[mainJoints[i]];
      const pt2 = points[mainJoints[j]];

      if (pt1 && pt2) {
        ctx.beginPath();
        ctx.moveTo(pt1[0], pt1[1]);
        ctx.lineTo(pt2[0], pt2[1]);
        ctx.stroke();
      }
    }
  });

  // 绘制关节点
  mainJoints.forEach(jointIdx => {
    if (jointIdx < points.length) {
      const [x, y] = points[jointIdx];

      // 创建径向渐变
      const gradient = ctx.createRadialGradient(x, y, 0, x, y, 6);
      gradient.addColorStop(0, MODALITY_COLORS.NTU);
      gradient.addColorStop(1, MODALITY_COLORS.NTU + '40');

      ctx.beginPath();
      ctx.arc(x, y, 5, 0, Math.PI * 2);
      ctx.fillStyle = gradient;
      ctx.fill();

      ctx.strokeStyle = '#fff';
      ctx.lineWidth = 1;
      ctx.stroke();
    }
  });
}

// ========== 图像类：生成HTML ==========

function createImageCardHTML(modalityKey, imagePath) {
  const config = MODALITY_CONFIG[modalityKey];
  if (!config) return '';

  return `
    <div class="card-image-container">
      <img src="${imagePath}" alt="${config.name}" class="card-thumbnail" />
    </div>
  `;
}

// ========== 统一卡片生成器 ==========

function createModalityCard(modalityKey, modalityData) {
  const config = MODALITY_CONFIG[modalityKey];
  if (!config) {
    console.warn(`Unknown modality: ${modalityKey}`);
    return '';
  }

  const cardId = `modality-${config.id}`;

  let visualContent = '';

  // 根据类型决定初始显示内容
  if (config.type === 'image') {
    // 图像类：显示PNG缩略图
    if (modalityData.thumbnail) {
      visualContent = `
        <div class="card-visual">
          <img src="data:image/png;base64,${modalityData.thumbnail}"
               alt="${config.name}"
               class="card-thumbnail" />
        </div>
      `;
      console.log(`✅ ${modalityKey} 卡片生成: 使用PNG缩略图`);
    } else {
      visualContent = `
        <div class="card-visual">
          <div class="card-loading"></div>
        </div>
      `;
      console.warn(`⚠️ ${modalityKey} 卡片生成: 无缩略图`);
    }
  } else if (config.type === 'timeseries') {
    // 时序类：创建Canvas元素用于绘制3D波形
    visualContent = `
      <div class="card-visual">
        <canvas id="${cardId}-canvas" class="card-canvas"></canvas>
      </div>
    `;
    console.log(`🎨 ${modalityKey} 卡片生成: 创建时序Canvas（${config.channels}通道）`);
  } else if (config.type === 'skeleton') {
    // 骨架类：创建Canvas元素用于绘制火柴人
    visualContent = `
      <div class="card-visual">
        <canvas id="${cardId}-canvas" class="skeleton-canvas"></canvas>
      </div>
    `;
    console.log(`🎨 ${modalityKey} 卡片生成: 创建骨架Canvas`);
  } else {
    // 默认占位符或加载动画
    visualContent = `
      <div class="card-visual">
        <div class="card-loading"></div>
      </div>
    `;
    console.warn(`⚠️ ${modalityKey} 卡片生成: 未知类型 ${config.type}`);
  }

  return `
    <div class="modality-card" id="${cardId}" data-modality="${modalityKey}">
      <div class="card-title">${config.name}</div>
      ${visualContent}
    </div>
  `;
}

// ========== 初始化交互 ==========

function initializeCardInteractions() {
  // 卡片hover效果已通过CSS实现

  // 点击选择功能由 modality-selector.js 处理
  const container = document.getElementById('modalitySelector');
  if (container) {
    container.addEventListener('click', (e) => {
      const card = e.target.closest('.modality-card');
      if (card && window.ModalitySelector) {
        const modality = card.dataset.modality;
        // 触发选择逻辑（需要与ModalitySelector集成）
        console.log('Card clicked:', modality);
      }
    });
  }
}

// ========== 导出 ==========

window.ModalityCards = {
  createModalityCard,
  initializeCardInteractions,
  MODALITY_CONFIG,
  MODALITY_COLORS,
  drawTimeSeriesCard,
  drawSkeletonCard,
  createImageCardHTML
};

console.log('✅ ModalityCards component loaded');
