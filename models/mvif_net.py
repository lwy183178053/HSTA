"""MVIF-Net: Multi-View Interactive Fusion Network for encrypted traffic."""

from __future__ import annotations

import torch
from torch import nn

from .flash_attention import FlashAttentionBlock
from .mamba_model import MambaBlock


def _bounded_parameter(initial_scale: float, scale_max: float) -> float:
    if not 0.0 < initial_scale < scale_max:
        raise ValueError("initial_scale must satisfy 0 < initial_scale < scale_max")
    ratio = initial_scale / (scale_max - initial_scale)
    return float(torch.log(torch.tensor(ratio)).item())


class GraphMessageBlock(nn.Module):
    """Local and feature-similarity message passing without a shortcut."""

    def __init__(self, dim: int, dropout: float):
        super().__init__()
        self.norm = nn.LayerNorm(dim)
        self.local_proj = nn.Linear(dim, dim)
        self.nonlocal_proj = nn.Linear(dim, dim)
        self.activation = nn.GELU()
        self.drop = nn.Dropout(dropout)

    def forward(self, x: torch.Tensor, local_adj: torch.Tensor, nonlocal_adj: torch.Tensor) -> torch.Tensor:
        h = self.norm(x)
        mixed = self.local_proj(torch.bmm(local_adj, h))
        mixed = mixed + self.nonlocal_proj(torch.bmm(nonlocal_adj, h))
        return self.drop(self.activation(mixed))


class ConvBlock(nn.Module):
    """DFT convolution block without a shortcut."""

    def __init__(self, dim: int, kernel: int, dropout: float):
        super().__init__()
        self.conv = nn.Conv1d(dim, dim, kernel_size=kernel, padding=kernel // 2)
        self.batch_norm = nn.BatchNorm1d(dim)
        self.activation = nn.GELU()
        self.drop = nn.Dropout(dropout)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.drop(self.activation(self.batch_norm(self.conv(x))))


class MVIFNet(nn.Module):
    """Fixed 76-token MVIF-Net configuration used for the formal comparison."""

    def __init__(
        self,
        input_dim: int,
        num_classes: int,
        dim: int = 256,
        depth: int = 2,
        heads: int = 4,
        mlp_ratio: int = 4,
        dropout: float = 0.15,
        d_state: int = 16,
        d_conv: int = 4,
        expand: int = 2,
        max_len: int = 30,
        graph_k: int = 4,
        branch_residual_init: float = 0.1,
        residual_scale_max: float = 0.5,
    ):
        super().__init__()
        if input_dim != 3 or max_len != 30 or depth != 2:
            raise ValueError("MVIF-Net requires input [B, 30, 3] and two blocks per branch")
        if graph_k <= 0 or graph_k >= max_len - 1:
            raise ValueError("graph_k must be between 1 and max_len - 2")
        if residual_scale_max <= branch_residual_init or branch_residual_init <= 0:
            raise ValueError("residual_scale_max must be greater than branch_residual_init > 0")

        self.dim = int(dim)
        self.input_max_len = int(max_len)
        self.graph_k = int(graph_k)
        self.register_buffer("padding_value", torch.zeros(input_dim))

        self.temporal_embed = nn.Linear(input_dim, dim)
        self.temporal = nn.ModuleList([
            MambaBlock(
                dim,
                d_state=d_state,
                d_conv=d_conv,
                expand=expand,
                dropout=dropout,
                residual=False,
            )
            for _ in range(depth)
        ])
        self.temporal_norm = nn.LayerNorm(dim)

        self.graph_embed = nn.Linear(input_dim, dim)
        self.graph_blocks = nn.ModuleList([
            GraphMessageBlock(dim, dropout)
            for _ in range(depth)
        ])
        self.graph_norm = nn.LayerNorm(dim)
        self.graph_residual_logit = nn.Parameter(
            torch.tensor(_bounded_parameter(branch_residual_init, residual_scale_max))
        )

        self.dft_input_norm = nn.LayerNorm(input_dim * 2)
        self.dft_input_proj = nn.Conv1d(input_dim * 2, dim, 1)
        self.dft_spatial = nn.ModuleList([
            ConvBlock(dim, kernel, dropout)
            for kernel in (1, 3)
        ])
        self.dft_norm = nn.LayerNorm(dim)
        self.dft_residual_logit = nn.Parameter(
            torch.tensor(_bounded_parameter(branch_residual_init, residual_scale_max))
        )
        self.residual_scale_max = float(residual_scale_max)

        self.packet_position = nn.Parameter(torch.zeros(1, 30, dim))
        self.frequency_position = nn.Parameter(torch.zeros(1, 16, dim))
        self.branch_type = nn.Parameter(torch.zeros(3, dim))
        self.branch_names = ("mamba", "packet_graph", "dft_conv")
        self.branch_keys = list(self.branch_names)
        self.token_count = 76

        self.token_fusion = nn.Sequential(nn.Linear(dim, dim), nn.GELU(), nn.Dropout(dropout))
        self.attention = FlashAttentionBlock(dim, heads=heads, mlp_ratio=mlp_ratio, dropout=dropout)
        self.norm = nn.LayerNorm(dim)
        self.head = nn.Linear(dim, num_classes)

        self.branch_count = 3
        self.branch_norms = nn.ModuleList([nn.LayerNorm(dim) for _ in range(self.branch_count)])
        gate_hidden = max(dim // 2, 32)
        self.branch_gate = nn.Sequential(
            nn.Linear(self.branch_count * dim, gate_hidden),
            nn.GELU(),
            nn.Linear(gate_hidden, self.branch_count),
        )
        nn.init.zeros_(self.branch_gate[-1].weight)
        nn.init.zeros_(self.branch_gate[-1].bias)

        # Kept for state-dict compatibility with the completed bounded-scale run.
        # Auxiliary logits are never computed and never contribute to the loss.
        self.aux_heads = nn.ModuleList([nn.Linear(dim, num_classes) for _ in range(self.branch_count)])
        self.last_branch_gate: torch.Tensor | None = None
        self.layout = (
            "mamba_x2_no_residual_packet_tokens",
            "packet_graph_x2_single_interlayer_bounded_residual_local_nonlocal",
            "dft_conv1d_1x3_single_interlayer_bounded_residual",
            "interlayer_residual_scale_0.1_to_0.5",
            "branch_norm_gate",
            "no_aux",
            "token_fusion",
            "flash_attention",
            "norm_head",
        )

        for parameter in (self.packet_position, self.frequency_position, self.branch_type):
            nn.init.normal_(parameter, std=0.02)

    def effective_graph_residual_scale(self) -> torch.Tensor:
        return self.residual_scale_max * torch.sigmoid(self.graph_residual_logit)

    def effective_dft_residual_scale(self) -> torch.Tensor:
        return self.residual_scale_max * torch.sigmoid(self.dft_residual_logit)

    @staticmethod
    def _normalize_adjacency(adjacency: torch.Tensor) -> torch.Tensor:
        degree = adjacency.sum(dim=-1).clamp_min(1e-6)
        inv_sqrt = degree.rsqrt()
        return inv_sqrt.unsqueeze(-1) * adjacency * inv_sqrt.unsqueeze(-2)

    @torch.no_grad()
    def set_input_scaler(self, mean, scale) -> None:
        """Set the standardized raw-zero packet used for padding detection."""
        mean = torch.as_tensor(mean, dtype=torch.float32, device=self.padding_value.device)
        scale = torch.as_tensor(scale, dtype=torch.float32, device=self.padding_value.device)
        if (
            mean.shape != (3,)
            or scale.shape != (3,)
            or not torch.isfinite(mean).all()
            or not torch.isfinite(scale).all()
            or (scale <= 0).any()
        ):
            raise ValueError("expected three finite means and positive scales")
        self.padding_value.copy_(-mean / scale)

    def _packet_mask(self, x: torch.Tensor) -> torch.Tensor:
        return ~torch.isclose(x.float(), self.padding_value, atol=1e-6, rtol=1e-5).all(dim=-1)

    @torch.no_grad()
    def _graph_adjacency(self, x: torch.Tensor, valid_mask: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        _, length, _ = x.shape
        with torch.autocast(device_type=x.device.type, enabled=False):
            idx = torch.arange(length, device=x.device)
            separation = (idx[:, None] - idx[None, :]).abs()
            valid_pairs = valid_mask.unsqueeze(-1) & valid_mask.unsqueeze(-2)
            local = ((separation <= 1).unsqueeze(0) & valid_pairs).float()
            distances = (x.float().unsqueeze(2) - x.float().unsqueeze(1)).square().sum(-1)
            allowed = (separation > 1).unsqueeze(0) & valid_pairs
            distances = distances.masked_fill(~allowed, float("inf"))
            nearest = distances.argsort(dim=-1, stable=True)[..., :self.graph_k]
            weights = 1.0 / (1.0 + distances.gather(-1, nearest))
            nonlocal_adj = torch.zeros_like(distances).scatter_(-1, nearest, weights)
            nonlocal_adj = torch.maximum(nonlocal_adj, nonlocal_adj.transpose(1, 2))
            return self._normalize_adjacency(local), self._normalize_adjacency(nonlocal_adj)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        if x.ndim != 3 or x.shape[1:] != (30, 3):
            raise ValueError(f"expected [batch, 30, 3], got {tuple(x.shape)}")

        batch = x.shape[0]
        valid = self._packet_mask(x)
        packet_weight = valid.unsqueeze(-1)
        x = x.masked_fill(~packet_weight, 0.0)

        temporal_input = self.temporal_embed(x) * packet_weight
        temporal = temporal_input
        for block in self.temporal:
            temporal = block(temporal) * packet_weight
        temporal = self.temporal_norm(temporal)
        temporal_tokens = (temporal + self.packet_position + self.branch_type[0]) * packet_weight

        local_adj, nonlocal_adj = self._graph_adjacency(x, valid)
        graph = self.graph_embed(x) * packet_weight
        graph_input = graph
        for index, block in enumerate(self.graph_blocks):
            graph = block(graph, local_adj.to(graph.dtype), nonlocal_adj.to(graph.dtype)) * packet_weight
            if index == 0:
                graph = (graph + self.effective_graph_residual_scale() * graph_input) * packet_weight
        graph = self.graph_norm(graph)
        graph_tokens = (graph + self.packet_position + self.branch_type[1]) * packet_weight

        spectrum = torch.fft.rfft(x.float(), dim=1, norm="ortho")
        features = self.dft_input_norm(torch.cat((spectrum.real, spectrum.imag), dim=-1))
        frequency = self.dft_input_proj(features.transpose(1, 2))
        frequency_input = frequency
        for index, block in enumerate(self.dft_spatial):
            frequency = block(frequency)
            if index == 0:
                frequency = frequency + self.effective_dft_residual_scale() * frequency_input
        frequency = self.dft_norm(frequency.transpose(1, 2))
        frequency_tokens = frequency + self.frequency_position + self.branch_type[2]

        branch_tokens = [temporal_tokens, graph_tokens, frequency_tokens]
        branch_masks = [
            valid,
            valid,
            torch.ones(batch, frequency_tokens.shape[1], dtype=torch.bool, device=x.device),
        ]

        valid_count = valid.sum(dim=1, keepdim=True).clamp_min(1)
        normalized_tokens = []
        summaries = []
        for tokens_i, mask_i in zip(branch_tokens, branch_masks):
            tokens_i = self.branch_norms[len(normalized_tokens)](tokens_i)
            normalized_tokens.append(tokens_i)
            mask_weight = mask_i.unsqueeze(-1)
            denominator = valid_count if mask_i.shape[1] == valid.shape[1] else mask_i.sum(dim=1, keepdim=True).clamp_min(1)
            summaries.append((tokens_i * mask_weight).sum(dim=1) / denominator)
        branch_tokens = normalized_tokens
        branch_summaries = torch.stack(summaries, dim=1)
        gate = self.branch_gate(branch_summaries.reshape(batch, self.branch_count * self.dim)).softmax(dim=-1)
        self.last_branch_gate = gate.detach()
        scale = float(self.branch_count) * gate
        branch_tokens = [tokens_i * scale[:, index, None, None] for index, tokens_i in enumerate(branch_tokens)]

        valid_token_mask = torch.cat(branch_masks, dim=1)
        key_padding_mask = ~valid_token_mask
        token_mask = valid_token_mask.unsqueeze(-1)
        tokens = torch.cat(branch_tokens, dim=1) * token_mask
        projected = self.token_fusion(tokens) * token_mask
        fused = self.norm(
            self.attention(projected, key_padding_mask=key_padding_mask)
        )
        valid_count = valid_token_mask.sum(dim=1, keepdim=True).clamp_min(1)
        flow_embedding = (fused * token_mask).sum(dim=1) / valid_count
        return self.head(flow_embedding)


__all__ = ["MVIFNet", "GraphMessageBlock", "ConvBlock"]
