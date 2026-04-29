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
    console.log('🔵 ModalitySelector初始化开始');
    try {
      this.setLoadingState(true);
      await this.loadModalities();
      await this.loadModalityThumbnails(); // 加载缩略图
      this.renderCards();
      this.attachEventListeners();

      // 初始化Step 2模型集群（显示所有10个模型，但都变暗）
      console.log('🔵 调用updateModelCluster进行初始化');
      this.updateModelCluster();
      console.log('✅ ModalitySelector初始化完成');
    } catch (error) {
      console.error('❌ 模态选择器初始化失败:', error);
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

    console.log('开始加载缩略图...');

    // 为每个模态请求缩略图
    const thumbnailPromises = this.modalities.map(async (modality) => {
      try {
        console.log(`正在加载 ${modality.name} 的缩略图...`);

        const response = await this.fetchWithTimeout(
          `${apiBase}/api/modality_thumbnail?modality=${encodeURIComponent(modality.name)}`,
          { method: 'GET', timeout: 10000 }
        );

        if (response.ok) {
          const data = await response.json();
          // 存储完整响应数据（包含 data/thumbnail/shape/channels 等字段）
          this.modalityThumbnails[modality.name] = data;
          console.log(`✅ ${modality.name} 数据加载成功:`, {
            type: data.type,
            hasData: !!data.data,
            hasThumbnail: !!data.thumbnail,
            shape: data.shape
          });
        } else {
          console.warn(`⚠️ ${modality.name} API响应错误: ${response.status}`);
          this.modalityThumbnails[modality.name] = null;
        }
      } catch (error) {
        console.warn(`❌ 无法加载 ${modality.name} 的缩略图:`, error.message);
        // 使用默认图标
        this.modalityThumbnails[modality.name] = null;
      }
    });

    // 等待所有缩略图加载完成
    try {
      await Promise.all(thumbnailPromises);
      console.log('✅ 所有缩略图加载完成');
    } catch (err) {
      console.warn('⚠️ 部分缩略图加载失败:', err);
      // 即使部分失败也继续执行
    }
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
      // 使用 ModalityCards 组件生成卡片
      if (typeof ModalityCards !== 'undefined') {
        const config = ModalityCards.MODALITY_CONFIG[modality.id];
        if (config) {
          // 传递完整的API响应数据
          const modalityData = this.modalityThumbnails[modality.name] || {};

          // 调试：检查数据
          console.log(`🎨 渲染卡片 ${modality.id}:`, {
            name: modality.name,
            type: modalityData.type,
            hasData: !!modalityData.data,
            hasThumbnail: !!modalityData.thumbnail,
            shape: modalityData.shape
          });

          // 生成卡片HTML
          const cardHTML = ModalityCards.createModalityCard(modality.id, modalityData);
          container.insertAdjacentHTML('beforeend', cardHTML);

          // 设置 dataset
          const card = container.lastElementChild;
          card.dataset.modalityId = modality.id;
          card.dataset.modalityName = modality.name;

          // 如果有时序或骨架数据，立即绘制Canvas
          if (modalityData.data && (config.type === 'timeseries' || config.type === 'skeleton')) {
            const canvasId = `modality-${modality.id}-canvas`; // 使用完整的cardId前缀
            console.log(`🎨 即将绘制 ${modality.id} Canvas, canvasId: ${canvasId}, 数据形状: ${modalityData.shape}`);

            // 等待DOM更新后绘制
            setTimeout(() => {
              const canvasElement = document.getElementById(canvasId);
              if (canvasElement) {
                console.log(`✅ Canvas元素找到: ${canvasId}, 类型: ${config.type}, 尺寸: ${canvasElement.offsetWidth}x${canvasElement.offsetHeight}`);
                if (config.type === 'timeseries') {
                  // data格式: [channels][samples]，直接传递给drawTimeSeriesCard
                  const clickHandler = ModalityCards.drawTimeSeriesCard(canvasId, modalityData.data, config);
                  if (clickHandler) {
                    canvasElement.addEventListener('click', clickHandler);
                  }
                } else if (config.type === 'skeleton') {
                  ModalityCards.drawSkeletonCard(canvasId, modalityData.data);
                }
              } else {
                console.warn(`❌ Canvas元素未找到: ${canvasId}`);
              }
            }, 100);
          }
        }
      } else {
        // Fallback：使用原来的渲染方式
        const card = document.createElement('div');
        card.className = 'modality-card';
        card.dataset.modalityId = modality.id;
        card.dataset.modalityName = modality.name;

        const thumbnailData = this.modalityThumbnails[modality.name];
        let iconDisplay;

        if (thumbnailData) {
          iconDisplay = `<img src="data:image/png;base64,${thumbnailData}" class="card-thumbnail" alt="${modality.name}">`;
        } else {
          iconDisplay = `<div class="card-loading"></div>`;
        }

        card.innerHTML = `
          <div class="card-title">${modality.name}</div>
          ${iconDisplay}
          <div class="card-desc">${modality.description}</div>
        `;

        container.appendChild(card);
      }
    });

    console.log(`渲染了 ${this.modalities.length} 个模态卡片`);
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
    console.log(`🟢 卡片点击: ${modalityId}`);

    if (this.selectedModalities.has(modalityId)) {
      // 取消选择
      this.selectedModalities.delete(modalityId);
      card.classList.remove('active');
      console.log(`❌ 取消选择: ${modalityId}`);
    } else {
      // 检查是否超过最大选择数
      if (this.selectedModalities.size >= this.maxSelection) {
        this.showWarning(`最多只能选择${this.maxSelection}种模态`);
        return;
      }

      // 添加选择
      this.selectedModalities.add(modalityId);
      card.classList.add('active');
      console.log(`✅ 添加选择: ${modalityId}`);
    }

    this.updateUI();
    console.log('🔄 调用updateModelCluster更新模型高亮');
    this.updateModelCluster(); // 更新Step 2模型高亮
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
    // 始终显示所有10个模型，选中的高亮(active)，未选中的变暗(inactive)
    const clusterGrid = document.getElementById('modelCluster');
    if (!clusterGrid) {
      console.warn('⚠️ modelCluster element not found');
      return;
    }

    // 模态ID到工具的映射关系（使用小写ID）
    const clusterModels = [
      { id: 'sleep', title: 'Sleep Staging', subtitle: 'Depth-based Model', modalityId: 'depth' },
      { id: 'bp', title: 'Blood Pressure', subtitle: 'UWB Regression', modalityId: 'uwb' },
      { id: 'metabolic', title: 'Metabolic Score', subtitle: 'IMU Proxy', modalityId: 'imu' },
      { id: 'ecg', title: 'ECG Arrhythmia', subtitle: 'CSI Heart Pattern', modalityId: 'csi' },
      { id: 'risk', title: 'Risk Assessment', subtitle: 'RGB Triage', modalityId: 'rgb' },
      { id: 'action', title: 'Action Recognition', subtitle: 'Skeleton Model', modalityId: 'ntu' },
      { id: 'cardio', title: 'Cardiovascular', subtitle: 'Retina Analysis', modalityId: 'retina' },
      { id: 'lung', title: 'Lung Screening', subtitle: 'X-ray Analysis', modalityId: 'chest' },
      { id: 'cancer', title: 'Cancer Detection', subtitle: 'Pathology Model', modalityId: 'path' },
      { id: 'blood', title: 'Blood Analysis', subtitle: 'Hematology Model', modalityId: 'blood' }
    ];

    // 清空并重新创建所有模型卡片（使用与app.js相同的HTML结构）
    clusterGrid.innerHTML = '';

    clusterModels.forEach(model => {
      const card = document.createElement('div');
      const isSelected = this.selectedModalities.has(model.modalityId);
      card.className = `modelCard ${isSelected ? 'active' : 'inactive'}`;

      const nameDiv = document.createElement('div');
      nameDiv.className = 'modelName';
      nameDiv.textContent = model.title;

      const subDiv = document.createElement('div');
      subDiv.className = 'modelSub';
      subDiv.textContent = model.subtitle;

      card.appendChild(nameDiv);
      card.appendChild(subDiv);

      if (isSelected) {
        const badgeDiv = document.createElement('div');
        badgeDiv.className = 'modelBadge';
        badgeDiv.textContent = `${model.modalityId.toUpperCase()} → ${model.id}`;
        card.appendChild(badgeDiv);
      }

      clusterGrid.appendChild(card);
    });

    console.log('✅ 模型集群已更新, 选中模态:', Array.from(this.selectedModalities));
  }

  showWarning(message) {
    // 简单的警告提示
    alert(message);
  }

  async launchAnalysis() {
    console.log('🚀 launchAnalysis被调用');
    if (this.selectedModalities.size === 0) {
      console.warn('⚠️ 没有选择任何模态，取消分析');
      this.showWarning('请至少选择一种模态');
      return;
    }

    if (this.isLoading) {
      console.warn('⚠️ 正在处理中，忽略重复调用');
      this.showWarning('正在处理中，请稍候...');
      return;
    }

    // 重置结果标题
    const resultsTitle = document.getElementById('resultsTitle');
    if (resultsTitle) {
      resultsTitle.textContent = `Key results (analyzing ${this.selectedModalities.size} modalities...)`;
    }

    const selectedList = Array.from(this.selectedModalities).join(',');
    console.log(`📋 开始分析以下模态: ${selectedList}`);

    try {
      this.setLoadingState(true);
      this.showProgress();
      this.updateProgress(10, '准备分析...');

      // 调用后端API进行分析，带重试机制
      const data = await this.launchAnalysisWithRetry(selectedList);

      this.updateProgress(100, '分析完成');

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
        analyzeBtn.textContent = '分析中...';
        analyzeBtn.style.opacity = '0.6';
      } else {
        analyzeBtn.disabled = this.selectedModalities.size === 0;
        analyzeBtn.textContent = '开始分析';
        analyzeBtn.style.opacity = '1';
      }
    }

    // 隐藏Step 1的加载遮罩（不再使用）
    const uploadSpinner = document.getElementById('spinUpload');
    if (uploadSpinner) {
      uploadSpinner.style.display = 'none';
    }

    // 在Clinical Report Generation区域显示加载状态
    const reportSpinner = document.getElementById('spinDecrypt');
    if (reportSpinner) {
      if (loading) {
        // 更新文本显示当前处理状态
        const spinnerText = reportSpinner.querySelector('.spinText');
        if (spinnerText) {
          spinnerText.textContent = '正在生成临床报告...';
        }
        reportSpinner.style.display = 'flex';
      } else {
        reportSpinner.style.display = 'none';
      }
    }

    // 同时更新Step 3的状态标签
    const tDecrypt = document.getElementById('tDecrypt');
    if (tDecrypt) {
      if (loading) {
        tDecrypt.className = 'pill running';
        tDecrypt.textContent = 'Generating';
      } else {
        // 保持完成后状态或重置
        if (!tDecrypt.textContent.includes('Done') && !tDecrypt.textContent.includes('sec')) {
          tDecrypt.className = 'pill';
          tDecrypt.textContent = '—';
        }
      }
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

    // 调用app.js中的渲染函数来更新UI
    console.log('Rendering results with data:', data);

    // 更新Step 3状态为完成
    const tDecrypt = document.getElementById('tDecrypt');
    if (tDecrypt && data.step3) {
      const timeSec = data.step3.time_sec || 0;
      tDecrypt.className = 'pill success';
      tDecrypt.textContent = `Done (${timeSec.toFixed(1)}s)`;
      console.log(`✅ Step 3 status updated: Done (${timeSec.toFixed(1)}s)`);
    }

    // Step 1: 渲染模态数据
    if (typeof renderModalities === 'function') {
      renderModalities(data.step1?.modalities || {});
      console.log('✅ Rendered modalities');

      // 重新绘制时序和骨架类卡片（使用ModalityCards组件）
      if (typeof ModalityCards !== 'undefined' && data.step1?.modalities) {
        this.redrawCardsWithCanvas(data.step1.modalities);
      }

      // 更新Step 1状态为完成
      const tUpload = document.getElementById('tUpload');
      if (tUpload && data.step1 && data.step1.time_sec !== undefined) {
        tUpload.className = 'pill success';
        tUpload.textContent = `Done (${data.step1.time_sec.toFixed(2)}s)`;
        console.log(`✅ Step 1 status updated: Done (${data.step1.time_sec.toFixed(2)}s)`);
      }
    }

    // Step 2: 渲染模型集群和密文预览
    if (typeof renderCluster === 'function') {
      const s2 = data.step2 || {};
      renderCluster(s2.cluster_models || [], s2.assignments || []);

      // 更新Step 2状态为完成
      const tDispatch = document.getElementById('tDispatch');
      if (tDispatch && s2.time_sec !== undefined) {
        tDispatch.className = 'pill success';
        tDispatch.textContent = `Done (${s2.time_sec.toFixed(1)}s)`;
        console.log(`✅ Step 2 status updated: Done (${s2.time_sec.toFixed(1)}s)`);
      }

      // 更新密文预览
      const ctPreview = document.getElementById('ctResPreview');
      if (ctPreview && s2.aggregate_cipher_preview) {
        ctPreview.textContent = s2.aggregate_cipher_preview;
      }
      console.log('✅ Rendered cluster');
    }

    // Step 3: 渲染结果和报告
    if (typeof renderResults === 'function') {
      const s3 = data.step3 || {};
      renderResults(s3.results || []);
      console.log('✅ Rendered results');

      // 动态更新结果标题
      const resultsTitle = document.getElementById('resultsTitle');
      if (resultsTitle) {
        if (s3.results && s3.results.length > 0) {
          const count = s3.results.length;
          const modalityNames = s3.results.map(r => r.input_modality).join(', ');
          resultsTitle.textContent = `Key results (${count} modalities: ${modalityNames})`;
          console.log(`✅ Results title updated: ${resultsTitle.textContent}`);
        } else {
          resultsTitle.textContent = 'Key results (no data)';
        }
      }

      // 渲染报告
      if (typeof renderHealthReport === 'function' && s3.report) {
        renderHealthReport(s3.report);

        const conclusionPanel = document.getElementById('conclusionPanel');
        const recommendPanel = document.getElementById('recommendPanel');
        const reportText = document.getElementById('reportText');

        if (conclusionPanel) conclusionPanel.style.display = 'block';
        if (recommendPanel) recommendPanel.style.display = 'block';
        if (reportText) reportText.style.display = 'none';
      }
    }

    // 显示缩略图
    this.showThumbnails(data);
  }

  redrawCardsWithCanvas(modalitiesData) {
    // 根据后端返回的数据，用Canvas可视化替换缩略图
    Object.keys(modalitiesData).forEach(modalityName => {
      const modData = modalitiesData[modalityName];

      // 找到对应的卡片
      let modalityKey = null;
      if (modalityName === 'UWB') modalityKey = 'uwb';
      else if (modalityName === 'IMU') modalityKey = 'imu';
      else if (modalityName === 'CSI') modalityKey = 'csi';
      else if (modalityName === 'NTU') modalityKey = 'ntu';
      else if (modalityName === 'Depth') modalityKey = 'depth';
      else if (modalityName === 'RGB') modalityKey = 'rgb';
      else if (modalityName === 'Retina') modalityKey = 'retina';
      else if (modalityName === 'Chest') modalityKey = 'chest';
      else if (modalityName === 'Path') modalityKey = 'path';
      else if (modalityName === 'Blood') modalityKey = 'blood';

      if (!modalityKey) return;

      const config = ModalityCards.MODALITY_CONFIG[modalityKey];
      if (!config) return;

      const card = document.querySelector(`[data-modality-id="${modalityKey}"]`);
      if (!card) return;

      const visualContainer = card.querySelector('.card-visual');
      if (!visualContainer) return;

      // 移除preview-placeholder类（如果有）
      const placeholder = visualContainer.querySelector('.preview-placeholder');
      if (placeholder) {
        placeholder.classList.add('replacing'); // 添加过渡动画类
      }

      if (config.type === 'timeseries' && modData.raw_data) {
        // 时序类：绘制波形图
        visualContainer.innerHTML = `<canvas id="canvas-${modalityKey}" class="card-canvas"></canvas>`;
        const canvasId = `canvas-${modalityKey}`;

        setTimeout(() => {
          const clickHandler = ModalityCards.drawTimeSeriesCard(canvasId, modData.raw_data, config);
          if (clickHandler) {
            const canvas = document.getElementById(canvasId);
            if (canvas) {
              canvas.addEventListener('click', clickHandler);
            }
          }
        }, 100);

      } else if (config.type === 'skeleton' && modData.keypoints) {
        // 骨架类：绘制火柴人
        visualContainer.innerHTML = `<canvas id="canvas-${modalityKey}" class="card-canvas skeleton-canvas"></canvas>`;
        const canvasId = `canvas-${modalityKey}`;

        setTimeout(() => {
          ModalityCards.drawSkeletonCard(canvasId, modData.keypoints);
        }, 100);
      }
    });

    console.log('✅ Redrawn cards with Canvas visualizations');
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

// 不自动初始化，等待app.js调用
// document.addEventListener('DOMContentLoaded', () => {
//   new ModalitySelector();
// });
