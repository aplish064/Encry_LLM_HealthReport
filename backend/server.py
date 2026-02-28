
import os
import sys
import tenseal as ts
from fastmcp import FastMCP

mcp = FastMCP("Homomorphic_Prediction_Model_Cluster")

def load_context_and_vector(context_path: str, data_path: str):
    if not os.path.exists(context_path):
        raise FileNotFoundError(f"Context not found: {context_path}")
    if not os.path.exists(data_path):
        raise FileNotFoundError(f"Encrypted input not found: {data_path}")
    with open(context_path, "rb") as f:
        ctx = ts.context_from(f.read())
    with open(data_path, "rb") as f:
        vec = ts.ckks_vector_from(ctx, f.read())
    return ctx, vec

def save_vector(vec, output_path: str):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "wb") as f:
        f.write(vec.serialize())

def he_linear(enc_vec, weights, bias):
    # TenSEAL supports dot(list[float]) -> ckks_vector(length=1)
    out = enc_vec.dot(weights)
    out = out + bias
    return out

# Fixed 8-dim input feature vector for all tools in this demo.
WEIGHTS = {
    "secure_ecg_toolbox": ([0.35, 0.10, -0.08, 0.18, 0.22, -0.12, 0.05, 0.09], 0.95),
    "secure_bp_toolbox":  ([0.50, -0.15, 0.06, 0.14, 0.18, -0.10, 0.04, 0.08], 1.00),
    "secure_sleep_toolbox": ([0.28, 0.12, -0.06, 0.10, 0.16, -0.08, 0.05, 0.07], 0.85),
    "secure_metabolic_toolbox": ([0.22, 0.18, -0.04, 0.08, 0.14, -0.10, 0.06, 0.09], 0.90),
    "secure_risk_toolbox": ([0.30, 0.08, -0.05, 0.16, 0.20, -0.11, 0.03, 0.10], 0.92),
    "secure_anomaly_toolbox": ([0.26, 0.14, -0.07, 0.12, 0.24, -0.13, 0.02, 0.11], 0.88),
}

def _run(tool_name: str, context_path: str, data_path: str, output_path: str) -> str:
    sys.stderr.write(f"LOG: {tool_name} running on {data_path}\n")
    _, enc_vec = load_context_and_vector(context_path, data_path)
    w, b = WEIGHTS[tool_name]
    out = he_linear(enc_vec, w, b)
    save_vector(out, output_path)
    return f"OK: {tool_name} -> {output_path}"

@mcp.tool()
def secure_ecg_toolbox(context_path: str, data_path: str, output_path: str) -> str:
    """Encrypted ECG-arrhythmia proxy model (input: CSI features)."""
    try:
        return _run("secure_ecg_toolbox", context_path, data_path, output_path)
    except Exception as e:
        return f"ERR: {e}"

@mcp.tool()
def secure_bp_toolbox(context_path: str, data_path: str, output_path: str) -> str:
    """Encrypted blood pressure prediction model (input: UWB features)."""
    try:
        return _run("secure_bp_toolbox", context_path, data_path, output_path)
    except Exception as e:
        return f"ERR: {e}"

@mcp.tool()
def secure_sleep_toolbox(context_path: str, data_path: str, output_path: str) -> str:
    """Encrypted sleep stage estimation model (input: Depth features)."""
    try:
        return _run("secure_sleep_toolbox", context_path, data_path, output_path)
    except Exception as e:
        return f"ERR: {e}"

@mcp.tool()
def secure_metabolic_toolbox(context_path: str, data_path: str, output_path: str) -> str:
    """Encrypted metabolic assessment model (input: IMU features)."""
    try:
        return _run("secure_metabolic_toolbox", context_path, data_path, output_path)
    except Exception as e:
        return f"ERR: {e}"

@mcp.tool()
def secure_risk_toolbox(context_path: str, data_path: str, output_path: str) -> str:
    """Encrypted risk scoring model (input: RGB features)."""
    try:
        return _run("secure_risk_toolbox", context_path, data_path, output_path)
    except Exception as e:
        return f"ERR: {e}"

@mcp.tool()
def secure_anomaly_toolbox(context_path: str, data_path: str, output_path: str) -> str:
    """Encrypted anomaly detection model (optional; demo)."""
    try:
        return _run("secure_anomaly_toolbox", context_path, data_path, output_path)
    except Exception as e:
        return f"ERR: {e}"

if __name__ == "__main__":
    sys.stderr.write("LOG: MCP Cluster Server ready (6 tools).\n")
    mcp.run(transport="stdio")
