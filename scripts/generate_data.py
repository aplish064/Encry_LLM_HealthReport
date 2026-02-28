
import argparse
import csv
import numpy as np

def generate(modality: str, frames: int, seed: int):
    rng = np.random.default_rng(seed)
    modality = modality.upper()
    dims = 3 if modality == "UWB" else 6
    t = np.linspace(0, 10, frames)
    base = np.sin(2*np.pi*0.4*t) + 0.4*np.sin(2*np.pi*0.1*t + 0.8)
    drift = 0.02 * t
    spikes = np.zeros_like(t)
    spike_idx = rng.choice(np.arange(frames), size=max(1, frames//40), replace=False)
    spikes[spike_idx] = rng.normal(0, 1.0, size=spike_idx.shape[0])

    X = []
    for c in range(dims):
        phase = 0.25*c
        scale = 1.0 + 0.06*c
        noise = rng.normal(0, 0.06 + 0.01*c, size=frames)
        comp = scale*(base + 0.2*np.sin(2*np.pi*(0.18+0.02*c)*t + phase) + drift) + 0.15*spikes + noise
        X.append(comp)
    X = np.stack(X, axis=1)

    header = ["t"] + [f"c{i}" for i in range(dims)]
    rows = []
    for i in range(frames):
        rows.append([t[i]] + X[i].tolist())
    return header, rows

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--modality", choices=["UWB","IMU"], default="UWB")
    ap.add_argument("--frames", type=int, default=256)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out", default="sample_data.csv")
    args = ap.parse_args()
    header, rows = generate(args.modality, args.frames, args.seed)
    with open(args.out, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)
    print(f"Wrote {args.out} ({len(rows)} rows, {args.modality})")

if __name__ == "__main__":
    main()
