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
  'RGB': '#8b5cf6',      // 紫

  // 财务类
  'Income': '#0f766e',
  'Expenses': '#dc2626',
  'Savings': '#2563eb',
  'Loan': '#9333ea',
  'Credit': '#ca8a04',
  'Profile': '#475569'
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
  },
  'income': {
    id: 'income',
    name: 'Income',
    type: 'finance',
    icon: '$',
    description: 'Salary, recurring income, and income stability',
    fields: ['monthly_income_usd', 'income_stability', 'employment_tenure_months'],
    color: MODALITY_COLORS.Income
  },
  'expenses': {
    id: 'expenses',
    name: 'Expenses',
    type: 'finance',
    icon: '$',
    description: 'Recurring spending and monthly obligation load',
    fields: ['monthly_expenses_usd', 'fixed_obligations_usd', 'expense_volatility'],
    color: MODALITY_COLORS.Expenses
  },
  'savings': {
    id: 'savings',
    name: 'Savings',
    type: 'finance',
    icon: '$',
    description: 'Cash reserves and emergency-fund resilience',
    fields: ['savings_balance_usd', 'emergency_fund_months', 'monthly_savings_rate'],
    color: MODALITY_COLORS.Savings
  },
  'loan': {
    id: 'loan',
    name: 'Loan',
    type: 'finance',
    icon: '$',
    description: 'Debt balance, payment pressure, and loan stress',
    fields: ['loan_balance_usd', 'monthly_payment_usd', 'debt_to_income_ratio'],
    color: MODALITY_COLORS.Loan
  },
  'credit': {
    id: 'credit',
    name: 'Credit',
    type: 'finance',
    icon: '$',
    description: 'Credit score, utilization, and repayment risk',
    fields: ['credit_score', 'credit_utilization', 'missed_payments_12m'],
    color: MODALITY_COLORS.Credit
  },
  'profile': {
    id: 'profile',
    name: 'Profile',
    type: 'finance',
    icon: '$',
    description: 'Household context and financial profile signals',
    fields: ['age_band', 'household_size', 'risk_tolerance'],
    color: MODALITY_COLORS.Profile
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
  const normalizedKeypoints = Array.isArray(keypoints) && keypoints.length >= 75 && !Array.isArray(keypoints[0])
    ? Array.from({ length: 25 }, (_, index) => keypoints.slice(index * 3, index * 3 + 3))
    : keypoints;
  if (!Array.isArray(normalizedKeypoints) || !Array.isArray(normalizedKeypoints[0])) return null;

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
  const allX = normalizedKeypoints.map(pt => pt[0]);
  const allY = normalizedKeypoints.map(pt => pt[1]);
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

  const points = normalizedKeypoints.map(pt => {
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

function escapeCardText(value) {
  if (value === null || value === undefined) return '';
  return String(value)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function formatFinanceFieldName(fieldName) {
  return String(fieldName || '')
    .replace(/[_-]+/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
}

function normalizeFinancePreviewRows(preview, fields, description) {
  if (Array.isArray(preview) && preview.length) {
    return preview.slice(0, 3).map((item, index) => {
      if (item && typeof item === 'object') {
        const label = item.label || item.name || item.metric || `Field ${index + 1}`;
        const value = item.value ?? item.amount ?? item.text ?? item.status ?? 'Ready';
        return { label, value };
      }
      return { label: `Field ${index + 1}`, value: item };
    });
  }

  if (preview && typeof preview === 'object' && Object.keys(preview).length) {
    return Object.entries(preview).slice(0, 3).map(([label, value]) => ({ label, value }));
  }

  if (preview !== null && preview !== undefined && String(preview).trim()) {
    return [{ label: 'Preview', value: preview }];
  }

  if (Array.isArray(fields) && fields.length) {
    return fields.slice(0, 3).map(field => ({
      label: formatFinanceFieldName(field),
      value: 'field'
    }));
  }

  return [{ label: 'Data group', value: description || 'Ready' }];
}

function compactFinanceLabel(label) {
  const text = formatFinanceFieldName(label).toLowerCase();
  if (text.includes('income')) return 'Income';
  if (text.includes('expense') || text.includes('spending')) return 'Spend';
  if (text.includes('saving') || text.includes('reserve')) return 'Reserve';
  if (text.includes('loan') || text.includes('emi') || text.includes('payment')) return 'Payment';
  if (text.includes('debt')) return 'DTI';
  if (text.includes('credit')) return 'Score';
  if (text.includes('employment')) return 'Employment';
  if (text.includes('region')) return 'Region';
  if (text.includes('date')) return 'Date';
  if (text.includes('age')) return 'Age';
  return formatFinanceFieldName(label).split(' ').slice(0, 2).join(' ') || 'Signal';
}

function financeVisualLevels(modalityId) {
  const presets = {
    income: [62, 82, 48],
    expenses: [78, 54, 66],
    savings: [35, 58, 88],
    loan: [64],
    credit: [72],
    profile: [82, 58, 70]
  };
  return presets[modalityId] || [55, 72, 44];
}

function financeDateAxisLabels(count = 3) {
  const base = new Date();
  return Array.from({ length: count }, (_, index) => {
    const date = new Date(base.getFullYear(), base.getMonth() - (count - 1 - index), base.getDate());
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    return `${month}/${day}`;
  });
}

function createFinanceBarsHTML(config, rows, variantClass) {
  const levels = financeVisualLevels(config.id);
  const dateLabels = financeDateAxisLabels(3);
  const bars = levels.slice(0, 3).map((height, index) => {
    const row = rows[index] || rows[rows.length - 1] || { label: `Signal ${index + 1}` };
    const metricLabel = compactFinanceLabel(row.label);
    return `
      <span class="finance-bar" style="--h:${height}%" title="${escapeCardText(metricLabel)}">
        <i></i>
        <em class="finance-date-label">${escapeCardText(dateLabels[index])}</em>
      </span>
    `;
  }).join('');

  return `
    <div class="finance-chart ${variantClass}" aria-hidden="true">
      <div class="finance-chart-grid"></div>
      <div class="finance-bars">${bars}</div>
    </div>
  `;
}

function createFinanceGaugeHTML(config, rows, label) {
  const value = financeVisualLevels(config.id)[0];
  const caption = rows[0] ? compactFinanceLabel(rows[0].label) : label;
  return `
    <div class="finance-gauge-wrap" aria-hidden="true">
      <div class="finance-gauge" style="--gauge:${value * 3.6}deg">
        <span>Risk</span>
      </div>
      <div class="finance-gauge-meta">
        <strong>${escapeCardText(label)}</strong>
        <span>${escapeCardText(caption)}</span>
      </div>
    </div>
  `;
}

function createFinanceCreditHTML(config, rows) {
  const value = financeVisualLevels(config.id)[0];
  const labels = rows.slice(0, 2).map(row => compactFinanceLabel(row.label));
  return `
    <div class="finance-credit-chart" aria-hidden="true">
      <div class="finance-credit-band">
        <span class="finance-credit-marker" style="left:${value}%"></span>
      </div>
      <div class="finance-credit-scale">
        <span>300</span>
        <strong>${escapeCardText(labels[0] || 'Score')}</strong>
        <span>850</span>
      </div>
      <div class="finance-credit-tags">
        ${(labels.length ? labels : ['Score', 'DTI']).map(item => `<em>${escapeCardText(item)}</em>`).join('')}
      </div>
    </div>
  `;
}

function createFinanceProfileHTML(rows) {
  const labels = rows.slice(0, 3).map(row => compactFinanceLabel(row.label));
  const chipHtml = (labels.length ? labels : ['Employment', 'Region', 'Date']).map((label, index) => `
    <span class="finance-profile-chip" style="--i:${index}">
      <i></i>${escapeCardText(label)}
    </span>
  `).join('');

  return `
    <div class="finance-profile-map" aria-hidden="true">
      <div class="finance-profile-orbit">
        <span></span><span></span><span></span>
      </div>
      <div class="finance-profile-chips">${chipHtml}</div>
    </div>
  `;
}

function createFinancePreviewHTML(modalityData, config) {
  const rows = normalizeFinancePreviewRows(
    modalityData && modalityData.preview,
    (modalityData && modalityData.fields) || config.fields,
    (modalityData && modalityData.description) || config.description
  );
  const visualByType = {
    income: createFinanceBarsHTML(config, rows, 'finance-chart-income'),
    expenses: createFinanceBarsHTML(config, rows, 'finance-chart-expenses'),
    savings: createFinanceBarsHTML(config, rows, 'finance-chart-savings'),
    loan: createFinanceGaugeHTML(config, rows, 'Loan stress'),
    credit: createFinanceCreditHTML(config, rows),
    profile: createFinanceProfileHTML(rows)
  };
  const visualHtml = visualByType[config.id] || createFinanceBarsHTML(config, rows, 'finance-chart-generic');

  return `
    <div class="card-visual finance-card-preview" style="--finance-color: ${escapeCardText(config.color)}">
      ${visualHtml}
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
  const uploaded = Boolean(modalityData && modalityData.uploaded && modalityData.thumbnail);
  const defaultThumbnail = Boolean(!uploaded && modalityData && modalityData.thumbnail);
  const uploadedAttr = uploaded ? 'data-uploaded="true"' : 'data-uploaded="false"';
  const showReplaceButton = (
    uploaded ||
    defaultThumbnail ||
    config.type === 'finance' ||
    config.type === 'timeseries' ||
    config.type === 'skeleton'
  );
  const replaceButton = showReplaceButton
    ? `<button class="modality-replace-btn" type="button" data-modality-upload="${config.id}">Select</button>`
    : '';

  let visualContent = '';

  if (uploaded) {
    visualContent = `
      <div class="card-visual">
        <img src="data:image/png;base64,${escapeCardText(modalityData.thumbnail)}"
             alt="${config.name}"
             class="card-thumbnail" />
      </div>
    `;
    console.log(`✅ ${modalityKey} 卡片生成: 使用上传图片`);
  } else if (config.type === 'finance') {
    visualContent = createFinancePreviewHTML(modalityData, config);
    console.log(`💳 ${modalityKey} 卡片生成: 使用财务预览`);
  } else if (config.type === 'image' && defaultThumbnail) {
    visualContent = `
      <div class="card-visual" data-default-preview="true">
        <img src="data:image/png;base64,${escapeCardText(modalityData.thumbnail)}"
             alt="${config.name}"
             class="card-thumbnail" />
      </div>
    `;
    console.log(`✅ ${modalityKey} 卡片生成: 使用默认缩略图`);
  } else if (config.type === 'timeseries') {
    visualContent = `
      <div class="card-visual" data-default-preview="true">
        <canvas id="${cardId}-canvas" class="card-canvas"></canvas>
      </div>
    `;
    console.log(`🎨 ${modalityKey} 卡片生成: 使用默认时序Canvas`);
  } else if (config.type === 'skeleton') {
    visualContent = `
      <div class="card-visual" data-default-preview="true">
        <canvas id="${cardId}-canvas" class="skeleton-canvas"></canvas>
      </div>
    `;
    console.log(`🎨 ${modalityKey} 卡片生成: 使用默认骨架Canvas`);
  } else {
    visualContent = `
      <div class="card-visual">
        <button class="modality-upload-empty" type="button" data-modality-upload="${config.id}" aria-label="Upload image for ${config.name}">
          <span class="modality-upload-plus">+</span>
          <span class="modality-upload-text">Upload image</span>
        </button>
      </div>
    `;
    console.log(`⬜ ${modalityKey} 卡片生成: 等待上传图片`);
  }

  return `
    <div class="modality-card" id="${cardId}" data-modality="${modalityKey}" ${uploadedAttr}>
      ${replaceButton}
      <div class="card-title">${config.name}</div>
      ${visualContent}
      <input class="modality-upload-input" type="file" accept="image/*" data-modality-file="${config.id}" hidden />
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
