/**
 * 模态卡片可视化组件
 * 支持10种模态的交互式预览
 */

// ========== 配置 ==========

const MODALITY_COLORS = {
  // 时序类
  'UWB': '#10b981',      // 绿
  'IMU': '#f59e0b',      // 橙
  'CSI': '#8b5cf6',      // 紫

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
    name: 'RetinaMNIST',
    type: 'image',
    icon: '👁️',
    description: 'Retinal disease classification',
    color: MODALITY_COLORS.Retina
  },
  'chest': {
    id: 'chest',
    name: 'ChestMNIST',
    type: 'image',
    icon: '🫁',
    description: 'Thoracic disease classification',
    color: MODALITY_COLORS.Chest
  },
  'path': {
    id: 'path',
    name: 'PathMNIST',
    type: 'image',
    icon: '🔬',
    description: 'Pathology image classification',
    color: MODALITY_COLORS.Pathology
  },
  'blood': {
    id: 'blood',
    name: 'BloodMNIST',
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

// ========== 时序类：绘制多通道波形图 ==========

function drawTimeSeriesCard(canvasId, data, config) {
  const canvas = document.getElementById(canvasId);
  if (!canvas || !data) return null;

  const ctx = canvas.getContext('2d');
  const width = canvas.width = canvas.offsetWidth * 2; // Retina屏支持
  const height = canvas.height = 80 * 2;
  ctx.scale(2, 2);

  const displayWidth = width / 2;
  const displayHeight = height / 2;

  // 初始化状态
  if (!cardStates[canvasId]) {
    cardStates[canvasId] = {
      currentChannel: 0,
      channels: config.channels
    };
  }

  const state = cardStates[canvasId];
  const currentChannel = state.currentChannel;

  // 数据是二维数组 [channels, samples]
  const channelData = data[currentChannel] || [];

  // 计算所有通道的RMS值（能量）
  const channelEnergies = [];
  for (let ch = 0; ch < config.channels; ch++) {
    const chData = data[ch] || [];
    const rms = Math.sqrt(chData.reduce((sum, val) => sum + val * val, 0) / chData.length);
    channelEnergies.push(rms);
  }

  // 归一化能量
  const maxEnergy = Math.max(...channelEnergies, 1e-6);
  const normalizedEnergies = channelEnergies.map(e => e / maxEnergy);

  // 清空画布
  ctx.clearRect(0, 0, displayWidth, displayHeight);

  // 绘制当前通道波形
  if (channelData.length > 1) {
    // 找到当前通道的数据范围
    const minVal = Math.min(...channelData);
    const maxVal = Math.max(...channelData);
    const range = maxVal - minVal || 1;

    // 创建渐变
    const gradient = ctx.createLinearGradient(0, 0, 0, displayHeight - 20);
    gradient.addColorStop(0, config.color + '40'); // 25% 透明度
    gradient.addColorStop(1, config.color + '05'); // 几乎透明

    // 绘制波形
    ctx.beginPath();
    ctx.strokeStyle = config.color;
    ctx.lineWidth = 1.5;

    const stepX = displayWidth / (channelData.length - 1);

    for (let i = 0; i < channelData.length; i++) {
      const x = i * stepX;
      const normalizedY = (channelData[i] - minVal) / range;
      const y = displayHeight - 20 - normalizedY * (displayHeight - 30);

      if (i === 0) {
        ctx.moveTo(x, y);
      } else {
        // 使用贝塞尔曲线平滑
        const prevX = (i - 1) * stepX;
        const prevNormalizedY = (channelData[i - 1] - minVal) / range;
        const prevY = displayHeight - 20 - prevNormalizedY * (displayHeight - 30);

        const cpX = (prevX + x) / 2;
        ctx.quadraticCurveTo(cpX, prevY, cpX, (prevY + y) / 2);
        ctx.quadraticCurveTo(cpX, y, x, y);
      }
    }

    ctx.stroke();

    // 填充渐变
    ctx.lineTo(displayWidth, displayHeight - 20);
    ctx.lineTo(0, displayHeight - 20);
    ctx.closePath();
    ctx.fillStyle = gradient;
    ctx.fill();
  }

  // 绘制通道指示器
  ctx.font = '10px sans-serif';
  ctx.fillStyle = '#64748b';
  ctx.textAlign = 'center';
  ctx.fillText(`Channel ${currentChannel + 1}/${config.channels}`, displayWidth / 2, 12);

  // 绘制能量条
  const barWidth = 8;
  const barGap = 4;
  const totalBarsWidth = config.channels * barWidth + (config.channels - 1) * barGap;
  const startX = (displayWidth - totalBarsWidth) / 2;
  const barBaseY = displayHeight - 5;
  const maxHeight = 12;

  for (let ch = 0; ch < config.channels; ch++) {
    const x = startX + ch * (barWidth + barGap);
    const height = normalizedEnergies[ch] * maxHeight;
    const y = barBaseY - height;

    // 当前通道高亮
    if (ch === currentChannel) {
      ctx.fillStyle = config.color;
      ctx.shadowColor = config.color;
      ctx.shadowBlur = 8;
    } else {
      ctx.fillStyle = '#cbd5e1';
      ctx.shadowBlur = 0;
    }

    ctx.fillRect(x, y, barWidth, height);
    ctx.shadowBlur = 0; // 重置阴影
  }

  // 返回点击处理函数
  return function handleClick(event) {
    const rect = canvas.getBoundingClientRect();
    const x = event.clientX - rect.left;
    const y = event.clientY - rect.top;

    // 检查是否点击在能量条区域
    if (y > rect.height - 25) {
      const relativeX = x * 2; // 考虑Retina缩放
      if (relativeX >= startX && relativeX <= startX + totalBarsWidth) {
        const clickedBar = Math.floor((relativeX - startX) / (barWidth + barGap));
        if (clickedBar >= 0 && clickedBar < config.channels) {
          state.currentChannel = clickedBar;
          drawTimeSeriesCard(canvasId, data, config);
        }
      }
    }
  };
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
    // 时序类：创建Canvas元素用于绘制波形图
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
    // 默认占位符
    visualContent = `
      <div class="card-visual">
        <div class="canvas-placeholder" id="${cardId}-canvas">
          <div class="placeholder-text">数据类型: ${config.type}</div>
        </div>
      </div>
    `;
    console.log(`🎨 ${modalityKey} 卡片生成: 使用占位符（${config.type}）`);
  }

  return `
    <div class="modality-card" id="${cardId}" data-modality="${modalityKey}">
      <div class="card-title">${config.name}</div>
      ${visualContent}
      <div class="card-desc">${config.description}</div>
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
