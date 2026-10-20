"""Isolated Bi-Mamba+ MVIF-Net variant for architecture comparison."""

from __future__ import annotations

import math

import torch
from torch import nn
from torch.nn import functional as F

from .flash_attention import FlashAttentionBlock
from .mvif_net import ConvBlock, _bounded_parameter


class MambaPlusMixer(nn.Module):
    """Reference PyTorch selective-state-space mixer with the Mamba+ gate."""

    def __init__(self, dim: int, d_state: int = 16, d_conv: int = 4, expand: int = 2):
        super().__init__()
        if min(dim, d_state, d_conv, expand) <= 0:
            raise ValueError("dim, d_state, d_conv, and expand must all be positive")
        self.d_state = int(d_state)
        self.d_inner = int(dim * expand)
        self.dt_rank = max(math.ceil(dim / 16), 1)
        self.in_proj = nn.Linear(dim, self.d_inner * 2)
        self.conv1d = nn.Conv1d(self.d_inner, self.d_inner, d_conv, padding=d_conv - 1, groups=self.d_inner)
        self.x_proj = nn.Linear(self.d_inner, self.dt_rank + 2 * d_state, bias=False)
        self.dt_proj = nn.Linear(self.dt_rank, self.d_inner, bias=True)
        self.out_proj = nn.Linear(self.d_inner, dim)
        dt_init_std = self.dt_rank**-0.5
        nn.init.uniform_(self.dt_proj.weight, -dt_init_std, dt_init_std)
        dt = torch.exp(torch.rand(self.d_inner) * (math.log(0.1) - math.log(0.001)) + math.log(0.001))
        with torch.no_grad():
            self.dt_proj.bias.copy_(dt + torch.log(-torch.expm1(-dt)))
        values = torch.arange(1, d_state + 1, dtype=torch.float32).log()
        self.A_log = nn.Parameter(values.unsqueeze(0).expand(self.d_inner, -1).clone())
        self.D = nn.Parameter(torch.ones(self.d_inner))

    def forward(self, hidden_states: torch.Tensor) -> torch.Tensor:
        batch, seq_len, _ = hidden_states.shape
        x, z = self.in_proj(hidden_states).chunk(2, dim=-1)
        conv_x = F.silu(self.conv1d(x.transpose(1, 2))[..., :seq_len].transpose(1, 2))
        params = self.x_proj(conv_x)
        dt_feat, input_state, output_state = torch.split(params, [self.dt_rank, self.d_state, self.d_state], dim=-1)
        delta = F.softplus(self.dt_proj(dt_feat))
        state_matrix = -torch.exp(self.A_log.float())
        state = hidden_states.new_zeros(batch, self.d_inner, self.d_state)
        outputs = []
        for index in range(seq_len):
            delta_i = delta[:, index].unsqueeze(-1)
            x_i = conv_x[:, index]
            state = torch.exp(delta_i * state_matrix.unsqueeze(0)) * state
            state = state + delta_i * x_i.unsqueeze(-1) * input_state[:, index].unsqueeze(1)
            outputs.append((state * output_state[:, index].unsqueeze(1)).sum(-1) + self.D * x_i)
        y = torch.stack(outputs, dim=1)
        y = y * F.silu(z) + conv_x * (1.0 - torch.sigmoid(z))
        return self.out_proj(y)


def _reverse_valid_prefix(x: torch.Tensor, valid_mask: torch.Tensor) -> torch.Tensor:
    lengths = valid_mask.sum(dim=1).clamp_min(1)
    positions = torch.arange(x.shape[1], device=x.device).unsqueeze(0)
    indices = torch.where(positions < lengths[:, None], lengths[:, None] - 1 - positions, positions)
    return x.gather(1, indices.unsqueeze(-1).expand_as(x)) * valid_mask.unsqueeze(-1)


class BiMambaPlusEncoder(nn.Module):
    """One bidirectional Mamba+ encoder layer with internal Add & Norm blocks."""

    def __init__(self, dim: int, d_state: int, d_conv: int, expand: int, dropout: float, mlp_ratio: int):
        super().__init__()
        self.forward_mixer = MambaPlusMixer(dim, d_state=d_state, d_conv=d_conv, expand=expand)
        self.backward_mixer = MambaPlusMixer(dim, d_state=d_state, d_conv=d_conv, expand=expand)
        self.forward_norm = nn.LayerNorm(dim)
        self.backward_norm = nn.LayerNorm(dim)
        self.direction_dropout = nn.Dropout(dropout)
        hidden = dim * mlp_ratio
        self.ffn = nn.Sequential(
            nn.Conv1d(dim, hidden, 1), nn.GELU(), nn.Dropout(dropout), nn.Conv1d(hidden, dim, 1),
        )
        self.ffn_dropout = nn.Dropout(dropout)
        self.ffn_norm = nn.LayerNorm(dim)

    def forward(self, x: torch.Tensor, valid_mask: torch.Tensor) -> torch.Tensor:
        mask = valid_mask.unsqueeze(-1)
        x = x.float() * mask
        forward = self.forward_norm(x + self.direction_dropout(self.forward_mixer(x)))
        reversed_x = _reverse_valid_prefix(x, valid_mask)
        backward_reversed = self.backward_norm(
            reversed_x + self.direction_dropout(self.backward_mixer(reversed_x))
        )
        backward = _reverse_valid_prefix(backward_reversed, valid_mask)
        merged = (forward + backward) * mask
        ffn = self.ffn(merged.transpose(1, 2)).transpose(1, 2)
        return self.ffn_norm(merged + self.ffn_dropout(ffn)) * mask


class DynamicGraphMessageBlock(nn.Module):
    """Per-layer hidden-similarity packet graph, with no residual shortcut."""

    def __init__(self, dim: int, dropout: float, graph_k: int):
        super().__init__()
        self.graph_k = int(graph_k)
        self.norm = nn.LayerNorm(dim)
        self.query = nn.Linear(dim, dim, bias=False)
        self.key = nn.Linear(dim, dim, bias=False)
        self.local_proj = nn.Linear(dim, dim)
        self.similarity_proj = nn.Linear(dim, dim)
        self.activation = nn.GELU()
        self.drop = nn.Dropout(dropout)
        self.last_similarity_adjacency: torch.Tensor | None = None

    @staticmethod
    def _normalize(adjacency: torch.Tensor) -> torch.Tensor:
        degree = adjacency.sum(dim=-1).clamp_min(1e-6)
        inv_sqrt = degree.rsqrt()
        return inv_sqrt.unsqueeze(-1) * adjacency * inv_sqrt.unsqueeze(-2)

    def _adjacencies(self, hidden: torch.Tensor, valid_mask: torch.Tensor):
        _, length, _ = hidden.shape
        positions = torch.arange(length, device=hidden.device)
        separation = (positions[:, None] - positions[None, :]).abs()
        valid_pairs = valid_mask.unsqueeze(-1) & valid_mask.unsqueeze(-2)
        local = (separation <= 1).unsqueeze(0) & valid_pairs
        with torch.autocast(device_type=hidden.device.type, enabled=False):
            hidden32 = hidden.float()
            query = F.normalize(self.query(hidden32), dim=-1)
            key = F.normalize(self.key(hidden32), dim=-1)
            scores = torch.bmm(query, key.transpose(1, 2))
            allowed = (separation > 1).unsqueeze(0) & valid_pairs
            top_scores, top_indices = scores.masked_fill(~allowed, -1e4).topk(min(self.graph_k, length), dim=-1)
            selected_valid = allowed.gather(-1, top_indices)
            weights = torch.softmax(top_scores, dim=-1) * selected_valid.to(scores.dtype)
            weights = weights / weights.sum(dim=-1, keepdim=True).clamp_min(1e-6)
            similarity = torch.zeros_like(scores).scatter(-1, top_indices, weights)
            similarity = torch.maximum(similarity, similarity.transpose(1, 2))
            similarity = self._normalize(similarity)
        self.last_similarity_adjacency = similarity.detach()
        return self._normalize(local.to(hidden.dtype)), similarity.to(hidden.dtype)

    def forward(self, x: torch.Tensor, valid_mask: torch.Tensor) -> torch.Tensor:
        mask = valid_mask.unsqueeze(-1)
        hidden = self.norm(x) * mask
        local, similarity = self._adjacencies(hidden, valid_mask)
        local_message = self.local_proj(torch.bmm(local, hidden))
        similarity_message = self.similarity_proj(torch.bmm(similarity, hidden))
        return self.drop(self.activation(local_message + similarity_message)) * mask


class MVIFBiMambaPlus(nn.Module):
    """MVIF-Net research variant with Bi-Mamba+, dynamic graph, and learnable DFT response."""

    def __init__(
        self, input_dim: int, num_classes: int, dim: int = 256, depth: int = 2,
        heads: int = 4, mlp_ratio: int = 4, dropout: float = 0.15,
        d_state: int = 16, d_conv: int = 4, expand: int = 2, max_len: int = 30,
        graph_k: int = 4, branch_residual_init: float = 0.1, residual_scale_max: float = 0.5,
    ):
        super().__init__()
        if input_dim != 3 or max_len != 30:
            raise ValueError("MVIF-BiMamba+ requires input [B, 30, 3]")
        if depth != 2:
            raise ValueError("MVIF-BiMamba+ uses two graph/DFT blocks and one Bi-Mamba+ encoder layer")
        if graph_k <= 0 or graph_k >= max_len - 1:
            raise ValueError("graph_k must be between 1 and max_len - 2")
        if residual_scale_max <= branch_residual_init or branch_residual_init <= 0:
            raise ValueError("residual_scale_max must be greater than branch_residual_init > 0")
        self.dim = int(dim)
        self.input_max_len = int(max_len)
        self.graph_k = int(graph_k)
        self.residual_scale_max = float(residual_scale_max)
        self.register_buffer("padding_value", torch.zeros(input_dim))

        self.temporal_embed = nn.Linear(input_dim, dim)
        self.temporal = BiMambaPlusEncoder(dim, d_state, d_conv, expand, dropout, mlp_ratio)
        self.graph_embed = nn.Linear(input_dim, dim)
        self.graph_blocks = nn.ModuleList([DynamicGraphMessageBlock(dim, dropout, graph_k) for _ in range(depth)])
        self.graph_norm = nn.LayerNorm(dim)

        self.dft_input_norm = nn.LayerNorm(input_dim * 2)
        self.dft_input_proj = nn.Conv1d(input_dim * 2, dim, 1)
        self.frequency_response = nn.Parameter(torch.zeros(16, input_dim, 2))
        with torch.no_grad():
            self.frequency_response[..., 0].fill_(1.0)
        self.dft_spatial = nn.ModuleList([ConvBlock(dim, kernel, dropout) for kernel in (1, 3)])
        self.dft_norm = nn.LayerNorm(dim)
        self.dft_residual_logit = nn.Parameter(
            torch.tensor(_bounded_parameter(branch_residual_init, residual_scale_max))
        )

        self.packet_position = nn.Parameter(torch.zeros(1, 30, dim))
        self.frequency_position = nn.Parameter(torch.zeros(1, 16, dim))
        self.branch_type = nn.Parameter(torch.zeros(3, dim))
        self.branch_names = ("bi_mamba_plus", "dynamic_packet_graph", "learnable_dft_conv")
        self.branch_keys = list(self.branch_names)
        self.branch_count = 3
        self.token_count = 76
        self.token_fusion = nn.Sequential(nn.Linear(dim, dim), nn.GELU(), nn.Dropout(dropout))
        self.attention = FlashAttentionBlock(dim, heads=heads, mlp_ratio=mlp_ratio, dropout=dropout)
        self.norm = nn.LayerNorm(dim)
        self.head = nn.Linear(dim, num_classes)
        # Bi-Mamba+ already ends with Add & Norm, so its fusion norm is an identity.
        self.branch_norms = nn.ModuleList([nn.Identity(), nn.LayerNorm(dim), nn.LayerNorm(dim)])
        gate_hidden = max(dim // 2, 32)
        self.branch_gate = nn.Sequential(
            nn.Linear(self.branch_count * dim, gate_hidden), nn.GELU(), nn.Linear(gate_hidden, self.branch_count),
        )
        nn.init.zeros_(self.branch_gate[-1].weight)
        nn.init.zeros_(self.branch_gate[-1].bias)
        self.last_branch_gate: torch.Tensor | None = None
        self.layout = (
            "single_bi_mamba_plus_encoder_internal_add_norm_ffn",
            "dynamic_hidden_similarity_packet_graph_x2_no_residual",
            "differentiable_rfft_learnable_complex_response_dft_conv1d_1x3",
            "dft_interlayer_bounded_residual_scale_0.1_to_0.5",
            "branch_norm_gate", "token_fusion", "sdpa_key_padding_mask_global_mean", "norm_head",
        )
        for parameter in (self.packet_position, self.frequency_position, self.branch_type):
            nn.init.normal_(parameter, std=0.02)

    def effective_dft_residual_scale(self) -> torch.Tensor:
        return self.residual_scale_max * torch.sigmoid(self.dft_residual_logit)

    @torch.no_grad()
    def set_input_scaler(self, mean, scale) -> None:
        mean = torch.as_tensor(mean, dtype=torch.float32, device=self.padding_value.device)
        scale = torch.as_tensor(scale, dtype=torch.float32, device=self.padding_value.device)
        if (
            mean.shape != (3,) or scale.shape != (3,)
            or not torch.isfinite(mean).all() or not torch.isfinite(scale).all()
            or (scale <= 0).any()
        ):
            raise ValueError("expected three finite means and positive scales")
        self.padding_value.copy_(-mean / scale)

    def _packet_mask(self, x: torch.Tensor) -> torch.Tensor:
        return ~torch.isclose(x.float(), self.padding_value, atol=1e-6, rtol=1e-5).all(dim=-1)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        if x.ndim != 3 or x.shape[1:] != (30, 3):
            raise ValueError(f"expected [batch, 30, 3], got {tuple(x.shape)}")
        batch = x.shape[0]
        valid = self._packet_mask(x)
        packet_mask = valid.unsqueeze(-1)
        x = x.masked_fill(~packet_mask, 0.0)

        temporal = self.temporal_embed(x) * packet_mask
        with torch.autocast(device_type=x.device.type, enabled=False):
            temporal = self.temporal(temporal.float(), valid)
        temporal_tokens = (temporal + self.packet_position + self.branch_type[0]) * packet_mask

        graph = self.graph_embed(x) * packet_mask
        for block in self.graph_blocks:
            graph = block(graph, valid) * packet_mask
        graph_tokens = (self.graph_norm(graph) + self.packet_position + self.branch_type[1]) * packet_mask

        spectrum = torch.fft.rfft(x.float(), dim=1, norm="ortho")
        response = torch.complex(self.frequency_response[..., 0], self.frequency_response[..., 1])
        spectrum = spectrum * response.unsqueeze(0)
        features = self.dft_input_norm(torch.cat((spectrum.real, spectrum.imag), dim=-1))
        frequency = self.dft_input_proj(features.transpose(1, 2))
        frequency_input = frequency
        for index, block in enumerate(self.dft_spatial):
            frequency = block(frequency)
            if index == 0:
                frequency = frequency + self.effective_dft_residual_scale() * frequency_input
        frequency_tokens = self.dft_norm(frequency.transpose(1, 2)) + self.frequency_position + self.branch_type[2]

        branch_tokens = [temporal_tokens, graph_tokens, frequency_tokens]
        branch_masks = [
            valid, valid,
            torch.ones(batch, frequency_tokens.shape[1], dtype=torch.bool, device=x.device),
        ]
        normalized_tokens = []
        summaries = []
        for index, (tokens_i, mask_i) in enumerate(zip(branch_tokens, branch_masks)):
            tokens_i = self.branch_norms[index](tokens_i)
            normalized_tokens.append(tokens_i)
            mask_weight = mask_i.unsqueeze(-1)
            denominator = mask_i.sum(dim=1, keepdim=True).clamp_min(1)
            summaries.append((tokens_i * mask_weight).sum(dim=1) / denominator)
        branch_tokens = normalized_tokens
        branch_summaries = torch.stack(summaries, dim=1)
        gate = self.branch_gate(branch_summaries.reshape(batch, self.branch_count * self.dim)).softmax(dim=-1)
        self.last_branch_gate = gate.detach()
        scale = float(self.branch_count) * gate
        branch_tokens = [tokens_i * scale[:, i, None, None] for i, tokens_i in enumerate(branch_tokens)]

        valid_tokens = torch.cat(branch_masks, dim=1)
        token_mask = valid_tokens.unsqueeze(-1)
        tokens = torch.cat(branch_tokens, dim=1) * token_mask
        projected = self.token_fusion(tokens) * token_mask
        fused = self.norm(self.attention(projected, key_padding_mask=~valid_tokens))
        valid_count = valid_tokens.sum(dim=1, keepdim=True).clamp_min(1)
        flow_embedding = (fused * token_mask).sum(dim=1) / valid_count
        return self.head(flow_embedding)


__all__ = ["MambaPlusMixer", "BiMambaPlusEncoder", "DynamicGraphMessageBlock", "MVIFBiMambaPlus"]
