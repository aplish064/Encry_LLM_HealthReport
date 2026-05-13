/**
 * Modality selector and interaction logic.
 */

class ModalitySelector {
  constructor() {
    this.currentScenario = 'healthcare';
    this.selectedModalities = new Set();
    this.maxSelection = 10; // 支持最多10种模态
    this.modalities = [];
    this.isLoading = false;
    this.retryCount = 0;
    this.maxRetries = 3;
    this.apiTimeout = 30000; // 30 seconds
    this.reportTimeoutMs = 45000; // 45 seconds for report generation
    this.modalityThumbnails = {}; // 存储模态缩略图
    this.uploadedMedicalImage = null;
    this.uploadedModalityImages = {};
    this.selectedLlmProvider = 'xiaomi-mimo';
    this.selectedLlmLabel = 'Xiaomi MiMo';
    this.llmConfirmationResolver = null;
    this.init();
  }

  async init() {
    console.log('🔵 ModalitySelector initialization started');
    try {
      this.setLoadingState(true);
      this.applyScenarioLabels();
      this.modalities = this.getDefaultModalities();
      this.maxSelection = this.currentScenario === 'finance' ? 6 : 10;
      this.renderCards();
      this.attachEventListeners();

      // Initialize Step 2 local encoders (show all 10 encoders, dimmed by default)
      console.log('🔵 Initializing local encoders');
      this.updateModelCluster();
      this.updateUI();
      console.log('✅ ModalitySelector initialization complete');
      this.refreshModalityData();
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
      const apiBase = (typeof API_BASE !== 'undefined' && API_BASE)
        ? API_BASE
        : (window.API_BASE || (window.location.port === "8001"
          ? `${window.location.protocol}//${window.location.hostname}:8082`
          : ""));
      const response = await this.fetchWithTimeout(`${apiBase}/api/modalities?scenario=${encodeURIComponent(this.currentScenario)}`, {
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
      this.maxSelection = this.currentScenario === 'finance' ? Math.min(6, this.modalities.length || 6) : 10;
    } catch (error) {
      console.error('Failed to load modality configuration:', error);
      this.modalities = this.getDefaultModalities();
      this.maxSelection = this.currentScenario === 'finance' ? 6 : 10;
      console.warn('Using fallback modality configuration');
    }
  }

  async refreshModalityData() {
    try {
      await this.loadModalities();
      this.renderCards();
      this.updateUI();
      this.updateModelCluster();
      await this.loadModalityThumbnails();
      this.renderCards();
      this.updateUI();
    } catch (error) {
      console.warn('Background modality refresh failed:', error);
    }
  }

  async loadModalityThumbnails() {
    // 加载每个模态的缩略图预览
    const apiBase = (typeof API_BASE !== 'undefined' && API_BASE)
      ? API_BASE
      : (window.API_BASE || (window.location.port === "8001"
        ? `${window.location.protocol}//${window.location.hostname}:8082`
        : ""));

    console.log('Loading modality thumbnails...');

    // 为每个模态请求缩略图
    const thumbnailPromises = this.modalities.map(async (modality) => {
      try {
        console.log(`Loading thumbnail for ${modality.name}...`);

        const response = await this.fetchWithTimeout(
          `${apiBase}/api/modality_thumbnail?scenario=${encodeURIComponent(this.currentScenario)}&modality=${encodeURIComponent(modality.name)}`,
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
    if (this.currentScenario === 'finance') {
      return [
        {
          id: 'income',
          name: 'Income',
          type: 'finance',
          description: 'Salary, recurring income, and income stability',
          fields: ['monthly_income_usd', 'income_stability', 'employment_tenure_months'],
          icon: '$'
        },
        {
          id: 'expenses',
          name: 'Expenses',
          type: 'finance',
          description: 'Recurring spending and monthly obligation load',
          fields: ['monthly_expenses_usd', 'fixed_obligations_usd', 'expense_volatility'],
          icon: '$'
        },
        {
          id: 'savings',
          name: 'Savings',
          type: 'finance',
          description: 'Cash reserves and emergency-fund resilience',
          fields: ['savings_balance_usd', 'emergency_fund_months', 'monthly_savings_rate'],
          icon: '$'
        },
        {
          id: 'loan',
          name: 'Loan',
          type: 'finance',
          description: 'Debt balance, payment pressure, and loan stress',
          fields: ['loan_balance_usd', 'monthly_payment_usd', 'debt_to_income_ratio'],
          icon: '$'
        },
        {
          id: 'credit',
          name: 'Credit',
          type: 'finance',
          description: 'Credit score, utilization, and repayment risk',
          fields: ['credit_score', 'credit_utilization', 'missed_payments_12m'],
          icon: '$'
        },
        {
          id: 'profile',
          name: 'Profile',
          type: 'finance',
          description: 'Household context and financial profile signals',
          fields: ['age_band', 'household_size', 'risk_tolerance'],
          icon: '$'
        }
      ];
    }

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

  getScenarioLabels() {
    if (this.currentScenario === 'finance') {
      return {
        selectStep: 'Select Financial Data',
        dataTitle: 'Select Financial Data',
        dataSubtitle: 'Choose financial field groups for encrypted risk inference.',
        modelTitle: 'Financial Data Encoders',
        modelSubtitle: 'Selected financial data are dispatched to specialized local encoders.',
        reportTitle: 'Protected Financial Risk Report',
        reportSubtitle: 'Privacy-preserved financial summary with status and recommendations.'
      };
    }

    return {
      selectStep: 'Select Medical Data',
      dataTitle: 'Select Medical Data',
      dataSubtitle: 'Choose multimodal data sources for encrypted health inference.',
      modelTitle: 'Multimodal Data Encoders',
      modelSubtitle: 'Selected medical data are dispatched to specialized local encoders.',
      reportTitle: 'Protected Health Report',
      reportSubtitle: 'Privacy-preserved clinical summary with status and recommendations.'
    };
  }

  applyScenarioLabels() {
    const labels = this.getScenarioLabels();
    const labelTargets = {
      stepSelectLabel: labels.selectStep,
      dataPanelTitle: labels.dataTitle,
      dataPanelSubtitle: labels.dataSubtitle,
      modelPanelTitle: labels.modelTitle,
      modelPanelSubtitle: labels.modelSubtitle,
      reportPanelTitle: labels.reportTitle,
      reportPanelSubtitle: labels.reportSubtitle
    };

    Object.entries(labelTargets).forEach(([id, text]) => {
      const element = document.getElementById(id);
      if (element) element.textContent = text;
    });
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
          const modalityData = {
            ...modality,
            ...(this.modalityThumbnails[modality.name] || {}),
            ...(this.uploadedModalityImages[modality.id] || {})
          };

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
          if (!modalityData.uploaded && modalityData.data && (config.type === 'timeseries' || config.type === 'skeleton')) {
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
    const sceneTabs = document.getElementById('sceneTabs');

    if (container) {
      container.addEventListener('click', (e) => {
        const uploadButton = e.target.closest('[data-modality-upload]');
        if (uploadButton) {
          e.preventDefault();
          e.stopPropagation();
          if (this.isLoading) return;
          const modalityId = uploadButton.dataset.modalityUpload;
          const input = container.querySelector(`.modality-upload-input[data-modality-file="${modalityId}"]`);
          if (input) input.click();
          return;
        }

        const card = e.target.closest('.modality-card');
        if (card) {
          this.handleCardClick(card);
        }
      });

      container.addEventListener('change', (e) => {
        const input = e.target.closest('.modality-upload-input[data-modality-file]');
        if (!input) return;
        if (this.isLoading) {
          input.value = '';
          return;
        }
        const file = input.files && input.files[0];
        if (file) this.uploadMedicalImage(file, input.dataset.modalityFile);
        input.value = '';
      });
    }

    if (analyzeBtn) {
      analyzeBtn.addEventListener('click', () => {
        this.launchAnalysis();
      });
    }

    if (sceneTabs) {
      sceneTabs.addEventListener('click', (event) => {
        const tab = event.target.closest('.scene-tab[data-scenario]');
        if (tab) this.switchScenario(tab.dataset.scenario);
      });
    }

    document.addEventListener('click', (event) => {
      const button = event.target.closest('.llm-icon-option[data-llm-provider]');
      if (button) this.selectLlmProvider(button);

      const confirmButton = event.target.closest('#confirmLlmBtn');
      if (confirmButton) this.confirmLlmSelection(confirmButton);
    });
    this.updateLlmSelectionState();
  }

  async switchScenario(nextScenario) {
    const normalizedScenario = String(nextScenario || '').toLowerCase();
    if (!['healthcare', 'finance'].includes(normalizedScenario) || normalizedScenario === this.currentScenario || this.isLoading) {
      return;
    }

    this.currentScenario = normalizedScenario;
    document.querySelectorAll('.scene-tab[data-scenario]').forEach(tab => {
      const isActive = tab.dataset.scenario === this.currentScenario;
      tab.classList.toggle('active', isActive);
      tab.setAttribute('aria-selected', isActive ? 'true' : 'false');
    });

    this.selectedModalities.clear();
    this.modalityThumbnails = {};
    this.uploadedMedicalImage = null;
    this.uploadedModalityImages = {};
    this.applyScenarioLabels();
    this.resetWorkflowForScenario();
    this.setLoadingState(true);

    try {
      await this.loadModalities();
      await this.loadModalityThumbnails();
      this.renderCards();
      this.updateUI();
      this.updateModelCluster();
    } catch (error) {
      console.error('Scenario switch failed:', error);
      this.showError('Could not switch scene. Please retry.');
    } finally {
      this.setLoadingState(false);
      this.updateUI();
    }
  }

  resetWorkflowForScenario() {
    this.hideProgress();
    const progressFill = document.getElementById('progressFill');
    if (progressFill) progressFill.style.width = '0%';
    const progressText = document.getElementById('progressText');
    if (progressText) progressText.textContent = 'Preparing...';

    ['tUpload', 'tDispatch', 'tProtect', 'tDecrypt'].forEach(id => {
      const pill = document.getElementById(id);
      if (pill) {
        pill.className = 'pill';
        pill.textContent = '—';
      }
    });

    const ctPreview = document.getElementById('ctResPreview');
    if (ctPreview) {
      if (typeof updateCipherPreviewRows === 'function') {
        updateCipherPreviewRows('—');
      } else {
        ctPreview.textContent = '—';
      }
    }
    const privacyPanel = document.getElementById('privacyPanel');
    if (privacyPanel) privacyPanel.textContent = 'Select modalities and run analysis to generate the anonymized privacy flow.';
    const resultsTitle = document.getElementById('resultsTitle');
    if (resultsTitle) resultsTitle.textContent = 'Key Results';
    const resultTable = document.getElementById('resultTable');
    const resultBody = resultTable ? resultTable.querySelector('tbody') : null;
    if (resultBody) {
      resultBody.innerHTML = '<tr><td colspan="4" style="text-align:center; color: #5b6474;">Loading...</td></tr>';
    }
    const conclusionPanel = document.getElementById('conclusionPanel');
    if (conclusionPanel) {
      conclusionPanel.style.display = 'block';
      conclusionPanel.textContent = 'Loading...';
    }
    const recommendPanel = document.getElementById('recommendPanel');
    if (recommendPanel) {
      recommendPanel.style.display = 'block';
      recommendPanel.textContent = 'Loading...';
    }
    const reportText = document.getElementById('reportText');
    if (reportText) {
      reportText.style.display = 'none';
      reportText.textContent = '—';
    }
    const thumbnailsGrid = document.getElementById('thumbnailsGrid');
    if (thumbnailsGrid) {
      thumbnailsGrid.style.display = 'none';
      thumbnailsGrid.innerHTML = '';
    }
    this.updateLlmSelectionState();
    if (typeof setWorkflowStep === 'function') {
      setWorkflowStep('select');
    }
  }

  get llmProviderButtons() {
    return Array.from(document.querySelectorAll('.llm-icon-option[data-llm-provider]'));
  }

  selectLlmProvider(button) {
    this.selectedLlmProvider = button.dataset.llmProvider || 'qwen';
    this.selectedLlmLabel = button.dataset.llmLabel || 'Qwen';
    this.llmProviderButtons.forEach(option => {
      const isSelected = option.dataset.llmProvider === this.selectedLlmProvider;
      option.classList.toggle('active', isSelected);
      option.setAttribute('aria-pressed', isSelected ? 'true' : 'false');
    });
    this.updateLlmSelectionState();
  }

  getActiveLlmButton() {
    return this.llmProviderButtons.find(button => button.dataset.llmProvider === this.selectedLlmProvider)
      || this.llmProviderButtons.find(button => button.classList.contains('active'))
      || this.llmProviderButtons[0]
      || null;
  }

  getSelectedLlmProvider() {
    const activeButton = this.getActiveLlmButton();
    return activeButton ? activeButton.dataset.llmProvider : this.selectedLlmProvider || 'qwen';
  }

  getSelectedLlmLabel() {
    const activeButton = this.getActiveLlmButton();
    return activeButton ? activeButton.dataset.llmLabel : this.selectedLlmLabel || 'Qwen';
  }

  updateLlmSelectionState(stateText) {
    const label = this.getSelectedLlmLabel();
    const provider = this.getSelectedLlmProvider();
    const tLlm = document.getElementById('tLlm');
    const routeMeta = document.getElementById('llmRouteMeta');
    const confirmButton = document.getElementById('confirmLlmBtn');
    const route = document.getElementById('llmPromptRoute');
    const group = document.getElementById('llmIconGroup');
    const activeButton = this.getActiveLlmButton();

    this.llmProviderButtons.forEach(option => {
      const isSelected = option.dataset.llmProvider === provider;
      option.classList.toggle('active', isSelected);
      option.setAttribute('aria-pressed', isSelected ? 'true' : 'false');
    });
    if (tLlm) {
      tLlm.textContent = label;
    }
    if (routeMeta) {
      routeMeta.textContent = stateText || `Ready to send to ${label} after shuffle.`;
    }
    if (confirmButton && !confirmButton.disabled) {
      confirmButton.textContent = `Confirm ${label} and generate report`;
    }
    if (route && group && activeButton) {
      window.requestAnimationFrame(() => {
        const groupRect = group.getBoundingClientRect();
        const buttonRect = activeButton.getBoundingClientRect();
        const targetX = Math.round(buttonRect.left + buttonRect.width / 2 - groupRect.left);
        route.style.setProperty('--arrow-x', `${Math.max(20, targetX)}px`);
      });
    }
  }

  waitForLlmConfirmation() {
    const confirmButton = document.getElementById('confirmLlmBtn');
    if (confirmButton) {
      confirmButton.disabled = false;
      confirmButton.textContent = `Confirm ${this.getSelectedLlmLabel()} and generate report`;
      confirmButton.classList.remove('confirmed');
    }

    return new Promise(resolve => {
      this.llmConfirmationResolver = resolve;
    });
  }

  confirmLlmSelection(button) {
    const label = this.getSelectedLlmLabel();
    if (button) {
      button.disabled = true;
      button.classList.add('confirmed');
      button.textContent = `Confirmed ${label}`;
    }
    this.updateLlmSelectionState(`Confirmed ${label}. Generating report...`);
    if (this.llmConfirmationResolver) {
      const resolve = this.llmConfirmationResolver;
      this.llmConfirmationResolver = null;
      resolve();
    }
  }

  async uploadMedicalImage(file, modalityId) {
    if (this.isLoading) return;
    const targetModality = this.modalities.find(modality => modality.id === modalityId);
    const targetLabel = targetModality ? targetModality.name : modalityId;
    if (!file.type.startsWith('image/')) {
      this.showWarning('Please choose an image file.');
      return;
    }

    try {
      const dataUrl = await this.readFileAsDataUrl(file);
      const apiBase = (typeof API_BASE !== 'undefined' && API_BASE)
        ? API_BASE
        : (window.API_BASE || (window.location.port === "8001"
          ? `${window.location.protocol}//${window.location.hostname}:8082`
          : ""));
      const response = await this.fetchWithTimeout(`${apiBase}/api/upload_medical_image`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          modality_id: modalityId,
          filename: file.name,
          content_type: file.type,
          data_url: dataUrl
        })
      }, 15000);
      const payload = await response.json().catch(() => ({}));
      if (!response.ok || payload.error) {
        throw new Error(payload.error || `HTTP error! status: ${response.status}`);
      }

      if (this.isLoading) return;

      this.uploadedMedicalImage = payload;
      this.uploadedModalityImages[modalityId] = {
        type: 'image',
        thumbnail: payload.thumbnail,
        shape: payload.shape || [64, 64, 3],
        uploaded: true
      };
      this.renderCards();
      this.restoreSelectedCards();
      this.selectedModalities.add(modalityId);
      this.restoreSelectedCards();
      this.updateUI();
      this.updateModelCluster();
    } catch (error) {
      console.error('Medical image upload failed:', error);
      if (this.isLoading) return;
      this.showError(`${targetLabel} image upload failed: ${error.message}`);
    }
  }

  readFileAsDataUrl(file) {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => resolve(reader.result);
      reader.onerror = () => reject(new Error('Could not read selected image.'));
      reader.readAsDataURL(file);
    });
  }

  restoreSelectedCards() {
    document.querySelectorAll('.modality-card').forEach(card => {
      const modalityId = card.dataset.modalityId;
      card.classList.toggle('active', this.selectedModalities.has(modalityId));
    });
  }

  handleCardClick(card) {
    if (this.isLoading) return;
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
    const limitElement = document.getElementById('selectionLimit');
    if (limitElement) {
      limitElement.textContent = this.maxSelection;
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
    // 根据选中的数据更新Step 2的local encoders
    const clusterGrid = document.getElementById('modelCluster');
    if (!clusterGrid) {
      console.warn('⚠️ modelCluster element not found');
      return;
    }

    const healthcareModels = [
      { id: 'sleep', title: 'Gesture Recognition', subtitle: 'Depth', modalityId: 'depth' },
      { id: 'bp', title: 'Human Movement Detection', subtitle: 'UWB', modalityId: 'uwb' },
      { id: 'metabolic', title: 'Walking Activity Recognition', subtitle: 'IMU', modalityId: 'imu' },
      { id: 'ecg', title: 'Human Activity Recognition', subtitle: 'CSI', modalityId: 'csi' },
      { id: 'risk', title: 'Fall Detection', subtitle: 'RGB', modalityId: 'rgb' },
      { id: 'action', title: 'Human Action Recognition', subtitle: 'NTU', modalityId: 'ntu' },
      { id: 'cardio', title: 'Retina Screening', subtitle: 'Fundus', modalityId: 'retina' },
      { id: 'lung', title: 'Chest Screening', subtitle: 'X-ray', modalityId: 'chest' },
      { id: 'cancer', title: 'Pathology Screening', subtitle: 'Microscopy', modalityId: 'path' },
      { id: 'blood', title: 'Blood Cell Screening', subtitle: 'Smear', modalityId: 'blood' }
    ];
    const financeModels = [
      { id: 'income_capacity', title: 'Income Capacity', subtitle: 'Income Encoder', modalityId: 'income' },
      { id: 'expense_burden', title: 'Expense Burden', subtitle: 'Expenses Encoder', modalityId: 'expenses' },
      { id: 'savings_resilience', title: 'Savings Resilience', subtitle: 'Savings Encoder', modalityId: 'savings' },
      { id: 'loan_stress', title: 'Loan Stress', subtitle: 'Loan Encoder', modalityId: 'loan' },
      { id: 'credit_risk', title: 'Credit Risk', subtitle: 'Credit Encoder', modalityId: 'credit' },
      { id: 'profile_context', title: 'Profile Context', subtitle: 'Profile Encoder', modalityId: 'profile' }
    ];
    const clusterModels = this.currentScenario === 'finance' ? financeModels : healthcareModels;

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
      resultsTitle.textContent = `Key results (analyzing ${this.selectedModalities.size} data sources...)`;
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
      const apiBase = (typeof API_BASE !== 'undefined' && API_BASE)
        ? API_BASE
        : (window.API_BASE || (window.location.port === "8001"
          ? `${window.location.protocol}//${window.location.hostname}:8082`
          : ""));

      if (typeof setWorkflowStep === 'function') {
        setWorkflowStep('model');
      }
      const dispatchData = await this.fetchJson(
        `${apiBase}/api/dispatch?scenario=${encodeURIComponent(this.currentScenario)}&selected_modalities=${encodeURIComponent(selectedList)}`
      );
      this.renderDispatchStage(dispatchData);

      if (typeof setWorkflowStep === 'function') {
        setWorkflowStep('privacy');
      }
      this.updateProgress(55, 'Generating synthetic candidate pool and shuffling outputs...');
      const privacyData = await this.fetchJson(
        `${apiBase}/api/privacy_shuffle?session_id=${encodeURIComponent(dispatchData.session_id)}`
      );
      this.renderPrivacyStage({
        ...privacyData,
        aggregate_cipher_preview: dispatchData.step2?.aggregate_cipher_preview,
      });
      await this.wait(10500);

      if (typeof setWorkflowStep === 'function') {
        setWorkflowStep('llm');
      }
      this.updateLlmSelectionState('Choose an LLM, then confirm to generate the report.');
      await this.waitForLlmConfirmation();
      const llmProvider = this.getSelectedLlmProvider();
      const llmLabel = this.getSelectedLlmLabel();
      this.updateLlmSelectionState(`Sending protected summary to ${llmLabel}.`);

      if (typeof setWorkflowStep === 'function') {
        setWorkflowStep('report');
      }
      const reportKind = this.currentScenario === 'finance' ? 'financial risk report' : 'health report';
      this.updateProgress(85, `Generating protected ${reportKind} with ${llmLabel}...`);
      const reportSpinner = document.getElementById('spinDecrypt');
      if (reportSpinner) {
        const spinnerText = reportSpinner.querySelector('.spinText');
        if (spinnerText) spinnerText.textContent = `Generating ${reportKind} with ${llmLabel}...`;
        reportSpinner.style.display = 'flex';
      }
      const tDecrypt = document.getElementById('tDecrypt');
      if (tDecrypt) {
        tDecrypt.className = 'pill running';
        tDecrypt.textContent = 'Generating';
      }
      const reportData = await this.fetchJson(
        `${apiBase}/api/report?session_id=${encodeURIComponent(dispatchData.session_id)}&llm_provider=${encodeURIComponent(llmProvider)}`,
        { timeout: this.reportTimeoutMs }
      );
      this.updateLlmSelectionState(`Protected summary sent to ${llmLabel}.`);

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
        llm_provider: reportData.llm_provider || privacyData.llm_provider || dispatchData.llm_provider,
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
        if (typeof updateCipherPreviewRows === 'function') {
          updateCipherPreviewRows(s2.aggregate_cipher_preview);
        } else {
          ctPreview.textContent = s2.aggregate_cipher_preview;
        }
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
      aggregate_cipher_preview: data.aggregate_cipher_preview || data.step2?.aggregate_cipher_preview,
      plaintext_prompt: data.plaintext_prompt || data.llm_prompt || (data.step3 ? (data.step3.plaintext_prompt || data.step3.llm_prompt) : ""),
    };
    const tProtect = document.getElementById('tProtect');
    if (tProtect) {
      tProtect.className = 'pill success';
      tProtect.textContent = privacy.enabled ? 'Done' : 'Unavailable';
    }
    if (typeof renderPrivacyProtection === 'function') {
      renderPrivacyProtection(privacy);
      this.updateLlmSelectionState();
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

    // Report generation starts only after the user confirms the target LLM.
    const reportSpinner = document.getElementById('spinDecrypt');
    if (reportSpinner) {
      reportSpinner.style.display = 'none';
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
        tDecrypt.className = 'pill';
        tDecrypt.textContent = '—';
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

    const content = document.createElement('div');
    content.style.cssText = 'display: flex; align-items: center; gap: 12px;';

    const icon = document.createElement('span');
    icon.style.cssText = 'font-size: 24px;';
    icon.textContent = '❌';

    const messageDiv = document.createElement('div');
    messageDiv.style.cssText = 'flex: 1;';
    messageDiv.textContent = message;

    const closeButton = document.createElement('button');
    closeButton.type = 'button';
    closeButton.style.cssText = 'background: none; border: none; font-size: 20px; cursor: pointer; color: #991b1b;';
    closeButton.textContent = '✕';
    closeButton.addEventListener('click', () => {
      errorDiv.remove();
    });

    content.appendChild(icon);
    content.appendChild(messageDiv);
    content.appendChild(closeButton);
    errorDiv.appendChild(content);

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
        if (typeof updateCipherPreviewRows === 'function') {
          updateCipherPreviewRows(s2.aggregate_cipher_preview);
        } else {
          ctPreview.textContent = s2.aggregate_cipher_preview;
        }
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
          resultsTitle.textContent = 'Key results';
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
