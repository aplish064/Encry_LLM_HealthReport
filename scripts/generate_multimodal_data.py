#!/usr/bin/env python3
"""Generate mock multimodal data files used in the demo.

Outputs (by default into ./sample_data):
- depth.npy (64x64 float32 in [0,1])
- rgb.npy   (64x64x3 float32 in [0,1])
- uwb.csv   (t,c0,c1,c2)
- imu.csv   (t,c0..c5)
- csi.csv   (t,c0..c7)  # demo-compressed CSI features

Note: The web demo auto-simulates data on the backend every 10s.
This script is only for offline inspection / reproduction.
"""

import os
import numpy as np

def sim_timeseries(frames: int, dims: int, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    t = np.linspace(0, 10, frames)
    base = np.sin(2*np.pi*0.35*t) + 0.35*np.sin(2*np.pi*0.09*t + 0.7)
    drift = 0.015*t
    X = []
    for i in range(dims):
        noise = rng.normal(0, 0.06 + 0.01*i, size=frames)
        comp = (1.0+0.05*i)*(base + 0.2*np.sin(2*np.pi*(0.18+0.02*i)*t + 0.25*i) + drift) + noise
        X.append(comp)
    return np.stack(X, axis=1)

def sim_depth(seed: int, h: int = 64, w: int = 64) -> np.ndarray:
    rng = np.random.default_rng(seed)
    y, x = np.mgrid[0:h, 0:w]
    cx, cy = w*0.5 + rng.normal(0, 2.0), h*0.5 + rng.normal(0, 2.0)
    r = np.sqrt((x-cx)**2 + (y-cy)**2)
    depth = np.exp(-(r**2)/(2*(w*0.22)**2)) + 0.15*rng.normal(0, 1, size=(h,w))
    return np.clip(depth, 0, 1).astype(np.float32)

def sim_rgb(seed: int, h: int = 64, w: int = 64) -> np.ndarray:
    rng = np.random.default_rng(seed)
    base = rng.uniform(0.15, 0.9, size=(h,w,3))
    y, x = np.mgrid[0:h, 0:w]
    cx, cy = w*0.55 + rng.normal(0, 3.0), h*0.45 + rng.normal(0, 3.0)
    r2 = (x-cx)**2 + (y-cy)**2
    blob = np.exp(-r2/(2*(w*0.18)**2))
    base[...,0] = np.clip(base[...,0] + 0.35*blob, 0, 1)
    base[...,1] = np.clip(base[...,1] + 0.15*blob, 0, 1)
    return base.astype(np.float32)

def save_csv(path: str, X: np.ndarray):
    frames, dims = X.shape
    t = np.linspace(0, 10, frames)
    header = ["t"] + [f"c{i}" for i in range(dims)]
    with open(path, "w", encoding="utf-8") as f:
        f.write(",".join(header) + "\n")
        for i in range(frames):
            row = [f"{t[i]:.6f}"] + [f"{X[i,j]:.6f}" for j in range(dims)]
            f.write(",".join(row) + "\n")

def main(out_dir: str = "sample_data", seed: int = 123):
    os.makedirs(out_dir, exist_ok=True)

    uwb = sim_timeseries(240, 3, seed+11)
    imu = sim_timeseries(240, 6, seed+22)
    csi = sim_timeseries(240, 8, seed+33)
    depth = sim_depth(seed+44)
    rgb = sim_rgb(seed+55)

    save_csv(os.path.join(out_dir, "uwb.csv"), uwb)
    save_csv(os.path.join(out_dir, "imu.csv"), imu)
    save_csv(os.path.join(out_dir, "csi.csv"), csi)
    np.save(os.path.join(out_dir, "depth.npy"), depth)
    np.save(os.path.join(out_dir, "rgb.npy"), rgb)

    print(f"Saved mock data into: {out_dir}")

if __name__ == "__main__":
    main()
