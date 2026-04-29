# Test Data Directory

This directory contains test data for the 10 modalities used in the privacy-preserving health monitoring system.

## Required Files (9 files)

### Time Series Sensor Data
- **`uwb_from_utar.txt`** - UWB radar sensor data (200×3)
  - Format: Whitespace-separated numeric values
  - Purpose: Blood pressure, motion detection
  - Source: UTAR dataset

- **`imu_from_utar.txt`** - IMU inertial sensor data (250×6)
  - Format: Whitespace-separated numeric values
  - Purpose: Gait analysis, metabolic assessment
  - Source: UTAR dataset

- **`csi_from_utar.csv`** - WiFi channel state information (200×8)
  - Format: Comma-separated values (CSV)
  - Purpose: Heart rate, respiratory monitoring
  - Source: UTAR dataset

### Skeleton Keypoint Data
- **`ntu_from_test.txt`** - NTU skeleton keypoint data
  - Format: 3D joint coordinates (25 keypoints × 3 dimensions)
  - Purpose: Human action recognition, fall detection
  - Source: NTU RGB+D dataset

- **`ntu_labels.txt`** - NTU action labels
  - Format: Text labels (one per sample)
  - Purpose: Action classification for skeleton data
  - Source: NTU RGB+D dataset

### Medical Imaging Data
- **`retina_sample.npz`** - Retinal fundus images (10 samples)
  - Format: NumPy compressed array
  - Purpose: Diabetic retinopathy screening
  - Content: High-resolution fundus photography

- **`chest_sample.npz`** - Chest X-ray images (10 samples)
  - Format: NumPy compressed array
  - Purpose: Pneumonia detection, lung analysis
  - Content: Posteroanterior chest X-rays

- **`path_sample.npz`** - Pathology images (10 samples)
  - Format: NumPy compressed array
  - Purpose: Tissue analysis, cancer detection
  - Content: Histopathology slides

- **`blood_sample.npz`** - Blood cell images (10 samples)
  - Format: NumPy compressed array
  - Purpose: Blood disorder diagnosis
  - Content: Microscopy blood smears

## Image Files (2 files)

Located in `frontend/assets/user/`:

- **`deep2.png`** - Depth image (64×64 grayscale)
  - Purpose: Sleep posture detection
  - Format: PNG image

- **`RGB.png`** - RGB image (64×64×3 color)
  - Purpose: Risk scoring, fall detection
  - Format: PNG image

## Total Modalities: 10 ✅

1. UWB radar sensor
2. IMU inertial sensor
3. WiFi CSI
4. Skeleton keypoints
5. Retinal fundus imaging
6. Chest X-ray
7. Pathology imaging
8. Blood cell imaging
9. Depth sensing
10. RGB imaging

## Historical Context

### Old Sample Files (Removed)
The following files were previously used but have been replaced:
- ~~`csi_sample.csv`~~ (replaced by `csi_from_utar.csv`)
- ~~`imu_sample.txt`~~ (replaced by `imu_from_utar.txt`)
- ~~`uwb_sample.txt`~~ (replaced by `uwb_from_utar.txt`)

**Note:** The old sample files used simplified naming and may have had different formats. The new `*_from_utar.*` files provide standardized, dataset-originated test data.

## Data Usage in Backend

The backend application (`backend/app.py`) loads these files for the 5 primary modalities:

```python
DATA_PATHS = {
    "UWB": os.path.join(BASE_DIR, "test_data", "uwb_from_utar.txt"),
    "IMU": os.path.join(BASE_DIR, "test_data", "imu_from_utar.txt"),
    "CSI": os.path.join(BASE_DIR, "test_data", "csi_from_utar.csv"),
}

ASSET_USER_DIR = os.path.join(BASE_DIR, "frontend", "assets", "user")
DEPTH_PNG_PATH = os.path.join(ASSET_USER_DIR, "deep2.png")
RGB_PNG_PATH = os.path.join(ASSET_USER_DIR, "RGB.png")
```

**Fallback Simulation:** If any required file is missing, the system automatically generates simulated data using the following functions:
- `sim_timeseries()` - For UWB, IMU, CSI modalities
- `sim_depth()` - For depth images
- `sim_rgb()` - For RGB images

## Data Format Specifications

### Time Series Files (.txt, .csv)
- Whitespace or comma-separated values
- Multi-column format (3-8 channels depending on modality)
- Row count: 200-250 samples typical
- No header row

### NumPy Files (.npz)
- Compressed NumPy arrays
- Load with: `data = np.load('file.npz')`
- Access with: `images = data['images']` or `data['arr_0']`
- Shape: (N, H, W) or (N, H, W, C) depending on modality

### Image Files (.png)
- Standard PNG format
- Depth: 64×64 grayscale (1 channel)
- RGB: 64×64×3 color (3 channels)

## Adding New Test Data

To add new test data:

1. Place files in this directory (`test_data/`)
2. Update `DATA_PATHS` in `backend/app.py` if adding new time series modalities
3. Follow existing format conventions for consistency
4. Update this README to document the new files

## Privacy and Security

**Important:** All test data in this directory is for demonstration purposes only. The system is designed to:
- Encrypt sensitive data locally using CKKS homomorphic encryption
- Transmit only encrypted ciphertext to the server
- Never expose raw sensor data in unencrypted form

For production deployment, ensure all test data is replaced with properly anonymized, consented patient data following HIPAA/GDPR guidelines.
