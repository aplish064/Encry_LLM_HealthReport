/**
 * 加密可视化动画组件
 * 展示数据加密过程，让用户"感受"到数据正在被加密
 */

class EncryptionAnimator {
    constructor(containerId) {
        this.container = document.getElementById(containerId);
        if (!this.container) {
            console.error(`Container ${containerId} not found`);
            return;
        }

        this.currentStage = 0;
        this.stages = ['keygen', 'encrypt', 'transmit', 'confirm'];
    }

    /**
     * 执行完整的加密动画流程
     * @param {Object} data - 要加密的数据信息
     * @param {Function} progressCallback - 进度回调函数
     */
    async animateEncryption(data, progressCallback) {
        if (!this.container) return;

        // 清空容器
        this.container.innerHTML = '';
        this.container.style.display = 'block';

        // 阶段1: 密钥生成 (0.5s)
        await this.animateKeyGeneration(progressCallback);

        // 阶段2: 数据加密 (1s)
        await this.animateDataEncryption(data, progressCallback);

        // 阶段3: 传输 (0.5s)
        await this.animateTransmission(progressCallback);

        // 阶段4: 确认 (0.2s)
        await this.animateConfirmation(progressCallback);
    }

    /**
     * 阶段1: 密钥生成动画
     */
    async animateKeyGeneration(progressCallback) {
        const stageHtml = `
            <div class="encryption-stage" id="keygenStage">
                <div class="stage-icon">🔑</div>
                <div class="stage-title">生成CKKS加密密钥...</div>
                <div class="stage-details">
                    <div class="detail-item">
                        <span class="detail-label">多项式阶数:</span>
                        <span class="detail-value">16384</span>
                    </div>
                    <div class="detail-item">
                        <span class="detail-label">系数模数位长:</span>
                        <span class="detail-value">[60, 40, 40, 40, 40, 40, 60]</span>
                    </div>
                    <div class="detail-item">
                        <span class="detail-label">全局缩放:</span>
                        <span class="detail-value">2^40</span>
                    </div>
                </div>
                <div class="progress-bar">
                    <div class="progress-fill" id="keygenProgress" style="width: 0%"></div>
                </div>
            </div>
        `;

        this.container.innerHTML = stageHtml;

        // 动画进度条 0% -> 20%
        const progressBar = document.getElementById('keygenProgress');
        for (let i = 0; i <= 20; i++) {
            progressBar.style.width = i + '%';
            if (progressCallback) progressCallback(i, 'keygen');
            await this.sleep(25); // 0.5s total
        }
    }

    /**
     * 阶段2: 数据加密动画
     */
    async animateDataEncryption(data, progressCallback) {
        const sampleData = this.getSampleData(data);
        const stageHtml = `
            <div class="encryption-stage" id="encryptStage">
                <div class="stage-icon">🔒</div>
                <div class="stage-title">加密数据中...</div>
                <div class="data-transformation">
                    <div class="data-block plaintext-block">
                        <div class="block-title">明文数据</div>
                        <div class="block-content" id="plaintextContent">${sampleData.plaintext}</div>
                    </div>
                    <div class="transformation-arrow">
                        <div class="arrow-content">
                            <div class="arrow-icon">↓</div>
                            <div class="arrow-text">CKKS加密</div>
                        </div>
                    </div>
                    <div class="data-block ciphertext-block">
                        <div class="block-title">密文数据</div>
                        <div class="block-content" id="ciphertextContent">~ 加密中 ~</div>
                    </div>
                </div>
                <div class="progress-bar">
                    <div class="progress-fill" id="encryptProgress" style="width: 20%"></div>
                </div>
            </div>
        `;

        this.container.innerHTML = stageHtml;

        // 模拟加密过程，更新密文显示
        const ciphertextEl = document.getElementById('ciphertextContent');
        const progressBar = document.getElementById('encryptProgress');

        const encryptionSteps = [
            { progress: 30, text: '~ 初始化加密上下文 ~' },
            { progress: 40, text: '~ 编码明文向量 ~' },
            { progress: 50, text: '~ 生成密文多项式 ~' },
            { progress: 60, text: '~ 应用同态运算 ~' }
        ];

        for (const step of encryptionSteps) {
            progressBar.style.width = step.progress + '%';
            ciphertextEl.textContent = step.text;
            if (progressCallback) progressCallback(step.progress, 'encrypt');
            await this.sleep(250); // 1s total
        }

        // 最终密文
        progressBar.style.width = '60%';
        ciphertextEl.textContent = sampleData.ciphertext;
        if (progressCallback) progressCallback(60, 'encrypt');
    }

    /**
     * 阶段3: 传输动画
     */
    async animateTransmission(progressCallback) {
        const stageHtml = `
            <div class="encryption-stage" id="transmitStage">
                <div class="stage-icon">📡</div>
                <div class="stage-title">传输加密数据到服务器...</div>
                <div class="transmission-animation">
                    <div class="data-packet" id="dataPacket">📦</div>
                    <div class="server-icon">🖥️</div>
                </div>
                <div class="transmission-details">
                    <div class="detail-item">
                        <span class="detail-label">传输协议:</span>
                        <span class="detail-value">HTTPS + TLS 1.3</span>
                    </div>
                    <div class="detail-item">
                        <span class="detail-label">数据状态:</span>
                        <span class="detail-value security-badge">🔐 端到端加密</span>
                    </div>
                </div>
                <div class="progress-bar">
                    <div class="progress-fill" id="transmitProgress" style="width: 60%"></div>
                </div>
            </div>
        `;

        this.container.innerHTML = stageHtml;

        // 数据包传输动画
        const packet = document.getElementById('dataPacket');
        const progressBar = document.getElementById('transmitProgress');

        // 移动数据包
        packet.style.transition = 'transform 0.4s ease-in-out';
        packet.style.transform = 'translateX(200px)';

        for (let i = 60; i <= 80; i += 5) {
            progressBar.style.width = i + '%';
            if (progressCallback) progressCallback(i, 'transmit');
            await this.sleep(100); // 0.4s total
        }
    }

    /**
     * 阶段4: 确认动画
     */
    async animateConfirmation(progressCallback) {
        const stageHtml = `
            <div class="encryption-stage" id="confirmStage">
                <div class="stage-icon success-icon">✅</div>
                <div class="stage-title">数据已安全加密并传输</div>
                <div class="confirmation-details">
                    <div class="detail-item success-item">
                        <span class="detail-icon">🔒</span>
                        <span class="detail-text">所有敏感数据已加密</span>
                    </div>
                    <div class="detail-item success-item">
                        <span class="detail-icon">🛡️</span>
                        <span class="detail-text">服务器仅收到加密密文</span>
                    </div>
                    <div class="detail-item success-item">
                        <span class="detail-icon">🔐</span>
                        <span class="detail-text">推理结果将在本地解密</span>
                    </div>
                </div>
                <div class="progress-bar">
                    <div class="progress-fill success-fill" id="confirmProgress" style="width: 80%"></div>
                </div>
            </div>
        `;

        this.container.innerHTML = stageHtml;

        const progressBar = document.getElementById('confirmProgress');

        for (let i = 80; i <= 100; i += 5) {
            progressBar.style.width = i + '%';
            if (progressCallback) progressCallback(i, 'confirm');
            await this.sleep(50); // 0.2s total
        }
    }

    /**
     * 获取示例数据用于展示
     */
    getSampleData(data) {
        // 生成示例明文数据
        const plaintext = [];
        for (let i = 0; i < 5; i++) {
            const value = (Math.random() * 2 - 1).toFixed(3);
            plaintext.push(value);
        }

        // 生成示例密文数据
        const ciphertext = [];
        for (let i = 0; i < 3; i++) {
            const coeffs = [];
            for (let j = 0; j < 5; j++) {
                coeffs.push((Math.random() * 1e6).toFixed(0));
            }
            ciphertext.push(`[${coeffs.join(', ')}...]`);
        }

        return {
            plaintext: `[${plaintext.join(', ')}, ...]`,
            ciphertext: ciphertext.join('\n')
        };
    }

    /**
     * 隐藏动画容器
     */
    hide() {
        if (this.container) {
            this.container.style.display = 'none';
        }
    }

    /**
     * 显示动画容器
     */
    show() {
        if (this.container) {
            this.container.style.display = 'block';
        }
    }

    /**
     * 延时工具函数
     */
    sleep(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }
}

// 导出到全局
window.EncryptionAnimator = EncryptionAnimator;

console.log('✅ EncryptionAnimator component loaded');
