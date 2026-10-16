"""Model registry for the compact open-set benchmark."""

from __future__ import annotations

from .adapted_sota import NetMambaAdapted, PktTCNetAdapted
from .hsta_cm import HSTACM
from .hsta_cm_gated import HSTACMGated
from .recent_journal_baselines import BPFGNN, SRViT, TrafficAudio


def _name(value: str) -> str:
    return value.lower().replace("-", "_")


def _int(cfg: dict, key: str, default: int) -> int:
    return int(cfg.get(key, default))


def _float(cfg: dict, key: str, default: float) -> float:
    return float(cfg.get(key, default))


def build_model(name: str, input_dim: int, num_classes: int, seq_len: int, cfg: dict | None = None):
    cfg = dict(cfg or {})
    model = _name(name)
    dim = _int(cfg, "dim", 256)
    dropout = _float(cfg, "dropout", 0.1)
    depth = _int(cfg, "depth", 2)
    if model in {"hsta_cm", "hsta-cm"}:
        return HSTACM(
            input_dim, num_classes, dim=dim, depth=depth,
            heads=_int(cfg, "heads", 4), mlp_ratio=_int(cfg, "mlp_ratio", 4),
            dropout=dropout, d_state=_int(cfg, "d_state", 16),
            d_conv=_int(cfg, "d_conv", 4), expand=_int(cfg, "expand", 2),
            max_len=seq_len,
            use_mamba=bool(cfg.get("use_mamba", True)),
            use_gnn=bool(cfg.get("use_gnn", True)),
            use_dft=bool(cfg.get("use_dft", True)),
            use_attention=bool(cfg.get("use_attention", True)),
            graph_k=_int(cfg, "graph_k", 4),
        )
    if model in {"hsta_cm_gated", "hsta-cm-gated"}:
        return HSTACMGated(
            input_dim, num_classes, dim=dim, depth=depth,
            heads=_int(cfg, "heads", 4), mlp_ratio=_int(cfg, "mlp_ratio", 4),
            dropout=dropout, d_state=_int(cfg, "d_state", 16),
            d_conv=_int(cfg, "d_conv", 4), expand=_int(cfg, "expand", 2),
            max_len=seq_len, graph_k=_int(cfg, "graph_k", 4),
            use_gate=bool(cfg.get("use_gate", True)),
            use_aux=bool(cfg.get("use_aux", True)),
            graph_residual_mode=str(cfg.get("graph_residual_mode", "scaled")),
            dft_residual_mode=str(cfg.get("dft_residual_mode", "scaled")),
            aux_loss_weight=_float(cfg, "aux_loss_weight", 0.1),
            branch_residual_init=_float(cfg, "branch_residual_init", 0.1),
            residual_scale_mode=str(cfg.get("residual_scale_mode", "raw")),
            residual_scale_max=_float(cfg, "residual_scale_max", 1.0),
            mamba_outer_residual=bool(cfg.get("mamba_outer_residual", True)),
            graph_use_local=bool(cfg.get("graph_use_local", True)),
            use_dft=bool(cfg.get("use_dft", True)),
            use_time_cnn=bool(cfg.get("use_time_cnn", False)),
            time_cnn_residual_mode=str(cfg.get("time_cnn_residual_mode", "scaled")),
        )
    if model in {"30pkttcnet_adapted", "pkt_tcnet_adapted", "tcnet30pkt_adapted"}:
        return PktTCNetAdapted(
            input_dim, num_classes, channels=_int(cfg, "channels", dim), depth=depth,
            kernel_size=_int(cfg, "kernel_size", 3), dropout=dropout,
            classifier_hidden=_int(cfg, "classifier_hidden", dim),
        )
    if model in {"netmamba_adapted", "net_mamba_adapted"}:
        return NetMambaAdapted(
            input_dim, num_classes, dim=dim, depth=depth, dropout=dropout,
            d_state=_int(cfg, "d_state", 16), d_conv=_int(cfg, "d_conv", 4),
            expand=_int(cfg, "expand", 2), max_len=_int(cfg, "max_len", seq_len),
            pooling=str(cfg.get("pooling", "mean")),
        )
    if model == "srvit":
        kernels = tuple(int(k) for k in cfg.get("patch_kernel_sizes", (3, 5, 7)))
        return SRViT(
            input_dim, num_classes, dim=dim, depth=_int(cfg, "depth", 2),
            heads=_int(cfg, "heads", 4), mlp_ratio=_int(cfg, "mlp_ratio", 4),
            dropout=dropout, max_len=_int(cfg, "max_len", seq_len), patch_kernel_sizes=kernels,
        )
    if model == "trafficaudio":
        return TrafficAudio(
            input_dim, num_classes, dim=dim, dropout=dropout,
            n_fft=_int(cfg, "n_fft", 32), win_length=_int(cfg, "win_length", 32),
            hop_length=_int(cfg, "hop_length", 8), n_mels=_int(cfg, "n_mels", 16),
            n_mfcc=_int(cfg, "n_mfcc", 8),
        )
    if model in {"bpf_gnn", "bpfgnn"}:
        graph_depths = tuple(int(value) for value in cfg.get("graph_depths", (2, 2, 2)))
        return BPFGNN(
            input_dim, num_classes, dim=dim, dropout=dropout,
            top_k=_int(cfg, "top_k", 4), num_subflows=_int(cfg, "num_subflows", 5),
            graph_depths=graph_depths,
        )
    raise ValueError(
        f"Unknown model {name!r}; choose HSTA-CM, HSTA-CM-Gated, 30pktTCNET, NetMamba, SRViT, TrafficAudio or BPF-GNN"
    )


__all__ = ["HSTACM", "HSTACMGated", "PktTCNetAdapted", "NetMambaAdapted", "SRViT", "TrafficAudio", "BPFGNN", "build_model"]
