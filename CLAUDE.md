# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## AI Coding Guidelines

Behavioral guidelines to reduce common LLM coding mistakes. Merge with project-specific instructions as needed.

**Tradeoff:** These guidelines bias toward caution over speed. For trivial tasks, use judgment.

### 1. Think Before Coding

**Don't assume. Don't hide confusion. Surface tradeoffs.**

Before implementing:
- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them - don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

### 2. Simplicity First

**Minimum code that solves the problem. Nothing speculative.**

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.

Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

### 3. Surgical Changes

**Touch only what you must. Clean up only your own mess.**

When editing existing code:
- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it - don't delete it.

When your changes create orphans:
- Remove imports/variables/functions that YOUR changes made unused.
- Don't remove pre-existing dead code unless asked.

The test: Every changed line should trace directly to the user's request.

### 4. Goal-Driven Execution

**Define success criteria. Loop until verified.**

Transform tasks into verifiable goals:
- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Refactor X" → "Ensure tests pass before and after"

For multi-step tasks, state a brief plan:
```
1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]
```

Strong success criteria let you loop independently. Weak criteria ("make it work") require constant clarification.

### 5. Project-Specific Rules

**File Management:**
- All intermediate test scripts MUST be placed in `temp/` folder at project root
- Do NOT create any additional .md files except `README.md`
- Do NOT create one-click startup scripts (.sh, .bat, etc.)

**Environment Management:**
- Always use Python virtual environment in current project
- Create venv if it doesn't exist: `python -m venv venv`
- Activate before running: `source venv/bin/activate` (Linux/Mac) or `venv\Scripts\activate` (Windows)
- Install dependencies: `pip install -r backend/requirements.txt`

**Git Commit Policy:**
- Do NOT commit automatically unless explicitly asked
- User handles all git commits themselves
- Only commit when user explicitly requests it

---

**These guidelines are working if:** fewer unnecessary changes in diffs, fewer rewrites due to overcomplication, and clarifying questions come before implementation rather than after mistakes.

## Project Overview

A privacy-preserving multimodal health monitoring system demonstration using **Homomorphic Encryption (CKKS)** and **Large Language Models (DeepSeek)**. The system processes 5 sensor modalities through encrypted inference to generate clinical health reports while protecting user privacy.

### Core Pipeline

```
📊 Local Multimodal Sensor Data → 🔐 CKKS Encryption → 🤖 DeepSeek LLM Dispatch → 
🔧 MCP Tool Cluster (6 models) → 🔓 Local Decryption → 📈 Clinical Report
```

## Development Commands

### Setup Virtual Environment

```bash
# Create virtual environment (if not exists)
python -m venv venv

# Activate virtual environment
# Linux/Mac:
source venv/bin/activate
# Windows:
venv\Scripts\activate

# Install dependencies
pip install -r backend/requirements.txt
```

Required: Python 3.8+, FastAPI, TenSEAL, NumPy, Matplotlib, MCP, OpenAI SDK, PyTorch

### Start Backend Server

**Note: Ensure virtual environment is activated before running**

```bash
# Activate venv first (see above)
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate     # Windows

cd backend
# Basic mode (simulated LLM dispatch)
uvicorn app:app --host 127.0.0.1 --port 8080

# With DeepSeek API integration
export DEEPSEEK_API_KEY="your-api-key"
export DEEPSEEK_BASE_URL="https://api.deepseek.com"
export DEEPSEEK_MODEL="deepseek-chat"
uvicorn app:app --host 127.0.0.1 --port 8080
```

Backend runs on **port 8080** (configurable in frontend `app.js` via `API_BASE`)

### Start Frontend Server

```bash
cd frontend
python -m http.server 8001
```

Frontend runs on **port 8001** - Access at `http://127.0.0.1:8001`

### Generate Test Data

**Note: Ensure virtual environment is activated before running**

```bash
# Activate venv first (see above)

# Generate all 5 modalities (UWB, IMU, CSI, Depth, RGB)
python scripts/generate_multimodal_data.py

# Generate specific modality
python scripts/generate_data.py --modality UWB --frames 256 --seed 42
```

Outputs to `sample_data/` directory (gitignored)

## Architecture Overview

### Backend Structure (`backend/`)

**app.py** (1039 lines) - Main FastAPI application
- **Step 1**: Data collection from 5 modalities (Depth, UWB, IMU, CSI, RGB)
  - Real data loading from `test_data/` or simulation fallback
  - FFT spectrum analysis and spectrogram generation
  - Image preview generation for depth/RGB modalities
- **Step 2**: Encryption and LLM dispatch
  - Feature extraction (8-dim vectors per modality)
  - CKKS encryption context setup (`setup_context()`)
  - DeepSeek LLM intelligent dispatch to MCP tools
  - Parallel execution of 6 MCP tools via `run_mcp_inference()`
- **Step 3**: Decryption and report generation
  - Local decryption of inference results
  - Health report synthesis (`build_health_report()`)
  - LLM-generated clinical conclusion

**server.py** (99 lines) - MCP tool server
- 6 homomorphic inference tools using FastMCP
- Each tool implements encrypted linear regression: `output = input · weights + bias`
- Tools: `secure_ecg_toolbox`, `secure_bp_toolbox`, `secure_sleep_toolbox`, `secure_metabolic_toolbox`, `secure_risk_toolbox`, `secure_anomaly_toolbox`
- Runs as stdio subprocess, launched by `app.py` via `mcp.client.stdio`

**Key Configuration Paths**:
```python
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA_PATHS = {
    "UWB": os.path.join(BASE_DIR, "test_data", "uwb_sample.txt"),
    "IMU": os.path.join(BASE_DIR, "test_data", "imu_sample.txt"),
    "CSI": os.path.join(BASE_DIR, "test_data", "csi_sample.csv"),
}
ASSET_USER_DIR = os.path.join(BASE_DIR, "frontend", "assets", "user")
DEPTH_PNG_PATH = os.path.join(ASSET_USER_DIR, "deep2.png")
RGB_PNG_PATH = os.path.join(ASSET_USER_DIR, "RGB.png")
```

### Frontend Structure (`frontend/`)

**index.html** - Main application page
- 3-step pipeline visualization (Data → Encryption → Report)
- Real-time modalities preview with FFT spectra
- Interactive health dashboard with charts

**assets/js/app.js** (679 lines) - Frontend logic
- Auto-refresh cycle (default 10s, configurable via `setInterval`)
- Chart rendering: radar charts, donut charts, bar charts, progress bars
- API communication with backend (`/api/cycle` endpoint)
- SVG-based visualization (no external chart libraries)

**assets/css/styles.css** (987 lines) - Responsive layout
- Grid-based modality cards
- Step-by-step visualization
- Health report styling

### Sensor Modalities

| Modality | Data Type | Purpose | Feature Extraction |
|----------|-----------|---------|-------------------|
| **Depth** | 64×64 image | Sleep posture detection | Gradient-based features |
| **UWB** | Time series (3 channels) | Blood pressure, motion | Mean, std, min, max, percentiles |
| **IMU** | Time series (6 channels) | Gait analysis, metabolic assessment | Statistical moments, variance |
| **CSI** | Time series (8 channels) | Heart rate, respiratory monitoring | Frequency domain features |
| **RGB** | 64×64×3 image | Risk scoring, fall detection | Channel-wise statistics |

### MCP Tool Assignments

Default LLM dispatch mapping:
```python
DEFAULT_ASSIGNMENTS = [
    {"input_modality": "CSI", "model_id": "ecg", "tool": "secure_ecg_toolbox"},
    {"input_modality": "UWB", "model_id": "bp", "tool": "secure_bp_toolbox"},
    {"input_modality": "Depth", "model_id": "sleep", "tool": "secure_sleep_toolbox"},
    {"input_modality": "IMU", "model_id": "metabolic", "tool": "secure_metabolic_toolbox"},
    {"input_modality": "RGB", "model_id": "risk", "tool": "secure_risk_toolbox"},
]
```

When `DEEPSEEK_API_KEY` is configured, the LLM dynamically reassigns modalities to tools.

## Key Technical Details

### Homomorphic Encryption (CKKS)

Parameters configured in `setup_context()`:
```python
scheme: CKKS
poly_modulus_degree: 16384
coeff_mod_bit_sizes: [60, 40, 40, 40, 40, 40, 60]
global_scale: 2^40
```

Encryption workflow:
1. Extract 8-dimensional feature vectors from raw sensor data
2. Encrypt using `ts.ckks_vector(ctx, features)`
3. Execute encrypted inference via MCP tools
4. Decrypt results locally using `out_ct.decrypt()[0]`

### API Endpoints

- `GET /api/health` - Health check
- `GET /api/cycle` - Complete 3-step pipeline execution (returns JSON with steps 1/2/3)

### LLM Integration

Environment variables:
- `DEEPSEEK_API_KEY` / `LLM_API_KEY` - API key
- `DEEPSEEK_BASE_URL` / `LLM_BASE_URL` - Base URL (default: https://api.deepseek.com)
- `DEEPSEEK_MODEL` / `LLM_MODEL` - Model name (default: deepseek-chat)

Two LLM calls per cycle:
1. **Dispatch**: Assign modalities to tools (`llm_dispatch_plan()`)
2. **Conclusion**: Generate clinical report summary (`generate_report_conclusion()`)

### Data Simulation

When real data files are missing, the system falls back to simulation:
- `sim_timeseries()` - Generates time series with sine waves + noise
- `sim_depth()` - Gaussian blob pattern
- `sim_rgb()` - Colored blob on noise background

## Performance Characteristics

- **Data encryption**: ~0.1-0.3 seconds (5 modalities)
- **MCP inference**: ~15-20 seconds (5 tools in parallel via stdio)
- **Report generation**: ~0.5-1 second
- **Full cycle**: ~20-25 seconds

## Important Notes

### Demo Purpose Only
- ⚠️ This system is for **technical demonstration only**, NOT for medical diagnosis
- ⚠️ All health metrics are simulated/estimated values without clinical accuracy
- ⚠️ Fall risk assessment uses demo algorithms, not real medical models

### Data Privacy
- ✅ All sensitive data encrypted locally before transmission
- ✅ Server only receives encrypted ciphertext
- ✅ Inference results decrypted locally only
- ❌ Demo uses temporary file system (`/tmp/`); production requires secure storage

### Modification Guidelines

When modifying the system:

**Backend changes** (`backend/app.py`):
- Feature extraction functions: `feat_from_series()`, `feat_from_depth()`, `feat_from_rgb()`
- Encryption parameters: `setup_context()`
- Report generation: `build_health_report()`
- Modality simulation: `sim_timeseries()`, `sim_depth()`, `sim_rgb()`

**MCP tools** (`backend/server.py`):
- Model weights: Modify `WEIGHTS` dictionary
- Add new tools: Use `@mcp.tool()` decorator following existing pattern
- Tool logic: Update `_run()` function for custom inference

**Frontend changes** (`frontend/assets/js/app.js`):
- Refresh rate: Modify `setInterval(runCycle, 10000)` at end of file
- API endpoint: Change `API_BASE` constant
- Chart rendering: Update `renderResults()`, `renderModalities()`, `renderStep2()`

**Configuration**:
- Backend port: Change `--port 8080` in uvicorn command
- Frontend port: Change `8001` in http.server command
- Data paths: Update `DATA_PATHS` in `app.py`

## Troubleshooting

**Backend fails to start**: Ensure all dependencies installed via `pip install -r requirements.txt`

**TenSEAL installation issues**: 
```bash
pip install tenseal --no-build-isolation
# or
conda install -c conda-forge tenseal
```

**Frontend can't connect**: 
1. Check backend is running on port 8080
2. Verify `API_BASE` in `frontend/assets/js/app.js` matches backend port
3. Ensure firewall allows local connections

**Missing test data**: System will auto-simulate. To use real data, place files in `test_data/`:
- `uwb_sample.txt` (whitespace or comma-separated)
- `imu_sample.txt` (whitespace or comma-separated)
- `csi_sample.csv` (comma-separated)

**Charts not displaying**: Open browser DevTools (F12) → Console tab, check for:
- `"Step 3 data:"` log
- `"renderResults called with rows:"` log
- Network tab → `/api/cycle` request status
