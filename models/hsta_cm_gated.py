"""Package-level HSTA-CM with switchable branch gating and residual control.

The token layout is unchanged: 30 Mamba packet tokens, 30 packet-graph tokens
and 16 DFT frequency tokens. Every ablation arm constructs the same modules in
the same order, so shared parameters receive identical random initialisation
and all arms keep the same parameter count. The switches only change forward
behaviour.
"""

from __future__ import annotations

import torch
from torch import nn
from torch.nn import functional as F

from .hsta_cm import HSTACM

RESIDUAL_MODES = ("full", "scaled", "none")
SCALE_MODES = ("raw", "bounded")


def _scale_parameter(initial_scale: float, scale_mode: str, scale_max: float) -> float:
    if scale_mode not in SCALE_MODES:
        raise ValueError(f"scale_mode must be one of {SCALE_MODES}, got {scale_mode!r}")
    if initial_scale < 0 or scale_max <= 0:
        raise ValueError("initial_scale must be non-negative and scale_max must be positive")
    if scale_mode == "raw":
        return float(initial_scale)
    if not 0 < initial_scale < scale_max:
        raise ValueError("bounded residual scale requires 0 < initial_scale < scale_max")
    ratio = initial_scale / (scale_max - initial_scale)
    return float(torch.log(torch.tensor(ratio)).item())


class ModeGraphBlock(nn.Module):
    """Packet-graph message passing with a configurable residual path."""

    def __init__(
        self,
        dim: int,
        dropout: float,
        mode: str,
        initial_scale: float = 0.1,
        scale_mode: str = "raw",
        scale_max: float = 1.0,
    ):
        super().__init__()
        if mode not in RESIDUAL_MODES:
            raise ValueError(f"graph residual mode must be one of {RESIDUAL_MODES}, got {mode!r}")
        self.mode = str(mode)
        self.norm = nn.LayerNorm(dim)
        self.local_proj = nn.Linear(dim, dim)
        self.nonlocal_proj = nn.Linear(dim, dim)
        self.activation = nn.GELU()
        self.drop = nn.Dropout(dropout)
        self.scale_mode = str(scale_mode)
        self.scale_max = float(scale_max)
        self.residual_scale = nn.Parameter(torch.tensor(_scale_parameter(initial_scale, self.scale_mode, self.scale_max)))

    def effective_scale(self) -> torch.Tensor:
        if self.scale_mode == "bounded":
            return self.scale_max * torch.sigmoid(self.residual_scale)
        return self.residual_scale

    def forward(self, x: torch.Tensor, local_adj: torch.Tensor, nonlocal_adj: torch.Tensor) -> torch.Tensor:
        h = self.norm(x)
        mixed = self.local_proj(torch.bmm(local_adj, h)) + self.nonlocal_proj(torch.bmm(nonlocal_adj, h))
        update = self.drop(self.activation(mixed))
        if self.mode == "none":
            return update
        if self.mode == "scaled":
            return x + self.effective_scale() * update
        return x + update


class ModeConvBlock(nn.Module):
    """Frequency convolution with a configurable residual path."""

    def __init__(
        self,
        dim: int,
        kernel: int,
        dropout: float,
        mode: str,
        initial_scale: float = 0.1,
        scale_mode: str = "raw",
        scale_max: float = 1.0,
    ):
        super().__init__()
        if mode not in RESIDUAL_MODES:
            raise ValueError(f"dft residual mode must be one of {RESIDUAL_MODES}, got {mode!r}")
        self.mode = str(mode)
        self.conv = nn.Conv1d(dim, dim, kernel_size=kernel, padding=kernel // 2)
        self.batch_norm = nn.BatchNorm1d(dim)
        self.activation = nn.GELU()
        self.drop = nn.Dropout(dropout)
        self.scale_mode = str(scale_mode)
        self.scale_max = float(scale_max)
        self.residual_scale = nn.Parameter(torch.tensor(_scale_parameter(initial_scale, self.scale_mode, self.scale_max)))

    def effective_scale(self) -> torch.Tensor:
        if self.scale_mode == "bounded":
            return self.scale_max * torch.sigmoid(self.residual_scale)
        return self.residual_scale

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        update = self.drop(self.activation(self.batch_norm(self.conv(x))))
        if self.mode == "none":
            return update
        if self.mode == "scaled":
            return x + self.effective_scale() * update
        return x + update


class HSTACMGated(HSTACM):
    """Package-level HSTA-CM with optional DFT/time-CNN and branch controls."""

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
        use_gate: bool = True,
        use_aux: bool = True,
        graph_residual_mode: str = "scaled",
        dft_residual_mode: str = "scaled",
        branch_residual_init: float = 0.1,
        aux_loss_weight: float = 0.1,
        residual_scale_mode: str = "raw",
        residual_scale_max: float = 1.0,
        mamba_outer_residual: bool = True,
        graph_use_local: bool = True,
        use_dft: bool = True,
        use_time_cnn: bool = False,
        time_cnn_residual_mode: str = "scaled",
    ):
        super().__init__(
            input_dim=input_dim,
            num_classes=num_classes,
            dim=dim,
            depth=depth,
            heads=heads,
            mlp_ratio=mlp_ratio,
            dropout=dropout,
            d_state=d_state,
            d_conv=d_conv,
            expand=expand,
            max_len=max_len,
            use_mamba=True,
            use_gnn=True,
            use_dft=use_dft,
            use_attention=True,
            graph_k=graph_k,
        )
        if graph_residual_mode not in RESIDUAL_MODES:
            raise ValueError(f"graph_residual_mode must be one of {RESIDUAL_MODES}")
        if dft_residual_mode not in RESIDUAL_MODES:
            raise ValueError(f"dft_residual_mode must be one of {RESIDUAL_MODES}")
        if aux_loss_weight < 0 or branch_residual_init < 0:
            raise ValueError("aux_loss_weight and branch_residual_init must be non-negative")
        if residual_scale_mode not in SCALE_MODES:
            raise ValueError(f"residual_scale_mode must be one of {SCALE_MODES}")
        if residual_scale_max <= 0:
            raise ValueError("residual_scale_max must be positive")
        if time_cnn_residual_mode not in RESIDUAL_MODES:
            raise ValueError(f"time_cnn_residual_mode must be one of {RESIDUAL_MODES}")

        self.use_gate = bool(use_gate)
        self.use_aux = bool(use_aux)
        self.graph_residual_mode = str(graph_residual_mode)
        self.dft_residual_mode = str(dft_residual_mode)
        self.aux_loss_weight = float(aux_loss_weight)
        self.residual_scale_mode = str(residual_scale_mode)
        self.residual_scale_max = float(residual_scale_max)
        self.mamba_outer_residual = bool(mamba_outer_residual)
        self.graph_use_local = bool(graph_use_local)
        self.use_time_cnn = bool(use_time_cnn)
        self.time_cnn_residual_mode = str(time_cnn_residual_mode)

        self.graph_blocks = nn.ModuleList([
            ModeGraphBlock(
                dim, dropout, self.graph_residual_mode, branch_residual_init,
                self.residual_scale_mode, self.residual_scale_max,
            )
            for _ in range(depth)
        ])
        self.dft_spatial = nn.ModuleList([
            ModeConvBlock(
                dim, kernel, dropout, self.dft_residual_mode, branch_residual_init,
                self.residual_scale_mode, self.residual_scale_max,
            )
            for kernel in (1, 3)
        ]) if use_dft else nn.ModuleList()

        self.time_cnn_embed = nn.Linear(input_dim, dim) if self.use_time_cnn else None
        self.time_cnn_norm = nn.LayerNorm(dim) if self.use_time_cnn else None
        self.time_cnn_blocks = nn.ModuleList([
            ModeConvBlock(
                dim, kernel, dropout, self.time_cnn_residual_mode, branch_residual_init,
                self.residual_scale_mode, self.residual_scale_max,
            )
            for kernel in (1, 3)
        ]) if self.use_time_cnn else nn.ModuleList()

        self.branch_keys = ["mamba", "packet_graph"]
        if use_dft:
            self.branch_keys.append("dft_conv")
        if self.use_time_cnn:
            self.branch_keys.append("time_cnn")
        self.branch_count = len(self.branch_keys)
        self.token_count = (30 * sum(key in {"mamba", "packet_graph", "time_cnn"} for key in self.branch_keys)) + (16 if "dft_conv" in self.branch_keys else 0)
        self.branch_norms = nn.ModuleList([nn.LayerNorm(dim) for _ in range(self.branch_count)])
        gate_hidden = max(dim // 2, 32)
        self.branch_gate = nn.Sequential(
            nn.Linear(self.branch_count * dim, gate_hidden),
            nn.GELU(),
            nn.Linear(gate_hidden, self.branch_count),
        )
        nn.init.zeros_(self.branch_gate[-1].weight)
        nn.init.zeros_(self.branch_gate[-1].bias)
        self.aux_heads = nn.ModuleList([nn.Linear(dim, num_classes) for _ in range(self.branch_count)])
        self.time_cnn_branch_type = nn.Parameter(torch.zeros(dim)) if self.use_time_cnn else None
        if self.time_cnn_branch_type is not None:
            nn.init.normal_(self.time_cnn_branch_type, std=0.02)

        self._auxiliary_logits: tuple[torch.Tensor, ...] | None = None
        self.last_branch_gate: torch.Tensor | None = None
        layout = [
            "mamba_x2_packet_tokens" if self.mamba_outer_residual else "mamba_x2_no_outer_residual",
            f"packet_graph_x2_{self.graph_residual_mode}_{'local_nonlocal' if self.graph_use_local else 'nonlocal_only'}",
        ]
        if use_dft:
            layout.append(f"dft_conv1d_1x3_{self.dft_residual_mode}_residual")
        if self.use_time_cnn:
            layout.append(f"time_cnn1d_1x3_{self.time_cnn_residual_mode}_residual")
        layout.extend([
            "bounded_scale" if self.residual_scale_mode == "bounded" else "raw_scale",
            "branch_norm_gate" if self.use_gate else "no_gate",
            "aux_heads" if self.use_aux else "no_aux",
            "token_fusion",
            "flash_attention",
            "norm_head",
        ])
        self.layout = tuple(layout)

    def auxiliary_loss(self, targets: torch.Tensor) -> torch.Tensor | None:
        if not self.use_aux or not self.training or self._auxiliary_logits is None or self.aux_loss_weight <= 0:
            return None
        return self.aux_loss_weight * torch.stack([
            F.cross_entropy(logits, targets) for logits in self._auxiliary_logits
        ]).mean()

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
        if self.mamba_outer_residual:
            temporal = temporal + temporal_input
        temporal = self.temporal_norm(temporal)
        temporal_tokens = (temporal + self.packet_position + self.branch_type[0]) * packet_weight

        local_adj, nonlocal_adj = self._graph_adjacency(x, valid)
        if not self.graph_use_local:
            local_adj = torch.zeros_like(local_adj)
        graph = self.graph_embed(x) * packet_weight
        for block in self.graph_blocks:
            graph = block(graph, local_adj.to(graph.dtype), nonlocal_adj.to(graph.dtype)) * packet_weight
        graph = self.graph_norm(graph)
        graph_tokens = (graph + self.packet_position + self.branch_type[1]) * packet_weight

        branch_tokens = [temporal_tokens, graph_tokens]
        branch_masks = [valid, valid]
        if self.use_dft:
            spectrum = torch.fft.rfft(x.float(), dim=1, norm="ortho")
            features = self.dft_input_norm(torch.cat((spectrum.real, spectrum.imag), dim=-1))
            frequency = self.dft_residual(features.transpose(1, 2))
            for block in self.dft_spatial:
                frequency = block(frequency)
            frequency = self.dft_norm(frequency.transpose(1, 2))
            frequency_tokens = frequency + self.frequency_position + self.branch_type[2]
            branch_tokens.append(frequency_tokens)
            branch_masks.append(torch.ones(batch, frequency_tokens.shape[1], dtype=torch.bool, device=x.device))
        if self.use_time_cnn:
            time_cnn = self.time_cnn_embed(x) * packet_weight
            time_cnn = time_cnn.transpose(1, 2)
            for block in self.time_cnn_blocks:
                time_cnn = block(time_cnn)
            time_cnn = self.time_cnn_norm(time_cnn.transpose(1, 2))
            time_cnn_tokens = (time_cnn + self.packet_position + self.time_cnn_branch_type) * packet_weight
            branch_tokens.append(time_cnn_tokens)
            branch_masks.append(valid)

        valid_count = valid.sum(dim=1, keepdim=True).clamp_min(1)
        branch_summaries = None
        if self.use_gate:
            normalized_tokens = []
            summaries = []
            for index, (tokens_i, mask_i) in enumerate(zip(branch_tokens, branch_masks)):
                tokens_i = self.branch_norms[index](tokens_i)
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
        else:
            self.last_branch_gate = None

        if self.use_aux and branch_summaries is not None:
            self._auxiliary_logits = tuple(
                self.aux_heads[index](branch_summaries[:, index]) for index in range(self.branch_count)
            )
        else:
            self._auxiliary_logits = None

        token_mask = torch.cat(branch_masks, dim=1).unsqueeze(-1)
        tokens = torch.cat(branch_tokens, dim=1) * token_mask
        projected = self.token_fusion(tokens) * token_mask
        fused = self.norm(self.attention(projected))
        fused_chunks = torch.split(fused, [chunk.shape[1] for chunk in branch_tokens], dim=1)
        pooled_chunks = []
        for chunk, mask_i in zip(fused_chunks, branch_masks):
            denominator = valid_count if mask_i.shape[1] == valid.shape[1] else mask_i.sum(dim=1, keepdim=True).clamp_min(1)
            pooled_chunks.append((chunk * mask_i.unsqueeze(-1)).sum(dim=1) / denominator)
        pooled = torch.stack(pooled_chunks, dim=1)
        return self.head(pooled.mean(dim=1))
