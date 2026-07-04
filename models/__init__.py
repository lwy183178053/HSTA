from .cnn import CNN1DClassifier
from .adapted_sota import NetMambaAdapted, PktTCNetAdapted
from .hybrid_mm_mlp_a_mlp import HybridMMMLPAMLP
from .lstm import RNNClassifier
from .mamba_model import MambaClassifier
from .mlp import MLPClassifier
from .transformer import TrafficTransformer


TCNET_ALIASES = {"30pkttcnet_adapted", "pkt_tcnet_adapted", "tcnet30pkt_adapted"}
NETMAMBA_ALIASES = {"netmamba_adapted", "net_mamba_adapted"}
HYBRID_ALIASES = {"hybrid", "hybrid_lora"}


def _normalize_model_name(name: str) -> str:
    return name.lower().replace("-", "_")


def _cfg_int(cfg: dict, key: str, default: int) -> int:
    return int(cfg.get(key, default))


def _cfg_float(cfg: dict, key: str, default: float) -> float:
    return float(cfg.get(key, default))


def _max_len(cfg: dict, seq_len: int) -> int:
    return _cfg_int(cfg, "max_len", max(seq_len, 256))


def build_model(name: str, input_dim: int, num_classes: int, seq_len: int, cfg: dict):
    cfg = dict(cfg or {})
    name = _normalize_model_name(name)

    common_depth = _cfg_int(cfg, "depth", 5)
    if name == "mlp":
        return MLPClassifier(
            input_dim,
            num_classes,
            seq_len=seq_len,
            hidden=_cfg_int(cfg, "hidden", 128),
            depth=common_depth,
            dropout=_cfg_float(cfg, "dropout", 0.2),
        )
    if name == "cnn":
        return CNN1DClassifier(
            input_dim,
            num_classes,
            hidden=_cfg_int(cfg, "hidden", 128),
            depth=common_depth,
            kernel_size=_cfg_int(cfg, "kernel_size", 3),
            dropout=_cfg_float(cfg, "dropout", 0.15),
        )
    if name in {"lstm", "gru"}:
        return RNNClassifier(
            input_dim,
            num_classes,
            hidden=_cfg_int(cfg, "hidden", 128),
            depth=common_depth,
            dropout=_cfg_float(cfg, "dropout", 0.15),
            rnn_type=name,
            bidirectional=bool(cfg.get("bidirectional", False)),
            pooling=str(cfg.get("pooling", "last")),
        )
    if name == "transformer":
        return TrafficTransformer(
            input_dim,
            num_classes,
            dim=_cfg_int(cfg, "dim", 128),
            depth=common_depth,
            heads=_cfg_int(cfg, "heads", 4),
            mlp_ratio=_cfg_int(cfg, "mlp_ratio", 4),
            dropout=_cfg_float(cfg, "dropout", 0.1),
            max_len=_max_len(cfg, seq_len),
        )
    if name == "mamba":
        return MambaClassifier(
            input_dim,
            num_classes,
            dim=_cfg_int(cfg, "dim", 128),
            depth=common_depth,
            dropout=_cfg_float(cfg, "dropout", 0.1),
            d_state=_cfg_int(cfg, "d_state", 16),
            d_conv=_cfg_int(cfg, "d_conv", 4),
            expand=_cfg_int(cfg, "expand", 2),
            max_len=_max_len(cfg, seq_len),
            pooling=str(cfg.get("pooling", "mean")),
        )
    if name in TCNET_ALIASES:
        return PktTCNetAdapted(
            input_dim,
            num_classes,
            channels=_cfg_int(cfg, "channels", _cfg_int(cfg, "hidden", 128)),
            depth=common_depth,
            kernel_size=_cfg_int(cfg, "kernel_size", 3),
            dropout=_cfg_float(cfg, "dropout", 0.15),
            classifier_hidden=_cfg_int(cfg, "classifier_hidden", _cfg_int(cfg, "hidden", 128)),
        )
    if name in NETMAMBA_ALIASES:
        return NetMambaAdapted(
            input_dim,
            num_classes,
            dim=_cfg_int(cfg, "dim", 128),
            depth=common_depth,
            dropout=_cfg_float(cfg, "dropout", 0.15),
            d_state=_cfg_int(cfg, "d_state", 16),
            d_conv=_cfg_int(cfg, "d_conv", 4),
            expand=_cfg_int(cfg, "expand", 2),
            max_len=_max_len(cfg, seq_len),
            pooling=str(cfg.get("pooling", "mean")),
        )
    if name in HYBRID_ALIASES:
        lora = bool(cfg.get("lora", name == "hybrid_lora"))
        return HybridMMMLPAMLP(
            input_dim,
            num_classes,
            dim=_cfg_int(cfg, "dim", 128),
            layout=cfg.get("layout"),
            heads=_cfg_int(cfg, "heads", 4),
            mlp_ratio=_cfg_int(cfg, "mlp_ratio", 4),
            dropout=_cfg_float(cfg, "dropout", 0.1),
            d_state=_cfg_int(cfg, "d_state", 16),
            d_conv=_cfg_int(cfg, "d_conv", 4),
            expand=_cfg_int(cfg, "expand", 2),
            max_len=_max_len(cfg, seq_len),
            pooling=str(cfg.get("pooling", "mean")),
            lora=lora,
            r=_cfg_int(cfg, "r", 8),
            alpha=_cfg_int(cfg, "alpha", 16),
            freeze_backbone=bool(cfg.get("freeze_backbone", lora)),
            block_repeats=_cfg_int(cfg, "block_repeats", 1),
        )
    raise ValueError(f"Unknown model: {name}")
