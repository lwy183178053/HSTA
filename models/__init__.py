"""Model registry for the compact open-set benchmark."""

from __future__ import annotations

from .adapted_sota import NetMambaAdapted, PktTCNetAdapted
from .hsta_cm import HSTACM
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
            use_conv=bool(cfg.get("use_conv", True)),
            use_mamba=bool(cfg.get("use_mamba", True)),
            use_attention=bool(cfg.get("use_attention", True)),
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
        return BPFGNN(
            input_dim, num_classes, dim=dim, dropout=dropout,
            top_k=_int(cfg, "top_k", 4), num_subflows=_int(cfg, "num_subflows", 5),
        )
    raise ValueError(
        f"Unknown model {name!r}; choose HSTA-CM, 30pktTCNET, NetMamba, SRViT, TrafficAudio or BPF-GNN"
    )


__all__ = ["HSTACM", "PktTCNetAdapted", "NetMambaAdapted", "SRViT", "TrafficAudio", "BPFGNN", "build_model"]
