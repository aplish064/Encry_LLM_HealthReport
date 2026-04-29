/**
 * 模态选择器 - 管理模态卡片交互
 */

class ModalitySelector {
  constructor() {
    this.selectedModalities = new Set();
    this.maxSelection = 10; // 支持最多10种模态
    this.modalities = [];
    this.isLoading = false;
    this.retryCount = 0;
    this.maxRetries = 3;
    this.apiTimeout = 30000; // 30 seconds
    this.modalityThumbnails = {}; // 存储模态缩略图
    this.init();
  }

  async init() {
    try {
      this.setLoadingState(true);
      await this.loadModalities();
      await this.loadModalityThumbnails(); // 加载缩略图
      this.renderCards();
      this.attachEventListeners();
    } catch (error) {
      console.error('模态选择器初始化失败:', error);
      this.showError('初始化失败，请刷新页面重试');
    } finally {
      this.setLoadingState(false);
    }
  }

  async loadModalities() {
    try {
      // 使用全局API_BASE（在app.js中定义）
      const apiBase = (typeof API_BASE !== 'undefined') ? API_BASE : "http://127.0.0.1:8082";
      const response = await this.fetchWithTimeout(`${apiBase}/api/modalities`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json'
        }
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      this.modalities = data.modalities || [];
    } catch (error) {
      console.error('加载模态配置失败:', error);

      if (error.name === 'AbortError') {
        throw new Error('请求超时，请检查网络连接');
      }

      if (!navigator.onLine) {
        throw new Error('网络连接已断开，请检查网络');
      }

      // 使用默认配置
      this.modalities = this.getDefaultModalities();
      this.showWarning('使用默认模态配置');
    }
  }

  async loadModalityThumbnails() {
    // 加载每个模态的缩略图预览
    const apiBase = (typeof API_BASE !== 'undefined') ? API_BASE : "http://127.0.0.1:8082";

    // 为每个模态请求缩略图
    const thumbnailPromises = this.modalities.map(async (modality) => {
      try {
        const response = await this.fetchWithTimeout(
          `${apiBase}/api/modality_thumbnail?modality=${encodeURIComponent(modality.name)}`,
          { method: 'GET' }
        );

        if (response.ok) {
          const data = await response.json();
          if (data.thumbnail) {
            this.modalityThumbnails[modality.name] = data.thumbnail;
          }
        }
      } catch (error) {
        console.warn(`无法加载 ${modality.name} 的缩略图:`, error);
        // 使用默认图标
        this.modalityThumbnails[modality.name] = null;
      }
    });

    // 并行加载所有缩略图，但不阻塞初始化
    Promise.all(thumbnailPromises).then(() => {
      // 缩略图加载完成后重新渲染卡片
      this.renderCards();
    }).catch(err => {
      console.warn('部分缩略图加载失败:', err);
    });
  }

  async fetchWithTimeout(url, options = {}, timeout = this.apiTimeout) {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeout);

    try {
      const response = await fetch(url, {
        ...options,
        signal: controller.signal
      });
      clearTimeout(timeoutId);
      return response;
    } catch (error) {
      clearTimeout(timeoutId);
      throw error;
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

      // 使用缩略图或默认图标
      const thumbnailData = this.modalityThumbnails[modality.name];
      const iconDisplay = thumbnailData
        ? `<img src="data:image/png;base64,${thumbnailData}" class="card-thumbnail" alt="${modality.name}">`
        : `<div class="card-icon">${modality.icon || '📊'}</div>`;

      card.innerHTML = `
        ${iconDisplay}
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

    // 动态更新Step 2的工具集群显示
    this.updateModelCluster();
  }

  updateModelCluster() {
    // 根据选中的模态更新Step 2的Homomorphic Prediction Model Cluster
    const clusterGrid = document.getElementById('modelCluster');
    if (!clusterGrid) {
      console.warn('modelCluster element not found');
      return;
    }

    // 清空现有内容
    clusterGrid.innerHTML = '';

    // 模态ID到工具的映射关系（使用小写ID）
    const modalityToolMap = {
      'depth': { id: 'sleep', title: 'Sleep Staging', subtitle: 'Depth-based Model', icon: '🛏️' },
      'uwb': { id: 'bp', title: 'Blood Pressure', subtitle: 'UWB Regression', icon: '📡' },
      'imu': { id: 'metabolic', title: 'Metabolic Score', subtitle: 'IMU Proxy', icon: '🏃' },
      'csi': { id: 'ecg', title: 'ECG Arrhythmia', subtitle: 'CSI Heart Pattern', icon: '📶' },
      'rgb': { id: 'risk', title: 'Risk Assessment', subtitle: 'RGB Triage', icon: '📷' },
      'ntu': { id: 'action', title: 'Action Recognition', subtitle: 'Skeleton Model', icon: '🦴' },
      'retina': { id: 'cardio', title: 'Cardiovascular', subtitle: 'Retina Analysis', icon: '👁️' },
      'chest': { id: 'lung', title: 'Lung Screening', subtitle: 'X-ray Analysis', icon: '🫁' },
      'path': { id: 'cancer', title: 'Cancer Detection', subtitle: 'Pathology Model', icon: '🔬' },
      'blood': { id: 'blood', title: 'Blood Analysis', subtitle: 'Hematology Model', icon: '🩸' }
    };

    console.log('Selected modalities:', Array.from(this.selectedModalities));

    // 为每个选中的模态创建工具卡片
    this.selectedModalities.forEach(modalityId => {
      const tool = modalityToolMap[modalityId];
      if (tool) {
        const toolCard = document.createElement('div');
        toolCard.className = 'clusterCard';
        toolCard.innerHTML = `
          <div class="clusterIcon">${tool.icon}</div>
          <div class="clusterCardTitle">${tool.title}</div>
          <div class="clusterCardSubtitle">${tool.subtitle}</div>
        `;
        clusterGrid.appendChild(toolCard);
        console.log(`Added tool card for ${modalityId}:`, tool);
      } else {
        console.warn(`No tool mapping found for ${modalityId}`);
      }
    });

    // 如果没有选中任何模态，显示提示
    if (this.selectedModalities.size === 0) {
      clusterGrid.innerHTML = '<div style="grid-column: 1/-1; text-align: center; color: #6b7280; padding: 20px;">请选择模态以查看对应的工具</div>';
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

    if (this.isLoading) {
      this.showWarning('正在处理中，请稍候...');
      return;
    }

    const selectedList = Array.from(this.selectedModalities).join(',');

    try {
      this.setLoadingState(true);
      this.showProgress();
      this.updateProgress(10, '准备分析...');

      // 调用后端API进行分析，带重试机制
      const data = await this.launchAnalysisWithRetry(selectedList);

      this.updateProgress(100, '分析完成');

      // 显示加密动画
      this.showEncryptionAnimation();

      // 处理结果
      this.handleResults(data);

    } catch (error) {
      console.error('分析失败:', error);
      this.handleAnalysisError(error);
    } finally {
      this.setLoadingState(false);
    }
  }

  async launchAnalysisWithRetry(selectedList, attempt = 1) {
    try {
      this.updateProgress(20, `正在分析... (尝试 ${attempt}/${this.maxRetries})`);

      // 使用全局API_BASE（在app.js中定义）
      const apiBase = (typeof API_BASE !== 'undefined') ? API_BASE : "http://127.0.0.1:8082";
      const response = await this.fetchWithTimeout(
        `${apiBase}/api/cycle?selected_modalities=${encodeURIComponent(selectedList)}`,
        {
          method: 'GET',
          headers: {
            'Content-Type': 'application/json'
          }
        }
      );

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.message || `HTTP error! status: ${response.status}`);
      }

      this.updateProgress(80, '处理结果...');

      const data = await response.json();

      // 重置重试计数
      this.retryCount = 0;

      return data;

    } catch (error) {
      console.error(`分析尝试 ${attempt} 失败:`, error);

      if (attempt < this.maxRetries) {
        this.retryCount = attempt;

        // 显示重试提示
        this.updateProgress(0, `分析失败，${2}秒后重试...`);

        // 等待2秒后重试
        await new Promise(resolve => setTimeout(resolve, 2000));

        return this.launchAnalysisWithRetry(selectedList, attempt + 1);
      } else {
        // 达到最大重试次数
        throw error;
      }
    }
  }

  handleAnalysisError(error) {
    this.hideProgress();

    let errorMessage = '分析失败，请重试';

    if (error.message.includes('timeout') || error.name === 'AbortError') {
      errorMessage = '请求超时，请检查网络连接后重试';
    } else if (!navigator.onLine) {
      errorMessage = '网络连接已断开，请检查网络';
    } else if (error.message.includes('500')) {
      errorMessage = '服务器内部错误，请稍后重试';
    } else if (error.message.includes('404')) {
      errorMessage = '请求的资源不存在，请检查模态配置';
    } else if (error.message) {
      errorMessage = `分析失败: ${error.message}`;
    }

    this.showError(errorMessage);

    // 提供重试选项
    if (confirm(`${errorMessage}\n\n是否重试？`)) {
      this.launchAnalysis();
    }
  }

  setLoadingState(loading) {
    this.isLoading = loading;

    const analyzeBtn = document.getElementById('analyzeBtn');
    if (analyzeBtn) {
      if (loading) {
        analyzeBtn.disabled = true;
        analyzeBtn.textContent = '处理中...';
        analyzeBtn.style.opacity = '0.6';
      } else {
        analyzeBtn.disabled = this.selectedModalities.size === 0;
        analyzeBtn.textContent = '开始分析';
        analyzeBtn.style.opacity = '1';
      }
    }

    // 显示/隐藏加载遮罩
    const spinnerOverlay = document.getElementById('spinUpload');
    if (spinnerOverlay) {
      spinnerOverlay.style.display = loading ? 'flex' : 'none';
    }
  }

  showError(message) {
    // 创建错误提示框
    const errorDiv = document.createElement('div');
    errorDiv.className = 'error-message';
    errorDiv.style.cssText = `
      position: fixed;
      top: 20px;
      right: 20px;
      background: #fee2e2;
      border: 2px solid #ef4444;
      border-radius: 8px;
      padding: 16px;
      color: #991b1b;
      font-size: 14px;
      z-index: 10000;
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
      max-width: 400px;
    `;
    errorDiv.innerHTML = `
      <div style="display: flex; align-items: center; gap: 12px;">
        <span style="font-size: 24px;">❌</span>
        <div style="flex: 1;">${message}</div>
        <button onclick="this.parentElement.parentElement.remove()" style="background: none; border: none; font-size: 20px; cursor: pointer; color: #991b1b;">✕</button>
      </div>
    `;

    document.body.appendChild(errorDiv);

    // 5秒后自动移除
    setTimeout(() => {
      if (errorDiv.parentElement) {
        errorDiv.remove();
      }
    }, 5000);
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
      // 处理对象或数组格式
      let modalitiesList = [];

      if (Array.isArray(data.step1.modalities)) {
        // 已经是数组
        modalitiesList = data.step1.modalities;
      } else if (typeof data.step1.modalities === 'object') {
        // 是对象，转换为数组
        modalitiesList = Object.values(data.step1.modalities).map(mod => {
          // 如果mod是对象且有必要的属性
          if (typeof mod === 'object' && mod !== null) {
            return mod;
          }
          return null;
        }).filter(mod => mod !== null);
      }

      // 显示缩略图
      modalitiesList.forEach(mod => {
        if (mod && (mod.thumbnail || mod.preview_png)) {
          const thumbnail = document.createElement('div');
          thumbnail.className = 'thumbnail-item';
          const thumbnailData = mod.thumbnail || mod.preview_png;
          const displayName = mod.name || mod.id || Object.keys(data.step1.modalities).find(key => data.step1.modalities[key] === mod) || 'Unknown';

          thumbnail.innerHTML = `
            <img src="data:image/png;base64,${thumbnailData}" alt="${displayName}">
            <div class="thumbnail-label">${displayName}</div>
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
