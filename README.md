# MyGPTShield: Secure Multimodal HE + LLM Demo

A privacy-preserving multimodal inference demo using Homomorphic Encryption and Large Language Models. The current app includes both healthcare monitoring and personal finance risk scenes.

## 📋 Overview

This system demonstrates a complete **privacy-preserving multimodal inference pipeline**, from local data selection, through encrypted inference and MyGPTShield Server anonymization, to protected report generation.

### Core Pipeline

```
📊 Local Multimodal Sensor Data
    ↓
🔐 Homomorphic Encryption (CKKS)
    ↓
🤖 Local Encoder Dispatch
    ↓
🔧 Homomorphic Inference Model Cluster (MCP Tools)
    ↓
🛡️ MyGPTShield Server Privacy Shuffle
    ↓
📈 Protected Report Generation
```

## 🎯 Key Features

### 1. Multi-Scene Data Support

The system supports healthcare and finance scenes.

Healthcare modalities:

| Modality | Data Type | Purpose | Data Source |
|----------|-----------|---------|-------------|
| **Depth** | Depth Image (64×64) | Sleep posture detection | Real depth camera data |
| **UWB** | Ultra-Wideband Time Series | Blood pressure, motion tracking | Real UWB sensor data |
| **IMU** | Inertial Measurement Unit | Gait analysis, metabolic assessment | Real IMU sensor data |
| **CSI** | Channel State Information | Heart rate/respiratory monitoring | Simulated WiFi CSI data |
| **RGB** | Color Image | Risk scoring, fall detection | Real RGB camera data |
| **NTU** | Skeleton | Action recognition | Generated fallback data |
| **Retina** | Medical image | Cardiovascular risk proxy | Optional NPZ/upload |
| **Chest** | Medical image | Lung condition screening | Optional NPZ/upload |
| **Pathology** | Medical image | Cancer screening | Optional NPZ/upload |
| **Blood** | Medical image | Hematology screening | Optional NPZ/upload |

Finance modalities:

| Modality | Data Type | Purpose |
|----------|-----------|---------|
| **Income** | Numeric finance signal | Earning capacity baseline |
| **Expenses** | Numeric finance signal | Monthly spending burden |
| **Savings** | Numeric finance signal | Liquidity resilience |
| **Loan** | Mixed finance signal | Repayment pressure |
| **Credit** | Numeric finance signal | Credit and leverage risk |
| **Profile** | Categorical finance signal | Employment and regional context |

### 2. Homomorphic Encrypted Inference
- Uses **CKKS (Cheon-Kim-Kim-Song)** scheme
- Implemented with **TenSEAL** library
- Feature vectors are processed in encrypted form
- Server cannot access plaintext data

### 3. Local Encoders + Optional LLM Report Generation
- Dispatches selected modalities to specialized local encoders
- Supports external LLM providers when credentials are configured
- Falls back to built-in report generation when no external LLM is configured

### 4. Rich Visualizations
- **Spectrum Analysis**: FFT spectra and spectrograms
- **Healthcare Reports**: Fall risk, vital signs, activity analysis
- **Finance Reports**: Resilience, cashflow burden, loan stress, and credit risk
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
- `PyTorch` - Optional; the demo has a NumPy fallback for lightweight local runs

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
│   ├── requirements-lite.txt # Recommended local demo dependencies
│   └── requirements.txt    # Full dependencies, including optional torch
├── frontend/
│   ├── index.html          # Main page
│   └── assets/
│       ├── css/styles.css  # Stylesheets
│       ├── js/app.js       # Frontend logic
│       ├── icons/          # Icon resources
│       └── user/           # User uploaded images
├── test_data/              # Optional local data and finance CSV
├── test_data_backup/       # Backup medical image samples
└── docs/                   # Planning/spec artifacts
```

## 🚀 Quick Start

### Requirements

- Python 3.10+ recommended
- pip package manager
- Modern browser (Chrome/Firefox/Edge)
- Linux/macOS shell commands below use `python3`; on Windows, use `python`

### 1. Create a Virtual Environment

```bash
cd /path/to/Encry_LLM_HealthReport
python3 -m venv venv
source venv/bin/activate
```

If `python3 -m venv` fails on Ubuntu/Debian with `ensurepip is not available`, install the system venv package first:

```bash
sudo apt update
sudo apt install -y python3.10-venv
python3 -m venv venv
source venv/bin/activate
```

### 2. Install Dependencies

For most local demo runs, install the lightweight dependency set. It skips `torch`; the backend will use the built-in NumPy fallback model path.

```bash
pip install -r backend/requirements-lite.txt
```

If you specifically want the full optional PyTorch model dependency, install:

```bash
pip install -r backend/requirements.txt
```

### 3. Start the Backend

Use port `8082`:

```bash
cd backend
MPLCONFIGDIR=/tmp/matplotlib-cache ../venv/bin/python -m uvicorn app:app --host 127.0.0.1 --port 8082
```

Leave this terminal running.

### 4. Start the Frontend

Open a second terminal:

```bash
cd /path/to/Encry_LLM_HealthReport
source venv/bin/activate
cd frontend
../venv/bin/python -m http.server 8001 --bind 127.0.0.1
```

Open in browser:

```text
http://127.0.0.1:8001
```

### 5. Verify the Services

```bash
curl http://127.0.0.1:8082/api/health
curl "http://127.0.0.1:8082/api/modalities?scenario=finance"
```

Expected behavior:
- The frontend loads at `http://127.0.0.1:8001`
- Backend health returns JSON with `"status": "healthy"`
- You can switch between `Healthcare` and `Finance`
- Healthcare and finance cards support `Select` uploads
- The MyGPTShield Server step shows streaming ciphertext previews

### Optional LLM Configuration

The demo can run without external LLM credentials by using built-in fallback report generation. To call a compatible external provider, set environment variables before starting the backend:

```bash
export DEEPSEEK_API_KEY="your-api-key-here"
export DEEPSEEK_BASE_URL="https://api.deepseek.com"
export DEEPSEEK_MODEL="deepseek-chat"
```

## 🖥️ User Interface

### Step 1: Select Data
- **Healthcare scene**: Select medical/sensor modalities such as Depth, UWB, IMU, CSI, RGB, NTU, Retina, Chest, Pathology, and Blood.
- **Finance scene**: Select finance signals such as Income, Expenses, Savings, Loan, Credit, and Profile.
- **Uploads**: Use `Select` on a card to upload a replacement image preview for healthcare or finance cards.

### Step 2: Local Encoders
- **Dispatch**: Selected data are dispatched to specialized local encoders.
- **Model Cluster**: Specialized homomorphic inference models include:
  - ECG Arrhythmia - Arrhythmia detection
  - Blood Pressure - Blood pressure prediction
  - Sleep Staging - Sleep stage estimation
  - Metabolic Score - Metabolic assessment
  - Risk Assessment - Risk scoring
  - Anomaly Check - Anomaly detection
- **Encrypted Inference**: Display aggregated ciphertext preview

### Step 3: MyGPTShield Server
- **Ciphertext preview**: The encoded model output card streams multiple ciphertext previews before the synthetic database card appears.
- **Synthetic database**: The system generates synthetic peers and masks the real record in the distribution.
- **Privacy shuffle**: The real record is anonymized before a bucketed summary is sent to the selected LLM.

### Step 4: Protected Report Generation
- **Key Results**: Model inference results table (model name, input modality, score, status)
- **Recommendations**: Personalized health recommendations
- **Conclusion**: Comprehensive health report including:
  - Fall risk assessment (progress bar visualization)
  - 7-day activity distribution (donut chart)
  - Multi-dimensional health scores (radar chart)
  - Vital signs comparison (bar chart)
  - Detailed metric cards (heart rate, respiratory rate, blood pressure, SpO2, etc.)
  - Finance risk summaries when the Finance scene is selected

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
- `GET /api/modalities?scenario=healthcare|finance` - Data card definitions
- `GET /api/dispatch?scenario=...&selected_modalities=...` - Step 1/2 dispatch and encrypted inference
- `GET /api/privacy_shuffle?session_id=...` - Synthetic database and MyGPTShield Server privacy step
- `GET /api/report?session_id=...&llm_provider=...` - Protected report generation
- `GET /api/cycle` - Legacy complete cycle endpoint

## ⚙️ Configuration

### Custom Data Paths

Modify path configuration in `backend/app.py`:

```python
DATA_PATHS = {
    "UWB": os.path.join(BASE_DIR, "test_data", "uwb_sample.txt"),
    "IMU": os.path.join(BASE_DIR, "test_data", "imu_sample.txt"),
    "CSI": os.path.join(BASE_DIR, "test_data", "csi_sample.csv"),
}

DEPTH_PNG_PATH = os.path.join(ASSET_USER_DIR, "deep2.png")
RGB_PNG_PATH = os.path.join(ASSET_USER_DIR, "RGB.png")
```

If UWB/IMU/CSI sample files are missing, the backend generates deterministic fallback time-series data so the demo still runs.

### Frontend Backend URL

```javascript
// frontend/assets/js/app.js
const API_BASE = window.API_BASE || (
  window.location.port === "8001"
    ? `${window.location.protocol}//${window.location.hostname}:8082`
    : ""
);
```

Keep the frontend on `8001` and backend on `8082` unless you also update this API base logic.

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

### `python3 -m venv venv` Fails

**Issue**: `ensurepip is not available`

**Solution**:
```bash
sudo apt update
sudo apt install -y python3.10-venv
python3 -m venv venv
source venv/bin/activate
```

### Backend Startup Failure

**Issue**: `ModuleNotFoundError`

**Solution**:
```bash
source venv/bin/activate
pip install -r backend/requirements-lite.txt
```

If the missing module is `torch`, you can either install the full dependency file or keep using the lightweight path. The current backend supports a NumPy fallback when torch is absent.

```bash
pip install -r backend/requirements.txt
```

### Frontend Cannot Connect to Backend

**Issue**: CORS error or connection refused

**Solution**:
1. Confirm backend is running on port `8082`
2. Check `API_BASE` in `frontend/assets/js/app.js`
3. Ensure firewall allows local connections
4. Confirm the frontend is served from `http://127.0.0.1:8001`

### Port Already in Use

**Issue**: `Address already in use`

**Solution**:
```bash
# Linux/macOS
lsof -i :8082
lsof -i :8001
```

Stop the old process or choose another allowed backend port such as `8083`, then update `API_BASE` accordingly.

### Charts Not Displaying

**Issue**: Frontend charts/tables appear empty

**Solution**:
1. Open browser DevTools (F12)
2. Check Console tab for errors
3. Check Network tab, confirm `/api/dispatch`, `/api/privacy_shuffle`, and `/api/report` requests succeed
4. Look for Console logs:
   - `"Step 3 data:"` - should show complete data
   - `"renderResults called with rows:"` - should show 5 results

### Finance or Healthcare Upload Fails

**Issue**: Selecting an image on a card returns an upload error

**Solution**:
1. Use PNG/JPEG/WebP images under 8 MB
2. Confirm the backend is running on `8082`
3. Check `POST /api/upload_medical_image` in the browser Network tab
4. Finance uploads are used as UI previews; they do not need to be written to disk for analysis

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

### Phase 1: Data Selection (Step 1)
- Select healthcare or finance data cards
- Optionally upload image previews with each card's `Select` control
- Generate sparkline previews for quick visual inspection
- Compute frequency spectrum analysis (FFT)
- Display time-frequency spectrograms (CSI only)

### Phase 2: Encryption & Local Encoders (Step 2)
- Extract 8-dimensional features from each modality
- Encrypt features using CKKS homomorphic encryption
- Dispatch selected modalities to local encoder tools
- Execute encrypted inference using MCP tool cluster

### Phase 3: MyGPTShield Server (Step 3)
- Stream multiple ciphertext previews in the encoded output card
- Generate a synthetic peer database
- Shuffle and anonymize the real record before LLM summarization
- Send only a bucketed protected summary to the selected LLM

### Phase 4: Report Generation (Step 4)
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

**Last Updated**: 2026-05-12
**Version**: MyGPTShield demo with healthcare and finance scenes

## 🌟 Acknowledgments

- FL-Datasets-for-HAR contributors for providing real-world sensor data
- TenSEAL/OpenMined team for the homomorphic encryption library
- Anthropic for MCP protocol and Claude integration
- DeepSeek for LLM dispatch capabilities
