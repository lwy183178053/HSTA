import torch
import torch.nn as nn

from .mamba_model import MambaClassifier


PKT_TCNET_ADAPTED_NOTE = (
    "30pktTCNET-adapted: adapted to our packet-level side-channel input setting "
    "using packet size, direction, and packet inter-arrival time features."
)
NETMAMBA_ADAPTED_NOTE = (
    "NetMamba-adapted: adapted to our packet-level side-channel input setting "
    "using packet size, direction, and packet inter-arrival time features."
)


class TemporalConvBlock(nn.Module):
    def __init__(
        self,
        channels: int,
        kernel_size: int = 3,
        dilation: int = 1,
        dropout: float = 0.15,
    ):
        super().__init__()
        if kernel_size % 2 != 1:
            raise ValueError("TemporalConvBlock requires an odd kernel_size to preserve the residual shape.")
        padding = dilation * (kernel_size - 1) // 2
        self.net = nn.Sequential(
            nn.Conv1d(channels, channels, kernel_size=kernel_size, padding=padding, dilation=dilation),
            nn.BatchNorm1d(channels),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Conv1d(channels, channels, kernel_size=kernel_size, padding=padding, dilation=dilation),
            nn.BatchNorm1d(channels),
            nn.GELU(),
            nn.Dropout(dropout),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return x + self.net(x)


class PktTCNetAdapted(nn.Module):
    """30pktTCNET-style model adapted to our packet-level side-channel input setting.

    This is not a full reproduction of the original CESNET 30pktTCNET input
    pipeline. It uses only the shared [B, 30, 3] packet size, direction, and
    packet inter-arrival time features selected by this project's data loader.
    """

    def __init__(
        self,
        input_dim: int,
        num_classes: int,
        channels: int = 128,
        depth: int = 5,
        kernel_size: int = 3,
        dropout: float = 0.15,
        classifier_hidden: int = 128,
    ):
        super().__init__()
        if input_dim <= 0:
            raise ValueError("input_dim must be positive.")
        if num_classes <= 0:
            raise ValueError("num_classes must be positive.")
        if channels <= 0:
            raise ValueError("channels must be positive.")
        if depth <= 0:
            raise ValueError("depth must be positive.")
        if classifier_hidden <= 0:
            raise ValueError("classifier_hidden must be positive.")
        self.adapted_note = PKT_TCNET_ADAPTED_NOTE
        self.input_proj = nn.Sequential(
            nn.Conv1d(input_dim, channels, kernel_size=1),
            nn.BatchNorm1d(channels),
            nn.GELU(),
        )
        self.blocks = nn.ModuleList(
            [
                TemporalConvBlock(
                    channels=channels,
                    kernel_size=kernel_size,
                    dilation=2 ** layer_idx,
                    dropout=dropout,
                )
                for layer_idx in range(depth)
            ]
        )
        self.pool = nn.AdaptiveAvgPool1d(1)
        self.head = nn.Sequential(
            nn.Linear(channels, classifier_hidden),
            nn.LayerNorm(classifier_hidden),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(classifier_hidden, num_classes),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = x.transpose(1, 2)
        x = self.input_proj(x)
        for block in self.blocks:
            x = block(x)
        x = self.pool(x).squeeze(-1)
        return self.head(x)


class NetMambaAdapted(MambaClassifier):
    """NetMamba-style backbone adapted to our packet-level side-channel input setting.

    This model keeps the Mamba-based traffic backbone idea, but it does not use
    the original NetMamba raw-byte/token/pretraining data pipeline. It uses the
    shared [B, 30, 3] packet size, direction, and packet inter-arrival time
    features selected by this project's data loader.
    """

    def __init__(
        self,
        input_dim: int,
        num_classes: int,
        dim: int = 128,
        depth: int = 5,
        dropout: float = 0.15,
        d_state: int = 16,
        d_conv: int = 4,
        expand: int = 2,
        max_len: int = 256,
        pooling: str = "mean",
    ):
        super().__init__(
            input_dim=input_dim,
            num_classes=num_classes,
            dim=dim,
            depth=depth,
            dropout=dropout,
            d_state=d_state,
            d_conv=d_conv,
            expand=expand,
            max_len=max_len,
            pooling=pooling,
        )
        self.adapted_note = NETMAMBA_ADAPTED_NOTE
