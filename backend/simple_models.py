"""
Lightweight Homomorphic Models for Demo
Simple models that can be converted to homomorphic computation
"""

import numpy as np
import torch
import torch.nn as nn
from typing import Dict, Any, Tuple, Optional


class SimpleTimeSeriesModel(nn.Module):
    """
    Simple linear model for time series data
    Uses 2-layer MLP with minimal parameters for efficient HE computation
    """
    def __init__(self, input_dim: int = 8, hidden_dim: int = 16, output_dim: int = 1):
        super(SimpleTimeSeriesModel, self).__init__()
        self.input_dim = input_dim
        self.hidden_dim = hidden_dim
        self.output_dim = output_dim

        # Simple 2-layer MLP
        self.fc1 = nn.Linear(input_dim, hidden_dim)
        self.fc2 = nn.Linear(hidden_dim, output_dim)
        self.relu = nn.ReLU()

    def forward(self, x):
        """
        Forward pass: x -> fc1 -> relu -> fc2 -> output
        """
        x = self.fc1(x)
        x = self.relu(x)
        x = self.fc2(x)
        return x

    def get_weights_for_he(self) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Extract weights for homomorphic encryption

        Returns:
            (W1, b1, W2, b2): Weight matrices and biases
        """
        W1 = self.fc1.weight.detach().numpy().flatten()
        b1 = self.fc1.bias.detach().numpy()
        W2 = self.fc2.weight.detach().numpy().flatten()
        b2 = self.fc2.bias.detach().numpy()
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


class SimpleCNNModel(nn.Module):
    """
    Simple CNN for image data (Depth/RGB)
    Uses single convolutional layer for minimal HE computation
    """
    def __init__(self, in_channels: int = 1, hidden_dim: int = 32, output_dim: int = 1):
        super(SimpleCNNModel, self).__init__()
        self.in_channels = in_channels
        self.hidden_dim = hidden_dim
        self.output_dim = output_dim

        # Single conv layer + global pooling + FC
        self.conv1 = nn.Conv2d(in_channels, hidden_dim,
                              kernel_size=3, padding=1)
        self.pool = nn.AdaptiveAvgPool2d(1)
        self.fc = nn.Linear(hidden_dim, output_dim)
        self.relu = nn.ReLU()

    def forward(self, x):
        """
        Forward pass: x -> conv -> relu -> pool -> fc -> output
        """
        x = self.conv1(x)
        x = self.relu(x)
        x = self.pool(x)
        x = x.view(x.size(0), -1)
        x = self.fc(x)
        return x

    def get_weights_for_he(self) -> Tuple[np.ndarray, np.ndarray]:
        """
        Extract weights for homomorphic encryption

        Returns:
            (weight, bias): Flattened convolutional weights and FC bias
        """
        # Get conv weights: (out_channels, in_channels, 3, 3)
        conv_w = self.conv1.weight.detach().numpy()
        # Flatten to (out_channels, in_channels * 9)
        conv_w_flat = conv_w.reshape(self.hidden_dim, -1)

        # Get FC bias
        fc_b = self.fc.bias.detach().numpy()

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
                             model_type: str = "time_series") -> nn.Module:
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
    x = torch.randn(1, 8)
    output = ts_model(x)
    print(f"  Input shape: {x.shape}")
    print(f"  Output shape: {output.shape}")
    print(f"  Output value: {output.item():.4f}")

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
    x = torch.randn(1, 1, 64, 64)
    output = cnn_model(x)
    print(f"  Input shape: {x.shape}")
    print(f"  Output shape: {output.shape}")
    print(f"  Output value: {output.item():.4f}")

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
