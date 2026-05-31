from .cnn import CNN1DClassifier
from .adapted_sota import NetMambaAdapted, PktTCNetAdapted
from .hybrid_mm_mlp_a_mlp import HybridMMMLPAMLP
from .lstm import RNNClassifier
from .mamba_model import MambaClassifier
from .mlp import MLPClassifier
from .transformer import TrafficTransformer


def build_model(name: str, input_dim: int, num_classes: int, seq_len: int, cfg: dict):
    cfg = dict(cfg or {})
    name = name.lower().replace("-", "_")
    common_depth = int(cfg.get("depth", 5))
    if name == "mlp":
        return MLPClassifier(
            input_dim,
            num_classes,
            seq_len=seq_len,
            hidden=int(cfg.get("hidden", 128)),
            depth=common_depth,
            dropout=float(cfg.get("dropout", 0.2)),
        )
    if name == "cnn":
        return CNN1DClassifier(
            input_dim,
            num_classes,
            hidden=int(cfg.get("hidden", 128)),
            depth=common_depth,
            kernel_size=int(cfg.get("kernel_size", 3)),
            dropout=float(cfg.get("dropout", 0.15)),
        )
    if name in {"lstm", "gru"}:
        return RNNClassifier(
            input_dim,
            num_classes,
            hidden=int(cfg.get("hidden", 128)),
            depth=common_depth,
            dropout=float(cfg.get("dropout", 0.15)),
            rnn_type=name,
            bidirectional=bool(cfg.get("bidirectional", False)),
            pooling=str(cfg.get("pooling", "last")),
        )
    if name == "transformer":
        return TrafficTransformer(
            input_dim,
            num_classes,
            dim=int(cfg.get("dim", 128)),
            depth=common_depth,
            heads=int(cfg.get("heads", 4)),
            mlp_ratio=int(cfg.get("mlp_ratio", 4)),
            dropout=float(cfg.get("dropout", 0.1)),
            max_len=int(cfg.get("max_len", max(seq_len, 256))),
        )
    if name == "mamba":
        return MambaClassifier(
            input_dim,
            num_classes,
            dim=int(cfg.get("dim", 128)),
            depth=common_depth,
            dropout=float(cfg.get("dropout", 0.1)),
            d_state=int(cfg.get("d_state", 16)),
            d_conv=int(cfg.get("d_conv", 4)),
            expand=int(cfg.get("expand", 2)),
            max_len=int(cfg.get("max_len", max(seq_len, 256))),
            pooling=str(cfg.get("pooling", "mean")),
        )
    if name in {"30pkttcnet_adapted", "pkt_tcnet_adapted", "tcnet30pkt_adapted"}:
        return PktTCNetAdapted(
            input_dim,
            num_classes,
            channels=int(cfg.get("channels", cfg.get("hidden", 128))),
            depth=common_depth,
            kernel_size=int(cfg.get("kernel_size", 3)),
            dropout=float(cfg.get("dropout", 0.15)),
            classifier_hidden=int(cfg.get("classifier_hidden", cfg.get("hidden", 128))),
        )
    if name in {"netmamba_adapted", "net_mamba_adapted"}:
        return NetMambaAdapted(
            input_dim,
            num_classes,
            dim=int(cfg.get("dim", 128)),
            depth=common_depth,
            dropout=float(cfg.get("dropout", 0.15)),
            d_state=int(cfg.get("d_state", 16)),
            d_conv=int(cfg.get("d_conv", 4)),
            expand=int(cfg.get("expand", 2)),
            max_len=int(cfg.get("max_len", max(seq_len, 256))),
            pooling=str(cfg.get("pooling", "mean")),
        )
    if name in {"hybrid", "hybrid_lora"}:
        lora = bool(cfg.get("lora", name == "hybrid_lora"))
        return HybridMMMLPAMLP(
            input_dim,
            num_classes,
            dim=int(cfg.get("dim", 128)),
            layout=cfg.get("layout"),
            heads=int(cfg.get("heads", 4)),
            mlp_ratio=int(cfg.get("mlp_ratio", 4)),
            dropout=float(cfg.get("dropout", 0.1)),
            d_state=int(cfg.get("d_state", 16)),
            d_conv=int(cfg.get("d_conv", 4)),
            expand=int(cfg.get("expand", 2)),
            max_len=int(cfg.get("max_len", max(seq_len, 256))),
            pooling=str(cfg.get("pooling", "mean")),
            lora=lora,
            r=int(cfg.get("r", 8)),
            alpha=int(cfg.get("alpha", 16)),
            freeze_backbone=bool(cfg.get("freeze_backbone", lora)),
            block_repeats=int(cfg.get("block_repeats", 1)),
        )
    raise ValueError(f"Unknown model: {name}")
