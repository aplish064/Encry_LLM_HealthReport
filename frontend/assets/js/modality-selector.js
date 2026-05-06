/**
 * Modality selector and interaction logic.
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
    this.reportTimeoutMs = 45000; // 45 seconds for report generation
    this.modalityThumbnails = {}; // 存储模态缩略图
    this.init();
  }

  async init() {
    console.log('🔵 ModalitySelector initialization started');
    try {
      this.setLoadingState(true);
      await this.loadModalities();
      await this.loadModalityThumbnails(); // 加载缩略图
      this.renderCards();
      this.attachEventListeners();

      // Initialize Step 2 model cluster (show all 10 models, dimmed by default)
      console.log('🔵 Initializing model cluster');
      this.updateModelCluster();
      console.log('✅ ModalitySelector initialization complete');
    } catch (error) {
      console.error('❌ ModalitySelector initialization failed:', error);
      this.showError('Initialization failed. Please refresh and try again.');
    } finally {
      this.setLoadingState(false);
    }
  }

  async loadModalities() {
    try {
      // 使用全局API_BASE（在app.js中定义）
      const apiBase = (typeof API_BASE !== 'undefined')
        ? API_BASE
        : `${window.location.protocol}//${window.location.hostname}:8082`;
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
      console.error('Failed to load modality configuration:', error);

      if (error.name === 'AbortError') {
        throw new Error('Request timed out. Please check your network connection.');
      }

      if (!navigator.onLine) {
        throw new Error('Network is offline. Please check connection.');
      }

      // 使用默认配置
      this.modalities = this.getDefaultModalities();
      this.showWarning('Using fallback modality configuration');
    }
  }

  async loadModalityThumbnails() {
    // 加载每个模态的缩略图预览
    const apiBase = (typeof API_BASE !== 'undefined')
      ? API_BASE
      : `${window.location.protocol}//${window.location.hostname}:8082`;

    console.log('Loading modality thumbnails...');

    // 为每个模态请求缩略图
    const thumbnailPromises = this.modalities.map(async (modality) => {
      try {
        console.log(`Loading thumbnail for ${modality.name}...`);

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
        name: 'Depth Camera',
        type: 'image',
        description: 'Sleep posture detection',
        icon: '🛏️'
      },
      {
        id: 'uwb',
        name: 'UWB Radar',
        type: 'timeseries',
        description: 'Heart rate and blood pressure monitoring',
        icon: '📡'
      },
      {
        id: 'imu',
        name: 'IMU Sensor',
        type: 'timeseries',
        description: 'Gait analysis and metabolic assessment',
        icon: '🏃'
      },
      {
        id: 'csi',
        name: 'WiFi CSI',
        type: 'timeseries',
        description: 'Heart rate and respiratory monitoring',
        icon: '📶'
      },
      {
        id: 'rgb',
        name: 'RGB Camera',
        type: 'image',
        description: 'Risk scoring and activity assessment',
        icon: '📷'
      },
      {
        id: 'ntu',
        name: 'NTU Skeleton',
        type: 'skeleton',
        description: 'Action recognition and behavior analysis',
        icon: '🦴'
      },
      {
        id: 'retina',
        name: 'Retina Image',
        type: 'medical_image',
        description: 'Early cardiovascular risk screening',
        icon: '👁️'
      },
      {
        id: 'chest',
        name: 'Chest X-ray',
        type: 'medical_image',
        description: 'Lung condition screening',
        icon: '🫁'
      },
      {
        id: 'path',
        name: 'Pathology Image',
        type: 'medical_image',
        description: 'Cancer screening',
        icon: '🔬'
      },
      {
        id: 'blood',
        name: 'Blood Cell Image',
        type: 'medical_image',
        description: 'Hematology screening',
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

          // 时序和骨架类型需要Canvas绘制
          if (modalityData.data && (config.type === 'timeseries' || config.type === 'skeleton')) {
            const canvasId = `modality-${modality.id}-canvas`;
            console.log(`🎨 即将绘制 ${modality.id} Canvas, canvasId: ${canvasId}, 数据形状: ${modalityData.shape}`);

            // 等待DOM更新后绘制
            setTimeout(() => {
              const canvasElement = document.getElementById(canvasId);
              if (canvasElement) {
                console.log(`✅ Canvas元素找到: ${canvasId}, 类型: ${config.type}`);
                if (config.type === 'timeseries') {
                  ModalityCards.drawTimeSeriesCard(canvasId, modalityData.data, config);
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
        this.showWarning(`You can select up to ${this.maxSelection} modalities.`);
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
      this.showWarning('Please select at least one modality.');
      return;
    }

    if (this.isLoading) {
      console.warn('⚠️ 正在处理中，忽略重复调用');
      this.showWarning('Processing in progress. Please wait.');
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
      this.updateProgress(10, 'Preparing analysis...');
      if (typeof setWorkflowStep === 'function') {
        setWorkflowStep('model');
      }

      // 调用后端API进行分析，带重试机制
      const data = await this.launchAnalysisWithRetry(selectedList);

      this.updateProgress(100, 'Analysis completed.');

      // 处理结果
      this.handleResults(data);

    } catch (error) {
      console.error('Analysis failed:', error);
      this.handleAnalysisError(error);
    } finally {
      this.setLoadingState(false);
    }
  }

  async launchAnalysisWithRetry(selectedList, attempt = 1) {
    try {
      this.updateProgress(20, `Dispatching encrypted inference... (${attempt}/${this.maxRetries})`);
      const apiBase = (typeof API_BASE !== 'undefined')
        ? API_BASE
        : `${window.location.protocol}//${window.location.hostname}:8082`;

      if (typeof setWorkflowStep === 'function') {
        setWorkflowStep('model');
      }
      const dispatchData = await this.fetchJson(
        `${apiBase}/api/dispatch?selected_modalities=${encodeURIComponent(selectedList)}`
      );
      this.renderDispatchStage(dispatchData);

      if (typeof setWorkflowStep === 'function') {
        setWorkflowStep('privacy');
      }
      this.updateProgress(55, 'Generating synthetic candidate pool and shuffling outputs...');
      const privacyData = await this.fetchJson(
        `${apiBase}/api/privacy_shuffle?session_id=${encodeURIComponent(dispatchData.session_id)}`
      );
      this.renderPrivacyStage(privacyData);
      await this.wait(10500);

      if (typeof setWorkflowStep === 'function') {
        setWorkflowStep('report');
      }
      this.updateProgress(85, 'Generating protected health report...');
      const reportData = await this.fetchJson(
        `${apiBase}/api/report?session_id=${encodeURIComponent(dispatchData.session_id)}`,
        { timeout: this.reportTimeoutMs }
      );

      // 重置重试计数
      this.retryCount = 0;

      return {
        schema: "he-multimodal-staged-cycle/v1",
        session_id: dispatchData.session_id,
        generated_at: dispatchData.generated_at,
        step1: dispatchData.step1,
        step2: dispatchData.step2,
        step3: reportData.step3,
        privacy_protection: reportData.privacy_protection || privacyData.privacy_protection,
        data_source: reportData.data_source || dispatchData.data_source,
        llm_provider: reportData.llm_provider || dispatchData.llm_provider,
      };

    } catch (error) {
      console.error(`分析尝试 ${attempt} 失败:`, error);

      if (attempt < this.maxRetries) {
        this.retryCount = attempt;

        // 显示重试提示
        this.updateProgress(0, `Analysis failed, retrying in ${2} seconds...`);

        // 等待2秒后重试
        await new Promise(resolve => setTimeout(resolve, 2000));

        return this.launchAnalysisWithRetry(selectedList, attempt + 1);
      } else {
        // 达到最大重试次数
        throw error;
      }
    }
  }

  wait(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  formatSeconds(value, digits = 1) {
    const n = Number(value);
    if (!Number.isFinite(n)) {
      return "—";
    }
    return `${n.toFixed(digits)}s`;
  }

  safeText(value, fallback = "—") {
    if (value === null || value === undefined) return fallback;
    const str = String(value).trim();
    return str.length ? str : fallback;
  }

  async fetchJson(url, options = {}) {
    const { timeout, ...fetchOptions } = options;
    const response = await this.fetchWithTimeout(url, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json'
      },
      ...fetchOptions
    }, timeout);

    const data = await response.json().catch(() => ({}));
    if (!response.ok || data.error) {
      throw new Error(data.error || data.message || `HTTP error! status: ${response.status}`);
    }
    if (!data || typeof data !== 'object') {
      throw new Error(`Invalid API response for ${url}`);
    }
    return data;
  }

  renderDispatchStage(data) {
    if (typeof renderModalities === 'function') {
      renderModalities(data.step1?.modalities || {});
      if (typeof ModalityCards !== 'undefined' && data.step1?.modalities) {
        this.redrawCardsWithCanvas(data.step1.modalities);
      }
    }

    if (typeof renderCluster === 'function') {
      const s2 = data.step2 || {};
      renderCluster(s2.cluster_models || [], s2.assignments || []);
      const ctPreview = document.getElementById('ctResPreview');
      if (ctPreview && s2.aggregate_cipher_preview) {
        ctPreview.textContent = s2.aggregate_cipher_preview;
      }
    }

    const tUpload = document.getElementById('tUpload');
    if (tUpload && data.step1?.time_sec !== undefined) {
      tUpload.className = 'pill success';
      tUpload.textContent = `Done (${this.formatSeconds(data.step1.time_sec, 2)})`;
    }

    const tDispatch = document.getElementById('tDispatch');
    if (tDispatch && data.step2?.time_sec !== undefined) {
      tDispatch.className = 'pill success';
      tDispatch.textContent = `Done (${this.formatSeconds(data.step2.time_sec, 1)})`;
    }
  }

  renderPrivacyStage(data) {
    const privacy = {
      ...(data.privacy_protection || {}),
      plaintext_prompt: data.plaintext_prompt || data.llm_prompt || (data.step3 ? (data.step3.plaintext_prompt || data.step3.llm_prompt) : ""),
    };
    const tProtect = document.getElementById('tProtect');
    if (tProtect) {
      tProtect.className = 'pill success';
      tProtect.textContent = privacy.enabled ? 'Done' : 'Unavailable';
    }
    if (typeof renderPrivacyProtection === 'function') {
      renderPrivacyProtection(privacy);
    }
  }

  handleAnalysisError(error) {
    this.hideProgress();

    let errorMessage = 'Analysis failed. Please retry.';

    if (error.message.includes('timeout') || error.name === 'AbortError') {
      errorMessage = 'Request timed out. Check the network and retry.';
    } else if (!navigator.onLine) {
      errorMessage = 'Network appears offline. Check your connection.';
    } else if (error.message.includes('500')) {
      errorMessage = 'Server internal error. Please retry later.';
    } else if (error.message.includes('404')) {
      errorMessage = 'Requested resource not found. Check modality configuration.';
    } else if (error.message) {
      errorMessage = `Analysis failed: ${error.message}`;
    }

    this.showError(errorMessage);

    // 提供重试选项
    if (confirm(`${errorMessage}\n\nRetry?`)) {
      this.launchAnalysis();
    }
  }

  setLoadingState(loading) {
    this.isLoading = loading;

    const analyzeBtn = document.getElementById('analyzeBtn');
    if (analyzeBtn) {
      if (loading) {
        analyzeBtn.disabled = true;
        analyzeBtn.textContent = 'Analyzing...';
        analyzeBtn.style.opacity = '0.6';
      } else {
        analyzeBtn.disabled = this.selectedModalities.size === 0;
        analyzeBtn.textContent = 'Run Analysis';
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
          spinnerText.textContent = 'Generating clinical report...';
        }
        reportSpinner.style.display = 'flex';
      } else {
        reportSpinner.style.display = 'none';
      }
    }

    // 同时更新Step 3的状态标签
    const tProtect = document.getElementById('tProtect');
    if (tProtect) {
      if (loading) {
        tProtect.className = 'pill running';
        tProtect.textContent = 'Shuffling';
      } else if (!tProtect.textContent.includes('Done')) {
        tProtect.className = 'pill';
        tProtect.textContent = '—';
      }
    }

    // 同时更新Step 4的状态标签
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
    this.updateProgress(0, 'Preparing...');
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
        { text: '📊 Plaintext data', class: 'plaintext' },
        { text: '🔒 Encrypting...', class: 'encrypting' },
        { text: '🔐 Encrypted', class: 'ciphertext' }
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
    const tProtect = document.getElementById('tProtect');
    const privacy = data.privacy_protection || {};
    if (tProtect) {
      tProtect.className = 'pill success';
      tProtect.textContent = privacy.enabled ? 'Done' : 'Unavailable';
      console.log(`✅ Step 3 status updated: ${tProtect.textContent}`);
    }

    // Privacy animation is rendered during /api/privacy_shuffle. Re-rendering here
    // restarts the sequence and makes the stage appear to play twice.

    // 更新Step 4状态为完成
    const tDecrypt = document.getElementById('tDecrypt');
    if (tDecrypt && data.step3) {
      const timeSec = data.step3.time_sec || 0;
      tDecrypt.className = 'pill success';
      tDecrypt.textContent = `Done (${this.formatSeconds(timeSec, 1)})`;
      console.log(`✅ Step 4 status updated: Done (${this.formatSeconds(timeSec, 1)})`);
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
        tUpload.textContent = `Done (${this.formatSeconds(data.step1.time_sec, 2)})`;
        console.log(`✅ Step 1 status updated: Done (${this.formatSeconds(data.step1.time_sec, 2)})`);
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
        tDispatch.textContent = `Done (${this.formatSeconds(s2.time_sec, 1)})`;
        console.log(`✅ Step 2 status updated: Done (${this.formatSeconds(s2.time_sec, 1)})`);
      }

      // 更新密文预览
      const ctPreview = document.getElementById('ctResPreview');
      if (ctPreview && s2.aggregate_cipher_preview) {
        ctPreview.textContent = s2.aggregate_cipher_preview;
      }
      console.log('✅ Rendered cluster');
    }

    // Step 4: 渲染结果和报告
    if (typeof renderResults === 'function') {
      const s3 = data.step3 || {};
      renderResults(s3.results || []);
      console.log('✅ Rendered results');

      // 无论后续报告渲染是否完整，进入第四步并停止生成态提示。
      if (typeof setWorkflowStep === 'function') {
        setWorkflowStep('report');
      }

      // 动态更新结果标题
      const resultsTitle = document.getElementById('resultsTitle');
      if (resultsTitle) {
        if (s3.results && s3.results.length > 0) {
          const count = s3.results.length;
          const modalityNames = s3.results.map(r => r.input_modality).join(', ');
          resultsTitle.textContent = `Key results (${count} protected modalities: ${modalityNames})`;
          console.log(`✅ Results title updated: ${resultsTitle.textContent}`);
        } else {
          resultsTitle.textContent = 'Key results (no data)';
        }
      }

      // 渲染报告
      if (typeof renderHealthReport === 'function' && s3.report) {
        try {
          renderHealthReport(s3.report, s3.plaintext_prompt || s3.llm_prompt);
        } catch (renderError) {
          console.error('报告渲染失败:', renderError);
          const conclusionPanel = document.getElementById('conclusionPanel');
          const reportText = document.getElementById('reportText');
          if (conclusionPanel) {
            conclusionPanel.style.display = 'block';
            conclusionPanel.innerHTML = `<div class="reportText">${this.safeText(
              s3.report_conclusion || s3.conclusion || 'Report rendering failed. Please check the raw conclusion.'
            )}</div>`;
          }
          if (reportText) reportText.style.display = 'none';
        }

        const conclusionPanel = document.getElementById('conclusionPanel');
        const recommendPanel = document.getElementById('recommendPanel');
        const reportText = document.getElementById('reportText');

        if (conclusionPanel) conclusionPanel.style.display = 'block';
        if (recommendPanel) recommendPanel.style.display = 'block';
        if (reportText) reportText.style.display = 'none';
      } else {
        const conclusionPanel = document.getElementById('conclusionPanel');
        const recommendPanel = document.getElementById('recommendPanel');
        const reportText = document.getElementById('reportText');
        const conclusion = this.safeText(s3.report_conclusion || s3.conclusion || 'Protected report returned without structured fields yet.');

        if (conclusionPanel) {
          conclusionPanel.style.display = 'block';
          conclusionPanel.innerHTML = `<div class="reportText">${conclusion}</div>`;
        }
        if (recommendPanel) {
          recommendPanel.style.display = 'block';
          recommendPanel.textContent = '—';
        }
        if (reportText) {
          reportText.style.display = 'none';
        }
      }

      // 如果报告内容仍未写入，补充兜底提示，避免用户误以为任务未结束。
      const conclusionPanel = document.getElementById('conclusionPanel');
      const reportText = document.getElementById('reportText');
      if (conclusionPanel && !conclusionPanel.innerHTML.trim()) {
        const fallbackConclusion = this.safeText(
          s3.report_conclusion || s3.conclusion || 'Protected report returned, but structured content is not rendered yet.'
        );
        conclusionPanel.style.display = 'block';
        conclusionPanel.innerHTML = `<div class="reportText">${fallbackConclusion}</div>`;
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

    thumbnailsGrid.style.display = 'none';  // 隐藏缩略图网格，避免重复显示
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
