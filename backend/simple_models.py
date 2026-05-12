"""
Lightweight Homomorphic Models for Demo
Simple models that can be converted to homomorphic computation
"""

import numpy as np
from typing import Dict, Any, Tuple, Optional

try:
    import torch
    import torch.nn as nn
    TORCH_AVAILABLE = True
except ImportError:
    torch = None
    nn = None
    TORCH_AVAILABLE = False


class _NumpyModule:
    def __call__(self, x):
        return self.forward(x)


BaseModel = nn.Module if TORCH_AVAILABLE else _NumpyModule


class SimpleTimeSeriesModel(BaseModel):
    """
    Simple linear model for time series data
    Uses 2-layer MLP with minimal parameters for efficient HE computation
    """
    def __init__(self, input_dim: int = 8, hidden_dim: int = 16, output_dim: int = 1):
        super(SimpleTimeSeriesModel, self).__init__()
        self.input_dim = input_dim
        self.hidden_dim = hidden_dim
        self.output_dim = output_dim

        if TORCH_AVAILABLE:
            self.fc1 = nn.Linear(input_dim, hidden_dim)
            self.fc2 = nn.Linear(hidden_dim, output_dim)
            self.relu = nn.ReLU()
        else:
            rng = np.random.default_rng(input_dim * 1000 + hidden_dim * 10 + output_dim)
            self.w1 = rng.normal(0, 0.12, size=(hidden_dim, input_dim))
            self.b1 = rng.normal(0, 0.03, size=(hidden_dim,))
            self.w2 = rng.normal(0, 0.12, size=(output_dim, hidden_dim))
            self.b2 = rng.normal(0, 0.03, size=(output_dim,))

    def forward(self, x):
        """
        Forward pass: x -> fc1 -> relu -> fc2 -> output
        """
        if TORCH_AVAILABLE:
            x = self.fc1(x)
            x = self.relu(x)
            x = self.fc2(x)
            return x

        arr = np.asarray(x, dtype=float)
        hidden = np.maximum(arr @ self.w1.T + self.b1, 0)
        return hidden @ self.w2.T + self.b2

    def get_weights_for_he(self) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Extract weights for homomorphic encryption

        Returns:
            (W1, b1, W2, b2): Weight matrices and biases
        """
        if TORCH_AVAILABLE:
            W1 = self.fc1.weight.detach().numpy().flatten()
            b1 = self.fc1.bias.detach().numpy()
            W2 = self.fc2.weight.detach().numpy().flatten()
            b2 = self.fc2.bias.detach().numpy()
            return W1, b1, W2, b2

        W1 = self.w1.flatten()
        b1 = self.b1
        W2 = self.w2.flatten()
        b2 = self.b2
        return W1, b1, W2, b2

    def compute_he_formula(self, features: np.ndarray) -> Tuple[float, float]:
        """
        Simplified formula for HE: output = features · W + b
        Approximates the 2-layer MLP with a single linear transformation

        Args:
            features: Input feature vector

        Returns:
            (weight, bias) for single linear layer approximation
        """
        # Combine two layers into single linear transformation
        W1, b1, W2, b2 = self.get_weights_for_he()

        # For ReLU network, approximate with single linear layer
        # Effective weight = W2 * W1 (simplified)
        # Effective bias = W2 * b1 + b2
        effective_weight = np.dot(W2.reshape(-1, self.hidden_dim),
                                 W1.reshape(self.hidden_dim, -1))
        effective_bias = np.dot(W2, b1) + b2

        return effective_weight.flatten(), effective_bias


class SimpleCNNModel(BaseModel):
    """
    Simple CNN for image data (Depth/RGB)
    Uses single convolutional layer for minimal HE computation
    """
    def __init__(self, in_channels: int = 1, hidden_dim: int = 32, output_dim: int = 1):
        super(SimpleCNNModel, self).__init__()
        self.in_channels = in_channels
        self.hidden_dim = hidden_dim
        self.output_dim = output_dim

        if TORCH_AVAILABLE:
            self.conv1 = nn.Conv2d(in_channels, hidden_dim, kernel_size=3, padding=1)
            self.pool = nn.AdaptiveAvgPool2d(1)
            self.fc = nn.Linear(hidden_dim, output_dim)
            self.relu = nn.ReLU()
        else:
            rng = np.random.default_rng(in_channels * 1000 + hidden_dim * 10 + output_dim)
            self.conv_w = rng.normal(0, 0.08, size=(hidden_dim, in_channels, 3, 3))
            self.fc_w = rng.normal(0, 0.08, size=(output_dim, hidden_dim))
            self.fc_b = rng.normal(0, 0.03, size=(output_dim,))

    def forward(self, x):
        """
        Forward pass: x -> conv -> relu -> pool -> fc -> output
        """
        if TORCH_AVAILABLE:
            x = self.conv1(x)
            x = self.relu(x)
            x = self.pool(x)
            x = x.view(x.size(0), -1)
            x = self.fc(x)
            return x

        arr = np.asarray(x, dtype=float)
        if arr.ndim == 3:
            arr = arr[None, ...]
        pooled = arr.mean(axis=(-2, -1))
        channel_weights = self.conv_w.mean(axis=(-2, -1)).T
        hidden = np.maximum(pooled @ channel_weights, 0)
        return hidden @ self.fc_w.T + self.fc_b

    def get_weights_for_he(self) -> Tuple[np.ndarray, np.ndarray]:
        """
        Extract weights for homomorphic encryption

        Returns:
            (weight, bias): Flattened convolutional weights and FC bias
        """
        if TORCH_AVAILABLE:
            conv_w = self.conv1.weight.detach().numpy()
            fc_b = self.fc.bias.detach().numpy()
        else:
            conv_w = self.conv_w
            fc_b = self.fc_b

        # Flatten to (out_channels, in_channels * 9)
        conv_w_flat = conv_w.reshape(self.hidden_dim, -1)

        return conv_w_flat, fc_b

    def compute_he_formula(self, features: np.ndarray) -> Tuple[float, float]:
        """
        Simplified formula for HE: output = features · W + b
        Approximates CNN with single linear transformation

        Args:
            features: Flattened input features

        Returns:
            (weight, bias) for single linear layer approximation
        """
        conv_w, fc_b = self.get_weights_for_he()

        # Average conv weights across channels for simplicity
        effective_weight = np.mean(conv_w, axis=1)
        effective_bias = fc_b

        return effective_weight, effective_bias


def create_model_for_modality(modality: str,
                             model_type: str = "time_series") -> Any:
    """
    Factory function to create models for different sensor modalities

    Args:
        modality: Sensor type ("UWB", "IMU", "CSI", "Depth", "RGB")
        model_type: Model architecture ("time_series" or "cnn")

    Returns:
        Initialized PyTorch model

    Example:
        >>> model = create_model_for_modality("UWB")
        >>> model = create_model_for_modality("Depth", model_type="cnn")
    """
    # Model configurations per modality
    configs = {
        "UWB": {
            "type": "time_series",
            "input_dim": 8,
            "hidden_dim": 16,
            "output_dim": 1
        },
        "IMU": {
            "type": "time_series",
            "input_dim": 8,
            "hidden_dim": 16,
            "output_dim": 1
        },
        "CSI": {
            "type": "time_series",
            "input_dim": 8,
            "hidden_dim": 16,
            "output_dim": 1
        },
        "Depth": {
            "type": "cnn",
            "in_channels": 1,
            "hidden_dim": 32,
            "output_dim": 1
        },
        "RGB": {
            "type": "cnn",
            "in_channels": 3,
            "hidden_dim": 32,
            "output_dim": 1
        }
    }

    # Get configuration
    config = configs.get(modality, configs["UWB"])

    # Create model based on type
    if config["type"] == "time_series":
        model = SimpleTimeSeriesModel(
            input_dim=config["input_dim"],
            hidden_dim=config["hidden_dim"],
            output_dim=config["output_dim"]
        )
    else:  # CNN
        model = SimpleCNNModel(
            in_channels=config["in_channels"],
            hidden_dim=config["hidden_dim"],
            output_dim=config["output_dim"]
        )

    return model


# Demo test function
if __name__ == "__main__":
    print("Testing SimpleTimeSeriesModel...")
    ts_model = SimpleTimeSeriesModel(input_dim=8, hidden_dim=16, output_dim=1)

    # Test forward pass
    x = torch.randn(1, 8) if TORCH_AVAILABLE else np.random.randn(1, 8)
    output = ts_model(x)
    print(f"  Input shape: {x.shape}")
    print(f"  Output shape: {output.shape}")
    print(f"  Output value: {float(np.asarray(output).reshape(-1)[0]):.4f}")

    # Test HE weight extraction
    W1, b1, W2, b2 = ts_model.get_weights_for_he()
    print(f"  W1 shape: {W1.shape}, b1 shape: {b1.shape}")
    print(f"  W2 shape: {W2.shape}, b2 shape: {b2.shape}")

    # Test HE formula
    features = np.random.randn(8)
    weight, bias = ts_model.compute_he_formula(features)
    print(f"  HE weight shape: {weight.shape}, bias shape: {bias.shape}")

    print("\nTesting SimpleCNNModel...")
    cnn_model = SimpleCNNModel(in_channels=1, hidden_dim=32, output_dim=1)

    # Test forward pass
    x = torch.randn(1, 1, 64, 64) if TORCH_AVAILABLE else np.random.randn(1, 1, 64, 64)
    output = cnn_model(x)
    print(f"  Input shape: {x.shape}")
    print(f"  Output shape: {output.shape}")
    print(f"  Output value: {float(np.asarray(output).reshape(-1)[0]):.4f}")

    # Test HE weight extraction
    conv_w, fc_b = cnn_model.get_weights_for_he()
    print(f"  Conv weight shape: {conv_w.shape}, FC bias shape: {fc_b.shape}")

    # Test HE formula
    features = np.random.randn(64 * 64)
    weight, bias = cnn_model.compute_he_formula(features)
    print(f"  HE weight shape: {weight.shape}, bias shape: {bias.shape}")

    print("\nTesting create_model_for_modality...")
    for modality in ["UWB", "IMU", "CSI", "Depth", "RGB"]:
        model = create_model_for_modality(modality)
        print(f"  {modality}: {model.__class__.__name__}")

    print("\nAll tests passed!")
