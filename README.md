# Secure Multimodal Health Monitoring System (HE + LLM Demo)

A privacy-preserving multimodal health monitoring system demonstration using Homomorphic Encryption and Large Language Models.

## 📋 Overview

This system demonstrates a complete **privacy-preserving health monitoring pipeline**, from local multimodal sensor data collection, through encrypted inference, to clinical report generation—all while protecting user privacy.

### Core Pipeline

```
📊 Local Multimodal Sensor Data
    ↓
🔐 Homomorphic Encryption (CKKS)
    ↓
🤖 DeepSeek LLM Smart Dispatch
    ↓
🔧 Homomorphic Inference Model Cluster (MCP Tools)
    ↓
📈 Local Decryption + Clinical Report Generation
```

## 🎯 Key Features

### 1. Multi-Modal Data Support

The system supports 5 sensor modalities:

| Modality | Data Type | Purpose | Data Source |
|----------|-----------|---------|-------------|
| **Depth** | Depth Image (64×64) | Sleep posture detection | Real depth camera data |
| **UWB** | Ultra-Wideband Time Series | Blood pressure, motion tracking | Real UWB sensor data |
| **IMU** | Inertial Measurement Unit | Gait analysis, metabolic assessment | Real IMU sensor data |
| **CSI** | Channel State Information | Heart rate/respiratory monitoring | Simulated WiFi CSI data |
| **RGB** | Color Image | Risk scoring, fall detection | Real RGB camera data |

### 2. Homomorphic Encrypted Inference
- Uses **CKKS (Cheon-Kim-Kim-Song)** scheme
- Implemented with **TenSEAL** library
- Feature vectors are processed in encrypted form
- Server cannot access plaintext data

### 3. LLM-Based Smart Dispatch
- Powered by **DeepSeek** LLM
- Automatically assigns optimal inference tools for each modality
- Dynamic optimization of model cluster resources

### 4. Rich Visualizations
- **Spectrum Analysis**: FFT spectra and spectrograms
- **Health Reports**: Fall risk, vital signs, activity analysis
- **Interactive Dashboard**: Radar charts, donuts, progress bars, etc.

## 📊 Data Sources

Real sensor data from open-source datasets:

**FL-Datasets-for-HAR (Federated Learning Datasets for Human Activity Recognition)**
- GitHub: https://github.com/xmouyang/FL-Datasets-for-HAR
- Contains multi-modal human activity recognition data
- Dataset location: `FL-Datasets-for-HAR/` directory

Supported dataset files:
- `depth_dataset.zip` - Depth camera data
- `imu_dataset.zip` - IMU sensor data
- `uwb_dataset.zip` - UWB sensor data
- `Widardata.zip` - WiFi CSI data
- `large_scale_HARBox.zip` - Large-scale HAR data

**Citation**:
```
@article{ouyang2023fl,
  title={FL-Datasets-for-HAR: Federated Learning Datasets for Human Activity Recognition},
  author={Ouyang, Xiaoming and others},
  journal={GitHub repository},
  year={2023}
}
```

## 🏗️ System Architecture

### Tech Stack

**Backend**:
- `FastAPI` - Web framework
- `TenSEAL` - Homomorphic encryption library
- `NumPy` - Numerical computing
- `Matplotlib` - Data visualization
- `MCP (Model Context Protocol)` - Tool protocol
- `OpenAI SDK` - LLM interface

**Frontend**:
- Vanilla HTML/CSS/JavaScript
- SVG chart rendering
- Responsive layout design

### Directory Structure

```
web_v9_healthreport/
├── backend/
│   ├── app.py              # FastAPI main application
│   ├── server.py           # MCP tool server
│   ├── reference_clinet.py # Reference client
│   └── requirements.txt    # Python dependencies
├── frontend/
│   ├── index.html          # Main page
│   ├── test_gauge.html     # Test page
│   └── assets/
│       ├── css/styles.css  # Stylesheets
│       ├── js/app.js       # Frontend logic
│       ├── icons/          # Icon resources
│       └── user/           # User uploaded images
├── scripts/
│   ├── generate_data.py              # Data generation script
│   └── generate_multimodal_data.py   # Multimodal data generator
├── FL-Datasets-for-HAR/    # Real datasets (need to unzip)
├── uwb_walk.txt            # UWB walking data
├── imu_walk.txt            # IMU walking data
└── HAR_train.txt           # HAR training data
```

## 🚀 Quick Start

### Requirements

- Python 3.8+
- pip package manager
- Modern browser (Chrome/Firefox/Edge)

### 1. Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

Required packages:
- fastapi
- uvicorn
- numpy
- tenseal
- mcp
- openai
- matplotlib
- torch

### 2. Start Backend Server

**Option 1: Direct Start (with simulated data)**

```bash
cd backend
uvicorn app:app --host 127.0.0.1 --port 8080
```

**Option 2: Configure DeepSeek API (with real LLM dispatch)**

Windows PowerShell:
```powershell
$env:DEEPSEEK_API_KEY="your-api-key-here"
$env:DEEPSEEK_BASE_URL="https://api.deepseek.com"
$env:DEEPSEEK_MODEL="deepseek-chat"
cd backend
uvicorn app:app --host 127.0.0.1 --port 8080
```

Linux/Mac:
```bash
export DEEPSEEK_API_KEY="your-api-key-here"
export DEEPSEEK_BASE_URL="https://api.deepseek.com"
export DEEPSEEK_MODEL="deepseek-chat"
cd backend
uvicorn app:app --host 127.0.0.1 --port 8080
```

### 3. Start Frontend Server

**Open a new terminal**:

```bash
cd frontend
python -m http.server 8001
```

### 4. Access the System

Open in browser: **http://127.0.0.1:8001**

The system will automatically start the data collection and inference cycle.

## 🖥️ User Interface

### Step 1: Local Multimodal Data Stream
- **Data Preview**: Real-time preview of 5 modalities (Depth, UWB, IMU, CSI, RGB)
- **Spectrum Analysis**: Switch between UWB/IMU/CSI FFT spectra and spectrograms
- **Statistics**: Display statistics for each modality (mean, std, shape, etc.)

### Step 2: DeepSeek Dispatch → Homomorphic Prediction Cluster
- **LLM Dispatch**: DeepSeek intelligently assigns each modality to optimal inference tools
- **Model Cluster**: 6 specialized homomorphic inference models
  - ECG Arrhythmia - Arrhythmia detection
  - Blood Pressure - Blood pressure prediction
  - Sleep Staging - Sleep stage estimation
  - Metabolic Score - Metabolic assessment
  - Risk Assessment - Risk scoring
  - Anomaly Check - Anomaly detection
- **Encrypted Inference**: Display aggregated ciphertext preview

### Step 3: Clinical Report Generation
- **Key Results**: Model inference results table (model name, input modality, score, status)
- **Recommendations**: Personalized health recommendations
- **Conclusion**: Comprehensive health report including:
  - Fall risk assessment (progress bar visualization)
  - 7-day activity distribution (donut chart)
  - Multi-dimensional health scores (radar chart)
  - Vital signs comparison (bar chart)
  - Detailed metric cards (heart rate, respiratory rate, blood pressure, SpO2, etc.)

## 🔐 Homomorphic Encryption Technical Details

### CKKS Scheme Parameters

```python
scheme: CKKS
poly_modulus_degree: 16384
coeff_mod_bit_sizes: [60, 40, 40, 40, 40, 40, 60]
global_scale: 2^40
```

### Encryption Workflow

1. **Feature Extraction**: Extract 8-dimensional feature vectors from raw sensor data
2. **Encryption**: Encrypt feature vectors using CKKS scheme
3. **Inference**: Execute model inference on encrypted data
4. **Decryption**: Decrypt inference results locally only
5. **Report**: Generate readable health reports

## 🧪 Development and Testing

### Generate Simulated Data

```bash
python scripts/generate_multimodal_data.py
```

Generated files (saved to `sample_data/`):
- `uwb.csv` - UWB time series
- `imu.csv` - IMU time series
- `csi.csv` - CSI time series
- `depth.npy` - Depth images
- `rgb.npy` - RGB images

### Test Pages

Visit **http://127.0.0.1:8001/test_gauge.html** to view:
- Key results table styling test
- Fall probability progress bar test (low/moderate/high risk)
- Model cards layout test

### API Endpoints

- `GET /api/health` - Health check
- `GET /api/cycle` - Complete data collection → inference → report generation cycle

## ⚙️ Configuration

### Custom Data Paths

Modify path configuration in `backend/app.py`:

```python
DATA_PATHS = {
    "UWB": os.path.join(BASE_DIR, "uwb_walk.txt"),
    "IMU": os.path.join(BASE_DIR, "imu_walk.txt"),
}

DEPTH_PNG_PATH = os.path.join(ASSET_USER_DIR, "deep2.png")
RGB_PNG_PATH = os.path.join(ASSET_USER_DIR, "RGB.png")
```

### Adjust Refresh Rate

Modify the last line in `frontend/assets/js/app.js`:

```javascript
setInterval(runCycle, 10000); // Refresh every 10 seconds (10000 ms)
```

## 📈 Performance Metrics

- **Data Encryption**: ~0.1-0.3 seconds (5 modalities)
- **Homomorphic Inference**: ~15-20 seconds (5 tools in parallel)
- **Report Generation**: ~0.5-1 second
- **Full Cycle**: ~20-25 seconds

## ⚠️ Important Disclaimers

### Demo Purpose Only
- ⚠️ This system is for **technical demonstration only**, NOT for medical diagnosis
- ⚠️ All health metrics are simulated/estimated values without clinical accuracy
- ⚠️ Fall risk assessment uses demo algorithms, not real medical models

### Data Privacy
- ✅ All sensitive data encrypted locally
- ✅ Server only receives encrypted ciphertext
- ✅ Inference results decrypted locally
- ❌ This demo uses temporary file system; production requires secure storage

## 🛠️ Troubleshooting

### Backend Startup Failure

**Issue**: `ModuleNotFoundError`

**Solution**:
```bash
pip install -r backend/requirements.txt
```

### Frontend Cannot Connect to Backend

**Issue**: CORS error or connection refused

**Solution**:
1. Confirm backend is running on port 8080
2. Check `API_BASE` in `frontend/assets/js/app.js`
3. Ensure firewall allows local connections

### Charts Not Displaying

**Issue**: Frontend charts/tables appear empty

**Solution**:
1. Open browser DevTools (F12)
2. Check Console tab for errors
3. Check Network tab, confirm `/api/cycle` request succeeds
4. Look for Console logs:
   - `"Step 3 data:"` - should show complete data
   - `"renderResults called with rows:"` - should show 5 results

### TenSEAL Installation Issues

**Issue**: TenSEAL installation fails on Windows

**Solution**:
```bash
# Use pre-built wheel
pip install tenseal --no-build-isolation

# Or use conda
conda install -c conda-forge tenseal
```

## 🔬 Technical Details

### Feature Extraction

Each modality extracts an 8-dimensional feature vector:

**Time Series Data (UWB, IMU, CSI)**:
- Mean, standard deviation, min, max
- Mean absolute value, mean difference, mean square
- 90th percentile

**Image Data (Depth, RGB)**:
- Channel mean/std
- Gradient features (Depth)
- Color distribution (RGB)

### Homomorphic Tool Suite

6 MCP tools implementing different health monitoring functions:

1. `secure_ecg_toolbox` - ECG signal analysis
2. `secure_bp_toolbox` - Blood pressure regression
3. `secure_sleep_toolbox` - Sleep stage estimation
4. `secure_metabolic_toolbox` - Metabolic assessment
5. `secure_risk_toolbox` - Risk scoring
6. `secure_anomaly_toolbox` - Anomaly detection

### Health Report Metrics

Generated report includes the following metrics (demo values):

| Metric | Reference Range | Source |
|--------|----------------|---------|
| Heart Rate (HR) | 60-100 bpm | CSI frequency analysis |
| Respiratory Rate (RR) | 12-20 rpm | CSI low-frequency component |
| Systolic BP (SBP) | 90-120 mmHg | UWB regression model |
| SpO₂ | 95-100% | Cardiopulmonary proxy |
| Sleep Efficiency | ≥85% | Depth posture analysis |
| Cadence | 90-130 spm | IMU gait frequency |

## 📚 References

1. **FL-Datasets-for-HAR**
   Ouyang, X., et al. (2023). Federated Learning Datasets for Human Activity Recognition.
   https://github.com/xmouyang/FL-Datasets-for-HAR

2. **TenSEAL - Homomorphic Encryption Library**
   https://github.com/OpenMined/TenSEAL

3. **CKKS Scheme**
   Cheon, J. H., Kim, A., Kim, M., & Song, Y. (2017).
   Homomorphic encryption for arithmetic of approximate numbers.

4. **Model Context Protocol (MCP)**
   Anthropic. (2024). Model Context Protocol Specification.
   https://modelcontextprotocol.io

## 🤝 Contributing

Issues and Pull Requests are welcome!

## 📄 License

This project is for academic research and technical demonstration purposes only.

Dataset copyrights belong to the original authors. Please follow their respective licenses when using.

## ⚡ Performance Optimization Suggestions

### Production Environment

1. **Parallel Inference**: Use multiprocessing for handling multiple modalities
2. **Model Compression**: Reduce encryption parameters for better speed
3. **Caching**: Cache public key context and model weights
4. **Batch Processing**: Accumulate samples for batch inference
5. **GPU Acceleration**: Use GPU for homomorphic operations (hardware support required)

### Frontend Optimization

1. Reduce chart generation frequency (on-demand vs. every refresh)
2. Use WebSocket instead of polling
3. Lazy-load charts (only load visible parts)
4. Compress data transmission

## 🔍 System Workflow Details

### Phase 1: Data Collection (Step 1)
- Collect sensor data from 5 modalities
- Generate sparkline previews for quick visual inspection
- Compute frequency spectrum analysis (FFT)
- Display time-frequency spectrograms (CSI only)

### Phase 2: Encryption & Dispatch (Step 2)
- Extract 8-dimensional features from each modality
- Encrypt features using CKKS homomorphic encryption
- DeepSeek LLM analyzes modalities and dispatches to appropriate tools
- Execute encrypted inference using MCP tool cluster

### Phase 3: Report Generation (Step 3)
- Decrypt inference results locally
- Synthesize health metrics (demo estimators):
  - Heart rate from CSI rhythm band
  - Respiratory rate from CSI low-frequency
  - Blood pressure from UWB patterns
  - Sleep efficiency from Depth posture
  - Gait stability from IMU variance
- Generate fall risk assessment
- Create multi-chart clinical report

## 📞 Contact

- Project Author: [Your Name]
- Dataset Source: https://github.com/xmouyang/FL-Datasets-for-HAR
- Support: Submit GitHub Issues

---

**Last Updated**: 2026-02-27
**Version**: v9 (Multimodal + Spectrum Analysis Enhanced)

## 🌟 Acknowledgments

- FL-Datasets-for-HAR contributors for providing real-world sensor data
- TenSEAL/OpenMined team for the homomorphic encryption library
- Anthropic for MCP protocol and Claude integration
- DeepSeek for LLM dispatch capabilities
