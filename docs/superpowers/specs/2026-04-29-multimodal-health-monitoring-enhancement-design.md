# 多模态健康监测系统功能增强设计文档

**日期**: 2026-04-29
**版本**: 1.0
**状态**: 设计审查中

## 1. 概述

### 1.1 项目目标
将现有的5模态隐私保护健康监测系统扩展到10模态，实现用户可选择性上传数据、增强的加密可视化效果、以及轻量级同态模型演示。

### 1.2 当前系统状态
- **模态数量**: 5种 (Depth, UWB, IMU, CSI, RGB)
- **数据流**: 固定加载所有模态 → 自动加密 → 自动推理
- **用户交互**: 被动接收结果，无选择能力
- **模型复杂度**: 中等复杂度，推理时间~15-20秒

### 1.3 目标系统状态
- **模态数量**: 10种 (现有5种 + NTU + 4种医学图像)
- **数据流**: 用户选择模态 → 选择性加载 → 动画加密 → 推理
- **用户交互**: 主动选择模态，实时反馈加密过程
- **模型复杂度**: 轻量级模型，推理时间~5秒/模态

## 2. 系统架构设计

### 2.1 整体架构

```
用户界面层
├── 10模态卡片选择界面
├── 加密动画展示
├── 进度条反馈
└── 预览缩略图 + 健康报告

数据管理层
├── 模态配置文件
├── 选择性数据加载
└── 测试数据组织

加密推理层
├── 轻量级同态模型
├── 选择性加密处理
└── 快速推理优化
```

### 2.2 数据流设计

**现有流程 (被动)**:
```
系统启动 → 加载所有模态 → 加密所有数据 → 推理所有模型 → 显示结果
```

**新流程 (主动)**:
```
用户启动 → 显示10模态卡片 → 用户选择模态 → 点击"开始分析" →
显示加密动画 → 选择性加载数据 → 选择性加密 → 选择性推理 →
显示预览缩略图 + 健康报告
```

## 3. 功能详细设计

### 3.1 模态卡片选择界面

**位置**: 主界面 Step 1 区域

**布局**:
```
┌─────────────────────────────────────────────────────────────┐
│  Step 1: 选择数据模态                                        │
├─────────────────────────────────────────────────────────────┤
│  [Depth] [UWB] [IMU] [CSI] [RGB]                            │
│  [NTU] [Retina] [Chest] [Path] [Blood]                      │
│                                                              │
│  已选择: 3/10 模态                                           │
│  [开始分析] 按钮                                             │
└─────────────────────────────────────────────────────────────┘
```

**交互状态**:
- **未激活**: 灰色边框，半透明
- **已激活**: 蓝色边框，正常透明度
- **鼠标悬停**: 高亮显示，显示模态描述

**显示内容**:
- 模态图标
- 模态名称
- 简短描述 (如"心率监测" "肺部X光"等)

### 3.2 加密动画设计

**触发时机**: 用户点击"开始分析"后立即显示

**动画内容**:
```
阶段1 (1秒): 明文数据显示
┌────────────────────┐
│ UWB数据: [1.2, 3.4, ...] │
│ IMU数据: [0.1, -0.2, ...]│
└────────────────────┘

阶段2 (1秒): 加密转换动画
┌────────────────────┐
│ UWB数据: 🔒🔒🔒🔒... │  ← 文字变成锁图标
│ IMU数据: 🔒🔒🔒🔒... │
└────────────────────┘

阶段3 (1秒): 密文显示
┌────────────────────┐
│ CKKS密文: 7x9f3a...│  ← base64密文片段
│ 您的数据已被CKKS   │
│ 同态加密保护 🛡️    │
└────────────────────┘
```

**技术实现**: CSS动画 + JavaScript控制，使用`transform`和`opacity`属性

### 3.3 进度条设计

**显示时机**: 加密动画完成后

**进度阶段**:
```
[████████████████████░░░░] 75% 正在同态推理...

阶段划分:
1. 收集选中数据 (10%)
2. CKKS同态加密 (30%)
3. 发送到服务器 (20%)
4. 同态模型推理 (30%)
5. 解密分析结果 (10%)
```

### 3.4 预览缩略图设计

**显示位置**: Step 1结果区域

**布局**:
```
┌─────────────────────────────────────────────────────────────┐
│  已分析的数据模态                                            │
├─────────────────────────────────────────────────────────────┤
│  [UWB缩略图] [IMU缩略图] [ChestMNIST缩略图]                  │
│  └─ 点击可查看详细预览                                       │
└─────────────────────────────────────────────────────────────┘
```

**缩略图内容**:
- **时序数据**: 简化的波形图 (3-5个数据点)
- **图像数据**: 64x64像素缩略图
- **骨骼数据**: 简单的人体轮廓图

**交互**: 点击缩略图显示大图预览

### 3.5 健康报告显示

**保持现有设计不变**，只在报告的"输入数据"部分显示用户实际选择的模态。

## 4. 数据管理设计

### 4.1 测试数据组织

**目标**: test_data目录只包含10个模态的测试文件

**文件清单**:
```
test_data/
├── uwb_from_utar.txt        # UWB雷达数据 (200×3)
├── imu_from_utar.txt        # IMU惯性数据 (250×6)
├── csi_from_utar.csv        # CSI信道数据 (200×8)
├── ntu_from_test.txt        # NTU骨骼数据 (测试集样本)
├── depth_sample.png         # Depth深度图 (现有前端资源)
├── rgb_sample.png           # RGB图像 (现有前端资源)
├── retina_sample.npz        # 视网膜图像样本
├── chest_sample.npz         # 胸部X光样本
├── path_sample.npz          # 组织病理样本
└── blood_sample.npz         # 血细胞图像样本
```

**数据格式**:
- **时序数据**: 保持现有CSV/TXT格式
- **图像数据**: 保持现有PNG/NPZ格式
- **原则**: 各自保持最佳格式，便于处理

### 4.2 模态配置文件

**文件**: `backend/modality_config.json`

**结构**:
```json
{
  "modalities": {
    "Depth": {
      "id": "depth",
      "name": "深度图像",
      "type": "image",
      "data_path": "frontend/assets/user/deep2.png",
      "model_id": "sleep",
      "description": "睡眠姿态检测",
      "icon": "🛏️"
    },
    "UWB": {
      "id": "uwb",
      "name": "UWB雷达",
      "type": "timeseries",
      "data_path": "test_data/uwb_from_utar.txt",
      "model_id": "bp",
      "description": "心率、血压监测",
      "icon": "📡",
      "channels": 3,
      "sample_rate": 24.0
    },
    "IMU": {
      "id": "imu",
      "name": "IMU传感器",
      "type": "timeseries",
      "data_path": "test_data/imu_from_utar.txt",
      "model_id": "metabolic",
      "description": "步态分析、代谢评估",
      "icon": "🏃",
      "channels": 6,
      "sample_rate": 24.0
    },
    "CSI": {
      "id": "csi",
      "name": "WiFi信道",
      "type": "timeseries",
      "data_path": "test_data/csi_from_utar.csv",
      "model_id": "ecg",
      "description": "心率、呼吸频谱分析",
      "icon": "📶",
      "channels": 8,
      "sample_rate": 24.0
    },
    "RGB": {
      "id": "rgb",
      "name": "RGB图像",
      "type": "image",
      "data_path": "frontend/assets/user/RGB.png",
      "model_id": "risk",
      "description": "风险评估、行为识别",
      "icon": "🖼️"
    },
    "NTU": {
      "id": "ntu",
      "name": "骨骼关键点",
      "type": "skeleton",
      "data_path": "test_data/ntu_from_test.txt",
      "model_id": "ntu",
      "description": "人体行为识别",
      "icon": "🦴",
      "dimensions": 3
    },
    "RetinaMNIST": {
      "id": "retina",
      "name": "视网膜图像",
      "type": "medical_image",
      "data_path": "test_data/retina_sample.npz",
      "model_id": "retina",
      "description": "心血管疾病预警",
      "icon": "👁️",
      "classes": 11
    },
    "ChestMNIST": {
      "id": "chest",
      "name": "胸部X光",
      "type": "medical_image",
      "data_path": "test_data/chest_sample.npz",
      "model_id": "chest",
      "description": "肺部疾病筛查",
      "icon": "🫁",
      "classes": 14
    },
    "PathMNIST": {
      "id": "pathology",
      "name": "组织病理",
      "type": "medical_image",
      "data_path": "test_data/path_sample.npz",
      "model_id": "pathology",
      "description": "癌症筛查",
      "icon": "🔬",
      "classes": 9
    },
    "BloodMNIST": {
      "id": "blood",
      "name": "血细胞",
      "type": "medical_image",
      "data_path": "test_data/blood_sample.npz",
      "model_id": "blood",
      "description": "血液疾病诊断",
      "icon": "🩸",
      "classes": 8
    }
  }
}
```

## 5. 同态模型设计

### 5.1 模型简化策略

**原则**: 从code/HE-Net1中的现有模型提取简化版本，保留核心结构但减少层数。

### 5.2 轻量级模型架构

**时序数据模型** (UWB, IMU, CSI, NTU):
```python
# 原始模型: 4层LSTM + 3层全连接
# 简化模型: 2层全连接
class SimpleTimeSeriesModel:
    def __init__(self):
        self.fc1 = Linear(input_dim, 32)  # 降维到32
        self.fc2 = Linear(32, 8)          # 降维到8维特征
        self.output = Linear(8, num_classes)

    # 推理时间: ~2-3秒
```

**图像数据模型** (Depth, RGB, 医学图像):
```python
# 原始模型: 4层卷积 + 2层全连接
# 简化模型: 2层卷积 + 1层全连接
class SimpleCNNModel:
    def __init__(self):
        self.conv1 = Conv2d(3, 8, kernel_size=3)  # 8个卷积核
        self.conv2 = Conv2d(8, 16, kernel_size=3) # 16个卷积核
        self.fc = Linear(16*8*8, num_classes)

    # 推理时间: ~3-5秒
```

### 5.3 模型分配表

| 模态 | 模型类型 | 基础架构 | 推理时间 | 输出 |
|------|----------|----------|----------|------|
| Depth | CNN | SimpleCNNModel | 3秒 | 睡眠阶段 (4类) |
| UWB | TimeSeries | SimpleTimeSeriesModel | 2秒 | 血压等级 (3类) |
| IMU | TimeSeries | SimpleTimeSeriesModel | 2秒 | 代谢分数 (连续值) |
| CSI | TimeSeries | SimpleTimeSeriesModel | 3秒 | 心率变异性 (5类) |
| RGB | CNN | SimpleCNNModel | 4秒 | 风险等级 (3类) |
| NTU | TimeSeries | SimpleTimeSeriesModel | 3秒 | 动作类别 (6类) |
| RetinaMNIST | CNN | SimpleCNNModel | 4秒 | 心血管风险 (11类) |
| ChestMNIST | CNN | SimpleCNNModel | 5秒 | 肺部疾病 (14类) |
| PathMNIST | CNN | SimpleCNNModel | 5秒 | 组织类型 (9类) |
| BloodMNIST | CNN | SimpleCNNModel | 4秒 | 血细胞类型 (8类) |

## 6. API接口设计

### 6.1 新增/修改接口

**POST /api/analyze**
```json
// 请求
{
  "selected_modalities": ["UWB", "IMU", "ChestMNIST"],
  "animation_duration": 3000  // 毫秒
}

// 响应
{
  "status": "processing",
  "progress": 0,
  "message": "正在收集数据..."
}
```

**GET /api/progress**
```json
// 响应
{
  "progress": 45,
  "current_step": "CKKS同态加密",
  "estimated_time": 15
}
```

**修改 GET /api/cycle**
```json
// 新增查询参数
/api/cycle?modalities=UWB,IMU,ChestMNIST

// 响应新增字段
{
  "step1": {
    "selected_modalities": ["UWB", "IMU", "ChestMNIST"],
    "thumbnail_preview": {
      "UWB": "base64_image_data",
      "IMU": "base64_image_data",
      "ChestMNIST": "base64_image_data"
    }
  }
}
```

## 7. 前端实现设计

### 7.1 卡片组件设计

**HTML结构**:
```html
<div class="modality-selector">
  <div class="modality-card" data-modality="UWB" data-active="false">
    <div class="card-icon">📡</div>
    <div class="card-title">UWB雷达</div>
    <div class="card-desc">心率、血压监测</div>
  </div>
  <!-- 其他9个卡片 -->
</div>

<div class="action-bar">
  <div class="selection-count">已选择: <span id="count">0</span>/10 模态</div>
  <button id="analyzeBtn" class="analyze-btn" disabled>开始分析</button>
</div>
```

**CSS样式**:
```css
.modality-card {
  width: 120px;
  height: 120px;
  border: 2px solid #ddd;
  border-radius: 8px;
  opacity: 0.6;
  transition: all 0.3s;
  cursor: pointer;
}

.modality-card.active {
  border-color: #3b82f6;
  opacity: 1.0;
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3);
}

.modality-card:hover {
  transform: translateY(-2px);
}
```

### 7.2 加密动画组件

**实现方式**: CSS动画 + JavaScript控制

**动画时长**: 3秒 (1秒明文 + 1秒转换 + 1秒密文)

**JavaScript控制**:
```javascript
function showEncryptionAnimation(selectedModalities) {
  const container = document.getElementById('encryption-animation');
  container.innerHTML = `
    <div class="encryption-stage-1">
      <h3>原始数据</h3>
      ${selectedModalities.map(m => `
        <div class="data-row">
          <span>${m}: </span>
          <span class="plaintext">${generateSampleData(m)}</span>
        </div>
      `).join('')}
    </div>
  `;

  // 3秒后切换到密文显示
  setTimeout(() => {
    container.innerHTML = `
      <div class="encryption-stage-3">
        <h3>🛡️ 您的数据已被CKKS同态加密保护</h3>
        ${selectedModalities.map(m => `
          <div class="data-row">
            <span>${m}: </span>
            <span class="ciphertext">${generateRandomCiphertext()}</span>
          </div>
        `).join('')}
      </div>
    `;
  }, 3000);
}
```

### 7.3 进度条组件

**实现**: 简单的进度条 + 状态文本

```javascript
function updateProgress(progress, currentStep) {
  const progressBar = document.getElementById('progress-bar');
  const statusText = document.getElementById('status-text');

  progressBar.style.width = `${progress}%`;
  statusText.textContent = currentStep;
}
```

## 8. 后端实现设计

### 8.1 选择性数据加载

**当前实现**: 固定加载所有模态
**新实现**: 根据用户选择动态加载

```python
# 原始代码
uwb_data = get_data("UWB")
imu_data = get_data("IMU")
# ... 加载所有模态

# 新代码
def load_selected_modalities(selected_list):
    """只加载用户选择的模态数据"""
    data = {}
    for modality in selected_list:
        config = load_modality_config(modality)
        data[modality] = get_data(modality)
    return data
```

### 8.2 模态配置加载

```python
def load_modality_config(modality_name):
    """从配置文件加载模态信息"""
    config_path = "backend/modality_config.json"
    with open(config_path, 'r') as f:
        config = json.load(f)
    return config['modalities'][modality_name]
```

### 8.3 轻量级模型实现

**从HE-Net1提取简化模型**:

```python
# 参考: temp/code/HE-Net1/henet_encryptor.cpp
# 简化版本
class SimpleHENetModel:
    def __init__(self, context, modality_type):
        self.context = context
        self.modality_type = modality_type
        # 简化的模型参数
        self.weights = self._init_weights()

    def _init_weights(self):
        # 只使用2层网络
        if self.modality_type in ['timeseries', 'skeleton']:
            return {
                'fc1': np.random.randn(8, 32),
                'fc2': np.random.randn(32, 8)
            }
        else:  # image
            return {
                'conv1': np.random.randn(3, 8, 3, 3),
                'conv2': np.random.randn(8, 16, 3, 3)
            }

    def encrypt_and_infer(self, plaintext_data):
        # 同态加密 + 推理
        encrypted = self._encrypt(plaintext_data)
        result = self._infer(encrypted)
        return self._decrypt(result)
```

### 8.4 缩略图生成

```python
def generate_thumbnail(modality, data):
    """生成预览缩略图"""
    if modality['type'] == 'timeseries':
        return generate_timeseries_thumbnail(data)
    elif modality['type'] in ['image', 'medical_image']:
        return generate_image_thumbnail(data)
    elif modality['type'] == 'skeleton':
        return generate_skeleton_thumbnail(data)

def generate_timeseries_thumbnail(data, size=(64, 64)):
    """时序数据缩略图"""
    fig = plt.figure(figsize=size)
    plt.plot(data[:50])  # 只显示前50个点
    plt.axis('off')
    return png_b64_from_plt(fig)

def generate_image_thumbnail(image_data, size=(64, 64)):
    """图像缩略图"""
    # 如果是npz格式，提取第一张图像
    if isinstance(image_data, np.ndarray) and image_data.ndim == 3:
        img = image_data[0]  # 取第一张
    else:
        img = image_data

    # 调整大小
    from PIL import Image
    img_resized = Image.fromarray(img).resize(size)
    return pil_to_base64(img_resized)
```

## 9. 实现计划

### 9.1 阶段划分

**阶段1: 数据整理** (1-2小时)
- 复制NTU数据到test_data
- 从dataset创建医学图像样本
- 清理test_data目录
- 创建模态配置文件

**阶段2: 后端适配** (3-4小时)
- 实现选择性数据加载
- 创建轻量级同态模型
- 实现缩略图生成
- 修改API接口

**阶段3: 前端交互** (2-3小时)
- 实现卡片选择功能
- 实现加密动画
- 实现进度条
- 实现缩略图显示

**阶段4: 集成测试** (1-2小时)
- 端到端流程测试
- 性能优化
- 错误处理
- 用户体验调整

**总时间**: 7-11小时

### 9.2 实施顺序

1. **数据层**: 先整理数据，确保基础设施就绪
2. **后端层**: 实现核心逻辑和API
3. **前端层**: 实现用户界面
4. **集成层**: 系统测试和优化

### 9.3 测试策略

**单元测试**:
- 数据加载测试
- 模型推理测试
- API接口测试

**集成测试**:
- 端到端流程测试
- 不同模态组合测试
- 边界情况测试

**用户测试**:
- 界面交互测试
- 动画效果测试
- 性能体验测试

## 10. 风险与挑战

### 10.1 技术风险

**风险1**: 轻量级模型准确率可能较低
- **缓解**: 添加免责声明，强调这是demo性质

**风险2**: 加密动画可能影响用户体验
- **缓解**: 提供跳过选项，允许高级用户关闭动画

**风险3**: 10个模态同时选择可能导致性能问题
- **缓解**: 设置最大选择数量限制（建议最多5个）

### 10.2 兼容性风险

**风险4**: 新模型可能与现有系统集成困难
- **缓解**: 保持现有API兼容，新功能作为可选扩展

**风险5**: 浏览器兼容性问题
- **缓解**: 使用标准CSS动画，避免实验性特性

## 11. 成功标准

### 11.1 功能完整性
- ✅ 10个模态全部可显示和选择
- ✅ 用户可以选择任意模态组合
- ✅ 加密动画流畅展示
- ✅ 进度条准确反映处理进度
- ✅ 缩略图正确生成和显示
- ✅ 健康报告正确显示选中模态的结果

### 11.2 性能指标
- ✅ 单个模态推理时间 < 5秒
- ✅ 3个模态总处理时间 < 20秒
- ✅ 加密动画时长 < 5秒
- ✅ 界面响应时间 < 100ms

### 11.3 用户体验
- ✅ 界面直观易懂
- ✅ 交互流畅自然
- ✅ 错误提示友好
- ✅ 加密过程可视化清晰

## 12. 后续优化方向

### 12.1 短期优化 (1-2周)
- 添加模态推荐功能
- 实现批量分析
- 优化动画效果
- 添加历史记录功能

### 12.2 中期优化 (1-2月)
- 实现更复杂的同态模型
- 添加实时数据流处理
- 实现移动端适配
- 添加数据导出功能

### 12.3 长期优化 (3-6月)
- 支持自定义模态
- 实现联邦学习
- 添加模型训练功能
- 实现云端部署

---

**文档版本**: 1.0
**最后更新**: 2026-04-29
**下一步**: 用户审查批准后进入实施计划阶段
