/**
 * 模态选择器 - 管理模态卡片交互
 */

class ModalitySelector {
  constructor() {
    this.selectedModalities = new Set();
    this.maxSelection = 5;
    this.modalities = [];
    this.init();
  }

  async init() {
    try {
      await this.loadModalities();
      this.renderCards();
      this.attachEventListeners();
    } catch (error) {
      console.error('模态选择器初始化失败:', error);
    }
  }

  async loadModalities() {
    try {
      const response = await fetch('/api/modalities');
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      const data = await response.json();
      this.modalities = data.modalities || [];
    } catch (error) {
      console.error('加载模态配置失败:', error);
      // 使用默认配置
      this.modalities = this.getDefaultModalities();
    }
  }

  getDefaultModalities() {
    return [
      {
        id: 'depth',
        name: '深度图像',
        type: 'image',
        description: '睡眠姿态检测',
        icon: '🛏️'
      },
      {
        id: 'uwb',
        name: 'UWB雷达',
        type: 'timeseries',
        description: '心率、血压监测',
        icon: '📡'
      },
      {
        id: 'imu',
        name: 'IMU传感器',
        type: 'timeseries',
        description: '步态分析、代谢评估',
        icon: '🏃'
      },
      {
        id: 'csi',
        name: 'CSI信号',
        type: 'timeseries',
        description: '心率、呼吸监测',
        icon: '📶'
      },
      {
        id: 'rgb',
        name: 'RGB图像',
        type: 'image',
        description: '风险评分、跌倒检测',
        icon: '📷'
      },
      {
        id: 'ntu',
        name: 'NTU骨骼',
        type: 'skeleton',
        description: '动作识别、行为分析',
        icon: '🦴'
      },
      {
        id: 'retina',
        name: '视网膜图像',
        type: 'medical_image',
        description: '心血管疾病早期预警',
        icon: '👁️'
      },
      {
        id: 'chest',
        name: '胸部X光',
        type: 'medical_image',
        description: '肺部疾病筛查',
        icon: '🫁'
      },
      {
        id: 'path',
        name: '组织病理',
        type: 'medical_image',
        description: '癌症筛查',
        icon: '🔬'
      },
      {
        id: 'blood',
        name: '血细胞',
        type: 'medical_image',
        description: '血液疾病诊断',
        icon: '🩸'
      }
    ];
  }

  renderCards() {
    const container = document.getElementById('modalitySelector');
    if (!container) return;

    container.innerHTML = '';

    this.modalities.forEach(modality => {
      const card = document.createElement('div');
      card.className = 'modality-card';
      card.dataset.modalityId = modality.id;
      card.dataset.modalityName = modality.name;

      card.innerHTML = `
        <div class="card-icon">${modality.icon}</div>
        <div class="card-title">${modality.name}</div>
        <div class="card-desc">${modality.description}</div>
      `;

      container.appendChild(card);
    });
  }

  attachEventListeners() {
    const container = document.getElementById('modalitySelector');
    const analyzeBtn = document.getElementById('analyzeBtn');

    if (container) {
      container.addEventListener('click', (e) => {
        const card = e.target.closest('.modality-card');
        if (card) {
          this.handleCardClick(card);
        }
      });
    }

    if (analyzeBtn) {
      analyzeBtn.addEventListener('click', () => {
        this.launchAnalysis();
      });
    }
  }

  handleCardClick(card) {
    const modalityId = card.dataset.modalityId;

    if (this.selectedModalities.has(modalityId)) {
      // 取消选择
      this.selectedModalities.delete(modalityId);
      card.classList.remove('active');
    } else {
      // 检查是否超过最大选择数
      if (this.selectedModalities.size >= this.maxSelection) {
        this.showWarning(`最多只能选择${this.maxSelection}种模态`);
        return;
      }

      // 添加选择
      this.selectedModalities.add(modalityId);
      card.classList.add('active');
    }

    this.updateUI();
  }

  updateUI() {
    // 更新选择计数
    const countElement = document.getElementById('selectedCount');
    if (countElement) {
      countElement.textContent = this.selectedModalities.size;
    }

    // 更新按钮状态
    const analyzeBtn = document.getElementById('analyzeBtn');
    if (analyzeBtn) {
      analyzeBtn.disabled = this.selectedModalities.size === 0;
    }
  }

  showWarning(message) {
    // 简单的警告提示
    alert(message);
  }

  async launchAnalysis() {
    if (this.selectedModalities.size === 0) {
      this.showWarning('请至少选择一种模态');
      return;
    }

    const selectedList = Array.from(this.selectedModalities).join(',');

    try {
      // 显示进度条
      this.showProgress();

      // 调用后端API进行分析
      const response = await fetch(`/api/cycle?selected_modalities=${encodeURIComponent(selectedList)}`);

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();

      // 显示加密动画
      this.showEncryptionAnimation();

      // 处理结果
      this.handleResults(data);

    } catch (error) {
      console.error('分析失败:', error);
      this.showWarning('分析失败，请重试');
      this.hideProgress();
    }
  }

  showProgress() {
    const progressContainer = document.getElementById('progressContainer');
    if (progressContainer) {
      progressContainer.style.display = 'block';
    }
    this.updateProgress(0, '准备中...');
  }

  hideProgress() {
    const progressContainer = document.getElementById('progressContainer');
    if (progressContainer) {
      progressContainer.style.display = 'none';
    }
  }

  updateProgress(percent, text) {
    const progressFill = document.getElementById('progressFill');
    const progressText = document.getElementById('progressText');

    if (progressFill) {
      progressFill.style.width = `${percent}%`;
    }

    if (progressText) {
      progressText.textContent = text;
    }
  }

  showEncryptionAnimation() {
    const animationContainer = document.getElementById('encryptionAnimation');
    if (animationContainer) {
      animationContainer.style.display = 'block';

      const stage = document.getElementById('encryptionStage');

      // 三阶段动画：明文 → 加密中 → 密文
      const stages = [
        { text: '📊 原始数据', class: 'plaintext' },
        { text: '🔒 加密中...', class: 'encrypting' },
        { text: '🔐 已加密', class: 'ciphertext' }
      ];

      let currentStage = 0;

      const showNextStage = () => {
        if (currentStage < stages.length) {
          const s = stages[currentStage];
          stage.innerHTML = `
            <div class="data-row">
              <span class="${s.class}">${s.text}</span>
            </div>
          `;
          stage.className = 'encryption-stage';
          currentStage++;
          setTimeout(showNextStage, 1000);
        } else {
          // 动画完成，隐藏
          setTimeout(() => {
            animationContainer.style.display = 'none';
          }, 2000);
        }
      };

      showNextStage();
    }
  }

  handleResults(data) {
    // 隐藏进度条
    this.hideProgress();

    // 显示缩略图
    this.showThumbnails(data);

    // 触发结果更新事件
    window.dispatchEvent(new CustomEvent('analysisComplete', { detail: data }));
  }

  showThumbnails(data) {
    const thumbnailsGrid = document.getElementById('thumbnailsGrid');
    if (!thumbnailsGrid) return;

    thumbnailsGrid.style.display = 'grid';
    thumbnailsGrid.innerHTML = '';

    // 从步骤1数据中提取缩略图
    if (data.step1 && data.step1.modalities) {
      data.step1.modalities.forEach(mod => {
        if (mod.thumbnail) {
          const thumbnail = document.createElement('div');
          thumbnail.className = 'thumbnail-item';
          thumbnail.innerHTML = `
            <img src="data:image/png;base64,${mod.thumbnail}" alt="${mod.name}">
            <div class="thumbnail-label">${mod.name}</div>
          `;
          thumbnailsGrid.appendChild(thumbnail);
        }
      });
    }
  }
}

// 初始化模态选择器
document.addEventListener('DOMContentLoaded', () => {
  new ModalitySelector();
});
