from .adapted_sota import NetMambaAdapted, PktTCNetAdapted
from .gru import GRUClassifier
from .hsta import HSTA
from .recent_journal_baselines import BPFGNN, SRViT, TrafficAudio
from .transformer import TrafficTransformer


TCNET_ALIASES = {"30pkttcnet_adapted", "pkt_tcnet_adapted", "tcnet30pkt_adapted"}
NETMAMBA_ALIASES = {"netmamba_adapted", "net_mamba_adapted"}


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
    if name == "gru":
        return GRUClassifier(
            input_dim,
            num_classes,
            hidden=_cfg_int(cfg, "hidden", 128),
            depth=common_depth,
            dropout=_cfg_float(cfg, "dropout", 0.15),
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
    if name == "srvit":
        kernels = tuple(int(value) for value in cfg.get("patch_kernel_sizes", (3, 5, 7)))
        return SRViT(
            input_dim,
            num_classes,
            dim=_cfg_int(cfg, "dim", 128),
            depth=_cfg_int(cfg, "depth", 4),
            heads=_cfg_int(cfg, "heads", 4),
            mlp_ratio=_cfg_int(cfg, "mlp_ratio", 4),
            dropout=_cfg_float(cfg, "dropout", 0.15),
            max_len=_cfg_int(cfg, "max_len", seq_len),
            patch_kernel_sizes=kernels,
        )
    if name == "trafficaudio":
        return TrafficAudio(
            input_dim,
            num_classes,
            dim=_cfg_int(cfg, "dim", 128),
            dropout=_cfg_float(cfg, "dropout", 0.15),
            n_fft=_cfg_int(cfg, "n_fft", 16),
            win_length=_cfg_int(cfg, "win_length", 16),
            hop_length=_cfg_int(cfg, "hop_length", 4),
            n_mels=_cfg_int(cfg, "n_mels", 16),
            n_mfcc=_cfg_int(cfg, "n_mfcc", 8),
        )
    if name in {"bpf_gnn", "bpfgnn"}:
        return BPFGNN(
            input_dim,
            num_classes,
            dim=_cfg_int(cfg, "dim", 128),
            dropout=_cfg_float(cfg, "dropout", 0.15),
            top_k=_cfg_int(cfg, "top_k", 4),
            num_subflows=_cfg_int(cfg, "num_subflows", 5),
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
    if name in {"hsta", "hybrid"}:
        return HSTA(
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
            block_repeats=_cfg_int(cfg, "block_repeats", 1),
            attention_backend=str(cfg.get("attention_backend", "manual")),
        )
    raise ValueError(f"Unknown model: {name}")
